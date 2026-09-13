"""
Class-aware filtering using color and shape heuristics
Works with SAM's class-agnostic output to sort detections into classes
"""

import numpy as np
import cv2
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ClassFilter:
    """Heuristic filter for a specific class"""
    name: str
    # Color ranges (R, G, B means, 0-255)
    hue_range: Optional[tuple] = None      # (min_deg, max_deg)
    sat_range: Optional[tuple] = None      # (min, max, 0-255)
    val_range: Optional[tuple] = None      # (min, max, 0-255)
    # Shape
    min_solidity: float = 0.0
    min_rectangularity: float = 0.0
    max_solidity: float = 1.0
    max_rectangularity: float = 1.0
    # Color-specific rules
    green_dominant: bool = False           # G > R and G > B (trees)
    gray_dominant: bool = False            # low saturation (roads)
    red_dominant: bool = False             # R > G (roof tiles in Italy)
    
    def match(self, image: np.ndarray, mask: np.ndarray, 
              contour: np.ndarray, solidity: float, rectangularity: float) -> float:
        """
        Returns a confidence score 0-1 for how well the mask matches this class
        """
        score = 1.0
        
        # Shape checks
        if solidity < self.min_solidity: return 0.0
        if solidity > self.max_solidity: return 0.0
        if rectangularity < self.min_rectangularity: return 0.0
        if rectangularity > self.max_rectangularity: return 0.0
        
        # Color extraction
        if mask.sum() < 10: return 0.0
        
        # Extract mean color
        pixels = image[mask]
        if len(pixels) == 0: return 0.0
        mean_rgb = pixels.mean(axis=0)
        r, g, b = mean_rgb
        
        # Convert to HSV for hue-based tests
        hsv = cv2.cvtColor(
            np.uint8([[[int(r), int(g), int(b)]]]),
            cv2.COLOR_RGB2HSV
        )
        h, s, v = hsv[0, 0]
        
        # Color rules
        if self.green_dominant:
            # Green channel must be dominant
            if not (g > r + 5 and g > b + 5):
                score *= 0.2
            # Vegetation is usually darker/greener
            if v > 220:  # too bright → not vegetation
                score *= 0.5
            # Vegetation has moderate saturation
            if s < 30:
                score *= 0.4
        
        if self.gray_dominant:
            # Roads are low saturation
            if s > 60:
                score *= 0.3
        
        if self.red_dominant:
            # Italian roof tiles: R > G > B, warm hue
            if not (r > g and r > b):
                score *= 0.3
            # Hue should be in red-orange range (0-30 or 340-360 deg → H 0-15 or 170-180)
            if not (h < 20 or h > 160):
                score *= 0.4
        
        # Hue range
        if self.hue_range:
            hmin, hmax = self.hue_range
            if not (hmin <= h <= hmax):
                score *= 0.3
        
        # Saturation range
        if self.sat_range:
            smin, smax = self.sat_range
            if not (smin <= s <= smax):
                score *= 0.5
        
        # Value range
        if self.val_range:
            vmin, vmax = self.val_range
            if not (vmin <= v <= vmax):
                score *= 0.5
        
        return score




    def match_mean_color(self, mean_rgb, solidity, rectangularity):
        """
        Match using pre-computed mean RGB
        Args:
            mean_rgb: numpy array [r, g, b] 0-255
            solidity: 0-1
            rectangularity: 0-1
        Returns:
            score: 0-1
        """
        score = 1.0
        
        # Shape checks
        if solidity < self.min_solidity: return 0.0
        if solidity > self.max_solidity: return 0.0
        if rectangularity < self.min_rectangularity: return 0.0
        if rectangularity > self.max_rectangularity: return 0.0
        
        r, g, b = float(mean_rgb[0]), float(mean_rgb[1]), float(mean_rgb[2])
        
        # Convert to HSV
        import cv2
        import numpy as np
        hsv = cv2.cvtColor(
            np.uint8([[[int(r), int(g), int(b)]]]),
            cv2.COLOR_RGB2HSV
        )
        h, s, v = float(hsv[0, 0, 0]), float(hsv[0, 0, 1]), float(hsv[0, 0, 2])
        
        # Green dominant (trees)
        if self.green_dominant:
            if not (g > r + 5 and g > b + 5):
                score *= 0.2
            if v > 220:
                score *= 0.5
            if s < 30:
                score *= 0.4
        
        # Gray dominant (roads)
        if self.gray_dominant:
            if s > 60:
                score *= 0.3
        
        # Red dominant (Italian roof tiles)
        if self.red_dominant:
            if not (r > g and r > b):
                score *= 0.3
            if not (h < 20 or h > 160):
                score *= 0.4
        
        # Hue range
        if self.hue_range:
            hmin, hmax = self.hue_range
            if not (hmin <= h <= hmax):
                score *= 0.3
        
        # Saturation range
        if self.sat_range:
            smin, smax = self.sat_range
            if not (smin <= s <= smax):
                score *= 0.5
        
        # Value range
        if self.val_range:
            vmin, vmax = self.val_range
            if not (vmin <= v <= vmax):
                score *= 0.5
        
        return score


# Class filter definitions
# Tuned from ISPRS Vaihingen + Italian urban morphology observations
CLASS_FILTERS = {
    'building': ClassFilter(
        name='building',
        # Buildings: high rectangularity, red-orange or gray roofs
        min_solidity=0.75,
        min_rectangularity=0.72,
        max_solidity=1.0,
        # Italian buildings often have red tile roofs (r > g)
        # But also gray/asphalt modern roofs
        # So don't force any color rule
    ),
    'tree': ClassFilter(
        name='tree',
        # Trees: irregular blobs, GREEN
        min_solidity=0.35,
        max_solidity=0.95,   # not perfect
        min_rectangularity=0.0,
        max_rectangularity=0.85,  # not rectangular
        green_dominant=True,
    ),
    'car': ClassFilter(
        name='car',
        # Cars: small, mostly elongated, various colors but low-ish sat
        min_solidity=0.45,
        min_rectangularity=0.40,
        max_rectangularity=0.92,  # cars are somewhat rectangular
        sat_range=(10, 200),
        val_range=(30, 240),
    ),
    'road': ClassFilter(
        name='road',
        # Roads: large, elongated, gray (low saturation)
        min_solidity=0.25,
        max_solidity=0.85,
        min_rectangularity=0.0,
        max_rectangularity=0.7,
        gray_dominant=True,
        sat_range=(0, 70),
    ),
    'swimming_pool': ClassFilter(
        name='swimming_pool',
        # Pools: bright blue/cyan, rectangular
        min_solidity=0.80,
        min_rectangularity=0.75,
    ),
    'solar_panel': ClassFilter(
        name='solar_panel',
        # Panels: dark blue/gray, small rectangles
        min_solidity=0.85,
        min_rectangularity=0.80,
        val_range=(20, 180),
    ),
}


def get_filter(class_name: str) -> ClassFilter:
    """Get filter for a class, with fallback"""
    key = class_name.lower().strip().replace(' ', '_')
    if key in CLASS_FILTERS:
        return CLASS_FILTERS[key]
    for k, v in CLASS_FILTERS.items():
        if k in key or key in k:
            return v
    # Generic fallback: accept any shape
    return ClassFilter(name=class_name)
