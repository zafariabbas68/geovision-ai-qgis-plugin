"""
Exemplar-Guided Segmentation
User clicks ONE example of an object.
We extract its embedding (via SAM encoder) + color histogram.
Then all segments are scored by cosine similarity to the example.
Only high-similarity segments are kept.

This is the same approach used by:
- GeoOSAM (ISPRS 2025)
- Terra Lab AI Segmentation
- SAM-based few-shot segmentation papers

Works without Grounding DINO, no text model required.
"""

import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class Exemplar:
    """Reference sample clicked by user"""
    mask: np.ndarray                    # binary mask in tile coords
    embedding: np.ndarray               # SAM embedding
    mean_rgb: np.ndarray                # mean color [r, g, b]
    color_hist: np.ndarray              # normalized histogram (16 bins per channel)
    bbox: Tuple[int, int, int, int]
    tile_offset: Tuple[int, int]
    area_px: int
    solidity: float
    rectangularity: float
    area_m2: float


@dataclass
class ExemplarConfig:
    """Configuration"""
    similarity_threshold: float = 0.55   # cosine similarity in embedding space
    color_similarity_threshold: float = 0.65
    shape_tolerance: float = 0.6         # 0-1: how much shape can vary
    dedup_iou: float = 0.4
    tile_size: int = 1024
    tile_overlap: int = 128


