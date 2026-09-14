
import sys
import os

print("=" * 70)
print("🔍 GeoVision AI - Complete Environment Test")
print("=" * 70)

# Python info
print(f"\n🐍 Python: {sys.version}")
print(f"📍 Path: {sys.executable}")

# Add QGIS Python path
sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')

# Test PyQt5
print("\n📦 PyQt5:")
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    print("  ✅ PyQt5 imported successfully")
except Exception as e:
    print(f"  ❌ PyQt5: {e}")

# Test QGIS
print("\n📦 QGIS Core:")
try:
    from qgis.core import QgsApplication
    
    # Initialize QGIS
    print("  Initializing QGIS...")
    QgsApplication.setPrefixPath('/Applications/QGIS-LTR.app/Contents/Resources', True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    print(f"  ✅ QGIS {QgsApplication.version()} initialized!")
    
    # Test processing registry
    from qgis.core import QgsProcessingRegistry
    registry = QgsApplication.processingRegistry()
    print(f"  ✅ Processing registry available")
    
except Exception as e:
    print(f"  ❌ QGIS: {e}")

# Test qgis.PyQt
print("\n📦 qgis.PyQt:")
try:
    from qgis.PyQt.QtWidgets import QAction
    from qgis.PyQt.QtCore import QObject
    print("  ✅ qgis.PyQt imported successfully")
except Exception as e:
    print(f"  ❌ qgis.PyQt: {e}")

# Test AI packages
print("\n📦 AI Packages:")
try:
    import torch
    print(f"  ✅ PyTorch {torch.__version__}")
except Exception as e:
    print(f"  ❌ PyTorch: {e}")

try:
    import cv2
    print(f"  ✅ OpenCV {cv2.__version__}")
except Exception as e:
    print(f"  ❌ OpenCV: {e}")

try:
    import numpy
    print(f"  ✅ NumPy {numpy.__version__}")
except Exception as e:
    print(f"  ❌ NumPy: {e}")

try:
    import ultralytics
    print(f"  ✅ Ultralytics {ultralytics.__version__}")
except Exception as e:
    print(f"  ❌ Ultralytics: {e}")

try:
    import segment_anything
    print("  ✅ Segment-Anything")
except Exception as e:
    print(f"  ❌ Segment-Anything: {e}")

# Test plugin imports (these will fail if QGIS isn't initialized, but that's OK)
print("\n📦 Plugin Modules (basic):")
try:
    sys.path.insert(0, os.getcwd())
    # Just test basic Python imports, not full plugin
    from geovision_ai_plugin.core.config_manager import ConfigManager
    print("  ✅ ConfigManager (basic Python)")
except Exception as e:
    print(f"  ❌ ConfigManager: {e}")

# Clean up QGIS if it was initialized
try:
    if 'qgs' in locals():
        qgs.exitQgis()
        print("\n✅ QGIS cleaned up")
except:
    pass

print("\n" + "=" * 70)
print("✅ Test Complete!")
print("=" * 70)
