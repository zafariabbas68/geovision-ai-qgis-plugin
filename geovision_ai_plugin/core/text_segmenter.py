"""
Text-Prompted Segmentation — the WORKING version
This is the state BEFORE orthogonalization, NDVI, and batch processing.

Tested: box_threshold=0.12, mask-level dedup at 0.5 IoU
Result on parcel_test.tif: ~80 buildings
"""

import numpy as np
import cv2
from typing import List, Optional, Tuple
from dataclasses import dataclass


CLASS_PROFILES = {
    'building': {
        'prompts': ['building', 'house'],
        'box_threshold': 0.12,
        'text_threshold': 0.12,
        'min_area_m2': 15,
        'max_area_m2': 8000,
        'min_solidity': 0.40,
        'min_rectangularity': 0.35,
        'color_rule': None,
        'max_image_fraction': 0.30,
    },
    'tree': {
        'prompts': ['tree', 'vegetation'],
        'box_threshold': 0.15,
        'text_threshold': 0.15,
        'min_area_m2': 3,
        'max_area_m2': 400,
        'min_solidity': 0.35,
        'color_rule': 'green',
        'max_image_fraction': 0.10,
    },
    'road': {
        'prompts': ['asphalt road', 'street'],
        'box_threshold': 0.20,
        'text_threshold': 0.20,
        'min_area_m2': 30,
        'max_area_m2': 80000,
        'min_solidity': 0.25,
        'max_solidity': 0.85,
        'min_aspect_ratio': 0.05,
        'max_aspect_ratio': 0.60,
        'color_rule': 'gray',
        'max_green_ratio': 0.30,
        'max_image_fraction': 0.15,
        'max_bbox_fraction': 0.50,
    },
    'car': {
        'prompts': ['car', 'vehicle'],
        'box_threshold': 0.12,
        'text_threshold': 0.12,
        'min_area_m2': 2,
        'max_area_m2': 25,
        'color_rule': None,
        'max_image_fraction': 0.02,
    },
    'swimming pool': {
        'prompts': ['swimming pool', 'pool'],
        'box_threshold': 0.15,
        'text_threshold': 0.15,
        'min_area_m2': 8,
        'max_area_m2': 300,
        'color_rule': 'blue',
        'max_image_fraction': 0.05,
    },
}


@dataclass
class TextDetection:
    mask: np.ndarray
    bbox_px: Tuple[float, float, float, float]
    confidence: float
    phrase: str
    area_px: int = 0
    polygon_map: Optional[object] = None
    area_m2: float = 0.0
    perimeter_m: float = 0.0
    solidity: float = 0.0
    rectangularity: float = 0.0
    mean_rgb: Tuple[float, float, float] = (0, 0, 0)


