#!/usr/bin/env python3
"""
Test the model manager
"""
import sys
import os

sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')
sys.path.insert(0, os.getcwd())

print("=" * 60)
print("🧪 Testing Model Manager")
print("=" * 60)

try:
    from geovision_ai_plugin.core.config_manager import ConfigManager
    from geovision_ai_plugin.core.model_manager import ModelManager
    
    print("✅ ModelManager imported successfully")
    
    # Test creation
    config = ConfigManager()
    model_manager = ModelManager(config)
    
    print(f"✅ Device: {model_manager.device}")
    print(f"✅ Model directory: {model_manager.model_dir}")
    print(f"✅ Available models: {model_manager.get_available_models()}")
    
    # Test model info
    for model in model_manager.get_available_models():
        info = model_manager.get_model_info(model)
        print(f"  📌 {model}: {info['name']} - {info['speed']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