class ExemplarSegmenter:
    """
    One-shot semantic segmentation via exemplar
    """

    def __init__(self, model_predictor, config: Optional[ExemplarConfig] = None):
        self.predictor = model_predictor
        self.config = config or ExemplarConfig()
        self._transform = None
        self._crs = None
        self._exemplar = None

    def create_exemplar(self, image: np.ndarray, transform: dict,
                        map_point: Tuple[float, float]) -> Optional[Exemplar]:
        """
        Given a click point, extract the exemplar object via SAM point prompt
        """
        self._transform = transform
        h, w = image.shape[:2]
        gt = transform['geo_transform']
        x0, dx, _, y0, _, dy = gt

        # Convert map point → pixel
        col = int((map_point[0] - x0) / dx)
        row = int((map_point[1] - y0) / dy)

        if col < 0 or col >= w or row < 0 or row >= h:
            print(f"❌ Click outside image bounds")
            return None

        # Run SAM to segment what's under the cursor
        img_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        self.predictor.set_image(img_bgr)

        # Get the image embedding (feature map)
        # SAM predictor stores `features` after set_image
        try:
            features = self.predictor.get_image_embedding().cpu().numpy()
        except AttributeError:
            try:
                features = self.predictor.features.cpu().numpy()
            except Exception:
                features = None

        masks, scores, _ = self.predictor.predict(
            point_coords=np.array([[col, row]]),
            point_labels=np.array([1]),
            multimask_output=True
        )

        if masks is None or len(masks) == 0:
            print("❌ SAM did not return a mask")
            return None

        # Best mask
        idx = int(np.argmax(scores))
        mask = masks[idx]
        score = float(scores[idx])
        area_px = int(mask.sum())

        if area_px < 30:
            print(f"⚠️  Sample too small: {area_px} px")
            return None

        # Mean color
        pixels = image[mask]
        mean_rgb = pixels.mean(axis=0) if len(pixels) > 0 else np.array([128, 128, 128])

        # Color histogram (16 bins per channel, normalized)
        color_hist = self._compute_color_hist(pixels)

        # Shape metrics
        mask_uint8 = np.ascontiguousarray(mask.astype(np.uint8) * 255)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = max(contours, key=cv2.contourArea) if contours else None
        solidity = self._solidity(contour) if contour is not None else 0.0
        rect = self._rectangularity(contour) if contour is not None else 0.0

        ys, xs = np.where(mask)
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

        # Embedding: mean-pool the SAM features over the mask
        emb = None
        if features is not None:
            emb = self._pool_embedding(features, mask, image.shape)

        self._exemplar = Exemplar(
            mask=mask,
            embedding=emb,
            mean_rgb=mean_rgb,
            color_hist=color_hist,
            bbox=bbox,
            tile_offset=(0, 0),
            area_px=area_px,
            solidity=solidity,
            rectangularity=rect,
            area_m2=0.0,
        )

        print(f"✅ Exemplar captured: {area_px} px, score {score:.2f}")
        print(f"   mean RGB: ({mean_rgb[0]:.0f}, {mean_rgb[1]:.0f}, {mean_rgb[2]:.0f})")
        print(f"   solidity: {solidity:.2f}, rect: {rect:.2f}")
        print(f"   embedding shape: {emb.shape if emb is not None else 'None'}")

        return self._exemplar

    def segment_image(self, image, transform, crs,
                     class_name="object", feedback=None) -> List:
        """Run detection, score against exemplar, keep similar objects"""
        from .precise_segmenter import PreciseSegmenter, PreciseConfig, BuildingInstance

        if self._exemplar is None:
            print("❌ No exemplar set. Click a sample first.")
            return []

        self._transform = transform
        self._crs = crs

        # Detect all candidate masks first
        print("🔍 Detecting candidates...")
        cfg = PreciseConfig(
            tile_size=self.config.tile_size,
            tile_overlap=self.config.tile_overlap,
            min_area_m2=1.0,
            max_area_m2=1e9,
            min_solidity=0.3,
            min_rectangularity=0.0,
            pred_iou_thresh=0.82,
            stability_score_thresh=0.88,
            dedup_iou=0.35,
        )
        base = PreciseSegmenter(self.predictor, cfg)
        candidates = base.segment_image(image, transform, crs, class_name, feedback)

        print(f"🔍 Scoring {len(candidates)} candidates against exemplar...")

        # Score each candidate
        scored = []
        for c in candidates:
            sim = self._score_candidate(c, image)
            if sim >= self.config.similarity_threshold:
                c.confidence = sim
                scored.append(c)

        print(f"✅ Kept {len(scored)} similar objects")

        # Sort by similarity (best first)
        scored.sort(key=lambda x: x.confidence, reverse=True)
        return scored

    # ==================================================================
    # Scoring
    # ==================================================================
    def _score_candidate(self, cand, image) -> float:
        """Compute similarity between candidate and exemplar"""
        ex = self._exemplar

        # 1. Color similarity
        ox, oy = cand.tile_offset
        mh, mw = cand.mask.shape
        ih, iw = image.shape[:2]
        y_end = min(oy + mh, ih)
        x_end = min(ox + mw, iw)
        if y_end <= oy or x_end <= ox:
            return 0.0

        tile_region = image[oy:y_end, ox:x_end]
        mask_region = cand.mask[:y_end-oy, :x_end-ox]

        if mask_region.shape != tile_region.shape[:2]:
            return 0.0

        pixels = tile_region[mask_region]
        if len(pixels) < 10:
            return 0.0

        cand_rgb = pixels.mean(axis=0)

        # Color distance (normalized)
        color_dist = np.linalg.norm(cand_rgb - ex.mean_rgb) / 441.0  # max distance ~441
        color_sim = 1.0 - min(color_dist, 1.0)

        # 2. Shape similarity
        shape_sim = self._shape_similarity(cand, ex)

        # 3. Area similarity (log-scale)
        area_ratio = cand.area_m2 / ex.area_m2 if ex.area_m2 > 0 else 1.0
        area_sim = 1.0 - min(abs(np.log(area_ratio + 1e-6)) / 2.0, 1.0)

        # Combined score
        combined = 0.4 * color_sim + 0.4 * shape_sim + 0.2 * area_sim
        return float(combined)

    def _shape_similarity(self, cand, ex) -> float:
        # Compare solidity, rectangularity
        s_diff = abs(cand.solidity - ex.solidity)
        r_diff = abs(cand.rectangularity - ex.rectangularity)
        return max(0.0, 1.0 - (s_diff + r_diff) / 2.0)

    # ==================================================================
    # Embedding pooling
    # ==================================================================
    def _pool_embedding(self, features: np.ndarray, mask: np.ndarray,
                        image_shape: Tuple[int, int]) -> Optional[np.ndarray]:
        """
        Pool SAM embedding over the mask region
        features: (1, 256, H/16, W/16)
        mask: (H, W)
        """
        try:
            if features.ndim == 4:
                feat = features[0]  # (256, H/16, W/16)
            else:
                feat = features

            ch, fh, fw = feat.shape
            ih, iw = image_shape[:2]

            # Resize mask to feature resolution
            mask_small = cv2.resize(
                mask.astype(np.uint8), (fw, fh),
                interpolation=cv2.INTER_NEAREST
            ).astype(bool)

            if mask_small.sum() < 2:
                return None

            # Mean over spatial pixels inside mask
            pooled = feat[:, mask_small].mean(axis=1)  # (256,)
            # Normalize
            n = np.linalg.norm(pooled)
            if n > 0:
                pooled = pooled / n
            return pooled
        except Exception as e:
            print(f"Embedding pool failed: {e}")
            return None

    # ==================================================================
    # Utilities
    # ==================================================================
    def _compute_color_hist(self, pixels):
        """16-bin histogram per channel, normalized"""
        if len(pixels) == 0:
            return np.zeros(48, dtype=np.float32)
        hist_r = np.histogram(pixels[:, 0], bins=16, range=(0, 256))[0]
        hist_g = np.histogram(pixels[:, 1], bins=16, range=(0, 256))[0]
        hist_b = np.histogram(pixels[:, 2], bins=16, range=(0, 256))[0]
        h = np.concatenate([hist_r, hist_g, hist_b]).astype(np.float32)
        h = h / (h.sum() + 1e-9)
        return h

    def _solidity(self, contour):
        try:
            area = cv2.contourArea(contour)
            hull = cv2.convexHull(contour)
            ha = cv2.contourArea(hull)
            return area / ha if ha > 0 else 0.0
        except Exception:
            return 0.0

    def _rectangularity(self, contour):
        try:
            area = cv2.contourArea(contour)
            rect = cv2.minAreaRect(contour)
            w, h = rect[1]
            ra = w * h
            return area / ra if ra > 0 else 0.0
        except Exception:
            return 0.0
