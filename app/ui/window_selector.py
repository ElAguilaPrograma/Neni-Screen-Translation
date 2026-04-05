import sys
import ctypes
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                             QWidget, QDialog, QListWidget, QVBoxLayout, QDialogButtonBox)
from PySide6.QtCore import Qt
from app.utils.win32_utils import get_windows

class WindowSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar Ventana")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # Lista visual de ventanas
        self.list_widget = QListWidget()
        windows = get_windows()
        
        for hwnd, tittle in windows:
            item_text = f"[{hwnd}] - {tittle}"
            self.list_widget.addItem(item_text)
            # Guardar el HWND real dentro del objeto del item para recuperarlo luego
            self.list_widget.item(self.list_widget.count() - 1).setData(Qt.UserRole, hwnd)
        
        layout.addWidget(self.list_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_selected_window(self):
        # Retorna el HWND de la ventana seleccionada o None si no se seleccionó nada
        current_item = self.list_widget.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
                
