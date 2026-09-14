
import sys
import os
from pathlib import Path

print("=" * 60)
print("🔍 GeoVision AI Plugin - Complete Verification")
print("=" * 60)

# 1. Check Python version
print(f"\n🐍 Python version: {sys.version}")
print(f"Python executable: {sys.executable}")

# 2. Check installed packages
print("\n📦 Installed Packages:")
packages_to_check = {
    'numpy': 'NumPy',
    'torch': 'PyTorch',
    'cv2': 'OpenCV',
    'PIL': 'Pillow',
    'matplotlib': 'Matplotlib',
    'segment_anything': 'Segment-Anything',
    'ultralytics': 'Ultralytics',
    'requests': 'Requests',
    'tqdm': 'tqdm'
}

for module, name in packages_to_check.items():
    try:
        mod = __import__(module)
        version = getattr(mod, '__version__', 'unknown')
        print(f"  ✅ {name}: {version}")
    except ImportError:
        print(f"  ❌ {name}: Not installed")

# 3. Check project structure
print("\n📁 Project Structure:")
required_dirs = [
    'geovision_ai_plugin',
    'geovision_ai_plugin/core',
    'geovision_ai_plugin/ui',
    'geovision_ai_plugin/models',
    'geovision_ai_plugin/utils',
    'geovision_ai_plugin/processing_provider',
    'geovision_ai_plugin/tests',
    'geovision_ai_plugin/resources/icons'
]

for dir_path in required_dirs:
    if os.path.exists(dir_path):
        print(f"  ✅ {dir_path}/")
    else:
        print(f"  ❌ {dir_path}/ - MISSING")

# 4. Check key files
print("\n📄 Key Files:")
key_files = [
    'README.md',
    'LICENSE',
    '.gitignore',
    'requirements.txt',
    'setup.py',
    'geovision_ai_plugin/__init__.py',
    'geovision_ai_plugin/plugin.py',
    'geovision_ai_plugin/metadata.txt',
    'geovision_ai_plugin/core/config_manager.py',
    'geovision_ai_plugin/resources/icons/icon.png'
]

for file_path in key_files:
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"  ✅ {file_path} ({size} bytes)")
    else:
        print(f"  ❌ {file_path} - MISSING")

# 5. Test imports
print("\n🔌 Testing Imports:")
try:
    from geovision_ai_plugin import GeoVisionAIPlugin
    print("  ✅ GeoVisionAIPlugin imported")
except Exception as e:
    print(f"  ❌ GeoVisionAIPlugin import failed: {e}")

try:
    from geovision_ai_plugin.core.config_manager import ConfigManager
    print("  ✅ ConfigManager imported")
except Exception as e:
    print(f"  ❌ ConfigManager import failed: {e}")

print("\n" + "=" * 60)
print("✅ Verification complete!")
print("=" * 60)
