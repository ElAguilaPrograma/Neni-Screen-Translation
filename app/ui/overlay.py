from PySide6.QtWidgets import QFrame, QGraphicsView, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor
from app.ui.roi_drawer import ROIDrawer

try:
    from app.utils.win32_utils import (
        disable_overlay_full_click_through,
        enable_overlay_full_click_through,
    )
except Exception:
    # Fallback no-op para evitar romper en entornos sin backend Win32.
    def enable_overlay_full_click_through(_overlay):
        return False

    def disable_overlay_full_click_through(_overlay):
        return False

class WindowOverlay(QWidget):
    
    closed = Signal()
    rois_has_items = Signal(bool)
    
    def __init__(self, x, y, w, h):
        super().__init__()
        print(f"Creando overlay en posición ({x}, {y}) con tamaño ({w}x{h})", )
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(x, y, w, h)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = QGraphicsView()
        self.view.setStyleSheet("background: transparent; border: none;")
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.setFrameShape(QFrame.NoFrame)
        self.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.set_mode(None)
        
        self.setFocusPolicy(Qt.StrongFocus)
        
    def set_mode(self, mode):
        self.mode = mode
        if not hasattr(self, 'scene'):
            self.scene = ROIDrawer()
            self.scene.rois_changed.connect(self.rois_has_items.emit)
            self.view.setScene(self.scene)
            self.layout.addWidget(self.view)
            
        if mode == "edit":
            self.scene.clear_roi_texts()
            self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.view.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            self.view.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, False)
            disable_overlay_full_click_through(self)
            self.view.setInteractive(True)
            self.view.setStyleSheet("background: rgba(0, 0, 0, 80); border: 2px solid yellow;")
            print("Modo de edicion activo")
            
            for item in self.scene.items():
                item.setAcceptedMouseButtons(Qt.LeftButton | Qt.RightButton)
                
            self.activateWindow()
            self.raise_()
            self.setFocus(Qt.ActiveWindowFocusReason)
            self.scene.edit_mode = True
            self._sync_scene_rect()
        elif mode == "active":
            print("Activando modo activo...")
            if not self.scene.rois:
                print("No se definieron regiones de interés (ROI). Cambiando a modo edit.")
                self.set_mode("edit")
                return
            self.scene.clear_roi_texts()
            self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.view.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.view.viewport().setAttribute(Qt.WA_TransparentForMouseEvents, True)
            enable_overlay_full_click_through(self)
            self.view.setInteractive(False)
            # Verificar que ya existe una instancia de scene antes de intentar modificarla
            if hasattr(self, "scene"):
                self.scene.edit_mode = False
                for item in self.scene.items():
                    item.setAcceptedMouseButtons(Qt.NoButton)
            self.view.setStyleSheet("background: transparent; border: none;")
            print("Modo activo")
        else:
            self.hide()
            self.destroy()
            print(hasattr(self, "scene"))
        
        if mode != None:    
            self.show()

        if hasattr(self, "scene"):
            self.rois_has_items.emit(len(self.scene.rois) > 0)

    def update_roi_text(self, roi_id, text):
        if not hasattr(self, "scene"):
            return
        self.scene.update_roi_text(roi_id, text)

    def configure_roi_text_style(self, **style_kwargs):
        if not hasattr(self, "scene"):
            return
        self.scene.configure_text_style(**style_kwargs)

    def clear_roi_texts(self):
        if not hasattr(self, "scene"):
            return
        self.scene.clear_roi_texts()

    def _sync_scene_rect(self):
        viewport_rect = self.view.viewport().rect()
        self.scene.setSceneRect(0, 0, viewport_rect.width(), viewport_rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_scene_rect()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)
        
        # Efecto de opacidad cuando esta en modo edición
        if self.mode == "edit":
            overlay_color = QColor(0, 0, 0, 120)
            painter.fillRect(self.rect(), overlay_color)
        
        # Borde resaltado
        pen = QPen(QColor(255, 0, 0), 3)
        pen.setWidth(2)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        
        # Texto de instrucciones
        if self.mode == "edit":
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.rect().adjusted(0, 0, 0, -20), Qt.AlignCenter, "Dibujar regiones de interés (ROI) con el mouse")
            painter.drawText(self.rect().adjusted(0, 20, 0, 0), Qt.AlignCenter, "Clic derecho sobre una ROI para eliminar la ROI")