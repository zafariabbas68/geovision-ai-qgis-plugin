"""
Instance Segmentation Engine - OPTIMIZED FOR SPEED
Reduced points, no crops, larger tiles, better parallelization
"""

import numpy as np
import cv2
from typing import List, Tuple, Dict, Optional, Iterator
from dataclasses import dataclass
import logging
import traceback

logger = logging.getLogger(__name__)


def _safe_draw_contours(image, contours, color=1, thickness=-1):
    """
    Draw contours with full OpenCV 4.5-4.11 compatibility.
    Ensures the destination array is contiguous uint8.
    """
    if image is None or len(contours) == 0:
        return image
    # Ensure contiguous
    if not image.flags['C_CONTIGUOUS']:
        image = np.ascontiguousarray(image)
    if image.dtype != np.uint8:
        image = image.astype(np.uint8)
    # Final contiguity check
    image = np.ascontiguousarray(image)

    try:
        cv2.drawContours(image, contours, -1, int(color), int(thickness))
    except cv2.error as e:
        print(f"⚠️  drawContours failed: {e}")
    return image



@dataclass
class SegmentationConfig:
    """Configuration - tuned for CPU speed"""
    # SPEED-OPTIMIZED defaults
    tile_size: int = 768          # Was 512 - larger tile = fewer tiles
    tile_overlap: int = 32        # Was 64 - smaller overlap = faster
    merge_iou_threshold: float = 0.4

    min_object_area_px: int = 30  # Was 50 - keep small buildings
    max_object_area_px: int = 50000
    min_object_area_m2: float = 1.0
    max_object_area_m2: float = 100000.0

    simplify_tolerance: float = 0.3
    smooth_contours: bool = True
    rectangularize: bool = True

    use_watershed: bool = True
    watershed_min_distance: int = 15
    morphological_erosion: int = 1

    confidence_threshold: float = 0.4

    # ⚡ SAM speed parameters - THE KEY FIX
    sam_points_per_side: int = 16   # Was 32 - 4× fewer points
    sam_crop_n_layers: int = 0      # Was 1 - no crops = 2× faster
    sam_min_mask_area: int = 50


@dataclass
class DetectedObject:
    mask: np.ndarray
    confidence: float
    bbox: Tuple[int, int, int, int]
    tile_offset: Tuple[int, int]
    geometry: Optional[object] = None
    area_m2: float = 0.0
    perimeter_m: float = 0.0

    @property
    def global_bbox(self) -> Tuple[int, int, int, int]:
        x1, y1, x2, y2 = self.bbox
        ox, oy = self.tile_offset
        return (x1 + ox, y1 + oy, x2 + ox, y2 + oy)


