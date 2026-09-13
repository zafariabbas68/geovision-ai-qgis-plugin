"""
GeoVision AI Plugin - Main plugin class
Uses unified panel with tabs for Detect, Review, Settings
"""

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtCore import Qt

from .processing_provider.provider import Provider
from .core.config_manager import ConfigManager
from .ui.unified_panel import UnifiedPanel
from .ui.settings_dialog import SettingsDialog


class GeoVisionAIPlugin:
    """Main plugin class"""

    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.dock_widget = None
        self.config_manager = ConfigManager()
        self.action = None
        self.settings_action = None

    def initGui(self):
        """Initialize GUI"""
        icon_path = os.path.join(
            os.path.dirname(__file__),
            'resources/icons/icon.png'
        )
        
        # Try PNG first, then SVG fallback
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            icon = QIcon()
        
        # Main toolbar action - opens unified panel
        self.action = QAction(
            icon,
            'GeoVision AI',
            self.iface.mainWindow()
        )
        self.action.setObjectName('geovisionAIAction')
        self.action.setWhatsThis('Open GeoVision AI panel')
        self.action.setStatusTip('AI-powered raster segmentation')
        self.action.triggered.connect(self.toggle_dock)
        
        # Add to toolbar and menu
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu('&GeoVision AI', self.action)
        
        # Settings is available as a tab inside the main panel (no separate menu item)
        
        # Initialize Processing provider
        self.init_processing()
        
        # Create the unified dock widget (hidden by default)
        self.dock_widget = UnifiedPanel(self.iface, self.config_manager)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
        
        # Make sure it can be resized / moved / floated
        self.dock_widget.setMinimumWidth(350)
        self.dock_widget.setMinimumHeight(250)
        self.dock_widget.setFeatures(
            self.dock_widget.DockWidgetClosable |
            self.dock_widget.DockWidgetMovable |
            self.dock_widget.DockWidgetFloatable
        )
        
        # Set a good default size
        self.dock_widget.resize(420, 700)
        self.dock_widget.hide()
        
        # Panel starts hidden — user opens it from the toolbar icon

    def init_processing(self):
        """Initialize Processing provider"""
        self.provider = Provider(self.config_manager)
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        """Clean up when plugin is unloaded"""
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu('&GeoVision AI', self.action)
        # settings_action no longer exists
        
        if self.dock_widget:
            self.dock_widget.close()
            self.dock_widget.deleteLater()
            self.dock_widget = None

    def toggle_dock(self):
        """Toggle the unified panel visibility"""
        if self.dock_widget.isVisible():
            self.dock_widget.hide()
        else:
            self.dock_widget.show()
            self.dock_widget.raise_()
            # Switch to Detect tab by default
            try:
                self.dock_widget.switch_to_detect()
            except Exception:
                pass

    def open_settings(self):
        """Open the panel and switch to the Settings tab"""
        if not self.dock_widget.isVisible():
            self.dock_widget.show()
            self.dock_widget.raise_()
        try:
            self.dock_widget.switch_to_settings()
        except Exception:
            pass
