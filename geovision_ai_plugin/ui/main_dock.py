"""
GeoVision AI - Main UI with Precise Segmentation
"""

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QLineEdit,
    QDoubleSpinBox, QGroupBox, QProgressBar, QMessageBox,
    QCheckBox, QTabWidget, QFrame, QScrollArea, QFormLayout,
    QSlider
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.core import QgsProject, QgsMapLayer
import traceback


class SegmentationWorker(QThread):
    """Background worker for segmentation"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(object, object)
    
    def __init__(self, raster_layer, extent, class_name, config):
        super().__init__()
        self.raster_layer = raster_layer
        self.extent = extent
        self.class_name = class_name
        self.config = config
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def run(self):
        try:
            from qgis.core import QgsProcessingFeedback
            from ..core.raster_handler import RasterHandler
            from ..core.model_manager import ModelManager
            from ..core.precise_segmenter import PreciseSegmenter, PreciseConfig
            from ..core.vector_generator import VectorGenerator
            from ..core.config_manager import ConfigManager
            
            feedback = QgsProcessingFeedback()
            feedback.progressChanged.connect(self.progress.emit)
            
            # Load raster
            self.status.emit("Loading raster at native resolution...")
            rh = RasterHandler(self.raster_layer)
            
            # Use native extent + reasonable max size
            img, crs, transform = rh.get_raster_data_extent(
                self.extent, max_size=self.config.get('max_size', 2048)
            )
            self.status.emit(f"Image: {img.shape}")
            
            if self._cancelled: return
            
            # Load model
            self.status.emit("Loading SAM model...")
            cfg = ConfigManager()
            mm = ModelManager(cfg)
            model = mm.get_model(self.config.get('model_type', 'sam2_tiny'))
            
            if model is None:
                self.finished.emit(None, "Model failed to load")
                return
            
            if self._cancelled: return
            
            # Run precise segmentation
            self.status.emit("Running text-prompted segmentation...")
            
            # NEW: Use text-prompted detection with LangSAM
            from ..core.text_segmenter import TextPromptedSegmenter
            from ..core.text_projector import TextDetectionProjector
            
            # Compute pixel area in m² for area filtering
            gt = transform['geo_transform']
            pixel_area_m2 = abs(gt[1] * gt[5])
            
            # Run text-prompted detection
            text_seg = TextPromptedSegmenter()
            detections = text_seg.segment_image(
                img,
                text_prompt=self.class_name,
                box_threshold=self.config.get('box_threshold'),
                text_threshold=self.config.get('text_threshold'),
                min_area_m2=self.config.get('min_area', 0.0),
                max_area_m2=self.config.get('max_area', 1e9) if self.config.get('max_area', 0) > 0 else 1e9,
                pixel_area_m2=pixel_area_m2,
                feedback=feedback,
            )
            
            self.status.emit(f"Found {len(detections)} objects")
            
            if self._cancelled: return
            
            # Project to QGIS geometries
            self.status.emit("Projecting to map coordinates...")
            projector = TextDetectionProjector(transform, crs)
            layer = projector.create_layer(detections, self.class_name, feedback)
            
            self.finished.emit(layer, None)
            return
            
            # ---- OLD CODE BELOW (kept for reference, never reached) ----
            self.status.emit("Running precise segmentation...")
            instances = []
            layer = None
            
            self.status.emit(f"Found {len(instances)} buildings")
            
            if self._cancelled: return
            
            # Project to map coordinates
            self.status.emit("Projecting to map coordinates...")
            from ..core.precise_segmenter import PreciseSegmenter as PS
            
            projector = _MapProjector(transform, crs)
            vg = VectorGenerator(crs)
            
            layer = vg.create_vector_layer_from_instances(
                instances=instances,
                class_name=self.class_name,
                projector=projector,
                feedback=feedback
            )
            
            self.status.emit(f"Created {layer.featureCount()} polygons")
            self.finished.emit(layer, None)
        
        except Exception as e:
            err = f"{e}\n{traceback.format_exc()}"
            self.status.emit(f"Error: {e}")
            self.finished.emit(None, err)


class _MapProjector:
    """Projects mask contours to map coordinates"""
    def __init__(self, transform, crs):
        self.gt = transform['geo_transform']
        self.crs = crs
        self.w = transform['width']
        self.h = transform['height']
    
    def project(self, mask: 'np.ndarray', offset: tuple):
        """Project mask to QgsGeometry"""
        import numpy as np
        import cv2
        from qgis.core import QgsGeometry, QgsPointXY
        
        # Place mask in full image
        full = np.zeros((self.h, self.w), dtype=np.uint8)
        ox, oy = offset
        mh, mw = mask.shape
        ye = min(oy + mh, self.h)
        xe = min(ox + mw, self.w)
        full[oy:ye, ox:xe] = mask[:ye-oy, :xe-ox].astype(np.uint8)
        
        # Extract contour
        contours, _ = cv2.findContours(full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        
        contour = max(contours, key=cv2.contourArea)
        if len(contour) < 3:
            return None
        
        # Convert to map coords
        x0, dx, _, y0, _, dy = self.gt
        points = []
        for p in contour:
            col, row = p[0]
            points.append(QgsPointXY(x0 + col * dx, y0 + row * dy))
        
        geom = QgsGeometry.fromPolygonXY([points])
        if not geom.isGeosValid():
            geom = geom.buffer(0, 5)
            if not geom.isGeosValid():
                return None
        return geom


class MainDockWidget(QDockWidget):
    """Main dock widget - Precise mode"""
    
    TEMPLATES = {
        '🏠 Buildings': 'building',
        '🌳 Trees': 'tree',
        '🛣️ Roads': 'road',
        '🏊 Pools': 'swimming pool',
        '☀️ Solar': 'solar panel',
        '🚗 Vehicles': 'car',
    }
    
    def __init__(self, iface, config_manager):
        super().__init__('GeoVision AI', iface.mainWindow())
        self.iface = iface
        self.config_manager = config_manager
        self.raster_layer = None
        self.worker = None
        
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.setMinimumWidth(380)
        self.setup_ui()
        self.update_layer_list()
        
        QgsProject.instance().layersAdded.connect(self.update_layer_list)
        QgsProject.instance().layersRemoved.connect(self.update_layer_list)
    
    def setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("🎯 Precise Building Detection")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 6px; background: #1565c0; color: #ffffff; border-radius: 4px;")
        layout.addWidget(header)
        
        # Layer selection
        lg = QGroupBox("1. Input Imagery")
        ll = QVBoxLayout()
        self.layer_combo = QComboBox()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.update_layer_list)
        row = QHBoxLayout()
        row.addWidget(self.layer_combo, 1)
        row.addWidget(refresh_btn)
        ll.addLayout(row)
        lg.setLayout(ll)
        layout.addWidget(lg)
        
        # Zone
        zg = QGroupBox("2. Detection Zone")
        zl = QVBoxLayout()
        self.zone_view = QPushButton("📍 Use Current Map View")
        self.zone_view.setCheckable(True)
        self.zone_view.setChecked(True)
        self.zone_full = QPushButton("🗺️ Use Full Layer Extent")
        self.zone_full.setCheckable(True)
        self.zone_view.clicked.connect(lambda: self._set_zone('view'))
        self.zone_full.clicked.connect(lambda: self._set_zone('full'))
        zl.addWidget(self.zone_view)
        zl.addWidget(self.zone_full)
        self.zone_label = QLabel("Using current map view")
        self.zone_label.setStyleSheet("color: #666; font-size: 10px;")
        zl.addWidget(self.zone_label)
        zg.setLayout(zl)
        layout.addWidget(zg)
        
        # Class
        cg = QGroupBox("3. What to Detect")
        cl = QVBoxLayout()
        self.class_input = QLineEdit()
        self.class_input.setPlaceholderText("e.g., building, tree, solar panel")
        self.class_input.setText("building")
        self.class_input.setReadOnly(True)
        self.class_input.setStyleSheet("background-color: #f0f0f0; color: #333; font-weight: bold;")
        self.class_input.textChanged.connect(self._on_class_changed)
        cl.addWidget(self.class_input)
        cg.setLayout(cl)
        layout.addWidget(cg)
        
        # Detection settings
        
        # ── NEW: Exemplar / Sample mode ──
        exemplar_group = QGroupBox("3.5. Sample-Based Detection (Optional)")
        exemplar_layout = QVBoxLayout()
        
        info_label = QLabel(
            "Click \"Pick Sample\" then click on ONE example object\n"
            "(e.g. a tree). The AI will find look-alikes."
        )
        info_label.setStyleSheet("color: #555; font-size: 10px;")
        info_label.setWordWrap(True)
        exemplar_layout.addWidget(info_label)
        
        self.pick_sample_btn = QPushButton("🎯 Pick Sample from Map")
        self.pick_sample_btn.setCheckable(True)
        self.pick_sample_btn.clicked.connect(self._on_pick_sample)
        exemplar_layout.addWidget(self.pick_sample_btn)
        
        self.exemplar_status = QLabel("No sample picked")
        self.exemplar_status.setStyleSheet("color: #999; font-size: 10px;")
        exemplar_layout.addWidget(self.exemplar_status)
        
        self.use_exemplar_cb = QCheckBox("Use sample-based detection")
        self.use_exemplar_cb.setEnabled(False)
        exemplar_layout.addWidget(self.use_exemplar_cb)
        
        exemplar_group.setLayout(exemplar_layout)
        layout.addWidget(exemplar_group)
        
        # Store as instance attr
        self.exemplar_group = exemplar_group
        
        dg = QGroupBox("4. Detection Settings")
        dl = QFormLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'DINO + SAM (Building Footprints)',
        ])
        dl.addRow("Model:", self.model_combo)
        
        # Confidence slider
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 95)
        self.conf_slider.setValue(10)
        self.conf_label = QLabel("0.10")
        self.conf_label.setFixedWidth(40)
        self.conf_slider.valueChanged.connect(lambda v: self.conf_label.setText(f"{v/100:.2f}"))
        conf_row = QHBoxLayout()
        conf_row.addWidget(self.conf_slider)
        conf_row.addWidget(self.conf_label)
        dl.addRow("Confidence:", conf_row)
        
        self.min_area = QDoubleSpinBox()
        self.min_area.setRange(0, 100000)
        self.min_area.setValue(10)
        self.min_area.setSuffix(" m²")
        dl.addRow("Min area:", self.min_area)
        
        self.max_area = QDoubleSpinBox()
        self.max_area.setRange(0, 10000000)
        self.max_area.setValue(8000)
        self.max_area.setSuffix(" m²")
        dl.addRow("Max area:", self.max_area)
        
        self.max_size = QComboBox()
        self.max_size.addItems(['1024 (fast)', '2048 (balanced)', '4096 (precise)', 'Native (slow)'])
        self.max_size.setCurrentIndex(1)
        dl.addRow("Resolution:", self.max_size)
        
        dg.setLayout(dl)
        layout.addWidget(dg)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        self.status = QLabel("Ready")
        self.status.setStyleSheet("color: #666; padding: 4px;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        
        # Buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("▶ Start Precise Detection")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32; color: white;
                font-weight: bold; padding: 10px;
                border-radius: 4px; font-size: 13px;
            }
        """)
        self.start_btn.clicked.connect(self.start_detection)
        
        self.cancel_btn = QPushButton("⏹ Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet("background-color: #c62828; color: white; padding: 10px;")
        self.cancel_btn.clicked.connect(self.cancel_detection)
        
        btn_row.addWidget(self.start_btn, 2)
        btn_row.addWidget(self.cancel_btn, 1)
        layout.addLayout(btn_row)
        
        scroll.setWidget(main)
        self.setWidget(scroll)
    
    def _set_zone(self, mode):
        if mode == 'view':
            self.zone_view.setChecked(True)
            self.zone_full.setChecked(False)
            self.zone_label.setText("Using current map view")
        else:
            self.zone_full.setChecked(True)
            self.zone_view.setChecked(False)
            self.zone_label.setText("Using full layer extent")
    
    def update_layer_list(self):
        self.layer_combo.clear()
        self.layer_combo.addItem('-- Select Raster --', None)
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.type() == QgsMapLayer.RasterLayer:
                self.layer_combo.addItem(lyr.name(), lyr.id())
        if self.layer_combo.count() == 2:
            self.layer_combo.setCurrentIndex(1)
        self.layer_combo.currentIndexChanged.connect(self._on_layer_changed)
    
    def _on_layer_changed(self, idx):
        if idx > 0:
            lyr = QgsProject.instance().mapLayer(self.layer_combo.currentData())
            if lyr:
                self.raster_layer = lyr
                self.status.setText(f"✅ {lyr.name()}")
                self.status.setStyleSheet("color: #2e7d32;")
        else:
            self.raster_layer = None
    


    def _on_class_changed(self):
        """Auto-update area ranges based on selected class"""
        cls = self.class_input.text().strip().lower()
        
        presets = {
            'building': (15, 8000, 88),
            'car':      (2, 30, 70),
            'tree':     (5, 500, 75),
            'road':     (50, 100000, 75),
            'swimming_pool': (8, 200, 80),
            'solar_panel': (1, 500, 80),
        }
        
        if cls in presets:
            min_a, max_a, conf = presets[cls]
            self.min_area.setValue(min_a)
            self.max_area.setValue(max_a)
            self.conf_slider.setValue(conf)

    def start_detection(self):
        if not self.raster_layer:
            QMessageBox.warning(self, "Error", "Select a raster layer")
            return
        
        cls = self.class_input.text().strip()
        if not cls:
            QMessageBox.warning(self, "Error", "Enter a class name")
            return
        
        extent = (self.iface.mapCanvas().extent() if self.zone_view.isChecked() 
                  else self.raster_layer.extent())
        
        size_map = {0: 1024, 1: 2048, 2: 4096, 3: 8192}
        config = {
            'model_type': ['sam2_tiny', 'sam2_1_b', 'sam3'][self.model_combo.currentIndex()],
            'confidence': self.conf_slider.value() / 100.0,
            'min_area': self.min_area.value(),
            'max_area': self.max_area.value(),
            'max_size': size_map[self.max_size.currentIndex()],
            'tile_size': 1024,
            'tile_overlap': 128,
            'points_per_side': 32,
        }
        
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status.setText("⏳ Starting...")
        
        self.worker = SegmentationWorker(self.raster_layer, extent, cls, config)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.status.connect(self.status.setText)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_finished(self, layer, error):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setVisible(False)
        
        if error:
            self.status.setText(f"❌ {error[:150]}")
            QMessageBox.critical(self, "Error", error[:500])
            return
        
        if layer:
            QgsProject.instance().addMapLayer(layer)
            
            # Style
            from qgis.core import QgsFillSymbol, QgsSingleSymbolRenderer
            sym = QgsFillSymbol.createSimple({
                'color': '255,140,0,80',
                'outline_color': '255,80,0,255',
                'outline_width': '0.6',
            })
            layer.setRenderer(QgsSingleSymbolRenderer(sym))
            
            count = layer.featureCount()
            self.status.setText(f"✅ {count} buildings detected")
            self.status.setStyleSheet("color: #2e7d32; font-weight: bold;")
            QMessageBox.information(
                self, "Done",
                f"✅ Detected {count} individual buildings\n"
                f"Layer: {layer.name()}"
            )
    
    def cancel_detection(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()
            self.start_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.progress.setVisible(False)




    def _on_pick_sample(self, checked):
        """Activate sample picking tool"""
        if checked:
            from .pick_sample_tool import PickSampleTool
            self._sample_tool = PickSampleTool(self.iface.mapCanvas(), self.iface)
            self._sample_tool.sample_picked.connect(self._on_sample_picked)
            self.iface.mapCanvas().setMapTool(self._sample_tool)
            self.pick_sample_btn.setText("🎯 Click on map...")
        else:
            try:
                self.iface.mapCanvas().unsetMapTool(self._sample_tool)
            except Exception:
                pass
            self.pick_sample_btn.setText("🎯 Pick Sample from Map")

    def _on_sample_picked(self, map_x, map_y):
        """Called when user clicks on the sample"""
        try:
            if not self.raster_layer:
                print("❌ No raster layer selected")
                return

            from ..core.raster_handler import RasterHandler
            from ..core.model_manager import ModelManager
            from ..core.config_manager import ConfigManager
            from ..core.exemplar_segmenter import ExemplarSegmenter

            rh = RasterHandler(self.raster_layer)
            extent = self.iface.mapCanvas().extent()
            img, crs, transform = rh.get_raster_data_extent(extent, max_size=2048)

            self.exemplar_status.setText("Loading SAM...")
            mm = ModelManager(ConfigManager())
            model = mm.get_model('sam2_tiny')
            if model is None:
                print("❌ Failed to load SAM")
                self.exemplar_status.setText("❌ Failed to load SAM")
                return

            seg = ExemplarSegmenter(model)
            ex = seg.create_exemplar(img, transform, (map_x, map_y))
            if ex is None:
                self.exemplar_status.setText("❌ Failed to capture sample")
                return

            self._exemplar_segmenter = seg
            self.exemplar_status.setText(
                f"✅ Sample: {ex.area_px}px, "
                f"RGB({ex.mean_rgb[0]:.0f},{ex.mean_rgb[1]:.0f},{ex.mean_rgb[2]:.0f})"
            )
            self.exemplar_status.setStyleSheet("color: #2e7d32; font-size: 10px;")
            self.use_exemplar_cb.setEnabled(True)
            self.use_exemplar_cb.setChecked(True)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.exemplar_status.setText(f"❌ {e}")
            self.exemplar_status.setStyleSheet("color: #c62828; font-size: 10px;")


class _EmbeddedDetectWidget(QWidget):
    """QWidget version of the detect panel for embedding in a tab"""
    def __init__(self, iface, config_manager):
        super().__init__()
        self.iface = iface
        self.config_manager = config_manager
        self.raster_layer = None
        self.worker = None
        self._dock = MainDockWidget(iface, config_manager)
        # Extract the inner widget
        inner = self._dock.widget()
        if inner:
            inner.setParent(self)
            lay = QVBoxLayout(self)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(inner)
    
    def closeEvent(self, event):
        try:
            if self._dock:
                self._dock.close()
        except Exception:
            pass
        super().closeEvent(event)
