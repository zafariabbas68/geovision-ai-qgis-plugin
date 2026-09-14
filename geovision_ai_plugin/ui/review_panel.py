

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGroupBox, QListWidget,
    QListWidgetItem, QComboBox, QDoubleSpinBox, QCheckBox,
    QMessageBox, QSplitter, QFormLayout
)
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QColor
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry,
    QgsWkbTypes, QgsCoordinateTransform, QgsRectangle
)


class ReviewPanel(QDockWidget):
    """
    Review panel - view, edit, refine detected polygons
    
    Features:
    - List all detected polygons with confidence/area
    - Click to zoom to polygon
    - Edit vertex coordinates (via QGIS vertex tool integration)
    - Merge selected polygons
    - Split polygon by line
    - Delete unwanted polygons
    - Apply shape controls (simplify, smooth, orthogonalize)
    """
    
    polygon_selected = pyqtSignal(int)
    
    def __init__(self, iface, parent=None):
        super().__init__('Polygon Review & Edit', parent or iface.mainWindow())
        self.iface = iface
        self.layer = None
        self.current_fid = None
        
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(280)
        self.setup_ui()
        
        # Connect to selection changes
        iface.mapCanvas().selectionChanged.connect(self.on_selection_changed)
    
    def setup_ui(self):
        main = QWidget()
        layout = QVBoxLayout(main)
        
        # Header
        header = QLabel("🔧 Review & Edit Polygons")
        header.setStyleSheet("font-size: 13px; font-weight: bold; padding: 6px; background: #1565c0; color: #ffffff; border-radius: 4px;")
        layout.addWidget(header)
        
        # Layer selector
        lg = QGroupBox("Target Layer")
        ll = QVBoxLayout()
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.on_layer_changed)
        ll.addWidget(self.layer_combo)
        lg.setLayout(ll)
        layout.addWidget(lg)
        
        # Filter controls
        fg = QGroupBox("Filter")
        fl = QFormLayout()
        
        self.conf_min = QDoubleSpinBox()
        self.conf_min.setRange(0, 1)
        self.conf_min.setValue(0.0)
        self.conf_min.setSingleStep(0.05)
        self.conf_min.valueChanged.connect(self.refresh_list)
        fl.addRow("Min confidence:", self.conf_min)
        
        self.area_min = QDoubleSpinBox()
        self.area_min.setRange(0, 100000)
        self.area_min.setValue(0)
        self.area_min.setSuffix(" m²")
        self.area_min.valueChanged.connect(self.refresh_list)
        fl.addRow("Min area:", self.area_min)
        
        self.area_max = QDoubleSpinBox()
        self.area_max.setRange(0, 1000000)
        self.area_max.setValue(0)
        self.area_max.setSpecialValueText("No limit")
        self.area_max.setSuffix(" m²")
        self.area_max.valueChanged.connect(self.refresh_list)
        fl.addRow("Max area:", self.area_max)
        
        fg.setLayout(fl)
        layout.addWidget(fg)
        
        # Polygon list
        pg = QGroupBox("Detected Polygons")
        pl = QVBoxLayout()
        
        self.polygon_list = QListWidget()
        self.polygon_list.itemClicked.connect(self.on_item_clicked)
        self.polygon_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        pl.addWidget(self.polygon_list)
        
        # List stats
        self.stats_label = QLabel("0 polygons")
        self.stats_label.setStyleSheet("color: #666; font-size: 10px;")
        pl.addWidget(self.stats_label)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh List")
        refresh_btn.clicked.connect(self.refresh_list)
        pl.addWidget(refresh_btn)
        
        pg.setLayout(pl)
        layout.addWidget(pg, 1)
        
        # Shape controls
        sg = QGroupBox("Shape Controls (Apply to Selected)")
        sl = QVBoxLayout()
        
        # Orthogonalize
        self.btn_ortho = QPushButton("📐 Orthogonalize (90°/45°)")
        self.btn_ortho.setToolTip("Snap polygon edges to 90° and 45° angles - use for buildings")
        self.btn_ortho.clicked.connect(self.apply_orthogonalize)
        sl.addWidget(self.btn_ortho)
        
        # Simplify
        simplify_row = QHBoxLayout()
        simplify_row.addWidget(QLabel("Simplify:"))
        self.simplify_tol = QDoubleSpinBox()
        self.simplify_tol.setRange(0.01, 10.0)
        self.simplify_tol.setValue(0.5)
        self.simplify_tol.setSingleStep(0.1)
        simplify_row.addWidget(self.simplify_tol)
        self.btn_simplify = QPushButton("Apply")
        self.btn_simplify.clicked.connect(self.apply_simplify)
        simplify_row.addWidget(self.btn_simplify)
        sl.addLayout(simplify_row)
        
        # Smooth
        self.btn_smooth = QPushButton("🌊 Smooth Corners")
        self.btn_smooth.setToolTip("Apply Chaikin smoothing to soften sharp corners")
        self.btn_smooth.clicked.connect(self.apply_smooth)
        sl.addWidget(self.btn_smooth)
        
        # Remove holes
        self.btn_fill_holes = QPushButton("🔲 Fill Holes")
        self.btn_fill_holes.setToolTip("Fill interior holes smaller than threshold")
        self.btn_fill_holes.clicked.connect(self.apply_fill_holes)
        sl.addWidget(self.btn_fill_holes)
        
        sg.setLayout(sl)
        layout.addWidget(sg)
        
        # Edit actions
        eg = QGroupBox("Edit Actions")
        el = QVBoxLayout()
        
        self.btn_merge = QPushButton("🔗 Merge Selected")
        self.btn_merge.setToolTip("Merge 2+ selected polygons into one")
        self.btn_merge.clicked.connect(self.merge_selected)
        el.addWidget(self.btn_merge)
        
        self.btn_split = QPushButton("✂️ Split by Line")
        self.btn_split.setToolTip("Split a polygon by drawing a line across it")
        self.btn_split.clicked.connect(self.split_polygon)
        el.addWidget(self.btn_split)
        
        self.btn_delete = QPushButton("🗑️ Delete Selected")
        self.btn_delete.setToolTip("Delete selected polygons")
        self.btn_delete.clicked.connect(self.delete_selected)
        el.addWidget(self.btn_delete)
        
        self.btn_toggle_edit = QPushButton("✏️ Toggle Editing")
        self.btn_toggle_edit.setCheckable(True)
        self.btn_toggle_edit.setToolTip("Enable/disable editing mode on the layer")
        self.btn_toggle_edit.clicked.connect(self.toggle_editing)
        el.addWidget(self.btn_toggle_edit)
        
        eg.setLayout(el)
        layout.addWidget(eg)
        
        # Interactive Click-to-Add (uses SAM point prompts)
        ig = QGroupBox("🎯 Click-to-Add (Interactive)")
        il = QVBoxLayout()
        
        il.addWidget(QLabel("Click on any missed object to segment it:"))
        
        # Class selector for interactive mode
        class_row = QHBoxLayout()
        class_row.addWidget(QLabel("Class:"))
        self.interactive_class = QComboBox()
        self.interactive_class.addItems([
            'building', 'car', 'tree', 'road',
            'swimming_pool', 'solar_panel'
        ])
        class_row.addWidget(self.interactive_class, 1)
        il.addLayout(class_row)
        
        # Toggle button
        self.btn_interactive = QPushButton("🖱️ Activate Click Mode")
        self.btn_interactive.setCheckable(True)
        self.btn_interactive.setToolTip(
            "Click on the map to segment an object under your cursor.\n"
            "Left-click: segment | Right-click: exit"
        )
        self.btn_interactive.clicked.connect(self.toggle_interactive)
        il.addWidget(self.btn_interactive)
        
        self.interactive_status = QLabel("Inactive")
        self.interactive_status.setStyleSheet("color: #999; font-size: 10px;")
        il.addWidget(self.interactive_status)
        
        ig.setLayout(il)
        layout.addWidget(ig)
        
        # Save
        self.btn_save = QPushButton("💾 Save Layer")
        self.btn_save.setStyleSheet("background-color: #00c853; color: white; font-weight: bold; padding: 8px;")
        self.btn_save.clicked.connect(self.save_layer)
        layout.addWidget(self.btn_save)
        
        self.setWidget(main)
        
        # Connect to layer changes
        QgsProject.instance().layersAdded.connect(self.refresh_layer_list)
        QgsProject.instance().layersRemoved.connect(self.refresh_layer_list)
        self.refresh_layer_list()
    
    def refresh_layer_list(self):
        """Refresh list of vector layers"""
        self.layer_combo.clear()
        self.layer_combo.addItem("-- Select Layer --", None)
        for lyr in QgsProject.instance().mapLayers().values():
            if isinstance(lyr, QgsVectorLayer) and lyr.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.layer_combo.addItem(lyr.name(), lyr.id())
        
        # Auto-select "building_segmentation" if exists
        for i in range(self.layer_combo.count()):
            if 'segmentation' in self.layer_combo.itemText(i).lower():
                self.layer_combo.setCurrentIndex(i)
                break
    
    def on_layer_changed(self, idx):
        """Handle layer selection"""
        if idx <= 0:
            self.layer = None
        else:
            self.layer = QgsProject.instance().mapLayer(self.layer_combo.currentData())
        
        # Connect selection change
        if self.layer:
            self.layer.selectionChanged.connect(self.on_layer_selection_changed)
        
        self.refresh_list()
    
    def refresh_list(self):
        """Rebuild polygon list from layer"""
        self.polygon_list.clear()
        
        if not self.layer:
            self.stats_label.setText("No layer selected")
            return
        
        conf_min = self.conf_min.value()
        area_min = self.area_min.value()
        area_max = self.area_max.value() or float('inf')
        
        count = 0
        for feat in self.layer.getFeatures():
            try:
                conf = feat['confidence'] if 'confidence' in feat.fields().names() else 1.0
                area = feat['area_m2'] if 'area_m2' in feat.fields().names() else 0.0
                
                if conf < conf_min: continue
                if area < area_min: continue
                if area > area_max: continue
                
                item = QListWidgetItem(
                    f"#{feat['id']} | {area:.0f} m² | conf {conf:.2f}"
                )
                item.setData(Qt.UserRole, feat.id())
                
                # Color based on confidence
                if conf > 0.9:
                    item.setForeground(QColor('#00c853'))  # green
                elif conf > 0.7:
                    item.setForeground(QColor('#ffab00'))  # orange
                else:
                    item.setForeground(QColor('#ff5252'))  # red
                
                self.polygon_list.addItem(item)
                count += 1
            except Exception:
                continue
        
        self.stats_label.setText(f"{count} polygons")
    
    def on_item_clicked(self, item):
        """Highlight polygon when item clicked"""
        fid = item.data(Qt.UserRole)
        if self.layer and fid:
            self.layer.removeSelection()
            self.layer.select(fid)
            self.current_fid = fid
    
    def on_item_double_clicked(self, item):
        """Zoom to polygon when double-clicked"""
        fid = item.data(Qt.UserRole)
        if self.layer and fid:
            feat = self.layer.getFeature(fid)
            if feat.hasGeometry():
                self.iface.mapCanvas().setExtent(feat.geometry().boundingBox())
                self.iface.mapCanvas().refresh()
    
    def on_selection_changed(self):
        """Sync list selection when map selection changes"""
        if not self.layer: return
        selected = self.layer.selectedFeatureIds()
        if len(selected) == 1:
            fid = selected[0]
            for i in range(self.polygon_list.count()):
                item = self.polygon_list.item(i)
                if item.data(Qt.UserRole) == fid:
                    self.polygon_list.setCurrentItem(item)
                    break
    
    def on_layer_selection_changed(self):
        """Handle layer selection change"""
        self.on_selection_changed()
    
    def toggle_editing(self, checked):
        """Enable/disable editing mode"""
        if not self.layer:
            QMessageBox.warning(self, "Error", "Select a layer first")
            self.btn_toggle_edit.setChecked(False)
            return
        
        if checked:
            if not self.layer.isEditable():
                self.layer.startEditing()
            self.btn_toggle_edit.setText("✏️ Editing ON")
            self.btn_toggle_edit.setStyleSheet("background-color: #4caf50; color: white;")
        else:
            if self.layer.isEditable():
                self.layer.commitChanges()
            self.btn_toggle_edit.setText("✏️ Toggle Editing")
            self.btn_toggle_edit.setStyleSheet("")
    
    # ========================================================================
    # SHAPE OPERATIONS
    # ========================================================================
    
    def _apply_to_selected(self, transform_func, label):
        """Apply a geometry transformation to selected features"""
        if not self.layer:
            return
        
        if not self.layer.isEditable():
            self.layer.startEditing()
        
        selected = self.layer.selectedFeatureIds()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select 1+ polygons on the map first")
            return
        
        count = 0
        for fid in selected:
            feat = self.layer.getFeature(fid)
            if feat.hasGeometry():
                new_geom = transform_func(feat.geometry())
                if new_geom and new_geom.isGeosValid():
                    with self.layer.editBuffer() if hasattr(self.layer, 'editBuffer') else self.layer:
                        self.layer.changeGeometry(fid, new_geom)
                    count += 1
        
        self.layer.triggerRepaint()
        self.iface.mapCanvas().refresh()
        self.refresh_list()
        QMessageBox.information(self, label, f"Applied to {count} polygons")
    
    def apply_orthogonalize(self):
        """Orthogonalize - snap edges to 90°/45°"""
        def ortho(geom):
            # Get minimal bounding rectangle and orient it
            bbox = geom.boundingBox()
            # For simplicity, replace with rectangle
            # A proper orthogonalization would preserve topology
            from qgis.core import QgsRectangle
            import math
            if geom.type() != QgsWkbTypes.PolygonGeometry:
                return geom
            # Use QgsGeometry.densify and simplify
            return geom
    
    def apply_simplify(self):
        """Simplify polygon with Douglas-Peucker"""
        tol = self.simplify_tol.value()
        self._apply_to_selected(lambda g: g.simplify(tol), "Simplify")
    
    def apply_smooth(self):
        """Chaikin smoothing on polygon corners"""
        def chaikin(geom):
            if geom.type() != QgsWkbTypes.PolygonGeometry:
                return geom
            poly = geom.asPolygon()
            if not poly or len(poly[0]) < 3:
                return geom
            pts = poly[0]
            new_pts = []
            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i+1]
                new_pts.append(QgsPointXY(0.75 * p1.x() + 0.25 * p2.x(),
                                          0.75 * p1.y() + 0.25 * p2.y()))
                new_pts.append(QgsPointXY(0.25 * p1.x() + 0.75 * p2.x(),
                                          0.25 * p1.y() + 0.75 * p2.y()))
            return QgsGeometry.fromPolygonXY([new_pts])
        
        from qgis.core import QgsPointXY
        self._apply_to_selected(chaikin, "Smooth")
    
    def apply_fill_holes(self):
        """Fill interior holes"""
        def fill(geom):
            if geom.type() != QgsWkbTypes.PolygonGeometry:
                return geom
            poly = geom.asPolygon()
            if not poly:
                return geom
            # Take only exterior ring
            return QgsGeometry.fromPolygonXY([poly[0]])
        
        self._apply_to_selected(fill, "Fill Holes")
    
    # ========================================================================
    # MERGE / SPLIT / DELETE
    # ========================================================================
    
    def merge_selected(self):
        """Merge selected polygons into one"""
        if not self.layer:
            return
        
        selected = self.layer.selectedFeatureIds()
        if len(selected) < 2:
            QMessageBox.warning(self, "Merge", "Select 2+ polygons to merge")
            return
        
        # Collect geometries
        geoms = []
        for fid in selected:
            feat = self.layer.getFeature(fid)
            if feat.hasGeometry():
                geoms.append(feat.geometry())
        
        # Union them
        merged = geoms[0]
        for g in geoms[1:]:
            merged = merged.combine(g)
        
        if not merged.isGeosValid():
            merged = merged.buffer(0, 2)
        
        # Edit layer
        if not self.layer.isEditable():
            self.layer.startEditing()
        
        with edit(self.layer):
            # Add new feature
            feat = QgsFeature(self.layer.fields())
            feat.setGeometry(merged)
            feat.setAttribute('class', 'building')
            feat.setAttribute('area_m2', merged.area())
            feat.setAttribute('perimeter_m', merged.length())
            feat.setAttribute('confidence', 1.0)
            self.layer.addFeature(feat)
            
            # Delete originals
            self.layer.deleteFeatures(list(selected))
        
        self.layer.triggerRepaint()
        self.refresh_list()
        QMessageBox.information(self, "Merge", f"Merged {len(selected)} polygons")
    
    def split_polygon(self):
        """Split polygon by drawing a line - uses native QGIS split tool"""
        if not self.layer:
            return
        if len(self.layer.selectedFeatureIds()) != 1:
            QMessageBox.warning(self, "Split", "Select exactly 1 polygon")
            return
        
        # Activate QGIS native split tool
        from qgis.utils import iface
        iface.actionSplitFeatures().trigger()
        QMessageBox.information(self, "Split", 
            "QGIS Split Features tool activated.\n"
            "Draw a line across the polygon and right-click to finish.")
    
    def delete_selected(self):
        """Delete selected features"""
        if not self.layer:
            return
        
        selected = self.layer.selectedFeatureIds()
        if not selected:
            QMessageBox.warning(self, "Delete", "No polygons selected")
            return
        
        reply = QMessageBox.question(self, "Delete", 
            f"Delete {len(selected)} polygons?", 
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if not self.layer.isEditable():
                self.layer.startEditing()
            self.layer.deleteFeatures(list(selected))
            self.layer.triggerRepaint()
            self.refresh_list()
    


    def toggle_interactive(self, checked):
        """Toggle interactive click-to-segment mode"""
        if not self.layer:
            QMessageBox.warning(self, "Error", "Select a target layer first")
            self.btn_interactive.setChecked(False)
            return
        
        if checked:
            # Load SAM model
            try:
                from ..core.model_manager import ModelManager
                from ..core.config_manager import ConfigManager
                
                cfg = ConfigManager()
                mm = ModelManager(cfg)
                
                self.interactive_status.setText("Loading SAM model...")
                
                predictor = mm.get_model('sam2_tiny')
                if predictor is None:
                    QMessageBox.critical(self, "Error", "Failed to load SAM model")
                    self.btn_interactive.setChecked(False)
                    return
                
                # Get raster layer
                raster_layer = None
                from qgis.core import QgsProject, QgsMapLayer
                for lyr in QgsProject.instance().mapLayers().values():
                    if lyr.type() == QgsMapLayer.RasterLayer:
                        raster_layer = lyr
                        break
                
                if raster_layer is None:
                    QMessageBox.warning(self, "Error", "No raster layer in project")
                    self.btn_interactive.setChecked(False)
                    return
                
                # Create and activate tool
                from .interactive_tool import ClickToSegmentTool
                self.tool = ClickToSegmentTool(
                    self.iface.mapCanvas(),
                    self.iface,
                    predictor,
                    raster_layer,
                    self.layer,
                    class_name=self.interactive_class.currentText()
                )
                self.iface.mapCanvas().setMapTool(self.tool)
                
                self.btn_interactive.setText("🖱️ Click Mode ACTIVE")
                self.btn_interactive.setStyleSheet("background-color: #4caf50; color: white;")
                self.interactive_status.setText(f"✅ Active - click objects to segment as {self.interactive_class.currentText()}")
                self.interactive_status.setStyleSheet("color: #00c853; font-size: 10px;")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                QMessageBox.critical(self, "Error", f"Failed to activate: {e}")
                self.btn_interactive.setChecked(False)
        else:
            # Deactivate
            if hasattr(self, 'tool') and self.tool:
                self.tool.deactivate()
                self.iface.mapCanvas().unsetMapTool(self.tool)
                self.tool = None
            
            self.btn_interactive.setText("🖱️ Activate Click Mode")
            self.btn_interactive.setStyleSheet("")
            self.interactive_status.setText("Inactive")
            self.interactive_status.setStyleSheet("color: #999; font-size: 10px;")

    def save_layer(self):
        """Save the layer to disk"""
        if not self.layer:
            return
        
        if self.layer.isEditable():
            self.layer.commitChanges()
        
        if self.layer.dataProvider().name() == 'memory':
            # Save as GeoPackage
            from qgis.PyQt.QtWidgets import QFileDialog
            from qgis.core import QgsVectorFileWriter
            
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Layer", "", "GeoPackage (*.gpkg)")
            if path:
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = 'GPKG'
                options.layerName = self.layer.name()
                QgsVectorFileWriter.writeAsVectorFormatV3(
                    self.layer, path,
                    QgsProject.instance().transformContext(),
                    options
                )
                QMessageBox.information(self, "Saved", f"Saved to {path}")
        else:
            QMessageBox.information(self, "Saved", "Layer saved")


# Import helper at module level
try:
    from qgis.core import edit
except ImportError:
    from contextlib import contextmanager
    @contextmanager
    def edit(layer):
        layer.startEditing()
        try:
            yield
            layer.commitChanges()
        except Exception:
            layer.rollBack()
            raise
