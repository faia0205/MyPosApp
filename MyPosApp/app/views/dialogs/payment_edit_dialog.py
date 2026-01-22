from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QCheckBox, QDialogButtonBox)
from app.utils.style import StyleGenerator

class PaymentEditDialog(QDialog):
    """支払方法編集ダイアログ"""
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("支払方法編集")
        self.resize(300, 200)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit {{ 
                padding: 8px; color: black; background-color: white; 
                border-radius: 4px;
            }}
            QLabel {{ font-weight: bold; margin-top: 10px; }}
            {StyleGenerator.get_checkbox_style()} /* 共通チェックボックス */
        """)
        self.data = data
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("名称 (例: PayPay, クレジット):"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)
        
        self.cash_chk = QCheckBox("現金として扱う (お釣り計算対象)")
        layout.addWidget(self.cash_chk)
        
        self.active_chk = QCheckBox("有効")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        if self.data:
            self.name_edit.setText(self.data['name'])
            self.cash_chk.setChecked(bool(self.data['is_cash']))
            self.active_chk.setChecked(bool(self.data['is_active']))

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "is_cash": self.cash_chk.isChecked(),
            "is_active": self.active_chk.isChecked()
        }