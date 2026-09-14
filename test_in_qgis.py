
import sys
import os

print("=" * 60)
print("🧪 Testing GeoVision AI in QGIS")
print("=" * 60)

# Add the plugin path
plugin_path = "/Users/ghulamabbaszafari/Downloads/geovision_ai_plugin"
if plugin_path not in sys.path:
    sys.path.insert(0, plugin_path)

try:
    # Test importing the plugin
    from geovision_ai_plugin import GeoVisionAIPlugin
    print("✅ Plugin imported successfully")
    
    # Check if QGIS is available
    from qgis.core import QgsApplication
    print(f"✅ QGIS version: {QgsApplication.version()}")
    
    print("\n📌 The plugin is ready to use!")
    print("   To test the plugin in QGIS:")
    print("   1. Open QGIS")
    print("   2. Load a raster layer")
    print("   3. Open the GeoVision AI plugin")
    print("   4. Select the raster and enter a class")
    print("   5. Click 'Segment'")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
