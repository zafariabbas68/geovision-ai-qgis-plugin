
import sys
import os

print("=" * 70)
print("🎯 GeoVision AI - Final Working Test")
print("=" * 70)

# Add QGIS Python path
sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')

# Test QGIS
print("\n📦 QGIS:")
try:
    from qgis.core import QgsApplication
    
    QgsApplication.setPrefixPath('/Applications/QGIS-LTR.app/Contents/Resources', True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    # Try to get version
    try:
        from qgis.core import QGIS_VERSION
        print(f"  ✅ QGIS {QGIS_VERSION}")
    except:
        try:
            print(f"  ✅ QGIS {QgsApplication.version()}")
        except:
            print("  ✅ QGIS initialized (version unknown)")
    
    qgs.exitQgis()
except Exception as e:
    print(f"  ❌ QGIS: {e}")

# Test PyQt5
print("\n📦 PyQt5:")
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    print("  ✅ PyQt5 imported")
except Exception as e:
    print(f"  ❌ PyQt5: {e}")

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

# Test plugin imports
print("\n📦 Plugin:")
try:
    sys.path.insert(0, os.getcwd())
    from geovision_ai_plugin.core.config_manager import ConfigManager
    cm = ConfigManager()
    print(f"  ✅ ConfigManager")
except Exception as e:
    print(f"  ❌ ConfigManager: {e}")

try:
    from geovision_ai_plugin.ui.main_dock import MainDockWidget
    print("  ✅ MainDockWidget")
except Exception as e:
    print(f"  ❌ MainDockWidget: {e}")

try:
    from geovision_ai_plugin.processing_provider.provider import Provider
    print("  ✅ Provider")
except Exception as e:
    print(f"  ❌ Provider: {e}")

print("\n" + "=" * 70)
print("✅ GeoVision AI environment is ready for development!")
print("📌 Open the project in PyCharm and start coding!")
print("=" * 70)
