from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QSpinBox, QDialogButtonBox)

class ExpenseEditDialog(QDialog):
    """経費登録ダイアログ"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("経費・出費の登録")
        self.resize(300, 200)
        self.setStyleSheet("background-color: #333; color: white;")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("項目名 (例: 氷買い出し, 準備金増資):"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)
        
        layout.addWidget(QLabel("金額 (円):"))
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(-999999, 999999)
        self.amount_spin.setSingleStep(100)
        layout.addWidget(self.amount_spin)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {
            "title": self.title_edit.text(),
            "amount": self.amount_spin.value()
        }