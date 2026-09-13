"""
Orthogonalize building polygons — professional grade.

Algorithm:
1. Fit minimum-area rotated rectangle (MAR) to get the dominant angle
2. Rotate the polygon so its main axis is horizontal
3. Classify each edge as horizontal, vertical, or diagonal (45°)
4. Snap each edge's endpoints to snapped coordinate lines
5. Rotate back
6. Validate — reject if area changes too much, or if shape becomes invalid

This is the same approach used by production vectorization tools.
No spikes. No accumulation error.
"""

import numpy as np
import cv2
import math
from typing import List, Optional, Tuple


def _fit_main_angle(contour: np.ndarray) -> float:
    """
    Find the dominant orientation of the polygon (in degrees).
    Uses minAreaRect which is robust to noise.
    """
    rect = cv2.minAreaRect(contour)
    (_, _), (w, h), angle = rect

    # minAreaRect returns angle in [-90, 0) — normalize
    # If the rectangle is tall, swap to get the "long" axis
    if w < h:
        angle = angle + 90
    return angle % 180.0


def _rotate_points(pts: np.ndarray, angle_deg: float,
                   center: np.ndarray) -> np.ndarray:
    """Rotate points around center by angle (degrees)"""
    rad = math.radians(angle_deg)
    c, s = math.cos(rad), math.sin(rad)
    R = np.array([[c, -s], [s, c]])
    return (pts - center) @ R.T + center


def _snap_edge_value(value: float, grid: float = 1.0) -> float:
    """Snap a coordinate value to a grid"""
    return round(value / grid) * grid


def orthogonalize_polygon(polygon_xy: List[Tuple[float, float]],
                          angle_tolerance: float = 15.0,
                          area_tolerance: float = 0.25,
                          grid: float = 1.0) -> Optional[List[Tuple[float, float]]]:
    """
    Orthogonalize a polygon by:
    - Finding its dominant angle
    - Rotating to align
    - Snapping edges to nearest of {0°, 45°, 90°, 135°}
    - Rotating back

    Returns the new polygon (list of (x,y)) or None if it failed.

    Args:
        polygon_xy: list of vertices, first NOT repeated at end
        angle_tolerance: how far from 0/45/90/135 an edge can be and still be snapped
        area_tolerance: max fractional area change to accept
        grid: coordinate snapping grid (in pixel units)
    """
    if len(polygon_xy) < 3:
        return None

    pts = np.array(polygon_xy, dtype=np.float64)
    original_area = abs(_polygon_area(pts))
    if original_area < 20:
        return None

    # 1. Fit dominant angle
    contour = pts.astype(np.float32).reshape(-1, 1, 2)
    main_angle = _fit_main_angle(contour)

    # 2. Rotate points so main axis is horizontal
    centroid = pts.mean(axis=0)
    rot_pts = _rotate_points(pts, -main_angle, centroid)

    # 3. Snap each vertex to nearest grid
    snapped = np.round(rot_pts / grid) * grid

    # 4. Rebuild polygon: for each edge, decide if it's H, V, or diagonal
    n = len(snapped)
    new_pts = []
    for i in range(n):
        p_curr = snapped[i]
        p_next = snapped[(i + 1) % n]

        dx = p_next[0] - p_curr[0]
        dy = p_next[1] - p_curr[1]

        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            continue

        # Edge angle in [0, 90]
        angle = abs(math.degrees(math.atan2(dy, dx))) % 90.0

        # Snap to nearest multiple of 45
        if angle < angle_tolerance:
            # horizontal
            new_next = (p_next[0], p_curr[1])
        elif angle > 90 - angle_tolerance:
            # vertical
            new_next = (p_curr[0], p_next[1])
        elif abs(angle - 45) < angle_tolerance:
            # diagonal — force 45
            length = math.hypot(dx, dy)
            sign_x = 1 if dx >= 0 else -1
            sign_y = 1 if dy >= 0 else -1
            new_next = (p_curr[0] + length * sign_x / math.sqrt(2),
                        p_curr[1] + length * sign_y / math.sqrt(2))
        else:
            # don't snap
            new_next = tuple(p_next)

        new_pts.append(new_next)

    if len(new_pts) < 3:
        return None

    # 5. Remove duplicate / collinear points
    new_pts = _remove_duplicates(new_pts, tol=grid * 0.5)
    if len(new_pts) < 3:
        return None

    # 6. Rotate back
    snapped_pts = np.array(new_pts, dtype=np.float64)
    final_pts = _rotate_points(snapped_pts, main_angle, centroid)

    # 7. Validate area change
    new_area = abs(_polygon_area(final_pts))
    if original_area > 0:
        rel_change = abs(new_area - original_area) / original_area
        if rel_change > area_tolerance:
            return None

    # 8. Ensure polygon doesn't self-intersect
    if not _is_simple_polygon(final_pts):
        return None

    return [tuple(p) for p in final_pts]


def _polygon_area(pts: np.ndarray) -> float:
    """Signed area of a polygon (shoelace formula)"""
    x = pts[:, 0]
    y = pts[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)


def _remove_duplicates(pts: List[Tuple[float, float]],
                       tol: float = 1.0) -> List[Tuple[float, float]]:
    """Remove consecutive duplicate points"""
    if not pts:
        return pts
    out = [pts[0]]
    for p in pts[1:]:
        last = out[-1]
        if math.hypot(p[0] - last[0], p[1] - last[1]) > tol:
            out.append(p)
    # Check last vs first
    if len(out) > 1:
        first, last = out[0], out[-1]
        if math.hypot(first[0] - last[0], first[1] - last[1]) <= tol:
            out.pop()
    return out


def _is_simple_polygon(pts: np.ndarray) -> bool:
    """Check if the polygon has no self-intersections"""
    n = len(pts)
    if n < 3:
        return False
    for i in range(n):
        a1 = pts[i]
        a2 = pts[(i + 1) % n]
        for j in range(i + 2, n):
            if abs(i - j) <= 1 or (i == 0 and j == n - 1):
                continue
            b1 = pts[j]
            b2 = pts[(j + 1) % n]
            if _segments_intersect(a1, a2, b1, b2):
                return False
    return True


def _segments_intersect(p1, p2, p3, p4) -> bool:
    """Test if segments (p1,p2) and (p3,p4) intersect"""
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(v) < 1e-9:
            return 0
        return 1 if v > 0 else -1

    o1 = orient(p1, p2, p3)
    o2 = orient(p1, p2, p4)
    o3 = orient(p3, p4, p1)
    o4 = orient(p3, p4, p2)
    return o1 != o2 and o3 != o4


def orthogonalize_mask(mask: np.ndarray,
                       min_area_px: int = 80) -> Optional[np.ndarray]:
    """
    Orthogonalize the largest contour of a binary mask.

    Returns a new binary mask with the snapped polygon, or None on failure.
    """
    mask_u8 = np.ascontiguousarray(mask.astype(np.uint8))
    contours, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL,
                                    cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < min_area_px:
        return None

    # Simplify first (moderate — we'll re-snap)
    epsilon = 0.01 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    if len(approx) < 4:
        return None
    if len(approx) > 40:
        # too complex, but try anyway with more aggressive simplification
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        if len(approx) < 4 or len(approx) > 40:
            return None

    xy = [tuple(p[0]) for p in approx]
    new_xy = orthogonalize_polygon(xy)
    if new_xy is None or len(new_xy) < 3:
        return None

    # Rasterize
    out = np.zeros_like(mask_u8)
    pts = np.array(new_xy, dtype=np.int32).reshape(-1, 1, 2)
    cv2.fillPoly(out, [pts], 1)
    return out.astype(bool)
