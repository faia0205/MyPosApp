from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QSpinBox, QDialogButtonBox, QDateTimeEdit, QFormLayout)
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
        form = QFormLayout()

        # 日時 (編集時のみ、または常に表示)
        self.date_edit = QDateTimeEdit()
        self.date_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.date_edit.setCalendarPopup(True)
        
        # データがあればその時間を、なければ現在時刻を設定
        if self.data.get('timestamp'):
            # 文字列 "yyyy-MM-dd HH:mm:ss" を QDateTime に変換
            dt = QDateTime.fromString(self.data['timestamp'], "yyyy-MM-dd HH:mm:ss")
            self.date_edit.setDateTime(dt)
        else:
            self.date_edit.setDateTime(QDateTime.currentDateTime())
            
        form.addRow("日時:", self.date_edit)

        # 項目名
        self.title_edit = QLineEdit()
        self.title_edit.setText(self.data.get('title', ''))
        form.addRow("項目名:", self.title_edit)

        # 金額
        self.amount_edit = QSpinBox()
        self.amount_edit.setRange(1, 9999999)
        self.amount_edit.setValue(self.data.get('amount', 0))
        form.addRow("金額:", self.amount_edit)

        layout.addLayout(form)

        # ボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        timestamp_str = self.date_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        return {
            'title': self.title_edit.text(),
            'amount': self.amount_edit.value(),
            'timestamp': timestamp_str  # 新しい日時
        }