"""
Vector Generation with Individual Feature Support
Each detected object becomes its own polygon
"""

import numpy as np
from typing import List, Dict, Any, Optional
from qgis.core import (
    QgsVectorLayer, QgsField, QgsFeature, QgsGeometry,
    QgsCoordinateReferenceSystem, QgsPointXY, QgsProject,
    QgsFields, QgsWkbTypes, QgsCoordinateTransform,
    QgsUnitTypes
)
from qgis.PyQt.QtCore import QVariant


class VectorGenerator:
    """
    Convert instance segmentations to QGIS vector layers
    Each DetectedObject becomes an individual polygon feature
    """

    def __init__(self, crs: QgsCoordinateReferenceSystem):
        self.crs = crs
        self._metric_crs = self._get_metric_crs()
        self._transform_to_metric = None

        if self._metric_crs and self._metric_crs != self.crs:
            try:
                self._transform_to_metric = QgsCoordinateTransform(
                    self.crs, self._metric_crs, QgsProject.instance()
                )
            except Exception as e:
                print(f"⚠️  Could not create CRS transform: {e}")
                self._transform_to_metric = None

    def _get_metric_crs(self) -> Optional[QgsCoordinateReferenceSystem]:
        """
        Get an appropriate metric CRS for area calculations.
        For geographic CRS, project to UTM; for projected CRS, use as-is.
        """
        try:
            # Check if source CRS is geographic (degrees)
            if self.crs.isGeographic():
                # Try to determine UTM zone from centroid
                # Use Web Mercator as fallback (approximate meters at equator)
                print("ℹ️  Source CRS is geographic, using Web Mercator for area calc")
                return QgsCoordinateReferenceSystem('EPSG:3857')

            # Check map units using the modern QGIS API
            try:
                map_units = self.crs.mapUnits()
                # Use QgsUnitTypes enum - no iteration, just comparison
                if map_units == QgsUnitTypes.DistanceMeters:
                    return self.crs
                elif map_units == QgsUnitTypes.DistanceFeet:
                    return self.crs  # Still metric enough for our purposes
                else:
                    # Degrees or unknown - use Web Mercator
                    print(f"ℹ️  CRS units are not metric, using Web Mercator")
                    return QgsCoordinateReferenceSystem('EPSG:3857')
            except AttributeError:
                # Older API fallback
                units_str = str(self.crs.mapUnits())
                if 'meter' in units_str.lower() or 'metre' in units_str.lower():
                    return self.crs
                return QgsCoordinateReferenceSystem('EPSG:3857')

        except Exception as e:
            print(f"⚠️  CRS analysis failed: {e}, using Web Mercator")
            return QgsCoordinateReferenceSystem('EPSG:3857')

    def create_vector_layer(self,
                           detections: List,
                           class_name: str,
                           simplify_tolerance: float,
                           min_area_m2: float,
                           max_area_m2: float,
                           projector,
                           feedback=None) -> QgsVectorLayer:
        """
        Create a QGIS vector layer from individual detections
        """
        # Define schema
        fields = QgsFields()
        fields.append(QgsField('id', QVariant.Int))
        fields.append(QgsField('class', QVariant.String))
        fields.append(QgsField('area_m2', QVariant.Double))
        fields.append(QgsField('perimeter_m', QVariant.Double))
        fields.append(QgsField('confidence', QVariant.Double))
        fields.append(QgsField('bbox_area', QVariant.Double))
        fields.append(QgsField('solidity', QVariant.Double))

        # Create memory layer
        layer = QgsVectorLayer(
            f'Polygon?crs={self.crs.authid()}',
            f'{class_name}_segmentation',
            'memory'
        )
        layer.dataProvider().addAttributes(fields)
        layer.updateFields()

        features = []
        feature_id = 1
        total = len(detections)

        for idx, det in enumerate(detections):
            if feedback and idx % 10 == 0:
                progress = int(90 + 10 * (idx / max(total, 1)))
                feedback.setProgress(progress)

            try:
                # Project to geometry
                result = projector.project_detection(det, class_name)

                if result is None:
                    continue

                geom = result['geometry']

                # Apply simplification
                if simplify_tolerance > 0:
                    try:
                        geom_simplified = geom.simplify(simplify_tolerance)
                        if geom_simplified.isGeosValid():
                            geom = geom_simplified
                    except:
                        pass

                # Calculate area in metric CRS
                area_m2 = self._calculate_area_m2(geom)
                perimeter_m = self._calculate_perimeter_m(geom)

                # Apply area filters
                if area_m2 < min_area_m2:
                    continue
                if max_area_m2 > 0 and area_m2 > max_area_m2:
                    continue

                # Calculate shape metrics
                bbox_area = self._calculate_bbox_area(geom)
                solidity = self._calculate_solidity(geom)

                # Create feature
                feature = QgsFeature()
                feature.setGeometry(geom)
                feature.setAttributes([
                    feature_id,
                    class_name,
                    area_m2,
                    perimeter_m,
                    result['confidence'],
                    bbox_area,
                    solidity
                ])

                features.append(feature)
                feature_id += 1

            except Exception as e:
                print(f"⚠️  Feature {idx} failed: {e}")
                continue

        # Add all features
        layer.dataProvider().addFeatures(features)
        layer.updateExtents()

        if feedback:
            feedback.pushInfo(f"✅ Created {len(features)} individual polygons")

        return layer

    def _calculate_area_m2(self, geom: QgsGeometry) -> float:
        """Calculate area in square meters"""
        try:
            if self._transform_to_metric:
                geom_metric = QgsGeometry(geom)
                geom_metric.transform(self._transform_to_metric)
                return geom_metric.area()
            return geom.area()
        except Exception as e:
            print(f"⚠️  Area calc failed: {e}, using raw area")
            return geom.area()

    def _calculate_perimeter_m(self, geom: QgsGeometry) -> float:
        """Calculate perimeter in meters"""
        try:
            if self._transform_to_metric:
                geom_metric = QgsGeometry(geom)
                geom_metric.transform(self._transform_to_metric)
                return geom_metric.length()
            return geom.length()
        except Exception as e:
            return geom.length()

    def _calculate_bbox_area(self, geom: QgsGeometry) -> float:
        """Calculate bounding box area"""
        try:
            bbox = geom.boundingBox()
            return bbox.width() * bbox.height()
        except:
            return 0.0

    def _calculate_solidity(self, geom: QgsGeometry) -> float:
        """Calculate solidity: area / convex hull area"""
        try:
            hull = geom.convexHull()
            hull_area = hull.area()
            if hull_area > 0:
                return geom.area() / hull_area
        except:
            pass
        return 0.0

    def save_layer(self, layer: QgsVectorLayer, file_path: str) -> bool:
        """Save layer to GeoPackage"""
        from qgis.core import QgsVectorFileWriter

        try:
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.layerName = layer.name()

            result = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                file_path,
                QgsProject.instance().transformContext(),
                options
            )
            return result[0] == QgsVectorFileWriter.NoError
        except Exception as e:
            print(f"Save error: {e}")
            return False


