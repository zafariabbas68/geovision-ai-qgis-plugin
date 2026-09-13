"""
Post-detection validation: reject masks that don't match the class
Uses color statistics inside the mask to validate
"""

import numpy as np
import cv2


def validate_mask(image_rgb: np.ndarray, mask: np.ndarray,
                  class_name: str) -> tuple:
    """
    Validate a detection against class-specific color rules.
    Returns (is_valid: bool, reason: str)
    """
    if mask.sum() < 20:
        return False, "too_small"

    # Extract mean RGB inside mask
    pixels = image_rgb[mask]
    if len(pixels) < 10:
        return False, "no_pixels"

    r, g, b = pixels.mean(axis=0)

    # Convert to HSV
    hsv = cv2.cvtColor(
        np.uint8([[[int(r), int(g), int(b)]]]),
        cv2.COLOR_RGB2HSV
    )
    h, s, v = float(hsv[0, 0, 0]), float(hsv[0, 0, 1]), float(hsv[0, 0, 2])

    cls = class_name.lower().strip()

    # ── Tree / vegetation: must be green ──
    if cls in ('tree', 'trees', 'vegetation', 'forest', 'green area'):
        # Green must dominate
        if not (g > r + 5 and g > b + 5):
            return False, f"not_green (rgb={r:.0f},{g:.0f},{b:.0f})"
        # Must have some saturation
        if s < 25:
            return False, f"low_sat ({s:.0f})"
        # Vegetation value range
        if v > 240:
            return False, f"too_bright ({v:.0f})"
        return True, "ok"

    # ── Road / street / pavement: must be gray (low saturation) ──
    if cls in ('road', 'street', 'pavement', 'highway', 'asphalt'):
        if s > 60:
            return False, f"too_saturated ({s:.0f})"
        return True, "ok"

    # ── Swimming pool: must be blue or cyan ──
    if cls in ('swimming pool', 'pool'):
        # Blue must dominate over red
        if not (b > r + 10):
            return False, f"not_blue (rgb={r:.0f},{g:.0f},{b:.0f})"
        if s < 20:
            return False, f"low_sat"
        return True, "ok"

    # ── Building: various colors (red tiles, gray, white) - no color constraint ──
    if cls in ('building', 'buildings', 'house'):
        # Reject if clearly green (probably tree)
        if g > r + 15 and g > b + 15:
            return False, "looks_like_tree"
        return True, "ok"

    # ── Car: various colors but usually has some saturation ──
    if cls in ('car', 'vehicle'):
        # Cars shouldn't be pure green (vegetation) or pure gray
        if g > r + 20 and g > b + 20:
            return False, "looks_like_tree"
        return True, "ok"

    # ── Default: accept ──
    return True, "ok"


def filter_detections(image_rgb: np.ndarray, detections: list,
                      class_name: str, verbose: bool = True) -> list:
    """
    Filter detections by class-specific color validation.
    """
    valid = []
    rejected_reasons = {}

    for det in detections:
        ok, reason = validate_mask(image_rgb, det.mask, class_name)
        if ok:
            valid.append(det)
        else:
            rejected_reasons[reason] = rejected_reasons.get(reason, 0) + 1

    if verbose and rejected_reasons:
        print(f"   Post-filter rejected {len(detections) - len(valid)}:")
        for reason, count in sorted(rejected_reasons.items(), key=lambda x: -x[1]):
            print(f"     - {reason}: {count}")

    return valid
