"""
Interactive click-to-add tool
Click on an image, SAM segments the object under the cursor
Adds it directly to the detected layer
"""

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsPointXY, QgsWkbTypes, QgsCoordinateTransform
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QObject
from qgis.PyQt.QtGui import QCursor, QColor
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtWidgets import QMessageBox
import numpy as np
import traceback


class ClickToSegmentTool(QgsMapToolEmitPoint):
    """
    Click on an object → SAM segments it → adds as new polygon to layer
    """
    
    segment_added = pyqtSignal(int)  # emits new feature id
    
    def __init__(self, canvas, iface, predictor, raster_layer, target_layer, class_name='building'):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.predictor = predictor
        self.raster_layer = raster_layer
        self.target_layer = target_layer
        self.class_name = class_name
        self.enabled = False
        
        # Preview rubber band
        self.preview_band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self.preview_band.setColor(QColor(0, 200, 100, 100))
        self.preview_band.setWidth(2)
        
        self.canvasClicked.connect(self.on_click)
    
    def activate(self):
        """Activate the tool"""
        self.enabled = True
        self.canvas.setCursor(QCursor(Qt.CrossCursor))
        self.iface.mapCanvas().refresh()
        print(f"🎯 Click-to-Segment activated for class: {self.class_name}")
        print("   Click on objects to segment them")
        print("   Right-click to exit")
    
    def deactivate(self):
        """Deactivate the tool"""
        self.enabled = False
        self.preview_band.reset(QgsWkbTypes.PolygonGeometry)
        super().deactivate()
    
    def canvasMoveEvent(self, event):
        """Preview on hover (optional - can be slow)"""
        pass
    
    def on_click(self, point, button):
        """Handle canvas click"""
        if button == Qt.RightButton:
            self.deactivate()
            return
        
        if not self.enabled:
            return
        
        try:
            self.segment_at_point(point)
        except Exception as e:
            print(f"❌ Segment failed: {e}")
            traceback.print_exc()
    
    def segment_at_point(self, map_point):
        """Segment object at the given map point"""
        from geovision_ai_plugin.core.raster_handler import RasterHandler
        
        # Get raster extent + image
        rh = RasterHandler(self.raster_layer)
        extent = self.raster_layer.extent()
        img, crs, transform = rh.get_raster_data_extent(extent, max_size=2048)
        
        if img is None or img.size == 0:
            QMessageBox.warning(None, "Error", "Could not load raster")
            return
        
        # Convert map point to pixel coordinates
        gt = transform['geo_transform']
        x0, dx, _, y0, _, dy = gt
        col = int((map_point.x() - x0) / dx)
        row = int((map_point.y() - y0) / dy)
        
        # Check bounds
        h, w = img.shape[:2]
        if col < 0 or col >= w or row < 0 or row >= h:
            print(f"⚠️ Click outside image bounds: ({col}, {row})")
            return
        
        print(f"🎯 Segmenting at pixel ({col}, {row})...")
        
        # Prepare image for SAM
        import cv2
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Set image in predictor
        self.predictor.set_image(img_bgr)
        
        # Point prompt
        point_coords = np.array([[col, row]])
        point_labels = np.array([1])  # 1 = positive point
        
        # Predict
        masks, scores, _ = self.predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            multimask_output=True
        )
        
        if masks is None or len(masks) == 0:
            print("❌ No mask generated")
            return
        
        # Pick best mask
        best_idx = int(np.argmax(scores))
        mask = masks[best_idx]
        score = float(scores[best_idx])
        
        area_px = int(np.sum(mask))
        if area_px < 20:
            print(f"⚠️ Mask too small: {area_px} pixels")
            return
        
        print(f"✅ Segment: {area_px} px, score {score:.3f}")
        
        # Convert mask to polygon
        mask_uint8 = np.ascontiguousarray(mask.astype(np.uint8) * 255)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return
        
        # Take largest contour
        contour = max(contours, key=cv2.contourArea)
        if len(contour) < 3:
            return
        
        # Simplify
        epsilon = 0.002 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # Convert to map coordinates
        points = []
        for p in approx:
            px, py = p[0]
            map_x = x0 + px * dx
            map_y = y0 + py * dy
            points.append(QgsPointXY(map_x, map_y))
        
        geom = QgsGeometry.fromPolygonXY([points])
        
        # Ensure target layer is editable
        if not self.target_layer.isEditable():
            self.target_layer.startEditing()
        
        # Compute area in metric CRS
        from qgis.core import QgsCoordinateReferenceSystem
        metric_crs = QgsCoordinateReferenceSystem('EPSG:3857')
        ctr = QgsCoordinateTransform(self.target_layer.crs(), metric_crs, QgsProject.instance())
        geom_metric = QgsGeometry(geom)
        geom_metric.transform(ctr)
        area_m2 = geom_metric.area()
        perim_m = geom_metric.length()
        
        # Add feature
        feat = QgsFeature(self.target_layer.fields())
        feat.setGeometry(geom)
        
        # Get field values
        fields = self.target_layer.fields()
        field_names = [f.name() for f in fields]
        
        for i, name in enumerate(field_names):
            if name == 'id':
                # Find max id
                max_id = 0
                for f in self.target_layer.getFeatures():
                    if 'id' in field_names:
                        try:
                            max_id = max(max_id, int(f['id']))
                        except:
                            pass
                feat.setAttribute('id', max_id + 1)
            elif name == 'class':
                feat.setAttribute('class', self.class_name)
            elif name == 'area_m2':
                feat.setAttribute('area_m2', area_m2)
            elif name == 'perimeter_m':
                feat.setAttribute('perimeter_m', perim_m)
            elif name == 'confidence':
                feat.setAttribute('confidence', score)
            elif name == 'solidity':
                feat.setAttribute('solidity', 0.0)
            elif name == 'rectangularity':
                feat.setAttribute('rectangularity', 0.0)
        
        self.target_layer.addFeature(feat)
        self.target_layer.triggerRepaint()
        
        # Emit signal
        self.segment_added.emit(feat.id())
        
        print(f"✅ Added polygon: {area_m2:.1f} m², confidence {score:.2f}")
