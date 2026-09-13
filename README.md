# GeoVision AI - QGIS Plugin

AI-powered raster-to-vector segmentation for QGIS.

## Features

- **Universal Raster Input**: Works with any raster displayed in QGIS
- **AI-Powered Segmentation**: Uses SAM2/SAM3 foundation models
- **Vector Output**: Returns polygons with attributes (id, class, area, confidence)
- **Project CRS**: Maintains coordinate reference system integrity
- **Multi-class Support**: Custom class definitions

## Installation

1. Open QGIS
2. Go to Plugins > Manage and Install Plugins
3. Click "Install from ZIP"
4. Select the GeoVision AI plugin ZIP file
5. Click "Install Plugin"

## Usage

1. Load a raster layer in QGIS
2. Open the GeoVision AI dock panel
3. Select the raster layer
4. Enter the feature class (e.g., "buildings", "trees")
5. Click "Segment"
6. The vector layer will be added to your project

## Requirements

- QGIS 3.34 or higher
- Python 3.10 or higher
- PyTorch (automatically installed)

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/geovision-ai-plugin.git
cd geovision-ai-plugin

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements_dev.txt
```

### Testing

```bash
pytest tests/
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.
