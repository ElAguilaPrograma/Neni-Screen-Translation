from PySide6.QtWidgets import QGraphicsView, QPushButton, QVBoxLayout, QWidget
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor
from app.ui.roi_drawer import ROIDrawer

class WindowOverlay(QWidget):
    
    closed = Signal()
    
    def __init__(self, x, y, w, h):
        super().__init__()
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(x, y, w, h)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QGraphicsView()
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.installEventFilter(self)
        self.scene = ROIDrawer()
        self.view.setScene(self.scene)
        self.layout.addWidget(self.view)
        
        self.set_mode("edit")
        
        self.setFocusPolicy(Qt.StrongFocus)
        
    def set_mode(self, mode):
        self.mode = mode
        if mode == "edit":
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.view.setStyleSheet("background: rgba(0, 0, 0, 80); border: 2px solid yellow;")
            print("Modo de edicion activo")
            self.activateWindow()
            self.raise_()
            self.setFocus(Qt.ActiveWindowFocusReason)
        else:
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.view.setStyleSheet("background: transparent; border: none;")
            print("Modo activo")
            
        self.show()

    def eventFilter(self, watched, event):
        if watched is self.view and event.type() == QEvent.KeyPress:
            if self._handle_key_event(event):
                return True
        return super().eventFilter(watched, event)

    def _handle_key_event(self, event):
        if event.key() == Qt.Key_Escape:
            print("Cerrando selección...")
            self.closed.emit()
            self.close()
            return True

        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            if self.mode == "edit":
                self.set_mode("active")
                return True

        return False
        
    def keyPressEvent(self, event):
        if self._handle_key_event(event):
            event.accept()
            return
        super().keyPressEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        
        # Efecto de opacidad
        overlay_color = QColor(0, 0, 0, 120)
        painter.fillRect(self.rect(), overlay_color)
        
        # Borde resaltado
        pen = QPen(QColor(255, 0, 0), 3)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        # Texto de instrucciones
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect().adjusted(0, 0, 0, -20), Qt.AlignCenter, "Presiona Enter para confirmar la selección")
        painter.drawText(self.rect().adjusted(0, 20, 0, 0), Qt.AlignCenter, "Presiona Escape para salir de la selección")