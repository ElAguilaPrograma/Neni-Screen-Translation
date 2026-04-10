from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton


class AppDialog(QDialog):
    def __init__(self, title: str, message: str, parent=None):
        super().__init__(parent)

        self.setWindowTitle(title or "Aviso")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self.message_label = QLabel(message or "")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.accept_button = QPushButton("Aceptar")
        self.accept_button.clicked.connect(self.accept)

        layout.addWidget(self.message_label)
        layout.addWidget(self.accept_button)
