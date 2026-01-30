from dataclasses import asdict
from PySide6.QtGui import QColor

from app.models.discount import DiscountRule
from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.discount_edit_dialog import DiscountEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab

class DiscountSettingTab(BaseSettingTab):
    def __init__(self):
        super().__init__()
        self.repo = DiscountRepository()
        self.log_repo = LogRepository()
        
        self.set_columns(["ID", "名称", "内容", "対象", "状態"])
        # カラム幅調整 (対象列を見やすく)
        self.table.horizontalHeader().setStretchLastSection(False) 
        self.table.setColumnWidth(3, 250) 
        
        self.load_data()

    def load_data(self):
        self.rules = self.repo.fetch_all_rules()
        self.table.setRowCount(len(self.rules))
        
        for row, r in enumerate(self.rules):
            # r は DiscountRule オブジェクト
            is_active = r.is_active
            base_col = "white" if is_active else "#757575"
            
            self.table.setItem(row, 0, self.create_item(r.id, base_col))
            self.table.setItem(row, 1, self.create_item(r.name, base_col))
            
            unit = "円引" if r.discount_type == 'fixed' else "%OFF"
            val_text = f"{r.discount_value}{unit}"
            self.table.setItem(row, 2, self.create_item(val_text, "#ffeb3b" if is_active else base_col))
            
            # 対象の表示ロジック
            target_text = ""
            target_color = "white"
            
            if r.apply_type == 'cart':
                target_text = "■ カート全体"
                target_color = "#81d4fa"
            elif r.apply_type == 'category':
                target_text = f"【カテゴリ】 {r.target_value}"
                target_color = "#ffcc80"
            elif r.apply_type == 'item':
                target_text = f"【 商  品 】 {r.target_value}"
                target_color = "#a5d6a7"
            elif r.apply_type == 'bundle':
                target_text = "★ セット・バンドル"
                target_color = "#e1bee7"
                if "select" in r.target_value: target_text += " (まとめ買い)"
                else: target_text += " (組合せ)"
            
            self.table.setItem(row, 3, self.create_item(target_text, target_color if is_active else base_col))
            self.table.setItem(row, 4, self.create_item("有効" if is_active else "無効", base_col))

    def on_add(self):
        dlg = DiscountEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            new_rule = DiscountRule(
                id=None,
                name=d['name'],
                discount_type=d['discount_type'],
                discount_value=d['discount_value'],
                apply_type=d['apply_type'],
                target_value=d['target_value'],
                is_auto=d['is_auto'],
                is_active=d['is_active']
            )
            if self.repo.add(new_rule):
                self.log_repo.add_log("info", f"割引ルール追加: {d['name']}")
                self.load_data()

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.rules)
        if not target: return
        
        dlg = DiscountEditDialog(data=asdict(target), parent=self)
        if dlg.exec():
            d = dlg.get_data()
            updated_rule = DiscountRule(
                id=target.id,
                name=d['name'],
                discount_type=d['discount_type'],
                discount_value=d['discount_value'],
                apply_type=d['apply_type'],
                target_value=d['target_value'],
                is_auto=d['is_auto'],
                is_active=d['is_active']
            )
            if self.repo.update(updated_rule):
                self.log_repo.add_log("info", f"割引ルール更新: {target.name}")
                self.load_data()

    def on_delete_selected(self):
        # 無効化のみ
        target = self.get_selected_row_data(self.rules)
        if not target: return
        
        target.is_active = False
        if self.repo.update(target):
            self.log_repo.add_log("info", f"割引ルール無効化: {target.name}")
            self.load_data()