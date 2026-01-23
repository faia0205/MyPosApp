from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.user_edit_dialog import UserEditDialog

class UserSettingTab(QWidget):
    """ユーザー管理タブ"""
    def __init__(self):
        super().__init__()
        self.repo = UserRepository()
        # ★追加
        self.log_repo = LogRepository()
        
        self._init_ui()
        self.load_data()

    # ... (_init_ui, load_data は前回の修正のままでOK) ...
    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ボタンエリア
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("＋ ユーザー追加")
        btn_add.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold; padding: 5px;")
        btn_add.clicked.connect(self._add_user)
        btn_layout.addWidget(btn_add)
        
        btn_edit = QPushButton("編集")
        btn_edit.clicked.connect(self._edit_selected)
        btn_layout.addWidget(btn_edit)
        
        btn_del = QPushButton("削除")
        btn_del.setStyleSheet("background-color: #c62828; color: white; padding: 5px;")
        btn_del.clicked.connect(self._delete_selected)
        btn_layout.addWidget(btn_del)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # テーブル
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "名前", "コード", "権限", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit_selected)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: #222; gridline-color: #444; color: white; }
            QHeaderView::section { background-color: #333; color: white; border: 1px solid #444; }
            QTableWidget::item:selected { background-color: #0d47a1; }
        """)
        layout.addWidget(self.table)
        
        layout.addWidget(QLabel("※ 無効化されたユーザーはグレーアウトされます（ログイン不可）。"))

    def load_data(self):
        """全ユーザーを表示 (無効ユーザーはグレーアウト)"""
        users = self.repo.fetch_all_users()
        self.table.setRowCount(len(users))
        self.current_users = users 

        for i, u in enumerate(users):
            is_active = u.is_active
            
            # --- 色の決定 ---
            if is_active:
                text_color = "white"
                bg_color = None
                role_color = "#ffcc80" if u.role == 'admin' else "white"
                status_text = "有効"
                status_color = "#69f0ae" 
            else:
                text_color = "#757575" 
                bg_color = "#2b2b2b"   
                role_color = text_color
                status_text = "無効"
                status_color = text_color

            def create_item(text, color, bg=None):
                it = QTableWidgetItem(str(text))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                it.setForeground(QColor(color))
                if bg: it.setBackground(QColor(bg))
                return it

            self.table.setItem(i, 0, create_item(u.id, text_color, bg_color))
            self.table.setItem(i, 1, create_item(u.name, text_color, bg_color))
            self.table.setItem(i, 2, create_item(u.user_code, text_color, bg_color))
            self.table.setItem(i, 3, create_item(u.role, role_color, bg_color))
            self.table.setItem(i, 4, create_item(status_text, status_color, bg_color))

    def _add_user(self):
        dialog = UserEditDialog(parent=self)
        if dialog.exec():
            d = dialog.get_data()
            
            new_user = User(
                id=None,
                name=d['name'],
                user_code=d['code'],
                role=d['role'],
                is_active=d['is_active']
            )
            
            if self.repo.add_user(new_user):
                self.log_repo.add_log("info", f"ユーザー追加: {new_user.name}")
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "追加失敗\nコードが重複している可能性があります。")

    def _edit_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.current_users[row]
        
        from dataclasses import asdict
        target_dict = asdict(target)
        
        dialog = UserEditDialog(target_dict, parent=self)
        if dialog.exec():
            d = dialog.get_data()
            
            updated_user = User(
                id=target.id,
                name=d['name'],
                user_code=d['code'],
                role=d['role'],
                is_active=d['is_active']
            )
            
            if self.repo.update_user(updated_user):
                self.log_repo.add_log("info", f"ユーザー更新: {target.name} -> {updated_user.name}")
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "更新失敗")

    def _delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.current_users[row]
        
        # 削除確認メッセージ
        msg = f"{target.name} を削除しますか？\n\n「Yes」= 完全に削除\n「No」= 無効化 (推奨)\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if res == QMessageBox.Yes:
            # 物理削除
            if self.repo.delete_user(target.id):
                # ★追加: ログ
                self.log_repo.add_log("warning", f"ユーザー完全削除: {target.name}")
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "削除できませんでした")
        elif res == QMessageBox.No:
            # 無効化 (論理削除)
            if self.repo.update_user(target):
                self.log_repo.add_log("info", f"ユーザー無効化: {target.name}")
                self.load_data()