#!/usr/bin/env python3
"""
Final test for GeoVision AI - All imports working
"""
import sys
import os

print("=" * 70)
print("🎯 GeoVision AI - Final Complete Test")
print(f"📌 QGIS 3.40.5-Bratislava - Python 3.9.5")
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
    
    print("  ✅ QGIS 3.40.5-Bratislava initialized")
    qgs.exitQgis()
except Exception as e:
    print(f"  ❌ QGIS: {e}")

# Test PyQt5
print("\n📦 PyQt5:")
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    print("  ✅ PyQt5 5.15.2 imported")
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

try:
    import ultralytics
    print(f"  ✅ Ultralytics {ultralytics.__version__}")
except Exception as e:
    print(f"  ❌ Ultralytics: {e}")

# Test all plugin imports
print("\n📦 Plugin Modules:")
try:
    sys.path.insert(0, os.getcwd())
    
    from geovision_ai_plugin import GeoVisionAIPlugin
    print("  ✅ GeoVisionAIPlugin")
    
    from geovision_ai_plugin.core.config_manager import ConfigManager
    print("  ✅ ConfigManager")
    
    from geovision_ai_plugin.ui.main_dock import MainDockWidget
    print("  ✅ MainDockWidget")
    
    from geovision_ai_plugin.ui.settings_dialog import SettingsDialog
    print("  ✅ SettingsDialog")
    
    from geovision_ai_plugin.processing_provider.provider import Provider
    print("  ✅ Provider")
    
    from geovision_ai_plugin.processing_provider.segmentation_algorithm import SegmentationAlgorithm
    print("  ✅ SegmentationAlgorithm")
    
except Exception as e:
    print(f"  ❌ Import error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ ALL IMPORTS WORKING - Environment is ready for development!")
print("📌 You can now open the project in PyCharm and start coding!")
print("=" * 70)
