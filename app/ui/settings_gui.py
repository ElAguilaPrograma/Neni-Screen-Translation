import onnxruntime as ort
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QPushButton, QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Signal

# Aqui manejare las opciones de configuracion globales, como el OCR engine, modelo de traducción,
# usar o no GPU, color de fondo del overlay, opacidad del overlay, etc.
# y otras cosas que puedan ser necesarias en varias partes de la app. 

class SettingsDialog(QDialog):
    # Señal para indicar el provider seleccionado 
    settings_changed = Signal(str)
    
    def __init__(self, current_device, parent=None, providers_override=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Hardware")
        self.setFixedSize(430, 270)
        self.current_device = current_device
        self.providers_override = list(providers_override) if providers_override else None
        
        self.init_ui()
        self.load_providers()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Sección de aceleración
        header = QLabel("Aceleración de Hardware")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(header)
        
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
        """)
        card_layout = QVBoxLayout(card)

        # Selector de Dispositivo
        device_layout = QHBoxLayout()
        self.label_info = QLabel("Motor de ejecución:")
        self.combo_devices = QComboBox()
        self.combo_devices.setMinimumWidth(200)
        
        device_layout.addWidget(self.label_info)
        device_layout.addWidget(self.combo_devices)
        card_layout.addLayout(device_layout)

        self.label_status = QLabel("")
        self.label_status.setWordWrap(True)
        card_layout.addWidget(self.label_status)
        
        layout.addWidget(card)
        
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        buttons_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_apply = QPushButton("Aplicar Cambios")
        self.btn_apply.setObjectName("btn_save")

        # Estilos del dialogo + botones (evita texto invisible en temas oscuros).
        self.setStyleSheet("""
            QDialog {
                background: #f5f5f5;
            }
            QLabel {
                color: #222;
            }
            QComboBox {
                background: #ffffff;
                color: #222;
                border: 1px solid #c8c8c8;
                border-radius: 6px;
                padding: 5px 8px;
                min-height: 28px;
            }
            QComboBox QAbstractItemView {
                background: #ffffff;
                color: #222;
                selection-background-color: #dbeeff;
                selection-color: #111;
                border: 1px solid #c8c8c8;
            }
            QPushButton {
                padding: 8px 15px;
                border-radius: 5px;
                border: 1px solid #ccc;
                background: #f9f9f9;
                color: #222;
            }
            QPushButton#btn_save {
                background: #0078d4;
                color: white;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_save:hover { background: #005a9e; }
        """)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_apply)
        layout.addLayout(buttons_layout)
        
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply.clicked.connect(self.accept_settings)

    def load_providers(self):
        providers = self.providers_override if self.providers_override is not None else ort.get_available_providers()
        
        self.provider_map = {
            "CUDAExecutionProvider": "NVIDIA GPU (CUDA)",
            "DmlExecutionProvider": "Graficos Integrados (DirectML)",
            "CPUExecutionProvider": "Procesador (CPU)",
        }

        for provider in providers:
            if provider in self.provider_map:
                self.combo_devices.addItem(self.provider_map[provider], provider)

        if self.combo_devices.count() == 0:
            self.combo_devices.addItem(self.provider_map["CPUExecutionProvider"], "CPUExecutionProvider")

        index = self.combo_devices.findData(self.current_device)
        if index >= 0:
            self.combo_devices.setCurrentIndex(index)
        else:
            cpu_index = self.combo_devices.findData("CPUExecutionProvider")
            if cpu_index >= 0:
                self.combo_devices.setCurrentIndex(cpu_index)

        self._set_provider_status(providers)

    def _set_provider_status(self, providers):
        has_cuda = "CUDAExecutionProvider" in providers
        has_dml = "DmlExecutionProvider" in providers

        if has_cuda or has_dml:
            options = []
            if has_cuda:
                options.append("CUDA")
            if has_dml:
                options.append("DirectML")
            self.label_status.setText(
                "Aceleración disponible: " + ", ".join(options)
            )
            self.label_status.setStyleSheet("color: #1a6b1a;")
            return

        self.label_status.setText(
            "Solo CPU disponible. Instala un runtime con GPU para habilitar más opciones."
        )
        self.label_status.setStyleSheet("color: #8a6d00;")

    def accept_settings(self):
        selected_provider = self.combo_devices.currentData()
        self.settings_changed.emit(selected_provider)
        self.accept()