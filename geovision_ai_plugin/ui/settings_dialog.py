"""
GeoVision AI - Settings Widget
Theme-aware, works embedded in unified panel
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton, QFrame,
    QFormLayout, QComboBox
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont

from .theme import get_colors


class SettingsDialog(QWidget):
    """Settings widget with theme-aware colors"""

    def __init__(self, parent, config_manager):
        super().__init__(parent)
        self.config_manager = config_manager
        self.colors = get_colors()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        c = self.colors

        # ── Detection Settings ──
        model_group = QGroupBox("🤖 Detection Settings")
        ml = QFormLayout()
        ml.setLabelAlignment(Qt.AlignRight)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'SAM2-tiny (fast, CPU)',
            'SAM2.1_B (balanced)',
            'SAM3 (best, GPU required)',
        ])
        ml.addRow("Default model:", self.model_combo)

        self.gpu_check = QCheckBox("Use GPU when available")
        self.gpu_check.setChecked(True)
        ml.addRow("", self.gpu_check)

        self.auto_load = QCheckBox("Auto-load models on startup")
        self.auto_load.setChecked(False)
        ml.addRow("", self.auto_load)

        model_group.setLayout(ml)
        layout.addWidget(model_group)

        # ── Detection Defaults ──
        defaults_group = QGroupBox("🎯 Detection Defaults")
        dl = QFormLayout()
        dl.setLabelAlignment(Qt.AlignRight)

        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 0.95)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.10)
        dl.addRow("Default confidence:", self.conf_spin)

        self.min_area_spin = QDoubleSpinBox()
        self.min_area_spin.setRange(0, 100000)
        self.min_area_spin.setValue(10)
        self.min_area_spin.setSuffix(" m²")
        dl.addRow("Default min area:", self.min_area_spin)

        self.max_area_spin = QDoubleSpinBox()
        self.max_area_spin.setRange(0, 10000000)
        self.max_area_spin.setValue(10000)
        self.max_area_spin.setSuffix(" m²")
        dl.addRow("Default max area:", self.max_area_spin)

        defaults_group.setLayout(dl)
        layout.addWidget(defaults_group)

        # ── Performance ──
        perf_group = QGroupBox("⚡ Performance")
        pl = QFormLayout()
        pl.setLabelAlignment(Qt.AlignRight)

        self.max_image = QSpinBox()
        self.max_image.setRange(512, 4096)
        self.max_image.setValue(1024)
        self.max_image.setSingleStep(128)
        self.max_image.setSuffix(" px")
        pl.addRow("Max image size:", self.max_image)

        self.dino_thresh = QDoubleSpinBox()
        self.dino_thresh.setRange(0.05, 0.95)
        self.dino_thresh.setSingleStep(0.05)
        self.dino_thresh.setValue(0.10)
        pl.addRow("DINO box threshold:", self.dino_thresh)

        perf_group.setLayout(pl)
        layout.addWidget(perf_group)

        # ── Save button ──
        save_row = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setStyleSheet(
            f"background-color: {c['accent']}; color: white; "
            f"font-weight: bold; padding: 8px; border-radius: 4px;"
        )
        self.save_btn.clicked.connect(self.save_settings)
        save_row.addStretch()
        save_row.addWidget(self.save_btn)
        save_row.addStretch()
        layout.addLayout(save_row)

        # ── Watermark / Credits ──
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {c['border']};")
        layout.addWidget(line)

        title = QLabel("GeoVision AI")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {c['text']};")
        layout.addWidget(title)

        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet(f"color: {c['text_muted']}; font-size: 11px;")
        layout.addWidget(version)

        layout.addSpacing(10)

        author = QLabel(
            "<b>Developed by Ghulam Abbas Zafari</b><br>"
            "Location: Milan, Italy<br>"
            "Year: 2026<br>"
            "GeoInformatics Engineer<br>"
            "Geospatial Developer"
        )
        author.setAlignment(Qt.AlignCenter)
        author.setStyleSheet(
            f"padding: 14px; "
            f"background: {c['header_bg']}; "
            f"color: {c['header_text']}; "
            f"border-radius: 6px; "
            f"border: 1px solid {c['border']}; "
            f"line-height: 1.5; "
            f"font-size: 11px;"
        )
        layout.addWidget(author)

        layout.addSpacing(8)

        tech = QLabel(
            "Built with:<br>"
            "• Meta Segment Anything Model (SAM)<br>"
            "• Grounding DINO (text-prompted detection)<br>"
            "• QGIS Processing Framework<br>"
            "• PyTorch · OpenCV · NumPy"
        )
        tech.setAlignment(Qt.AlignCenter)
        tech.setStyleSheet(
            f"color: {c['text_muted']}; font-size: 10px; padding: 6px;"
        )
        tech.setWordWrap(True)
        layout.addWidget(tech)

        layout.addSpacing(10)

        watermark = QLabel(
            "© 2026 Ghulam Abbas Zafari · Milan, Italy<br>"
            "<i>AI-powered geospatial segmentation</i>"
        )
        watermark.setAlignment(Qt.AlignCenter)
        watermark.setStyleSheet(
            f"color: {c['text_muted']}; "
            f"font-size: 9px; "
            f"padding: 10px; "
            f"border-top: 1px solid {c['border']}; "
            f"margin-top: 8px;"
        )
        layout.addWidget(watermark)

        layout.addStretch()

    def load_settings(self):
        """Load settings from config manager"""
        cfg = self.config_manager.config
        self.conf_spin.setValue(cfg.get('confidence_threshold', 0.10))
        self.min_area_spin.setValue(cfg.get('min_area', 10.0))
        self.max_area_spin.setValue(cfg.get('max_area', 10000.0))
        self.max_image.setValue(cfg.get('max_image_size', 1024))
        self.dino_thresh.setValue(cfg.get('dino_threshold', 0.10))
        self.gpu_check.setChecked(cfg.get('use_gpu', True))
        self.auto_load.setChecked(cfg.get('auto_load_models', False))

    def save_settings(self):
        """Save settings to config manager"""
        cfg = self.config_manager.config
        cfg['confidence_threshold'] = self.conf_spin.value()
        cfg['min_area'] = self.min_area_spin.value()
        cfg['max_area'] = self.max_area_spin.value()
        cfg['max_image_size'] = self.max_image.value()
        cfg['dino_threshold'] = self.dino_thresh.value()
        cfg['use_gpu'] = self.gpu_check.isChecked()
        cfg['auto_load_models'] = self.auto_load.isChecked()
        self.config_manager.save_config(cfg)

        # Feedback
        self.save_btn.setText("✅ Saved!")
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.save_btn.setText("💾 Save Settings"))
