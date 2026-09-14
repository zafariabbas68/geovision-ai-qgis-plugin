
import sys
import os
import numpy as np

sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
sys.path.insert(0, os.getcwd())

print("=" * 70)
print("🚀 GeoVision AI - Full Pipeline Test")
print("=" * 70)

try:
    # Test all components
    print("\n📦 Testing all components:")
    
    # 1. Config Manager
    from geovision_ai_plugin.core.config_manager import ConfigManager
    config = ConfigManager()
    print("  ✅ ConfigManager")
    
    # 2. Raster Handler
    from geovision_ai_plugin.core.raster_handler import RasterHandler
    print("  ✅ RasterHandler")
    
    # 3. Model Manager
    from geovision_ai_plugin.core.model_manager import ModelManager
    model_manager = ModelManager(config)
    print(f"  ✅ ModelManager (device: {model_manager.device})")
    
    # 4. Segmentation Engine
    from geovision_ai_plugin.core.segmentation_engine import SegmentationEngine
    print("  ✅ SegmentationEngine")
    
    # 5. Vector Generator
    from geovision_ai_plugin.core.vector_generator import VectorGenerator
    from qgis.core import QgsCoordinateReferenceSystem
    crs = QgsCoordinateReferenceSystem('EPSG:3857')
    generator = VectorGenerator(crs)
    print(f"  ✅ VectorGenerator (CRS: {crs.authid()})")
    
    print("\n" + "=" * 70)
    print("✅ All components loaded successfully!")
    print("📌 The full pipeline is ready for integration")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
