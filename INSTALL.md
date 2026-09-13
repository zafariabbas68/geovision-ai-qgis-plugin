# GeoVision AI - QGIS Plugin Installation

## Prerequisites
- QGIS 3.40.5 or higher
- Python 3.9.5 or higher
- Internet connection for model downloads

## Installation

### Method 1: Install from ZIP (Recommended)

1. **Build the plugin ZIP**:
   ```bash
   cd /Users/ghulamabbaszafari/Downloads/geovision_ai_plugin
   python3 scripts/build_plugin.py
   ```

2. **Install in QGIS**:
   - Open QGIS
   - Go to **Plugins** → **Manage and Install Plugins**
   - Click **Install from ZIP**
   - Browse to the ZIP file
   - Click **Install Plugin**

### Method 2: Install from Directory (Development)

1. **Create a symlink to the plugin**:
   ```bash
   ln -s /Users/ghulamabbaszafari/Downloads/geovision_ai_plugin/geovision_ai_plugin ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/
   ```

2. **Enable the plugin**:
   - Open QGIS
   - Go to **Plugins** → **Manage and Install Plugins**
   - Search for "GeoVision AI"
   - Enable the plugin

## First Run Setup

1. **Open the plugin**:
   - Click the GeoVision AI icon in the toolbar
   - Or go to **Plugins** → **GeoVision AI**

2. **Select a raster layer**:
   - Choose a raster from the dropdown
   - The plugin works with any raster: GeoTIFF, WMS, WMTS, etc.

3. **Enter a feature class**:
   - Type what you want to find (e.g., "buildings", "trees")
   - The AI will segment objects matching this description

4. **Configure settings** (optional):
   - Adjust confidence threshold
   - Set minimum area filter
   - Choose the AI model

5. **Run segmentation**:
   - Click the **Segment** button
   - Wait for the AI to process
   - The result will appear as a new vector layer

## Troubleshooting

### Model Download Fails
- Check your internet connection
- The plugin downloads models from Meta/Facebook servers
- You can manually download models and place them in:
  `~/.local/share/GeoVisionAI/models/weights/`

### Segmentation is Slow
- Use the SAM2-tiny model for faster processing
- Consider using a smaller area
- Enable GPU if available

### Import Errors
- Ensure QGIS is version 3.40.5 or higher
- Check that all dependencies are installed

## Uninstallation

1. **Remove the plugin**:
   - Go to **Plugins** → **Manage and Install Plugins**
   - Find **GeoVision AI**
   - Click **Uninstall**

2. **Remove model files** (optional):
   ```bash
   rm -rf ~/.local/share/GeoVisionAI/models/
   ```