def get_profile(text_prompt: str) -> dict:
    key = text_prompt.strip().lower()
    if key in CLASS_PROFILES:
        return CLASS_PROFILES[key]
    for k, v in CLASS_PROFILES.items():
        if k in key or key in k:
            return v
    return {
        'prompts': [text_prompt],
        'box_threshold': 0.15,
        'text_threshold': 0.15,
        'min_area_m2': 5,
        'max_area_m2': 10000,
        'color_rule': None,
    }


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _solidity(mask):
    cs, _ = cv2.findContours(
        np.ascontiguousarray(mask.astype(np.uint8)),
        cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return 0.0
    c = max(cs, key=cv2.contourArea)
    a = cv2.contourArea(c)
    ha = cv2.contourArea(cv2.convexHull(c))
    return float(a / ha) if ha > 0 else 0.0


def _rectangularity(mask):
    cs, _ = cv2.findContours(
        np.ascontiguousarray(mask.astype(np.uint8)),
        cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cs:
        return 0.0
    c = max(cs, key=cv2.contourArea)
    a = cv2.contourArea(c)
    rect = cv2.minAreaRect(c)
    w, h = rect[1]
    ra = w * h
    return float(a / ra) if ra > 0 else 0.0


def _mean_rgb(image, mask):
    if mask.sum() < 10:
        return (0.0, 0.0, 0.0)
    m = image[mask].mean(axis=0)
    return (float(m[0]), float(m[1]), float(m[2]))


def _check_color(rgb, rule):
    if rule is None:
        return True
    r, g, b = rgb
    if rule == 'green':
        return g > r + 5 and g > b + 5
    if rule == 'gray':
        # Roads: low saturation (grayish), moderate value
        mx, mn = max(r, g, b), min(r, g, b)
        s = (mx - mn) / mx if mx > 0 else 0
        v = mx
        # More permissive saturation (0.30)
        if s > 0.30:
            return False
        # Wider brightness range
        if v < 20 or v > 230:
            return False
        return True
    if rule == 'blue':
        return b > r + 8
    return True


def _green_ratio(image, mask):
    """Fraction of pixels in mask that are green-dominant"""
    if mask.sum() < 10:
        return 0.0
    pixels = image[mask]
    r = pixels[:, 0].astype(float)
    g = pixels[:, 1].astype(float)
    b = pixels[:, 2].astype(float)
    green = (g > r + 8) & (g > b + 8)
    return float(green.mean())


def _shape_aspect_ratio(bbox):
    """Return min(w,h)/max(w,h) for a bbox"""
    x1, y1, x2, y2 = bbox
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    if max(w, h) == 0:
        return 0.0
    return min(w, h) / max(w, h)


# ─────────────────────────────────────────────────────────────
# Segmenter — the working version
# ─────────────────────────────────────────────────────────────
class TextPromptedSegmenter:
    def __init__(self):
        self._lang_sam = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        print("🔄 Loading LangSAM...")
        from samgeo.text_sam import LangSAM
        self._lang_sam = LangSAM()
        self._loaded = True
        print("✅ LangSAM ready")

    def segment_image(
        self,
        image_rgb: np.ndarray,
        text_prompt: str,
        box_threshold: float = None,
        text_threshold: float = None,
        min_area_m2: float = None,
        max_area_m2: float = None,
        pixel_area_m2: float = 1.0,
        feedback=None,
    ) -> List[TextDetection]:
        from PIL import Image

        self._ensure_loaded()
        profile = get_profile(text_prompt)

        prompts = profile.get('prompts', [text_prompt])
        if box_threshold is None:
            box_threshold = profile.get('box_threshold', 0.15)
        if text_threshold is None:
            text_threshold = profile.get('text_threshold', 0.15)
        if min_area_m2 is None:
            min_area_m2 = profile.get('min_area_m2', 0)
        if max_area_m2 is None:
            max_area_m2 = profile.get('max_area_m2', 1e9)

        img_pil = Image.fromarray(image_rgb)
        all_raw = []

        # ── Stage 1+2: Multi-prompt DINO + SAM ──
        for prompt in prompts:
            try:
                print(f"\n[1] DINO  prompt='{prompt}'  box={box_threshold}")
                boxes, logits, phrases = self._lang_sam.predict_dino(
                    img_pil,
                    text_prompt=prompt,
                    box_threshold=box_threshold,
                    text_threshold=text_threshold,
                )
                print(f"    → {len(boxes)} candidates")
                if len(boxes) == 0:
                    continue

                print(f"[2] SAM   refining {len(boxes)}")
                masks = self._lang_sam.predict_sam(img_pil, boxes)

                for i in range(len(boxes)):
                    try:
                        m = masks[i]
                        mn = (m.cpu().numpy() if hasattr(m, 'cpu')
                              else np.asarray(m)).squeeze().astype(bool)
                        if mn.sum() < 20:
                            continue

                        bb = boxes[i]
                        bb = (bb.cpu().numpy() if hasattr(bb, 'cpu')
                              else np.asarray(bb)).flatten()
                        bbox = tuple(float(x) for x in bb[:4])

                        all_raw.append({
                            'mask': mn,
                            'bbox': bbox,
                            'score': float(logits[i]) if i < len(logits) else 0.0,
                            'phrase': phrases[i] if i < len(phrases) else prompt,
                        })
                    except Exception:
                        continue
            except Exception as e:
                print(f"    ⚠️  prompt '{prompt}' failed: {e}")
                continue

        print(f"\n[3] MERGE: {len(all_raw)} raw candidates from {len(prompts)} prompts")

        # ── Stage 3: Mask-level deduplication ──
        # Sort by score, keep highest, remove any mask that overlaps >0.5 IoU
        # with an already-kept mask. This is what gave us ~80 buildings.
        merged = self._dedupe_by_mask(all_raw, iou_threshold=0.7)

        # ── Stage 4: Validate ──
        detections = []
        rejected = {'small': 0, 'large': 0, 'shape': 0, 'color': 0}

        for raw in merged:
            mask = raw['mask']
            area_px = int(mask.sum())
            area_m2 = area_px * pixel_area_m2

            # Debug print
            print(f"    raw candidate: area_px={area_px}  area_m2={area_m2:.0f}  bbox={raw['bbox']}")

            if area_m2 < min_area_m2:
                rejected['small'] += 1
                print(f"      → REJECT small ({area_m2:.0f} < {min_area_m2})")
                continue
            if area_m2 > max_area_m2:
                rejected['large'] += 1
                print(f"      → REJECT large ({area_m2:.0f} > {max_area_m2})")
                continue

            sol = _solidity(mask)
            rect = _rectangularity(mask)
            rgb = _mean_rgb(image_rgb, mask)

            if 'min_solidity' in profile and sol < profile['min_solidity']:
                rejected['shape'] += 1
                continue
            if 'min_rectangularity' in profile and rect < profile['min_rectangularity']:
                rejected['shape'] += 1
                continue
            # ── Image-fraction check ──
            max_img_frac = profile.get('max_image_fraction', 0.9)
            img_total_px = image_rgb.shape[0] * image_rgb.shape[1]
            mask_frac = area_px / img_total_px if img_total_px > 0 else 0
            if mask_frac > max_img_frac:
                rejected['too_big'] = rejected.get('too_big', 0) + 1
                print(f"      → REJECT too_big ({mask_frac:.1%} > {max_img_frac:.0%})")
                continue

            # ── Bbox fraction check ──
            max_bbox_frac = profile.get('max_bbox_fraction', 0.95)
            bx1, by1, bx2, by2 = raw['bbox']
            if image_rgb.shape[1] > 0 and image_rgb.shape[0] > 0:
                bw_frac = abs(bx2 - bx1) / image_rgb.shape[1]
                bh_frac = abs(by2 - by1) / image_rgb.shape[0]
                if bw_frac > max_bbox_frac or bh_frac > max_bbox_frac:
                    rejected['too_wide'] = rejected.get('too_wide', 0) + 1
                    print(f"      → REJECT too_wide (w={bw_frac:.0%} h={bh_frac:.0%})")
                    continue

            if profile.get('color_rule') and not _check_color(rgb, profile['color_rule']):
                rejected['color'] += 1
                continue

            # Road-specific validation
            if text_prompt.strip().lower() in ('road', 'roads', 'street'):
                # Reject if too much green (fields, vegetation)
                gr = _green_ratio(image_rgb, mask)
                if gr > profile.get('max_green_ratio', 0.20):
                    rejected.setdefault('green', 0)
                    rejected['green'] += 1
                    continue

                # Reject if shape isn't elongated
                ar = _shape_aspect_ratio(raw['bbox'])
                min_ar = profile.get('min_aspect_ratio', 0.0)
                max_ar = profile.get('max_aspect_ratio', 1.0)
                if ar < min_ar or ar > max_ar:
                    rejected.setdefault('aspect', 0)
                    rejected['aspect'] += 1
                    continue

                # Reject if too solid (roads curve, fields are solid)
                max_sol = profile.get('max_solidity', 1.0)
                if sol > max_sol:
                    rejected.setdefault('road_shape', 0)
                    rejected['road_shape'] += 1
                    continue

            print(f"      → ACCEPTED: area={area_m2:.0f} m²  conf={raw['score']:.2f}")
            detections.append(TextDetection(
                mask=mask,
                bbox_px=raw['bbox'],
                confidence=raw['score'],
                phrase=raw['phrase'],
                area_px=area_px,
                solidity=sol,
                rectangularity=rect,
                mean_rgb=rgb,
                area_m2=area_m2,
            ))

        print(f"    rejected: {rejected}")
        print(f"[4] ✅ Final: {len(detections)} detections")

        if feedback:
            feedback.pushInfo(f"✅ {len(detections)} objects")

        return detections

    def _dedupe_by_mask(self, items, iou_threshold=0.5):
        """
        Remove duplicate detections by comparing actual masks.
        Keeps the one with higher confidence.
        """
        if len(items) < 2:
            return items

        items = sorted(items, key=lambda x: x['score'], reverse=True)
        kept = []
        used = [False] * len(items)

        for i, a in enumerate(items):
            if used[i]:
                continue
            kept.append(a)
            used[i] = True

            a_mask = a['mask']
            a_area = int(a_mask.sum())
            if a_area < 1:
                continue

            for j in range(i + 1, len(items)):
                if used[j]:
                    continue
                b = items[j]
                b_mask = b['mask']
                b_area = int(b_mask.sum())
                if b_area < 1:
                    used[j] = True
                    continue

                # Fast bbox pre-check
                ax1, ay1, ax2, ay2 = a['bbox']
                bx1, by1, bx2, by2 = b['bbox']
                if ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1:
                    continue

                inter = int(np.logical_and(a_mask, b_mask).sum())
                if inter == 0:
                    continue

                union = a_area + b_area - inter
                iou = inter / union if union > 0 else 0.0

                if iou > iou_threshold:
                    used[j] = True

        return kept
