import logging
from PySide6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPen, QColor, QBrush


logger = logging.getLogger(__name__)

class ROISchema:
    def __init__(self, roi_id, x, y, w, h):
        self.roi_id = roi_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        
class ROIDrawer(QGraphicsScene):
    rois_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.edit_mode = True
        self.rois: list[ROISchema] = []
        self.current_item = None
        self.start_point = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item_under_cursor = self.itemAt(event.scenePos(), self.views()[0].transform())
            if item_under_cursor:
                logger.debug("Seleccionando item existente")
                super().mousePressEvent(event)
                return
            self.start_point = event.scenePos()
            self.current_item = QGraphicsRectItem(QRectF(self.start_point, self.start_point))
            self.current_item.setPen(QPen(QColor(0, 255, 0), 2))
            self.current_item.setBrush(QBrush(QColor(0, 255, 0, 50)))
            self.current_item.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
            # Seleccion y movimiento en modo edición
            self.addItem(self.current_item)
        
        elif event.button() == Qt.RightButton:
            item = self.itemAt(event.scenePos(), self.views()[0].transform())
            if isinstance(item, QGraphicsRectItem):
                self.removeItem(item)
                self.save_rois()
                return
                
        super().mousePressEvent(event)
        
    def mouseClickRightButton(self, event):
        logger.debug("Borrando de roi_drawer")
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if isinstance(item, QGraphicsRectItem):
            self.removeItem(item)
    
    def mouseMoveEvent(self, event):
        if self.current_item and self.start_point:
            end_point = event.scenePos()
            rect = QRectF(self.start_point, end_point).normalized()
            self.current_item.setRect(rect)
        super().mouseMoveEvent(event)
        
    def mouseReleaseEvent(self, event):
        if self.current_item:
            rect = self.current_item.rect()
            if rect.width() < 25 or rect.height() < 25:
                self.removeItem(self.current_item)
                self.current_item = None
                return
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
                logger.debug(
                    "ROI guardada: ID=%s, x=%s, y=%s, w=%s, h=%s",
                    i,
                    r.x(),
                    r.y(),
                    r.width(),
                    r.height(),
                )
        self.rois_changed.emit(len(self.rois) > 0)
        