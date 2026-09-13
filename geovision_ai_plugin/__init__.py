"""
GeoVision AI Plugin - AI-powered raster segmentation for QGIS
"""
import sys
import os

# Run startup fixes
try:
    from .startup import *
except ImportError:
    print("⚠️  Startup module not found")

from .plugin import GeoVisionAIPlugin

def classFactory(iface):
    """Load GeoVisionAIPlugin class from plugin."""
    return GeoVisionAIPlugin(iface)
