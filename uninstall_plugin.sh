#!/bin/bash
# Quick uninstall script for GeoVision AI plugin

echo "🗑️  Uninstalling GeoVision AI plugin..."

# Remove from QGIS profiles
rm -rf ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/geovision_ai_plugin
rm -f ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/geovision_ai_plugin

# Remove models (optional)
read -p "Remove downloaded AI models? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf ~/.local/share/GeoVisionAI/models/
    echo "✅ Models removed"
fi

echo "✅ Plugin uninstalled!"
echo "📌 Restart QGIS to complete the uninstallation"
