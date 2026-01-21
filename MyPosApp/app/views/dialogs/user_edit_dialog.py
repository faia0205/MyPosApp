from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QCheckBox, QDialogButtonBox, QMessageBox)

class UserEditDialog(QDialog):
    """ユーザー追加・編集ダイアログ"""
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ユーザー編集" if user_data else "新規ユーザー追加")
        self.resize(300, 250)
        self.setStyleSheet("background-color: #333; color: white; QLineEdit { padding: 5px; }")
        
        self.user_data = user_data
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 名前
        layout.addWidget(QLabel("表示名 (例: 店長, 佐藤):"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # ユーザーコード
        layout.addWidget(QLabel("ログインコード (半角英数):"))
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("例: 001, admin")
        layout.addWidget(self.code_edit)

        # 権限 (Role)
        layout.addWidget(QLabel("権限:"))
        self.role_combo = QComboBox()
        self.role_combo.addItems(["staff", "admin"])
        layout.addWidget(self.role_combo)

        # 有効/無効
        self.active_chk = QCheckBox("有効 (ログイン可能)")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        # 初期値セット
        if self.user_data:
            self.name_edit.setText(self.user_data['name'])
            self.code_edit.setText(self.user_data['user_code'])
            self.role_combo.setCurrentText(self.user_data['role'])
            self.active_chk.setChecked(bool(self.user_data['is_active']))

        # ボタン
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._validate_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "エラー", "名前を入力してください")
            return
        if not self.code_edit.text().strip():
            QMessageBox.warning(self, "エラー", "コードを入力してください")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "code": self.code_edit.text().strip(),
            "role": self.role_combo.currentText(),
            "is_active": self.active_chk.isChecked()
        }