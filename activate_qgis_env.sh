#!/bin/bash
# Activate QGIS development environment with proper library paths

# Set QGIS library paths
export DYLD_LIBRARY_PATH="/Applications/QGIS-LTR.app/Contents/Frameworks:$DYLD_LIBRARY_PATH"
export DYLD_FALLBACK_LIBRARY_PATH="/Applications/QGIS-LTR.app/Contents/Frameworks:/Applications/QGIS-LTR.app/Contents/MacOS/lib:$DYLD_FALLBACK_LIBRARY_PATH"

# Set QGIS paths
export QGIS_PREFIX_PATH="/Applications/QGIS-LTR.app/Contents/Resources"
export PYTHONPATH="/Applications/QGIS-LTR.app/Contents/Resources/python:/Applications/QGIS-LTR.app/Contents/Resources/python/site-packages:$PYTHONPATH"

# Activate virtual environment
source venv/bin/activate

echo "✅ QGIS development environment activated!"
echo "Python: $(python3 --version)"
echo ""

# Test QGIS
python3 -c "
import os
import sys

# Add QGIS paths
sys.path.insert(0, '/Applications/QGIS-LTR.app/Contents/Resources/python')

try:
    from qgis.core import QgsApplication
    print(f'✅ QGIS {QgsApplication.version()} ready!')
except Exception as e:
    print(f'⚠️  QGIS import: {e}')
"
