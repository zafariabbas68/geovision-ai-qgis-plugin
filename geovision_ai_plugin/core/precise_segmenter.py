"""
Precise Building Segmentation using SAM
Tuned for high precision (not recall) — only well-formed, non-overlapping buildings
"""

import numpy as np
import cv2
import gc
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import traceback


@dataclass
class PreciseConfig:
    """Precision-tuned configuration"""
    # Tiling
    tile_size: int = 1024
    tile_overlap: int = 128

    # SAM parameters - HIGH precision
    points_per_side: int = 32
    pred_iou_thresh: float = 0.88       # ⬆ stricter
    stability_score_thresh: float = 0.95  # ⬆ stricter
    min_mask_area: int = 150             # ⬆ larger min
    box_nms_thresh: float = 0.65         # ⬇ tighter NMS

    # Object filtering - HIGH precision
    min_area_m2: float = 15.0            # ⬆ buildings are rarely < 25 m²
    max_area_m2: float = 8000.0
    min_solidity: float = 0.70           # ⬆ building-like convexity
    min_rectangularity: float = 0.65     # ⬆ building-like rectness

    # NEW: deduplication threshold
    dedup_iou: float = 0.35              # ⬇ aggressive dedup

    # Contour simplification
    simplify_epsilon_factor: float = 0.002


@dataclass
class BuildingInstance:
    mask: np.ndarray
    confidence: float
    bbox: Tuple[int, int, int, int]
    tile_offset: Tuple[int, int]
    contour: Optional[np.ndarray] = None
    area_m2: float = 0.0
    perimeter_m: float = 0.0
    solidity: float = 0.0
    rectangularity: float = 0.0


