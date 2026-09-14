
import sys
import os

sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("🧪 Testing Raster Handler")
print("=" * 60)

try:
    from geovision_ai_plugin.core.raster_handler import RasterHandler
    print("✅ RasterHandler imported successfully")
    
    # Test creation
    print("\n📦 Testing RasterHandler creation:")
    # This would normally need a real raster layer
    # For now, just test the class exists and has methods
    methods = [m for m in dir(RasterHandler) if not m.startswith('_')]
    print(f"  ✅ Available methods: {', '.join(methods[:5])}...")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
