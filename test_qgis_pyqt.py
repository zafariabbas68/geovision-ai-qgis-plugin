
import sys
import os

print("=" * 60)
print("🔍 Testing QGIS + PyQt5 Integration")
print("=" * 60)

# Add QGIS Python path
sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')

try:
    # Test PyQt5 first
    print("\n📦 Testing PyQt5...")
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    print("  ✅ PyQt5 imported successfully")
    
    # Test QGIS
    print("\n📦 Testing QGIS...")
    from qgis.core import QgsApplication
    
    # Initialize QGIS (without GUI)
    QgsApplication.setPrefixPath('/Applications/QGIS-LTR.app/Contents/Resources', True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    print(f"  ✅ QGIS {QgsApplication.version()} initialized")
    
    # Test qgis.PyQt
    print("\n📦 Testing qgis.PyQt...")
    from qgis.PyQt.QtWidgets import QAction
    from qgis.PyQt.QtCore import QObject
    print("  ✅ qgis.PyQt imported successfully")
    
    # Clean up
    qgs.exitQgis()
    print("\n✅ All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
