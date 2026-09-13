"""
Raster data handling for GeoVision AI
Supports: file rasters, WMS, WCS, and web services
"""

import numpy as np
import sys
import os

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from qgis.core import (
    QgsRasterLayer,
    QgsRasterBlock,
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob
)
from qgis.PyQt.QtGui import QImage, QPainter


class RasterHandler:
    """Handle raster data extraction and preparation for AI processing"""

    def __init__(self, raster_layer):
        """Initialize with a QGIS raster layer"""
        self.raster_layer = raster_layer
        self.provider = raster_layer.dataProvider()
        self.width = self.provider.xSize()
        self.height = self.provider.ySize()
        self.extent = raster_layer.extent()
        self.use_opencv = OPENCV_AVAILABLE

        # For WMS layers, use a reasonable size
        if self.width <= 0 or self.height <= 0:
            print("⚠️  WMS layer detected - will use rendering")
            self.width = 512
            self.height = 512

        # Limit size to prevent memory issues
        max_size = 1024
        if self.width > max_size or self.height > max_size:
            aspect = self.width / self.height if self.height > 0 else 1
            if aspect > 1:
                self.width = max_size
                self.height = int(max_size / aspect)
            else:
                self.height = max_size
                self.width = int(max_size * aspect)
            print(f"📐 Scaled to {self.width}x{self.height} for memory")

        print(f"📊 Raster: {raster_layer.name()} ({self.width}x{self.height})")

    # ========================================================================
    # Main entry point - returns data for full layer
    # ========================================================================
    def get_raster_data(self):
        """
        Extract raster data for the full layer

        Returns:
            (numpy array (H, W, 3), CRS, extent, transform dict)
        """
        try:
            if self.provider.xSize() <= 0 or self.provider.ySize() <= 0:
                raster_data = self._render_extent(self.extent, self.width, self.height)
            else:
                raster_data = self._read_bands()
        except Exception as e:
            print(f"Band reading failed: {e}, using render fallback")
            raster_data = self._render_extent(self.extent, self.width, self.height)

        transform = self._get_geotransform(self.extent, self.width, self.height)
        return raster_data, self.raster_layer.crs(), self.extent, transform

    # ========================================================================
    # NEW METHOD - returns data clipped to a specific extent
    # ========================================================================
    def get_raster_data_extent(self, extent, max_size=2048):
        """
        Get raster data clipped to a specific extent (for zone-based detection)

        Args:
            extent: QgsRectangle defining the area of interest
            max_size: Maximum dimension in pixels

        Returns:
            Tuple of (image (H,W,3), crs, transform_dict)
        """
        # Validate extent
        if extent is None or extent.isEmpty():
            print("⚠️  Empty extent, using full layer extent")
            extent = self.raster_layer.extent()

        # Calculate output size from extent
        try:
            res_x = self.raster_layer.rasterUnitsPerPixelX()
            res_y = abs(self.raster_layer.rasterUnitsPerPixelY())
        except Exception:
            res_x = 0
            res_y = 0

        if res_x > 0 and res_y > 0:
            width = int(extent.width() / res_x)
            height = int(extent.height() / res_y)
        else:
            # Fallback for WMS or layers without resolution info
            width = 1024
            height = 1024

        # Cap to max_size while maintaining aspect ratio
        if width > max_size or height > max_size:
            scale = min(max_size / width, max_size / height)
            width = int(width * scale)
            height = int(height * scale)

        # Ensure reasonable minimum
        width = max(width, 128)
        height = max(height, 128)

        print(f"📐 Extent render size: {width}x{height}")

        # Read or render
        if self.provider.xSize() > 0 and self.provider.ySize() > 0:
            raster_data = self._read_bands_extent(extent, width, height)
        else:
            raster_data = self._render_extent(extent, width, height)

        # Build transform for this extent
        transform = self._get_geotransform(extent, width, height)

        return raster_data, self.raster_layer.crs(), transform

    # ========================================================================
    # Internal helpers
    # ========================================================================
    def _read_bands(self):
        """Read RGB bands from full layer"""
        return self._read_bands_extent(self.extent, self.width, self.height)

    def _read_bands_extent(self, extent, width, height):
        """Read RGB bands clipped to extent"""
        band_count = self.provider.bandCount()
        band_indices = [1, 2, 3] if band_count >= 3 else [1, 1, 1]

        raster_data = np.zeros((height, width, 3), dtype=np.uint8)

        for idx, band_num in enumerate(band_indices[:3]):
            try:
                block = self.provider.block(band_num, extent, width, height)
                if block:
                    data = block.data()
                    if data is not None and len(data) > 0:
                        band_data = np.array(data).reshape(height, width)
                        raster_data[:, :, idx] = self._normalize_band(band_data)
            except Exception as e:
                print(f"Error reading band {band_num}: {e}")
                raster_data[:, :, idx] = 0

        return raster_data

    def _normalize_band(self, band_data):
        """Normalize band to 0-255 uint8"""
        if band_data.dtype == np.uint8:
            return band_data

        band_data = np.nan_to_num(band_data, nan=0, posinf=255, neginf=0)
        band_min = np.min(band_data)
        band_max = np.max(band_data)

        if band_max == band_min:
            return np.zeros_like(band_data, dtype=np.uint8)

        normalized = ((band_data - band_min) / (band_max - band_min) * 255)
        return normalized.astype(np.uint8)

    def _render_extent(self, extent, width, height):
        """Render WMS/raster layer to image for a given extent"""
        if width <= 0 or height <= 0:
            width, height = 512, 512

        print(f"🖼️  Rendering {width}x{height}")

        try:
            image = QImage(width, height, QImage.Format_RGB888)
            image.fill(0)

            painter = QPainter(image)

            settings = QgsMapSettings()
            settings.setExtent(extent)
            settings.setOutputSize(image.size())
            settings.setLayers([self.raster_layer])
            settings.setDestinationCrs(self.raster_layer.crs())
            settings.setBackgroundColor(image.pixelColor(0, 0))

            job = QgsMapRendererCustomPainterJob(settings, painter)
            job.render()
            painter.end()

            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.array(ptr).reshape(height, width, 3).copy()

            return arr

        except Exception as e:
            print(f"Rendering failed: {e}")
            placeholder = np.zeros((height, width, 3), dtype=np.uint8)
            placeholder[:, :, 0] = 128
            return placeholder

    def _get_geotransform(self, extent, width, height):
        """Build GDAL-style geotransform dict"""
        if width <= 0 or height <= 0:
            width, height = 512, 512

        x_min = extent.xMinimum()
        y_max = extent.yMaximum()

        x_res = extent.width() / width if width > 0 else 1.0
        y_res = -(extent.height() / height) if height > 0 else -1.0

        return {
            'geo_transform': [x_min, x_res, 0, y_max, 0, y_res],
            'width': width,
            'height': height
        }

    def get_raster_info(self):
        """Get raster info dict"""
        return {
            'name': self.raster_layer.name(),
            'width': self.width,
            'height': self.height,
            'band_count': self.provider.bandCount(),
            'crs': self.raster_layer.crs().authid(),
            'extent': {
                'xmin': self.extent.xMinimum(),
                'ymin': self.extent.yMinimum(),
                'xmax': self.extent.xMaximum(),
                'ymax': self.extent.yMaximum()
            }
        }
