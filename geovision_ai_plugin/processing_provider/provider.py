"""
Processing provider for GeoVision AI
"""
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

from .segmentation_algorithm import SegmentationAlgorithm


class Provider(QgsProcessingProvider):
    """Provider for GeoVision AI algorithms"""

    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

    def loadAlgorithms(self):
        """Register algorithms"""
        self.addAlgorithm(SegmentationAlgorithm(self.config_manager))

    def id(self):
        """Provider ID"""
        return 'geovision_ai'

    def name(self):
        """Provider name"""
        return self.tr('GeoVision AI')

    def icon(self):
        """Provider icon"""
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'resources/icons/icon.png'
        )
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return QIcon()
