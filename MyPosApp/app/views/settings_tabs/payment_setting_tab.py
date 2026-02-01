from dataclasses import asdict
from PySide6.QtWidgets import QMessageBox

from app.models.payment_method import PaymentMethod
from app.services.payment_service import PaymentService  # Serviceをインポート
from app.views.dialogs.payment_edit_dialog import PaymentEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab

class PaymentSettingTab(BaseSettingTab):
    def __init__(self, service: PaymentService):
        super().__init__()
        self.service = service  # Repositoryの代わりにServiceを保持

        self.set_columns(["ID", "名称", "現金扱い", "状態"])
        self.load_data()

    def load_data(self):
        # Service経由で取得
        self.methods = self.service.get_all_methods()
        self.table.setRowCount(len(self.methods))

        for row, m in enumerate(self.methods):
            active = m.is_active
            col = "white" if active else "#757575"
            self.table.setItem(row, 0, self.create_item(m.id, col))
            self.table.setItem(row, 1, self.create_item(m.name, col))
            self.table.setItem(row, 2, self.create_item("Yes" if m.is_cash else "No", col))
            self.table.setItem(row, 3, self.create_item("有効" if active else "無効", col))

    def on_add(self):
        dlg = PaymentEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            # IDはAutoIncrementなので0
            new_obj = PaymentMethod(0, d['name'], d['is_cash'], d['is_active'])
            
            # Service経由で追加
            if self.service.add_method(new_obj):
                self.load_data()

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.methods)
        if not target: return
        
        dlg = PaymentEditDialog(data=asdict(target), parent=self)
        if dlg.exec():
            d = dlg.get_data()
            updated_obj = PaymentMethod(target.id, d['name'], d['is_cash'], d['is_active'])
            
            # Service経由で更新
            if self.service.update_method(updated_obj):
                self.load_data()

    def on_delete_selected(self):
        target = self.get_selected_row_data(self.methods)
        if not target: return
        
        msg = f"支払方法「{target.name}」を削除しますか？\n\n「Yes」= 完全に削除\n「No」= 無効化 (停止)\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if res == QMessageBox.Yes:
            # Service経由で削除
            if self.service.delete_method(target):
                self.load_data()
        elif res == QMessageBox.No:
            # Service経由で無効化
            if self.service.disable_method(target):
                self.load_data()