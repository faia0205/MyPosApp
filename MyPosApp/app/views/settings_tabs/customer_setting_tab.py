from PySide6.QtWidgets import QPushButton, QHeaderView, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from dataclasses import asdict

from app.models.customer import Customer
from app.services.customer_service import CustomerService  # Serviceをインポート
from app.views.dialogs.customer_edit_dialog import CustomerEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab

class CustomerSettingTab(BaseSettingTab):
    def __init__(self, service: CustomerService):
        super().__init__()
        self.service = service  # Repositoryの代わりにServiceを保持

        self.set_columns(["ID", "ラベル", "属性 (詳細)", "状態"])
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Stretch)

        # 並び替えボタン
        self.btn_up = QPushButton("▲ 上へ")
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.layout_btns.insertWidget(2, self.btn_up)

        self.btn_down = QPushButton("▼ 下へ")
        self.btn_down.clicked.connect(lambda: self._move(1))
        self.layout_btns.insertWidget(3, self.btn_down)

        self.load_data()

    def load_data(self):
        # Service経由でデータ取得
        self.customers = self.service.get_all_customers()
        self.table.setRowCount(len(self.customers))

        for row, c in enumerate(self.customers):
            is_active = c.is_active
            text_col = "white" if is_active else "#757575"
            bg_col = None if is_active else "#2b2b2b"

            self.table.setItem(row, 0, self.create_item(c.id, text_col, bg_col))
            
            # ラベル (色付き)
            label_item = self.create_item(c.label, text_color="black" if is_active else text_col, bg_color=c.color if is_active else bg_col)
            self.table.setItem(row, 1, label_item)

            # 属性文字列化
            attrs = c.attributes
            attr_str = ", ".join([f"{k}: {v}" for k, v in attrs.items()]) if attrs else "-"
            self.table.setItem(row, 2, self.create_item(attr_str, text_col, bg_col))

            status = "有効" if is_active else "無効"
            self.table.setItem(row, 3, self.create_item(status, text_col, bg_col))

    def on_add(self):
        # Dialog用に辞書リスト作成
        presets_as_dicts = [asdict(c) for c in self.customers]
        for i, c in enumerate(self.customers):
            presets_as_dicts[i]['attributes'] = c.attributes

        dlg = CustomerEditDialog(all_presets=presets_as_dicts, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            new_customer = Customer(
                id=None,
                label=d['label'],
                attributes_json="",
                color=d['color'],
                is_active=d['is_active']
            )
            new_customer.set_attributes(d['attributes'])

            # Service経由で追加
            if self.service.add_customer(new_customer):
                self.load_data()

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.customers)
        if not target: return

        # Dialog用データ準備
        target_dict = asdict(target)
        target_dict['attributes'] = target.attributes
        
        presets_as_dicts = [asdict(c) for c in self.customers]
        for i, c in enumerate(self.customers):
            presets_as_dicts[i]['attributes'] = c.attributes

        dlg = CustomerEditDialog(data=target_dict, all_presets=presets_as_dicts, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            updated_customer = Customer(
                id=target.id,
                label=d['label'],
                attributes_json="",
                color=d['color'],
                display_order=target.display_order,
                is_active=d['is_active']
            )
            updated_customer.set_attributes(d['attributes'])

            # Service経由で更新
            if self.service.update_customer(updated_customer):
                self.load_data()

    def on_delete_selected(self):
        target = self.get_selected_row_data(self.customers)
        if not target: return

        msg = f"客層「{target.label}」を削除しますか？\n\n「Yes」= 完全に削除\n「No」= 無効化 (非表示)\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if res == QMessageBox.Yes:
            # Service経由で削除
            if self.service.delete_customer(target):
                self.load_data()
        elif res == QMessageBox.No:
            # Service経由で無効化
            if self.service.disable_customer(target):
                self.load_data()

    def _move(self, direction):
        row = self.table.currentRow()
        if row < 0: return
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.customers): return

        a, b = self.customers[row], self.customers[new_row]
        order_map = {a.id: b.display_order, b.id: a.display_order}

        # Service経由で並び替え
        if self.service.update_display_order(order_map):
            self.load_data()
            self.table.selectRow(new_row)