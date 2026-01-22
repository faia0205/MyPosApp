from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QSpinBox, QDialogButtonBox, QDateTimeEdit)
from PySide6.QtCore import QDateTime, Qt
from app.utils.style import StyleGenerator

class ExpenseEditDialog(QDialog):
    """経費登録・編集ダイアログ"""
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("経費・出費の編集" if data else "経費・出費の登録")
        self.resize(300, 250)
        # チェックボックススタイルも念のため適用
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit, QDateTimeEdit {{ background-color: white; color: black; padding: 5px; border-radius: 4px; }}
            {StyleGenerator.get_spinbox_style()}
        """)
        self.data = data
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 日時 (編集時のみ、あるいは新規でも指定可能に)
        layout.addWidget(QLabel("日時:"))
        self.date_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(self.date_edit)
        
        layout.addWidget(QLabel("項目名:"))
        self.title_edit = QLineEdit()
        layout.addWidget(self.title_edit)
        
        layout.addWidget(QLabel("金額 (円):"))
        self.amount_spin = QSpinBox()
        self.amount_spin.setRange(-999999, 999999)
        self.amount_spin.setSingleStep(100)
        layout.addWidget(self.amount_spin)

        # 初期値
        if self.data:
            # data['timestamp'] は文字列 "YYYY-MM-DD HH:MM:SS"
            dt = QDateTime.fromString(self.data['timestamp'], "yyyy-MM-dd HH:mm:ss")
            if dt.isValid():
                self.date_edit.setDateTime(dt)
            self.title_edit.setText(self.data['title'])
            self.amount_spin.setValue(self.data['amount'])

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self):
        return {
            "timestamp": self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "title": self.title_edit.text(),
            "amount": self.amount_spin.value()
        }