class PreciseSegmenter:
    """
    High-precision building segmentation
    Key differences from before:
    - Higher pred_iou + stability thresholds
    - Aggressive NMS + deduplication
    - Stricter shape filters (solidity > 0.78, rectness > 0.72)
    - Sort by area then keep only the largest per cluster
    """

    def __init__(self, model_predictor, config: Optional[PreciseConfig] = None):
        self.predictor = model_predictor
        self.config = config or PreciseConfig()
        self._transform = None
        self._crs = None
        self._class_name = "building"
        self._current_image = None

    def segment_image(self, image, transform, crs,
                     class_name="building", feedback=None) -> List[BuildingInstance]:
        self._transform = transform
        self._crs = crs
        self._class_name = class_name
        self._current_image = image

        h, w = image.shape[:2]
        print(f"🎯 Precise segmentation on {w}x{h} image")

        MAX_DIM = 2048
        if h > MAX_DIM or w > MAX_DIM:
            scale = MAX_DIM / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = new_h, new_w
            gt = transform['geo_transform']
            transform = dict(transform)
            transform['geo_transform'] = [
                gt[0], gt[1] / scale, gt[2],
                gt[3], gt[4], gt[5] / scale
            ]
            transform['width'] = new_w
            transform['height'] = new_h
            self._transform = transform

        image = self._enhance_contrast(image)

        tiles = list(self._generate_tiles(image))
        n_tiles = len(tiles)
        print(f"📦 {n_tiles} tiles")

        if feedback:
            feedback.pushInfo(f"Processing {n_tiles} tiles...")

        all_instances = []
        for idx, (tile, offset) in enumerate(tiles):
            if feedback:
                progress = int(5 + 70 * (idx / max(n_tiles, 1)))
                feedback.setProgress(progress)
                feedback.pushInfo(f"Tile {idx+1}/{n_tiles}")
            try:
                instances = self._process_tile(tile, offset)
                all_instances.extend(instances)
                print(f"  Tile {idx}: {len(instances)} candidates")
            except Exception as e:
                print(f"  Tile {idx} failed: {e}")

        print(f"🔍 Total raw candidates: {len(all_instances)}")

        # Step 1: NMS within tile (removes overlapping masks from SAM)
        nms_filtered = self._apply_nms(all_instances)
        print(f"🔍 After NMS: {len(nms_filtered)}")

        # Step 2: Cross-tile deduplication (keep largest & most confident)
        deduped = self._deduplicate(nms_filtered)
        print(f"🔍 After dedup: {len(deduped)}")

        # Step 3: Shape filters
        filtered = self._filter_objects(deduped)
        print(f"🔍 After filter: {len(filtered)}")

        # Step 4: Merge fragments of same building (spatial clustering)
        merged = self._merge_fragments(filtered)
        print(f"🔍 After merge: {len(merged)}")

        if feedback:
            feedback.setProgress(90)

        # Step 5: Orthogonalize
        final = []
        for inst in merged:
            refined = self._orthogonalize(inst)
            if refined is not None:
                final.append(refined)

        print(f"✅ Final: {len(final)} buildings")

        if feedback:
            feedback.setProgress(95)
            feedback.pushInfo(f"✅ {len(final)} buildings")

        gc.collect()
        return final

    def _enhance_contrast(self, image):
        try:
            lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
        except Exception:
            return image

    def _generate_tiles(self, image):
        h, w = image.shape[:2]
        ts = self.config.tile_size
        ov = self.config.tile_overlap
        step = ts - ov

        if h <= ts and w <= ts:
            yield image, (0, 0)
            return

        for y in range(0, max(h - ov, 1), step):
            for x in range(0, max(w - ov, 1), step):
                x2 = min(x + ts, w)
                y2 = min(y + ts, h)
                x1 = max(x2 - ts, 0)
                y1 = max(y2 - ts, 0)
                tile = image[y1:y2, x1:x2].copy()
                if tile.size > 0:
                    yield tile, (x1, y1)

    def _process_tile(self, tile, offset):
        from segment_anything import SamAutomaticMaskGenerator

        instances = []
        tile_bgr = cv2.cvtColor(tile, cv2.COLOR_RGB2BGR)
        self.predictor.set_image(tile_bgr)

        # Per-class SAM tuning
        pts = self.config.points_per_side
        min_area_px = self.config.min_mask_area
        pps = pts
        
        if self._class_name == 'car':
            pps = 64           # more points for small objects
            min_area_px = 40   # cars are small
        elif self._class_name in ('tree',):
            pps = 32
            min_area_px = 150
        elif self._class_name == 'road':
            pps = 16           # fewer points (large objects)
            min_area_px = 500  # roads are huge
        
        mask_gen = SamAutomaticMaskGenerator(
            model=self.predictor.model,
            points_per_side=pps,
            pred_iou_thresh=self.config.pred_iou_thresh,
            stability_score_thresh=self.config.stability_score_thresh,
            crop_n_layers=0,
            min_mask_region_area=min_area_px,
            box_nms_thresh=self.config.box_nms_thresh,
        )

        masks = mask_gen.generate(tile_bgr)

        for m in masks:
            mask = m['segmentation']
            area_px = int(np.sum(mask))
            if area_px < self.config.min_mask_area:
                continue

            ys, xs = np.where(mask)
            if len(ys) == 0:
                continue
            bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

            mask_uint8 = np.ascontiguousarray(mask.astype(np.uint8) * 255)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                continue
            contour = max(contours, key=cv2.contourArea)

            instances.append(BuildingInstance(
                mask=mask,
                confidence=float(m.get('predicted_iou', 0.5)),
                bbox=bbox,
                tile_offset=offset,
                contour=contour
            ))

        return instances

    def _apply_nms(self, instances):
        """Non-maximum suppression to remove overlapping masks"""
        if len(instances) < 2:
            return instances

        # Sort by confidence (highest first)
        sorted_inst = sorted(instances, key=lambda x: x.confidence, reverse=True)
        kept = []

        for inst in sorted_inst:
            duplicate = False
            for k in kept:
                # Same tile → compare masks directly
                if inst.tile_offset == k.tile_offset:
                    # Compute mask IoU
                    inter = np.logical_and(inst.mask, k.mask).sum()
                    union = np.logical_or(inst.mask, k.mask).sum()
                    iou = inter / union if union > 0 else 0
                    if iou > 0.5:
                        duplicate = True
                        break
                else:
                    # Different tiles → use global bbox IoU
                    g1 = inst.tile_offset
                    g2 = k.tile_offset
                    b1 = (inst.bbox[0]+g1[0], inst.bbox[1]+g1[1], inst.bbox[2]+g1[0], inst.bbox[3]+g1[1])
                    b2 = (k.bbox[0]+g2[0], k.bbox[1]+g2[1], k.bbox[2]+g2[0], k.bbox[3]+g2[1])
                    x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
                    x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
                    if x2 > x1 and y2 > y1:
                        inter = (x2-x1) * (y2-y1)
                        a1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
                        a2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
                        union = a1 + a2 - inter
                        iou = inter / union if union > 0 else 0
                        if iou > self.config.dedup_iou:
                            duplicate = True
                            break
            if not duplicate:
                kept.append(inst)

        return kept

    def _deduplicate(self, instances):
        """Cross-tile deduplication by bbox IoU"""
        if len(instances) < 2:
            return instances

        sorted_inst = sorted(instances, key=lambda x: x.confidence, reverse=True)
        kept = []

        for inst in sorted_inst:
            duplicate = False
            for k in kept:
                g1 = inst.tile_offset
                g2 = k.tile_offset
                b1 = (inst.bbox[0]+g1[0], inst.bbox[1]+g1[1], inst.bbox[2]+g1[0], inst.bbox[3]+g1[1])
                b2 = (k.bbox[0]+g2[0], k.bbox[1]+g2[1], k.bbox[2]+g2[0], k.bbox[3]+g2[1])
                x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
                x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
                if x2 > x1 and y2 > y1:
                    inter = (x2-x1) * (y2-y1)
                    a1 = (b1[2]-b1[0]) * (b1[3]-b1[1])
                    a2 = (b2[2]-b2[0]) * (b2[3]-b2[1])
                    union = a1 + a2 - inter
                    iou = inter / union if union > 0 else 0
                    if iou > self.config.dedup_iou:
                        duplicate = True
                        break
            if not duplicate:
                kept.append(inst)

        return kept

    def _filter_objects(self, instances):
        """Filter using shape metrics + class-aware heuristics"""
        from .class_filters import get_filter
        
        filtered = []
        gt = self._transform['geo_transform']
        px_area_m2 = abs(gt[1] * gt[5])
        
        # Get class filter
        cf = get_filter(self._class_name)
        
        # Get the image (for color analysis)
        img = self._current_image
        rejected_color = 0
        
        for inst in instances:
            area_px = np.sum(inst.mask)
            area_m2 = area_px * px_area_m2
            if area_m2 < self.config.min_area_m2:
                continue
            if area_m2 > self.config.max_area_m2:
                continue

            solidity = self._compute_solidity(inst.mask)
            rectangularity = self._compute_rectangularity(inst.contour)
            
            # Basic shape thresholds from config
            if solidity < self.config.min_solidity:
                continue
            if rectangularity < self.config.min_rectangularity:
                continue
            
            # CLASS-AWARE filter (color + shape) using bbox-local data
            if img is not None:
                # Get the mean color from the mask INSIDE the tile
                # The mask is tile-local, and we know the tile offset
                ox, oy = inst.tile_offset
                mh, mw = inst.mask.shape
                
                # Clip to image bounds
                ih, iw = img.shape[:2]
                y_end = min(oy + mh, ih)
                x_end = min(ox + mw, iw)
                if y_end <= oy or x_end <= ox:
                    continue
                
                # Extract the tile region and matching mask
                tile_region = img[oy:y_end, ox:x_end]
                mask_region = inst.mask[:y_end-oy, :x_end-ox]
                
                # Skip if mask region doesn't match
                if mask_region.shape != tile_region.shape[:2]:
                    # Shape mismatch — try to resize or use bbox extraction
                    ys, xs = np.where(inst.mask)
                    if len(ys) == 0:
                        continue
                    y1, y2 = max(0, int(ys.min())), min(mh, int(ys.max())+1)
                    x1, x2 = max(0, int(xs.min())), min(mw, int(xs.max())+1)
                    # Use the tile crop
                    tile_crop = img[oy+y1:min(oy+y2, ih), ox+x1:min(ox+x2, iw)]
                    if tile_crop.size == 0:
                        continue
                    # Mean color of bbox
                    mean_rgb = tile_crop.reshape(-1, 3).mean(axis=0)
                else:
                    # Standard path — use mask
                    pixels = tile_region[mask_region]
                    if len(pixels) == 0:
                        continue
                    mean_rgb = pixels.mean(axis=0)
                
                # Call filter with mean color
                cls_score = cf.match_mean_color(
                    mean_rgb,
                    solidity,
                    rectangularity
                )
                if cls_score < 0.4:
                    rejected_color += 1
                    continue
            
            inst.area_m2 = area_m2
            inst.solidity = solidity
            inst.rectangularity = rectangularity
            filtered.append(inst)
        
        if rejected_color > 0:
            print(f"   Rejected {rejected_color} by class filter ({self._class_name})")

        return filtered

    def _merge_fragments(self, instances):
        """Merge instances whose bboxes heavily overlap or are adjacent"""
        if len(instances) < 2:
            return instances

        # Sort by area descending (keep larger as primary)
        sorted_inst = sorted(instances, key=lambda x: x.area_m2, reverse=True)
        kept = []
        used = set()

        for i, inst in enumerate(sorted_inst):
            if i in used:
                continue
            # Check if any later instance overlaps heavily
            for j in range(i+1, len(sorted_inst)):
                if j in used:
                    continue
                other = sorted_inst[j]
                # Global bbox
                g1 = inst.tile_offset
                g2 = other.tile_offset
                b1 = (inst.bbox[0]+g1[0], inst.bbox[1]+g1[1], inst.bbox[2]+g1[0], inst.bbox[3]+g1[1])
                b2 = (other.bbox[0]+g2[0], other.bbox[1]+g2[1], other.bbox[2]+g2[0], other.bbox[3]+g2[1])
                x1 = max(b1[0], b2[0]); y1 = max(b1[1], b2[1])
                x2 = min(b1[2], b2[2]); y2 = min(b1[3], b2[3])
                if x2 > x1 and y2 > y1:
                    inter = (x2-x1) * (y2-y1)
                    smaller_area = min((b1[2]-b1[0])*(b1[3]-b1[1]), (b2[2]-b2[0])*(b2[3]-b2[1]))
                    if smaller_area > 0 and inter / smaller_area > 0.6:
                        # Fragment — mark as used (drop it)
                        used.add(j)
            kept.append(inst)

        return kept

    def _compute_solidity(self, mask):
        try:
            mask_uint8 = np.ascontiguousarray(mask.astype(np.uint8) * 255)
            contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return 0.0
            c = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(c)
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            return area / hull_area if hull_area > 0 else 0.0
        except Exception:
            return 0.0

    def _compute_rectangularity(self, contour):
        try:
            area = cv2.contourArea(contour)
            rect = cv2.minAreaRect(contour)
            w, h = rect[1]
            rect_area = w * h
            return area / rect_area if rect_area > 0 else 0.0
        except Exception:
            return 0.0

    def _orthogonalize(self, inst):
        """Snap to right angles for buildings"""
        try:
            contour = inst.contour
            if len(contour) < 4:
                return inst

            peri = cv2.arcLength(contour, True)
            epsilon = self.config.simplify_epsilon_factor * peri
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) < 4:
                return inst

            # Use rectangle if it fits well
            if inst.rectangularity > 0.80:
                rect = cv2.minAreaRect(contour)
                box = np.int32(cv2.boxPoints(rect))
                inst.contour = box.reshape(-1, 1, 2)
            else:
                inst.contour = approx

            new_mask = np.zeros_like(inst.mask, dtype=np.uint8)
            cv2.drawContours(new_mask, [inst.contour], -1, 1, -1)
            inst.mask = new_mask.astype(bool)
            return inst
        except Exception as e:
            print(f"Orthogonalize failed: {e}")
            return inst
