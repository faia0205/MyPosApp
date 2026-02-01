from PySide6.QtWidgets import QMessageBox, QHeaderView
from dataclasses import asdict

from app.models.expense import Expense
from app.services.expense_service import ExpenseService  # Serviceをインポート
from app.views.dialogs.expense_edit_dialog import ExpenseEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab

class ExpenseSettingTab(BaseSettingTab):
    def __init__(self, service: ExpenseService):
        super().__init__()
        self.service = service

        self.set_columns(["ID", "日時", "項目名", "金額"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)

        self.load_data()

    def load_data(self):
        # Service経由で取得
        self.expenses = self.service.get_all_expenses()
        self.table.setRowCount(len(self.expenses))

        for row, ex in enumerate(self.expenses):
            self.table.setItem(row, 0, self.create_item(ex.id))
            self.table.setItem(row, 1, self.create_item(ex.timestamp))
            self.table.setItem(row, 2, self.create_item(ex.title))
            self.table.setItem(row, 3, self.create_item(f"¥{ex.amount:,}"))

    def on_add(self):
        dlg = ExpenseEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            # Service経由で追加
            if self.service.add_expense(d['title'], d['amount']):
                self.load_data()

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.expenses)
        if not target: return

        dlg = ExpenseEditDialog(data=asdict(target), parent=self)
        if dlg.exec():
            d = dlg.get_data()
            updated_expense = Expense(
                id=target.id,
                title=d['title'],
                amount=d['amount'],
                timestamp=d["timestamp"]
            )
            # Service経由で更新
            if self.service.update_expense(updated_expense):
                self.load_data()

    def on_delete_selected(self):
        target = self.get_selected_row_data(self.expenses)
        if not target: return
        
        if QMessageBox.question(self, "確認", f"「{target.title}」を削除しますか？\n(取り消せません)") == QMessageBox.Yes:
            # Service経由で削除
            if self.service.delete_expense(target):
                self.load_data()