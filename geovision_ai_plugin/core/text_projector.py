"""
Project pixel-space text detections to QGIS geometries in map coordinates
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple
from qgis.core import (
    QgsGeometry, QgsPointXY, QgsVectorLayer, QgsFeature,
    QgsFields, QgsField, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsProject, QgsUnitTypes,
)
from qgis.PyQt.QtCore import QVariant

from .text_segmenter import TextDetection


class TextDetectionProjector:
    """Convert TextDetection masks → QGIS polygons + layer"""

    def __init__(self, transform: Dict, crs: QgsCoordinateReferenceSystem):
        self.gt = transform['geo_transform']   # [x0, dx, 0, y0, 0, dy]
        self.w = transform['width']
        self.h = transform['height']
        self.crs = crs
        # Metric CRS for accurate area
        self.metric_crs = QgsCoordinateReferenceSystem('EPSG:3857')
        self._transform_to_metric = QgsCoordinateTransform(
            crs, self.metric_crs, QgsProject.instance()
        )

    def project_mask(self, mask: np.ndarray) -> Tuple[object, float, float]:
        """
        Convert a binary mask into a QgsGeometry + area_m2 + perimeter_m.

        Returns (geom, area_m2, perimeter_m) or (None, 0, 0) if failed.
        """
        # Ensure mask is uint8
        mask_u8 = np.ascontiguousarray(mask.astype(np.uint8) * 255)

        # Find contours
        contours, _ = cv2.findContours(
            mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None, 0.0, 0.0

        contour = max(contours, key=cv2.contourArea)
        if len(contour) < 3:
            return None, 0.0, 0.0

        # Simplify contour
        epsilon = 0.003 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Convert to map coordinates
        x0, dx, _, y0, _, dy = self.gt
        points = []
        for p in approx:
            col, row = p[0]
            x = x0 + col * dx
            y = y0 + row * dy
            points.append(QgsPointXY(x, y))

        geom = QgsGeometry.fromPolygonXY([points])
        if not geom.isGeosValid():
            geom = geom.buffer(0, 3)
            if not geom.isGeosValid():
                return None, 0.0, 0.0

        # Compute area/perimeter in metric CRS
        gm = QgsGeometry(geom)
        gm.transform(self._transform_to_metric)
        area_m2 = gm.area()
        perim_m = gm.length()

        return geom, area_m2, perim_m

    def create_layer(
        self,
        detections: List[TextDetection],
        class_name: str,
        feedback=None,
    ) -> QgsVectorLayer:
        """Create a QGIS memory layer with one polygon per detection"""
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('class', QVariant.String))
        fields.append(QgsField('area_m2', QVariant.Double))
        fields.append(QgsField('perimeter_m', QVariant.Double))
        fields.append(QgsField('confidence', QVariant.Double))

        layer = QgsVectorLayer(
            f'Polygon?crs={self.crs.authid()}',
            f'{class_name}_segmentation',
            'memory',
        )
        layer.dataProvider().addAttributes(fields)
        layer.updateFields()

        features = []
        fid = 1
        for det in detections:
            geom, area_m2, perim_m = self.project_mask(det.mask)
            if geom is None:
                continue

            f = QgsFeature()
            f.setGeometry(geom)
            f.setAttributes([
                fid,
                class_name,
                area_m2,
                perim_m,
                float(det.confidence),
            ])
            features.append(f)
            det.polygon_map = geom
            det.area_m2 = area_m2
            det.perimeter_m = perim_m
            fid += 1

        layer.dataProvider().addFeatures(features)
        layer.updateExtents()

        if feedback:
            feedback.pushInfo(f"✅ Created {len(features)} polygons")

        return layer
