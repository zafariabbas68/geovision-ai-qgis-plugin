"""
Theme-aware colors for the plugin
Detects QGIS light/dark theme and returns appropriate colors
"""

from qgis.PyQt.QtGui import QPalette, QColor
from qgis.PyQt.QtWidgets import QApplication


def is_dark_theme() -> bool:
    """Detect if QGIS is using dark theme"""
    try:
        app = QApplication.instance()
        if app is None:
            return False
        palette = app.palette()
        bg = palette.color(QPalette.Window)
        # Dark if brightness is low
        return bg.lightness() < 128
    except Exception:
        return False


def get_colors() -> dict:
    """Get theme-appropriate colors"""
    if is_dark_theme():
        return {
            'text': '#e0e0e0',
            'text_muted': '#999999',
            'bg_input': '#3c3c3c',
            'bg_group': '#2d2d2d',
            'border': '#555555',
            'accent': '#4a90d9',
            'success': '#4caf50',
            'error': '#f44336',
            'header_bg': '#1e4d7b',
            'header_text': '#ffffff',
        }
    else:
        return {
            'text': '#222222',
            'text_muted': '#666666',
            'bg_input': '#ffffff',
            'bg_group': '#f8f9fa',
            'border': '#d0d0d0',
            'accent': '#2e7d32',
            'success': '#2e7d32',
            'error': '#c62828',
            'header_bg': '#e3f2fd',
            'header_text': '#1565c0',
        }
