"""
Pick Sample Tool - Click on an object to use as exemplar
"""
from qgis.gui import QgsMapToolEmitPoint
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QCursor
from qgis.core import QgsPointXY


class PickSampleTool(QgsMapToolEmitPoint):
    """Click on map to select an exemplar object"""
    
    sample_picked = pyqtSignal(float, float)  # map x, y
    
    def __init__(self, canvas, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.canvasClicked.connect(self.on_click)
    
    def activate(self):
        self.canvas.setCursor(QCursor(Qt.CrossCursor))
        print("🎯 Click on the object you want to use as a sample")
        print("   (right-click to cancel)")
    
    def deactivate(self):
        try:
            super().deactivate()
        except Exception:
            pass
    
    def on_click(self, point, button):
        if button == Qt.RightButton:
            self.iface.mapCanvas().unsetMapTool(self)
            print("❌ Sample pick cancelled")
            return
        print(f"📍 Sample picked at ({point.x():.2f}, {point.y():.2f})")
        self.sample_picked.emit(point.x(), point.y())
