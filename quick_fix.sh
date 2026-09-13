#!/bin/bash
echo "🔧 Quick fix for metadata case sensitivity..."

# Fix metadata
cat > geovision_ai_plugin/metadata.txt << 'EOF2'
[general]
name=GeoVision AI
description=AI-powered raster-to-vector segmentation for QGIS
version=1.0.0
qgisMinimumVersion=3.34
author=Your Name
email=your.email@example.com
about=Segments rasters using AI models to extract vector polygons
tracker=https://github.com/yourusername/geovision-ai-plugin/issues
repository=https://github.com/yourusername/geovision-ai-plugin
icon=resources/icons/icon.png

[processing]
hasProcessingProvider=yes
EOF2

echo "✅ metadata.txt fixed with lowercase sections"

# Validate
python3 -c "
import configparser
config = configparser.ConfigParser()
config.read('geovision_ai_plugin/metadata.txt')
if config.has_section('general'):
    print('✅ [general] section found')
    print(f'   Plugin: {config.get(\"general\", \"name\")}')
    print('✅ metadata is valid for QGIS')
else:
    print('❌ metadata invalid')
    exit(1)
"

# Rebuild
rm -f geovision_ai_plugin.zip
zip -r geovision_ai_plugin.zip geovision_ai_plugin/ -x "*.pyc" "__pycache__/*" "venv/*" ".git/*" "*.swp" "*.swo" ".DS_Store"
echo "✅ Plugin rebuilt: $(ls -lh geovision_ai_plugin.zip | awk '{print $5}')"

echo ""
echo "📌 Now install in QGIS:"
echo "   Plugins → Manage and Install Plugins → Install from ZIP"
echo "   Select: $(pwd)/geovision_ai_plugin.zip"