class InstanceSegmenter:
    """SPEED-OPTIMIZED instance segmentation"""

    def __init__(self, model_predictor, config: SegmentationConfig = None):
        self.predictor = model_predictor
        self.config = config or SegmentationConfig()
        self.use_opencv = self._check_opencv()
        self._transform = None
        self._crs = None

    def _check_opencv(self) -> bool:
        try:
            import cv2
            return True
        except ImportError:
            return False

    def segment_image(self,
                     image: np.ndarray,
                     transform: Dict,
                     crs,
                     class_name: str = "objects",
                     feedback=None) -> List[DetectedObject]:
        """Main segmentation - optimized"""
        self._transform = transform
        self._crs = crs

        h, w = image.shape[:2]
        logger.info(f"Segmenting {w}x{h} image")

        # ⚡ CRITICAL: Downscale large images BEFORE tile processing
        MAX_DIM = 1024  # Never process more than 1024×1024 total
        if h > MAX_DIM or w > MAX_DIM:
            scale = MAX_DIM / max(h, w)
            new_h, new_w = int(h * scale), int(w * scale)
            logger.info(f"Downscaling to {new_w}x{new_h} for speed")
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            h, w = new_h, new_w
            # Update transform scale
            old_gt = transform['geo_transform']
            transform = dict(transform)
            transform['geo_transform'] = [
                old_gt[0], old_gt[1] / scale, old_gt[2],
                old_gt[3], old_gt[4], old_gt[5] / scale
            ]
            transform['width'] = new_w
            transform['height'] = new_h

        # Generate tiles
        tiles = list(self._generate_tiles(image))
        n_tiles = len(tiles)
        logger.info(f"Generated {n_tiles} tiles")

        if feedback:
            feedback.pushInfo(f"📦 {n_tiles} tiles (this will take a few minutes)")

        all_detections = []
        for idx, (tile, offset) in enumerate(tiles):
            if feedback:
                progress = int(10 + 70 * (idx / max(n_tiles, 1)))
                feedback.setProgress(progress)
                feedback.pushInfo(f"Tile {idx+1}/{n_tiles} ({offset[0]}, {offset[1]})")

            try:
                tile_dets = self._process_tile_fast(tile, offset)
                all_detections.extend(tile_dets)
                logger.info(f"Tile {idx}: {len(tile_dets)} objects")
            except Exception as e:
                logger.error(f"Tile {idx} failed: {e}")

        logger.info(f"Raw detections: {len(all_detections)}")

        if feedback:
            feedback.setProgress(85)
            feedback.pushInfo(f"Filtering {len(all_detections)} raw objects...")

        # Post-process: merge, separate, refine
        merged = self._merge_cross_tile_detections(all_detections)

        separated = []
        for det in merged:
            separated.extend(self._separate_instances(det))

        refined = [self._refine_geometry(d) for d in separated]
        refined = [d for d in refined if d is not None]

        if feedback:
            feedback.setProgress(90)
            feedback.pushInfo(f"✅ Final: {len(refined)} objects")

        return refined

    def _generate_tiles(self, image: np.ndarray) -> Iterator[Tuple[np.ndarray, Tuple[int, int]]]:
        """Generate tiles - larger tiles = fewer iterations"""
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

    def _process_tile_fast(self, tile: np.ndarray, offset: Tuple[int, int]) -> List[DetectedObject]:
        """
        SPEED-OPTIMIZED tile processing
        Uses SamAutomaticMaskGenerator with minimal parameters
        """
        detections = []

        try:
            from segment_anything import SamAutomaticMaskGenerator

            # Convert RGB → BGR
            if self.use_opencv:
                tile_bgr = cv2.cvtColor(tile, cv2.COLOR_RGB2BGR)
            else:
                tile_bgr = tile[:, :, ::-1]

            # Set image in predictor
            self.predictor.set_image(tile_bgr)

            # ⚡ CRITICAL: Use minimal SAM parameters
            mask_gen = SamAutomaticMaskGenerator(
                model=self.predictor.model,
                points_per_side=self.config.sam_points_per_side,   # 16 (was 32)
                pred_iou_thresh=self.config.confidence_threshold,
                stability_score_thresh=0.85,
                crop_n_layers=self.config.sam_crop_n_layers,        # 0 (was 1)
                crop_n_points_downscale_factor=2,
                min_mask_region_area=self.config.sam_min_mask_area,
                box_nms_thresh=0.7,
            )

            masks_data = mask_gen.generate(tile_bgr)

            for md in masks_data:
                mask = md['segmentation']
                area_px = np.sum(mask)

                if area_px < self.config.min_object_area_px:
                    continue
                if area_px > self.config.max_object_area_px:
                    continue

                ys, xs = np.where(mask)
                if len(ys) == 0:
                    continue
                bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

                detections.append(DetectedObject(
                    mask=mask,
                    confidence=float(md.get('predicted_iou', 0.5)),
                    bbox=bbox,
                    tile_offset=offset
                ))

        except Exception as e:
            logger.error(f"Tile processing: {e}\n{traceback.format_exc()}")

        return detections

    def _merge_cross_tile_detections(self, detections: List[DetectedObject]) -> List[DetectedObject]:
        if len(detections) < 2:
            return detections
        merged, used = [], set()
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
        for i, di in enumerate(sorted_dets):
            if i in used:
                continue
            group = [di]
            used.add(i)
            for j, dj in enumerate(sorted_dets[i+1:], start=i+1):
                if j in used:
                    continue
                if self._iou(di, dj) > self.config.merge_iou_threshold:
                    group.append(dj)
                    used.add(j)
            merged.append(max(group, key=lambda d: d.confidence))
        return merged

    def _iou(self, d1, d2) -> float:
        b1, b2 = d1.global_bbox, d2.global_bbox
        x1, y1 = max(b1[0], b2[0]), max(b1[1], b2[1])
        x2, y2 = min(b1[2], b2[2]), min(b1[3], b2[3])
        if x2 <= x1 or y2 <= y1:
            return 0.0
        inter = (x2 - x1) * (y2 - y1)
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union = a1 + a2 - inter
        return inter / union if union > 0 else 0.0

    def _separate_instances(self, det: DetectedObject) -> List[DetectedObject]:
        if not self.config.use_watershed or not self.use_opencv:
            return [det]
        mask = det.mask.astype(np.uint8)
        if self.config.morphological_erosion > 0:
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            eroded = cv2.erode(mask, k, iterations=1)
        else:
            eroded = mask
        dist = cv2.distanceTransform(eroded, cv2.DIST_L2, 5)
        ks = self.config.watershed_min_distance * 2 + 1
        dilated = cv2.dilate(dist, np.ones((ks, ks), np.uint8))
        peaks = ((dist == dilated) & (dist > self.config.watershed_min_distance)).astype(np.uint8)
        n_seeds, seeds = cv2.connectedComponents(peaks)
        if n_seeds <= 2:
            return [det]
        markers = seeds.astype(np.int32)
        markers[eroded == 0] = 0
        mask3 = np.ascontiguousarray(cv2.cvtColor(mask * 255, cv2.COLOR_GRAY2BGR))
        markers = np.ascontiguousarray(markers.astype(np.int32))
        markers = cv2.watershed(mask3, markers)
        instances = []
        for label in range(2, n_seeds):
            im = (markers == label).astype(bool)
            if np.sum(im) < self.config.min_object_area_px:
                continue
            ys, xs = np.where(im)
            instances.append(DetectedObject(
                mask=im,
                confidence=det.confidence * 0.95,
                bbox=(int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
                tile_offset=det.tile_offset
            ))
        return instances if instances else [det]

    def _refine_geometry(self, det: DetectedObject) -> Optional[DetectedObject]:
        if not self.use_opencv:
            return det
        try:
            # Force contiguous uint8 array (OpenCV 4.11 strictness)
            m = np.ascontiguousarray(det.mask.astype(np.uint8) * 255)
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
            m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
            m = np.ascontiguousarray(m)

            contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return det
            c = max(contours, key=cv2.contourArea)
            if self.config.smooth_contours:
                eps = 0.003 * cv2.arcLength(c, True)
                c = cv2.approxPolyDP(c, eps, True)
            if self.config.rectangularize:
                c = self._rectangularize(c)

            # Ensure output array is contiguous and correctly typed
            new_mask = np.zeros(det.mask.shape, dtype=np.uint8)
            new_mask = np.ascontiguousarray(new_mask)
            new_mask = _safe_draw_contours(new_mask, [c], 1, -1)
            det.mask = new_mask.astype(bool)
            return det
        except Exception as e:
            logger.warning(f"Refine failed, keeping original: {e}")
            return det

    def _rectangularize(self, contour):
        rect = cv2.minAreaRect(contour)
        box = np.int32(cv2.boxPoints(rect))
        orig = cv2.contourArea(contour)
        rect_a = cv2.contourArea(box)
        if rect_a > 0 and orig / rect_a > 0.85:
            return box.reshape(-1, 1, 2)
        return contour


class ObjectProjector:
    """Pixel → map projection"""

    def __init__(self, transform: Dict, crs):
        self.geo_transform = transform['geo_transform']
        self.crs = crs
        self.width = transform['width']
        self.height = transform['height']

    def project_detection(self, det: DetectedObject, class_name: str):
        from qgis.core import QgsGeometry, QgsPointXY
        mask_full = self._place_in_global(det)
        try:
            m = np.ascontiguousarray(mask_full.astype(np.uint8) * 255)
            contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except ImportError:
            return None
        if not contours:
            return None
        c = max(contours, key=cv2.contourArea)
        if len(c) < 3:
            return None
        pts = []
        for p in c:
            col, row = p[0]
            x, y = self._px_to_map(col, row)
            pts.append(QgsPointXY(x, y))
        try:
            geom = QgsGeometry.fromPolygonXY([pts])
        except Exception:
            return None
        if not geom.isGeosValid():
            geom = geom.buffer(0, 5)
            if not geom.isGeosValid():
                return None
        return {
            'geometry': geom,
            'area_m2': geom.area(),
            'perimeter_m': geom.length(),
            'confidence': det.confidence
        }

    def _place_in_global(self, det):
        full = np.zeros((self.height, self.width), dtype=bool)
        ox, oy = det.tile_offset
        h, w = det.mask.shape
        ye, xe = min(oy+h, self.height), min(ox+w, self.width)
        hc, wc = ye-oy, xe-ox
        if hc > 0 and wc > 0:
            full[oy:ye, ox:xe] = det.mask[:hc, :wc]
        return full

    def _px_to_map(self, col, row):
        x0, dx, _, y0, _, dy = self.geo_transform
        return x0 + col*dx, y0 + row*dy
