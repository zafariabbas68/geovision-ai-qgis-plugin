"""
GeoVision AI - Unified Panel
Tabs: Detect | Review & Edit | Settings
"""

from qgis.PyQt.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QScrollArea, QFrame, QLabel, QSizePolicy, QPushButton,
    QGroupBox, QFormLayout, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont

from .theme import get_colors


class ScrollableTab(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def set_content(self, content: QWidget):
        if content is None:
            return
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setWidget(content)


class UnifiedPanel(QDockWidget):
    def __init__(self, iface, config_manager):
        super().__init__('GeoVision AI', iface.mainWindow())
        self.iface = iface
        self.config_manager = config_manager
        self.colors = get_colors()

        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea
        )
        self.setMinimumWidth(420)
        self.setMinimumHeight(500)
        self.setFloating(False)
        self.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )

        self.setup_ui()

    def setup_ui(self):
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setStyleSheet(self._tab_style())

        # Tab 1: Detect
        tab1 = ScrollableTab()
        try:
            content = self._build_detect_content()
            tab1.set_content(content)
        except Exception as e:
            import traceback; traceback.print_exc()
            tab1.set_content(QLabel(f"❌ Detect error: {e}"))
        self.tabs.addTab(tab1, "🎯 Detect")

        # Tab 2: Review & Edit
        tab2 = ScrollableTab()
        try:
            content = self._build_review_content()
            tab2.set_content(content)
        except Exception as e:
            import traceback; traceback.print_exc()
            tab2.set_content(QLabel(f"❌ Review error: {e}"))
        self.tabs.addTab(tab2, "🔧 Review & Edit")

        # Tab 3: Settings (all inline — no dialog needed)
        tab3 = ScrollableTab()
        try:
            content = self._build_settings_content()
            tab3.set_content(content)
        except Exception as e:
            import traceback; traceback.print_exc()
            tab3.set_content(QLabel(f"❌ Settings error: {e}"))
        self.tabs.addTab(tab3, "⚙️ Settings")

        layout.addWidget(self.tabs)
        self.setWidget(main)

    def _tab_style(self):
        c = self.colors
        return f"""
            QTabWidget::pane {{
                border: 1px solid {c['border']};
                background: {c['bg_group']};
            }}
            QTabBar::tab {{
                background: {c['bg_group']};
                color: {c['text']};
                padding: 10px 18px;
                border: 1px solid {c['border']};
                font-weight: bold;
                font-size: 12px;
                min-width: 90px;
            }}
            QTabBar::tab:selected {{
                background: {c['header_bg']};
                color: {c['header_text']};
                border-bottom: 3px solid {c['accent']};
            }}
            QTabBar::tab:hover {{
                background: {c['accent']};
                color: white;
            }}
        """

    def _build_detect_content(self):
        from .main_dock import MainDockWidget
        dock = MainDockWidget(self.iface, self.config_manager)
        self._detect_dock = dock
        inner = dock.widget()
        if inner is not None:
            inner.setParent(None)
            self.detect_panel = dock
            return inner
        return QLabel("Detect panel: no content")

    def _build_review_content(self):
        from .review_panel import ReviewPanel
        panel = ReviewPanel(self.iface)
        self._review_panel = panel
        inner = panel.widget()
        if inner is not None:
            inner.setParent(None)
            self.review_panel = panel
            return inner
        return QLabel("Review panel: no content")

    def _build_settings_content(self):
        """Full settings inline — no dialog needed"""
        c = self.colors
        cfg = self.config_manager.config

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ── Header ──
        header = QLabel("⚙️ Settings")
        header.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {c['text']}; "
            f"padding: 8px; background: {c['header_bg']}; "
            f"color: {c['header_text']}; border-radius: 4px;"
        )
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # ── Model settings ──
        model_group = QGroupBox("🤖 Model")
        mg = QFormLayout()
        mg.setLabelAlignment(Qt.AlignRight)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'SAM2-tiny (fast, CPU)',
            'SAM2.1_B (balanced)',
            'SAM3 (GPU required)',
        ])
        mg.addRow("Model:", self.model_combo)

        self.use_gpu = QCheckBox("Use GPU when available")
        self.use_gpu.setChecked(cfg.get('use_gpu', True))
        mg.addRow("", self.use_gpu)

        self.auto_load = QCheckBox("Auto-load on startup")
        self.auto_load.setChecked(cfg.get('auto_load_models', False))
        mg.addRow("", self.auto_load)

        model_group.setLayout(mg)
        layout.addWidget(model_group)

        # ── Detection defaults ──
        det_group = QGroupBox("🎯 Detection Defaults")
        dg = QFormLayout()
        dg.setLabelAlignment(Qt.AlignRight)

        self.default_conf = QDoubleSpinBox()
        self.default_conf.setRange(0.05, 0.95)
        self.default_conf.setSingleStep(0.05)
        self.default_conf.setValue(cfg.get('confidence_threshold', 0.15))
        dg.addRow("Confidence:", self.default_conf)

        self.default_min_area = QDoubleSpinBox()
        self.default_min_area.setRange(0, 100000)
        self.default_min_area.setValue(cfg.get('min_area', 15))
        self.default_min_area.setSuffix(" m²")
        dg.addRow("Min area:", self.default_min_area)

        self.default_max_area = QDoubleSpinBox()
        self.default_max_area.setRange(0, 10000000)
        self.default_max_area.setValue(cfg.get('max_area', 8000))
        self.default_max_area.setSuffix(" m²")
        dg.addRow("Max area:", self.default_max_area)

        det_group.setLayout(dg)
        layout.addWidget(det_group)

        # ── Performance ──
        perf_group = QGroupBox("⚡ Performance")
        pg = QFormLayout()
        pg.setLabelAlignment(Qt.AlignRight)

        self.max_image = QSpinBox()
        self.max_image.setRange(512, 4096)
        self.max_image.setValue(cfg.get('max_image_size', 1024))
        self.max_image.setSingleStep(128)
        self.max_image.setSuffix(" px")
        pg.addRow("Max image size:", self.max_image)

        self.dino_thresh = QDoubleSpinBox()
        self.dino_thresh.setRange(0.05, 0.95)
        self.dino_thresh.setSingleStep(0.05)
        self.dino_thresh.setValue(cfg.get('dino_threshold', 0.15))
        pg.addRow("DINO threshold:", self.dino_thresh)

        perf_group.setLayout(pg)
        layout.addWidget(perf_group)

        # ── Save button ──
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {c['accent']}; color: white;"
            f"  font-weight: bold; padding: 10px 20px; border-radius: 6px;"
            f"  font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{ background-color: #1b5e20; }}"
        )
        self.save_btn.clicked.connect(self._save_settings)
        layout.addWidget(self.save_btn)

        # ── Separator ──
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color: {c['border']};")
        layout.addWidget(sep)

        # ── Credits / Watermark ──
        title = QLabel("GeoVision AI")
        tf = QFont(); tf.setPointSize(15); tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {c['text']}; padding: 4px;")
        layout.addWidget(title)

        ver = QLabel("Version 1.0.0")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px;")
        layout.addWidget(ver)

        author = QLabel(
            "<b>Developed by Ghulam Abbas Zafari</b><br>"
            "Location: Milan, Italy<br>"
            "Year: 2026<br>"
            "GeoInformatics Engineer<br>"
            "Geospatial Developer"
        )
        author.setAlignment(Qt.AlignCenter)
        author.setStyleSheet(
            f"padding: 12px; "
            f"background: {c['header_bg']}; "
            f"color: {c['header_text']}; "
            f"border-radius: 6px; "
            f"border: 1px solid {c['border']}; "
            f"line-height: 1.5; "
            f"font-size: 11px;"
        )
        layout.addWidget(author)

        tech = QLabel(
            "<b>Built with:</b><br>"
            "• Meta Segment Anything (SAM)<br>"
            "• Grounding DINO (text prompts)<br>"
            "• QGIS Processing Framework<br>"
            "• PyTorch · OpenCV · NumPy"
        )
        tech.setAlignment(Qt.AlignCenter)
        tech.setStyleSheet(f"color: {c['text_muted']}; font-size: 10px; padding: 8px;")
        tech.setWordWrap(True)
        layout.addWidget(tech)

        watermark = QLabel(
            "© 2026 Ghulam Abbas Zafari · Milan, Italy<br>"
            "<i>AI-powered geospatial segmentation</i>"
        )
        watermark.setAlignment(Qt.AlignCenter)
        watermark.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 9px; "
            f"padding: 10px; border-top: 1px solid {c['border']};"
        )
        layout.addWidget(watermark)

        return container

    def _save_settings(self):
        cfg = self.config_manager.config
        cfg['use_gpu'] = self.use_gpu.isChecked()
        cfg['auto_load_models'] = self.auto_load.isChecked()
        cfg['confidence_threshold'] = self.default_conf.value()
        cfg['min_area'] = self.default_min_area.value()
        cfg['max_area'] = self.default_max_area.value()
        cfg['max_image_size'] = self.max_image.value()
        cfg['dino_threshold'] = self.dino_thresh.value()
        self.config_manager.save_config(cfg)

        self.save_btn.setText("✅ Saved!")
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.save_btn.setText("💾 Save Settings"))

    def switch_to_detect(self):
        self.tabs.setCurrentIndex(0)

    def switch_to_review(self):
        self.tabs.setCurrentIndex(1)

    def switch_to_settings(self):
        self.tabs.setCurrentIndex(2)

    def closeEvent(self, event):
        for attr in ('detect_panel', 'review_panel'):
            try:
                obj = getattr(self, attr, None)
                if obj:
                    obj.close()
            except Exception:
                pass
        super().closeEvent(event)
