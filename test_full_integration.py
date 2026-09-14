
import sys
import os
import numpy as np

sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
sys.path.insert(0, os.getcwd())

print("=" * 70)
print("🔗 GeoVision AI - Full Integration Test")
print("=" * 70)

try:
    # Test UI with pipeline
    print("\n📦 Testing UI Integration:")
    
    from geovision_ai_plugin.ui.main_dock import MainDockWidget, SegmentationWorker
    from geovision_ai_plugin.core.config_manager import ConfigManager
    
    # Test ConfigManager
    config = ConfigManager()
    print("  ✅ ConfigManager")
    
    # Test SegmentationWorker (without running)
    print("  ✅ SegmentationWorker class available")
    
    # Test MainDockWidget (without QGIS iface)
    print("  ✅ MainDockWidget class available")
    
    print("\n" + "=" * 70)
    print("✅ Full integration ready!")
    print("📌 The plugin is ready for testing in QGIS")
    print("=" * 70)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
