from dataclasses import asdict
from app.models.payment_method import PaymentMethod
from app.repositories.payment_repo import PaymentRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.payment_edit_dialog import PaymentEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab

class PaymentSettingTab(BaseSettingTab):
    def __init__(self):
        super().__init__()
        self.repo = PaymentRepository()
        self.log_repo = LogRepository()
        
        self.set_columns(["ID", "名称", "現金扱い", "状態"])
        self.load_data()

    def load_data(self):
        self.methods = self.repo.fetch_all()
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
            
            if self.repo.add(new_obj):
                self.log_repo.add_log("info", f"支払方法追加: {d['name']}")
                self.load_data()

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.methods)
        if not target: return

        dlg = PaymentEditDialog(data=asdict(target), parent=self)
        if dlg.exec():
            d = dlg.get_data()
            updated_obj = PaymentMethod(target.id, d['name'], d['is_cash'], d['is_active'])
            
            if self.repo.update(updated_obj):
                self.log_repo.add_log("info", f"支払方法更新: {target.name}")
                self.load_data()

    def on_delete_selected(self):
        # 物理削除ではなく無効化を行う
        target = self.get_selected_row_data(self.methods)
        if not target: return
        
        target.is_active = False
        if self.repo.update(target):
            self.log_repo.add_log("info", f"支払方法無効化: {target.name}")
            self.load_data()