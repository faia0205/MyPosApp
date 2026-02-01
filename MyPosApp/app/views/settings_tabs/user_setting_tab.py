from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from dataclasses import asdict

from app.models.user import User
from app.services.user_service import UserService
from app.views.dialogs.user_edit_dialog import UserEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab

class UserSettingTab(BaseSettingTab):
    """ユーザー管理タブ"""
    def __init__(self, user_service: UserService):
        super().__init__()
        self.service = user_service
        
        self.set_columns(["ID", "名前", "コード", "権限", "状態"])
        self.load_data()

    def load_data(self):
        self.current_users = self.service.get_all_users()
        self.table.setRowCount(len(self.current_users))
        
        for row, u in enumerate(self.current_users):
            is_active = u.is_active
            
            # 色設定
            text_col = "white" if is_active else "#757575"
            bg_col = None if is_active else "#2b2b2b"
            role_col = "#ffcc80" if u.role == 'admin' and is_active else text_col
            status_text = "有効" if is_active else "無効"
            status_col = "#69f0ae" if is_active else text_col

            self.table.setItem(row, 0, self.create_item(u.id, text_col, bg_col))
            self.table.setItem(row, 1, self.create_item(u.name, text_col, bg_col))
            self.table.setItem(row, 2, self.create_item(u.user_code, text_col, bg_col))
            self.table.setItem(row, 3, self.create_item(u.role, role_col, bg_col))
            self.table.setItem(row, 4, self.create_item(status_text, status_col, bg_col))

    def on_add(self):
        dialog = UserEditDialog(parent=self)
        if dialog.exec():
            d = dialog.get_data()
            new_user = User(None, d['name'], d['code'], d['role'], d['is_active'])
            
            if self.service.add_user(new_user):
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "追加失敗\nコードが重複している可能性があります。")

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.current_users)
        if not target: return
        
        dialog = UserEditDialog(asdict(target), parent=self)
        if dialog.exec():
            d = dialog.get_data()
            updated_user = User(target.id, d['name'], d['code'], d['role'], d['is_active'])
            
            if self.service.update_user(updated_user):
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "更新失敗")

    def on_delete_selected(self):
        target = self.get_selected_row_data(self.current_users)
        if not target: return
        
        msg = f"{target.name} を削除しますか？\n\n「Yes」= 完全に削除\n「No」= 無効化 (推奨)\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if res == QMessageBox.Yes:
            if self.service.delete_user(target.id):
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "削除できませんでした")
        elif res == QMessageBox.No:
            target.is_active = False
            if self.service.update_user(target):
                self.load_data()