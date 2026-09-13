"""
Class-aware detection helpers
Each class (building, car, tree, etc.) has tuned parameters
Based on GeoOSAM architecture [citation:11]
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ClassProfile:
    """Detection parameters tuned for a specific class"""
    name: str
    min_area_m2: float
    max_area_m2: float
    min_solidity: float
    min_rectangularity: float
    points_per_side: int
    pred_iou_thresh: float
    stability_score: float
    tile_size: int
    description: str
    # Optional morphological hints
    edge_density_threshold: float = 0.0  # for detecting edges


# Tuned profiles per class
# Sources: ISPRS Vaihingen dataset [citation:4][citation:9], GeoOSAM [citation:11]
CLASS_PROFILES: Dict[str, ClassProfile] = {
    'building': ClassProfile(
        name='building',
        min_area_m2=15.0,
        max_area_m2=10000.0,
        min_solidity=0.72,
        min_rectangularity=0.65,
        points_per_side=32,
        pred_iou_thresh=0.86,
        stability_score=0.92,
        tile_size=1024,
        description='Rectangular buildings with sharp corners'
    ),
    'car': ClassProfile(
        name='car',
        min_area_m2=2.0,      # ~2-15 m²
        max_area_m2=30.0,
        min_solidity=0.55,
        min_rectangularity=0.45,   # cars are elongated, less rectangular
        points_per_side=48,   # more points for small objects
        pred_iou_thresh=0.75,
        stability_score=0.85,
        tile_size=512,        # smaller tiles for small objects
        description='Vehicles on roads and parking (2-30 m²)'
    ),
    'tree': ClassProfile(
        name='tree',
        min_area_m2=5.0,
        max_area_m2=500.0,
        min_solidity=0.4,     # trees are irregular
        min_rectangularity=0.0,    # no shape constraint
        points_per_side=32,
        pred_iou_thresh=0.80,
        stability_score=0.88,
        tile_size=1024,
        description='Tree crowns, irregular circular shapes'
    ),
    'road': ClassProfile(
        name='road',
        min_area_m2=50.0,
        max_area_m2=100000.0,
        min_solidity=0.3,
        min_rectangularity=0.0,
        points_per_side=16,   # fewer points, roads are big
        pred_iou_thresh=0.75,
        stability_score=0.85,
        tile_size=2048,       # larger tiles for long roads
        description='Road surfaces and pavement'
    ),
    'swimming_pool': ClassProfile(
        name='swimming pool',
        min_area_m2=8.0,
        max_area_m2=200.0,
        min_solidity=0.85,    # pools are usually rectangular
        min_rectangularity=0.75,
        points_per_side=32,
        pred_iou_thresh=0.85,
        stability_score=0.92,
        tile_size=512,
        description='Rectangular pools'
    ),
    'solar_panel': ClassProfile(
        name='solar panel',
        min_area_m2=1.0,
        max_area_m2=500.0,
        min_solidity=0.80,
        min_rectangularity=0.70,
        points_per_side=48,
        pred_iou_thresh=0.82,
        stability_score=0.90,
        tile_size=512,
        description='Solar panels, precise rectangular shapes'
    ),
}


def get_profile(class_name: str) -> ClassProfile:
    """Get detection profile for a class, with fallback"""
    key = class_name.lower().strip()
    
    # Direct match
    if key in CLASS_PROFILES:
        return CLASS_PROFILES[key]
    
    # Partial match
    for k in CLASS_PROFILES:
        if k in key or key in k:
            return CLASS_PROFILES[k]
    
    # Fallback: generic object
    return ClassProfile(
        name=class_name,
        min_area_m2=5.0,
        max_area_m2=5000.0,
        min_solidity=0.5,
        min_rectangularity=0.3,
        points_per_side=32,
        pred_iou_thresh=0.82,
        stability_score=0.90,
        tile_size=1024,
        description=f'Generic detection for "{class_name}"'
    )


def list_profiles() -> list:
    """List all available profiles"""
    return list(CLASS_PROFILES.keys())
