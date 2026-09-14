
import sys
import os


EXTRA_LIBS = '/Applications/QGIS-LTR.app/Contents/Resources/python/extra_libs'
USER_SITE = os.path.expanduser('~/.local/lib/python3.9/site-packages')


def fix_paths():
    """Add the paths where cv2, torch, etc. live"""

    # 1. Add extra_libs FIRST (highest priority)
    if os.path.exists(EXTRA_LIBS):
        if EXTRA_LIBS in sys.path:
            sys.path.remove(EXTRA_LIBS)
        sys.path.insert(0, EXTRA_LIBS)
        print(f"✅ GeoVision startup: added extra_libs to sys.path")
    else:
        print(f"⚠️  GeoVision startup: extra_libs not found")

    # 2. Add ~/.local/site-packages as fallback
    if os.path.exists(USER_SITE) and USER_SITE not in sys.path:
        sys.path.append(USER_SITE)


# Run on import
fix_paths()

# Verify
try:
    import cv2
    print(f"✅ GeoVision startup: OpenCV {cv2.__version__} loaded")
except Exception as e:
    print(f"❌ GeoVision startup: OpenCV failed: {e}")

try:
    import numpy
    print(f"✅ GeoVision startup: NumPy {numpy.__version__} loaded")
except Exception as e:
    print(f"⚠️  GeoVision startup: NumPy failed: {e}")
