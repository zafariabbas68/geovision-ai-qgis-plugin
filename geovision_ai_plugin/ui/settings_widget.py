"""
GeoVision AI - Settings Widget
Uses explicit colors that work in ANY theme.
No QGroupBox — flat layout with explicit QLabel styling.
"""

from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton,
    QComboBox, QSizePolicy
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QFont


# Explicit, theme-independent colors
BG_SECTION = "#f5f5f5"
BG_CREDITS = "#e3f2fd"
TEXT_PRIMARY = "#1a1a1a"
TEXT_MUTED = "#666666"
TEXT_CREDITS = "#0d47a1"
BORDER = "#cccccc"
ACCENT = "#2e7d32"


class SettingsWidget(QWidget):
    """Theme-independent settings widget"""

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setMinimumWidth(400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._build()

    def _section_header(self, title: str) -> QLabel:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {TEXT_PRIMARY}; "
            f"font-size: 13px; "
            f"font-weight: bold; "
            f"padding: 6px 0;"
        )
        return lbl

    def _row(self, label: str, widget: QWidget) -> QWidget:
        """Create a labeled row that renders correctly in any theme"""
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 4, 12, 4)
        h.setSpacing(10)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px;")
        lbl.setMinimumWidth(140)
        h.addWidget(lbl)

        widget.setMinimumWidth(180)
        h.addWidget(widget, 1)

        return row

    def _section_box(self, content: QWidget) -> QFrame:
        """A styled box for grouping rows"""
        box = QFrame()
        box.setStyleSheet(
            f"QFrame {{ background-color: {BG_SECTION}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; }}"
        )
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(0)
        layout.addWidget(content)
        return box

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ═══════════════════════════════════════════
        # Detection Settings
        # ═══════════════════════════════════════════
        layout.addWidget(self._section_header("🤖 Detection Settings"))

        inner = QWidget()
        inner_l = QVBoxLayout(inner)
        inner_l.setContentsMargins(0, 0, 0, 0)
        inner_l.setSpacing(0)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            'SAM2-tiny (fast, CPU)',
            'SAM2.1-B (balanced)',
            'SAM3 (GPU required)',
        ])
        inner_l.addWidget(self._row("Default model:", self.model_combo))

        self.use_gpu = QCheckBox("Use GPU when available")
        self.use_gpu.setChecked(True)
        self.use_gpu.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; padding: 4px 12px;")
        inner_l.addWidget(self.use_gpu)

        self.auto_load = QCheckBox("Auto-load models on startup")
        self.auto_load.setStyleSheet(f"color: {TEXT_PRIMARY}; font-size: 12px; padding: 4px 12px;")
        inner_l.addWidget(self.auto_load)

        layout.addWidget(self._section_box(inner))
        layout.addSpacing(10)

        # ═══════════════════════════════════════════
        # Detection Defaults
        # ═══════════════════════════════════════════
        layout.addWidget(self._section_header("🎯 Detection Defaults"))

        inner2 = QWidget()
        inner2_l = QVBoxLayout(inner2)
        inner2_l.setContentsMargins(0, 0, 0, 0)
        inner2_l.setSpacing(0)

        self.conf_spin = QDoubleSpinBox()
        self.conf_spin.setRange(0.05, 0.95)
        self.conf_spin.setSingleStep(0.05)
        self.conf_spin.setValue(0.15)
        inner2_l.addWidget(self._row("Default confidence:", self.conf_spin))

        self.min_area = QDoubleSpinBox()
        self.min_area.setRange(0, 100000)
        self.min_area.setValue(15)
        self.min_area.setSuffix(" m²")
        inner2_l.addWidget(self._row("Default min area:", self.min_area))

        self.max_area = QDoubleSpinBox()
        self.max_area.setRange(0, 10000000)
        self.max_area.setValue(8000)
        self.max_area.setSuffix(" m²")
        inner2_l.addWidget(self._row("Default max area:", self.max_area))

        layout.addWidget(self._section_box(inner2))
        layout.addSpacing(10)

        # ═══════════════════════════════════════════
        # Performance
        # ═══════════════════════════════════════════
        layout.addWidget(self._section_header("⚡ Performance"))

        inner3 = QWidget()
        inner3_l = QVBoxLayout(inner3)
        inner3_l.setContentsMargins(0, 0, 0, 0)
        inner3_l.setSpacing(0)

        self.max_image = QSpinBox()
        self.max_image.setRange(512, 4096)
        self.max_image.setValue(1024)
        self.max_image.setSingleStep(128)
        self.max_image.setSuffix(" px")
        inner3_l.addWidget(self._row("Max image size:", self.max_image))

        self.dino_thresh = QDoubleSpinBox()
        self.dino_thresh.setRange(0.05, 0.95)
        self.dino_thresh.setSingleStep(0.05)
        self.dino_thresh.setValue(0.15)
        inner3_l.addWidget(self._row("DINO threshold:", self.dino_thresh))

        layout.addWidget(self._section_box(inner3))
        layout.addSpacing(12)

        # ═══════════════════════════════════════════
        # Save button
        # ═══════════════════════════════════════════
        self.save_btn = QPushButton("💾 Save Settings")
        self.save_btn.setMinimumHeight(38)
        self.save_btn.setStyleSheet(
            f"QPushButton {{"
            f" background-color: {ACCENT}; color: white;"
            f" font-weight: bold; font-size: 13px;"
            f" padding: 8px; border: none; border-radius: 4px;"
            f"}}"
            f"QPushButton:hover {{ background-color: #1b5e20; }}"
        )
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)
        layout.addSpacing(12)

        # ═══════════════════════════════════════════
        # Credits
        # ═══════════════════════════════════════════
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(line)
        layout.addSpacing(8)

        title = QLabel("GeoVision AI")
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; padding: 4px;")
        layout.addWidget(title)

        ver = QLabel("Version 1.0.0")
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        layout.addWidget(ver)
        layout.addSpacing(8)

        author = QLabel(
            "<b>Developed by Ghulam Abbas Zafari</b><br>"
            "Location: Milan, Italy<br>"
            "Year: 2026<br>"
            "GeoInformatics Engineer<br>"
            "Geospatial Developer"
        )
        author.setAlignment(Qt.AlignCenter)
        author.setMinimumHeight(120)
        author.setStyleSheet(
            f"padding: 14px;"
            f" background-color: {BG_CREDITS};"
            f" color: {TEXT_CREDITS};"
            f" border: 1px solid {TEXT_CREDITS};"
            f" border-radius: 6px;"
            f" font-size: 12px;"
            f" line-height: 1.6;"
        )
        layout.addWidget(author)
        layout.addSpacing(10)

        tech = QLabel(
            "<b>Built with:</b><br>"
            "• Meta Segment Anything (SAM)<br>"
            "• Grounding DINO (text prompts)<br>"
            "• QGIS · PyTorch · OpenCV · NumPy"
        )
        tech.setAlignment(Qt.AlignCenter)
        tech.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; padding: 8px;"
        )
        tech.setWordWrap(True)
        layout.addWidget(tech)
        layout.addSpacing(8)

        watermark = QLabel(
            "© 2026 Ghulam Abbas Zafari · Milan, Italy<br>"
            "<i>AI-powered geospatial segmentation</i>"
        )
        watermark.setAlignment(Qt.AlignCenter)
        watermark.setStyleSheet(
            f"color: {TEXT_MUTED};"
            f" font-size: 9px;"
            f" padding: 12px 8px;"
            f" border-top: 1px solid {BORDER};"
        )
        layout.addWidget(watermark)

    def load_settings(self):
        cfg = self.config_manager.config
        self.conf_spin.setValue(cfg.get('confidence_threshold', 0.15))
        self.min_area.setValue(cfg.get('min_area', 15))
        self.max_area.setValue(cfg.get('max_area', 8000))
        self.max_image.setValue(cfg.get('max_image_size', 1024))
        self.dino_thresh.setValue(cfg.get('dino_threshold', 0.15))
        self.use_gpu.setChecked(cfg.get('use_gpu', True))
        self.auto_load.setChecked(cfg.get('auto_load_models', False))

    def _save(self):
        cfg = self.config_manager.config
        cfg['confidence_threshold'] = self.conf_spin.value()
        cfg['min_area'] = self.min_area.value()
        cfg['max_area'] = self.max_area.value()
        cfg['max_image_size'] = self.max_image.value()
        cfg['dino_threshold'] = self.dino_thresh.value()
        cfg['use_gpu'] = self.use_gpu.isChecked()
        cfg['auto_load_models'] = self.auto_load.isChecked()
        self.config_manager.save_config(cfg)

        self.save_btn.setText("✅ Saved!")
        from qgis.PyQt.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.save_btn.setText("💾 Save Settings"))