# ============================================================
# Method for PreciseSegmenter output (BuildingInstance objects)
# ============================================================

def create_vector_layer_from_instances(self, instances, class_name, projector, feedback=None):
    """Create vector layer from PreciseSegmenter BuildingInstance objects"""
    from qgis.core import (
        QgsVectorLayer, QgsField, QgsFeature, QgsFields,
        QgsCoordinateTransform, QgsProject, QgsUnitTypes
    )
    from qgis.PyQt.QtCore import QVariant
    
    # Fields
    fields = QgsFields()
    fields.append(QgsField('id', QVariant.Int))
    fields.append(QgsField('class', QVariant.String))
    fields.append(QgsField('area_m2', QVariant.Double))
    fields.append(QgsField('perimeter_m', QVariant.Double))
    fields.append(QgsField('confidence', QVariant.Double))
    fields.append(QgsField('solidity', QVariant.Double))
    fields.append(QgsField('rectangularity', QVariant.Double))
    
    layer = QgsVectorLayer(
        f'Polygon?crs={self.crs.authid()}',
        f'{class_name}_segmentation',
        'memory'
    )
    layer.dataProvider().addAttributes(fields)
    layer.updateFields()
    
    # Set up metric CRS for area computation
    try:
        if self.crs.isGeographic():
            metric_crs = QgsCoordinateReferenceSystem('EPSG:3857')
        else:
            metric_crs = self.crs
        transform = QgsCoordinateTransform(self.crs, metric_crs, QgsProject.instance())
    except Exception:
        transform = None
    
    features = []
    fid = 1
    
    for inst in instances:
        if feedback:
            feedback.pushInfo(f"Projecting {fid}/{len(instances)}...")
        
        try:
            geom = projector.project(inst.mask, inst.tile_offset)
            if geom is None:
                continue
            
            # Compute area in metric CRS
            if transform:
                gm = QgsGeometry(geom)
                gm.transform(transform)
                area = gm.area()
                perim = gm.length()
            else:
                area = geom.area()
                perim = geom.length()
            
            f = QgsFeature()
            f.setGeometry(geom)
            f.setAttributes([
                fid, class_name, area, perim,
                inst.confidence,
                getattr(inst, 'solidity', 0.0),
                getattr(inst, 'rectangularity', 0.0)
            ])
            features.append(f)
            fid += 1
        except Exception as e:
            print(f"Feature {fid} failed: {e}")
            continue
    
    layer.dataProvider().addFeatures(features)
    layer.updateExtents()
    
    if feedback:
        feedback.pushInfo(f"✅ Created {len(features)} polygons")
    
    return layer


# Attach to class
from qgis.core import QgsVectorLayer as _QVL
VectorGenerator.create_vector_layer_from_instances = create_vector_layer_from_instances
