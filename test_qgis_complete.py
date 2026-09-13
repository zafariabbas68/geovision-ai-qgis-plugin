#!/usr/bin/env python3
"""
Complete QGIS test with proper initialization
"""
import sys
import os

print("=" * 60)
print("🔍 Testing QGIS with Proper Initialization")
print("=" * 60)

# Add QGIS Python path
sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')

try:
    from qgis.core import QgsApplication
    
    # Initialize QGIS application
    print("\n📦 Initializing QGIS...")
    QgsApplication.setPrefixPath('/Applications/QGIS-LTR.app/Contents/Resources', True)
    qgs = QgsApplication([], False)
    qgs.initQgis()
    
    print(f"✅ QGIS {QgsApplication.version()} initialized successfully!")
    
    # Test some QGIS functionality
    print("\n📦 Testing QGIS functionality:")
    
    # Get the application reference
    app = QgsApplication.instance()
    print(f"  ✅ QGIS Application instance: {app}")
    
    # Test processing registry
    from qgis.core import QgsProcessingRegistry
    registry = QgsApplication.processingRegistry()
    print(f"  ✅ Processing registry: {registry}")
    
    # Clean up
    qgs.exitQgis()
    print("\n✅ QGIS test complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
