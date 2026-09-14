
import sys
import os
import numpy as np

sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("🧪 Testing Vector Generator")
print("=" * 60)

try:
    from geovision_ai_plugin.core.vector_generator import VectorGenerator
    from qgis.core import QgsCoordinateReferenceSystem
    
    print("✅ VectorGenerator imported successfully")
    
    # Create a simple CRS
    crs = QgsCoordinateReferenceSystem('EPSG:3857')
    
    # Create vector generator
    generator = VectorGenerator(crs)
    print(f"✅ VectorGenerator created with CRS: {crs.authid()}")
    
    # Create a test mask
    mask = np.zeros((100, 100), dtype=bool)
    mask[20:80, 20:80] = True
    
    # Test mask to polygons
    geo_transform = [0, 1, 0, 100, 0, -1]
    polygons = generator._mask_to_polygons(mask, geo_transform, 100, 100)
    print(f"✅ Created {len(polygons)} polygons from mask")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
