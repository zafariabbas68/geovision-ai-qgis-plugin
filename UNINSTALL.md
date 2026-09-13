# Uninstalling GeoVision AI Plugin

## Method 1: Uninstall from QGIS Plugin Manager

1. Open QGIS
2. Go to **Plugins** → **Manage and Install Plugins**
3. Find **GeoVision AI** in the installed plugins list
4. Click **Uninstall**
5. The plugin will be removed from QGIS

## Method 2: Manual Uninstall (if plugin doesn't appear in manager)

### On macOS:
```bash
# Remove the plugin from QGIS profiles
rm -rf ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/geovision_ai_plugin

# Remove any symlink if created
rm -f ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/geovision_ai_plugin
```

### On Windows:
```bash
rmdir /s "C:\Users\%USERNAME%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\geovision_ai_plugin"
```

### On Linux:
```bash
rm -rf ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/geovision_ai_plugin
```

## Remove Downloaded Models (Optional)

If you want to free up space, remove the AI models:

```bash
# Remove model files
rm -rf ~/.local/share/GeoVisionAI/models/
```

## Verify Uninstallation

After uninstalling:
1. Restart QGIS
2. Check that the GeoVision AI icon is no longer in the toolbar
3. Verify the plugin is not in **Plugins** menu

## Reinstalling

To reinstall the plugin:
1. Follow the installation instructions in INSTALL.md
2. Use the ZIP file: `geovision_ai_plugin.zip`
3. The plugin will be installed fresh
