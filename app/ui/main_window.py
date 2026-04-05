import ctypes
from ctypes import wintypes
from PySide6 import QtCore
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt

from app.ui.window_selector import WindowSelectorDialog
from app.utils.win32_utils import capture_window, get_current_window_position
from app.ui.overlay import WindowOverlay

class MainWindow(QMainWindow):
    
    window_selected = None
    overlay: WindowOverlay = None
    tracking_timer: QtCore.QTimer = None

    def __init__(self):
        super().__init__()
        
        self.tracking_timer = QtCore.QTimer()
        self.tracking_timer.timeout.connect(self.update_overlay_position)
        self.setWindowTitle("Screen Translator")
        self.setFixedSize(700, 600)
        
        # Estructura de la interfaz
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Botones
        self.btn_select = QPushButton("Seleccionar Ventana")
        self.btn_start = QPushButton("Seleccionar ROI")
        self.preview_label = QLabel("La ventana seleccionada aparecerá aquí")
        self.btn_stop = QPushButton("Detener Selección")
        
        self.btn_start.setObjectName("btn_start")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet(
            """
            QLabel {
                background-color: #ffffff;
                border: 1px dashed #cfcfcf;
                border-radius: 8px;
                color: #777;
            }
            """
        )
        
        layout.addWidget(self.btn_select)
        layout.addWidget(self.preview_label)
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        # Estilos
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5; /* Fondo gris muy claro */
            }
            QPushButton {
                background-color: #ffffff;   /* Botones blancos */
                border: 1px solid #dcdcdc;  /* Borde gris fino */
                border-radius: 8px;          /* Esquinas redondeadas */
                padding: 10px;               /* Espacio interno para que el botón sea alto */
                font-size: 14px;
                color: #333;                 /* Texto gris oscuro */
            }
            QPushButton:hover {
                background-color: #eeeeee;   /* Color al pasar el ratón por encima */
            }
            /* Estilo específico para el botón que llamamos 'btn_start' */
            QPushButton#btn_start {
                background-color: #0078d4;   /* Azul estilo Windows/Mac */
                color: white;                /* Texto blanco */
                font-weight: bold;
                border: none;                /* Sin borde para que se vea más limpio */
            }
            QPushButton#btn_start:hover {
                background-color: #005a9e;   /* Azul más oscuro al pasar el ratón */
            }
        """)
        
        self.btn_select.clicked.connect(self.on_select)
        self.btn_start.clicked.connect(self.on_start_overlay)
        self.btn_stop.clicked.connect(self.on_stop_overlay)
        
    def on_select(self):
        dialog = WindowSelectorDialog(self)
        if dialog.exec() == QDialog.Accepted:
            hwnd = dialog.get_selected_window()
            if hwnd:
                print(f"Ventana seleccionada: {hwnd}")
                self.btn_select.setText(f"Ventana: {hwnd}")
                self.update_preview(hwnd)
                self.window_selected = hwnd
                return self.window_selected
            else:
                print("No se seleccionó ninguna ventana.")
                self.preview_label.setText("No se seleccionó ninguna ventana")
        
    def on_start_overlay(self):
        if not self.window_selected:
            print("No hay ventana seleccionada para superponer.")
            return
        
        if not self.overlay:
            self.overlay = WindowOverlay(0, 0, 100, 100)
            self.overlay.closed.connect(self.on_stop_overlay)

        self.overlay.set_mode("edit")
        self.overlay.show()
        self.tracking_timer.start(100) 
        self.btn_start.setText("Presiona enter para empezar las traducciones")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def on_stop_overlay(self):
        if not self.window_selected:
            print("No hay ventana seleccionada para detener el seguimiento.")
            return
        
        if self.overlay:
            self.overlay.hide()
        self.tracking_timer.stop()
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Seleccionar ROI")
        self.btn_stop.setEnabled(False)
        print("Seleccion de ROI detenida.")

    def update_preview(self, hwnd):
        pixmap = capture_window(hwnd)
        if pixmap is None or pixmap.isNull():
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("No se pudo capturar la ventana")
            return

        self.preview_label.setText("")
        scaled_pixmap = pixmap.scaled(
            self.preview_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.preview_label.setPixmap(scaled_pixmap)
        
    def update_overlay_position(self):
        result = get_current_window_position(self.window_selected, self.overlay)
        if not result:
            self.tracking_timer.stop()
            self.overlay.hide()
            self.btn_start.setEnabled(True)
            self.btn_start.setText("Seleccionar ROI")
            self.btn_stop.setEnabled(False)
            
    def keyPressEvent(self, event):
        if not self.window_selected:
            print("No hay ventana seleccionada para iniciar la selección de ROI.")
            return 
        if event.key() == (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.AltModifier:
                print("Alt + Enter presionado: Iniciando selección de ROI...")
                if self.overlay:
                    self.overlay.set_mode("edit")
        return super().keyPressEvent(event)