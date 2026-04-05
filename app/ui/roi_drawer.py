from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, Signal, QObject
from PySide6.QtGui import QPen, QColor, QBrush

class ROISchema:
    def __init__(self, roi_id, x, y, w, h):
        self.roi_id = roi_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        
class ROIDrawer(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.roi: list[ROISchema] = []
        self.current_item = None
        self.start_point = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.scenePos()
            self.current_item = QGraphicsRectItem()
            self.current_item.setPen(QPen(QColor(0, 255, 0), 2))
            self.current_item.setBrush(QBrush(QColor(0, 255, 0, 50)))
            # Seleccion y movimiento en modo edición
            self.current_item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
            self.addItem(self.current_item)
            
        elif event.button() == Qt.RightButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, QGraphicsRectItem):
                self.removeItem(item)
                
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.current_item and self.start_point:
            end_point = event.scenePos()
            rect = QRectF(self.start_point, end_point).normalized()
            self.current_item.setRect(rect)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        self.start_point = None
        self.current_item = None
        self.save_rois()
        super().mouseReleaseEvent(event)
        
    def save_rois(self):
        self.rois = []
        for i, item in enumerate(self.items()):
            if isinstance(item, QGraphicsRectItem):
                r  = item.sceneBoundingRect()
                self.rois.append(ROISchema(i, r.x(), r.y(), r.width(), r.height()))
                print(f"ROI guardada: ID={i}, x={r.x()}, y={r.y()}, w={r.width()}, h={r.height()}")