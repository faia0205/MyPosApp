from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.repositories.user_repo import UserRepository
from app.views.dialogs.user_edit_dialog import UserEditDialog

class UserSettingTab(QWidget):
    """ユーザー管理タブ"""
    def __init__(self):
        super().__init__()
        self.repo = UserRepository()
        self._init_ui()
        self.load_data()

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
        """)
        layout.addWidget(self.table)
        
        layout.addWidget(QLabel("※ コードはログイン時に使用します。重複できません。"))

    def load_data(self):
        users = self.repo.fetch_all_users()
        self.table.setRowCount(len(users))
        self.current_users = users # データ保持

        def create_item(text, color=None):
            it = QTableWidgetItem(str(text))
            it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            if color:
                it.setForeground(QColor(color))
            return it

        for i, u in enumerate(users):
            self.table.setItem(i, 0, create_item(u['id']))
            self.table.setItem(i, 1, create_item(u['name']))
            self.table.setItem(i, 2, create_item(u['user_code']))
            
            # 権限の色分け
            role_color = "#ffcc80" if u['role'] == 'admin' else "white"
            self.table.setItem(i, 3, create_item(u['role'], role_color))
            
            # 状態
            status = "有効" if u['is_active'] else "無効"
            status_color = "#69f0ae" if u['is_active'] else "#bdbdbd"
            self.table.setItem(i, 4, create_item(status, status_color))

    def _add_user(self):
        dialog = UserEditDialog(parent=self)
        if dialog.exec():
            d = dialog.get_data()
            if self.repo.add_user(d['name'], d['code'], d['role']):
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "追加失敗\nコードが重複している可能性があります。")

    def _edit_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.current_users[row]
        
        dialog = UserEditDialog(target, parent=self)
        if dialog.exec():
            d = dialog.get_data()
            if self.repo.update_user(target['id'], d['name'], d['code'], d['role'], d['is_active']):
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "更新失敗\nコードが重複している可能性があります。")

    def _delete_selected(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.current_users[row]
        
        if QMessageBox.question(self, "確認", f"{target['name']} を削除しますか？") == QMessageBox.Yes:
            if self.repo.delete_user(target['id']):
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "削除できませんでした")