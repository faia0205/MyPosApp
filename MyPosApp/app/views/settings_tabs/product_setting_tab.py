from PySide6.QtWidgets import QMessageBox, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.models.product import Product
from app.repositories.product_repo import ProductRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.product_edit_dialog import ProductEditDialog
from app.views.settings_tabs.base_setting_tab import BaseSettingTab # ★継承

class ProductSettingTab(BaseSettingTab): # ★継承
    """商品管理タブ"""
    def __init__(self):
        # 基底クラスの初期化 (タイトルなし)
        super().__init__()
        
        self.repo = ProductRepository()
        self.log_repo = LogRepository()
        
        # カラム設定
        self.set_columns(["ID", "商品名", "価格", "カテゴリ", "色", "状態", "メモ"])
        
        # ★追加ボタンのカスタマイズ (並び替えボタンを挿入)
        # Baseクラスで作られた layout_btns に追加する
        
        # 一旦 stretch を削除してボタンを追加し、再度 stretch を入れる等の調整もできるが
        # ここでは insertWidget を使って「編集」ボタンの後ろあたりに入れる
        
        self.btn_up = QPushButton("▲ 上へ")
        self.btn_up.clicked.connect(lambda: self._move_row(-1))
        self.layout_btns.insertWidget(2, self.btn_up) # index 2 は編集ボタンの次

        self.btn_down = QPushButton("▼ 下へ")
        self.btn_down.clicked.connect(lambda: self._move_row(1))
        self.layout_btns.insertWidget(3, self.btn_down)
        
        # 初回ロード
        self.load_data()

    def load_data(self):
        """DBから全データを読み込んで表示"""
        products = self.repo.fetch_all_as_models()
        self.table.setRowCount(len(products))
        self.current_products = products

        # カテゴリリスト更新（ダイアログ用）
        self.existing_categories = sorted(list({p.category for p in products if p.category}))
        for default_cat in ["ドリンク", "フード"]:
            if default_cat not in self.existing_categories:
                self.existing_categories.insert(0, default_cat)

        for row, p in enumerate(products):
            # ID
            self.table.setItem(row, 0, self.create_item(p.id, align=Qt.AlignCenter))
            # Name
            self.table.setItem(row, 1, self.create_item(p.name))
            # Price
            self.table.setItem(row, 2, self.create_item(f"¥{p.price:,}", align=Qt.AlignRight))
            # Category
            self.table.setItem(row, 3, self.create_item(p.category))
            # Color (背景色付き)
            item_color = self.create_item(p.color, text_color="black", bg_color=p.color)
            self.table.setItem(row, 4, item_color)
            
            # Status
            status_text = "● 販売中" if p.is_active else "× 停止中"
            s_fg = "#69f0ae" if p.is_active else "#bdbdbd"
            s_bg = "#1b5e20" if p.is_active else "#424242"
            self.table.setItem(row, 5, self.create_item(status_text, text_color=s_fg, bg_color=s_bg, align=Qt.AlignCenter))
            
            # Note
            self.table.setItem(row, 6, self.create_item(p.note))

    def on_add(self):
        dialog = ProductEditDialog(parent=self)
        dialog.set_category_list(self.existing_categories)
        if dialog.exec():
            data = dialog.get_data()
            new_product = Product(
                id=None,
                name=data["name"],
                price=data["price"],
                category=data["category"],
                color=data["color"],
                note=data["note"],
                is_active=data["is_active"]
            )
            if self.repo.add_product(new_product):
                self.log_repo.add_log("info", f"商品追加: {new_product.name}")
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "追加に失敗しました")

    def on_edit_selected(self):
        target = self.get_selected_row_data(self.current_products)
        if not target: return
        
        dialog = ProductEditDialog(target, parent=self)
        dialog.set_category_list(self.existing_categories)
        
        if dialog.exec():
            data = dialog.get_data()
            updated_product = Product(
                id=target.id,
                name=data["name"],
                price=data["price"],
                category=data["category"],
                color=data["color"],
                note=data["note"],
                is_active=data["is_active"],
                display_order=target.display_order
            )
            if self.repo.update_product(updated_product):
                self.log_repo.add_log("info", f"商品変更: {target.name} -> {updated_product.name}")
                self.load_data()
                # 選択位置を維持したい場合はここで再選択処理

    def on_delete_selected(self):
        target = self.get_selected_row_data(self.current_products)
        if not target: return

        msg = f"商品「{target.name}」を削除しますか？\n\n「Yes」= 完全に削除\n「No」= 販売停止 (無効化)\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if res == QMessageBox.Yes:
            if self.repo.delete_product(target.id):
                self.log_repo.add_log("warning", f"商品完全削除: {target.name}")
                self.load_data()
        elif res == QMessageBox.No:
            target.is_active = False
            if self.repo.update_product(target):
                self.log_repo.add_log("info", f"商品無効化: {target.name}")
                self.load_data()

    def _move_row(self, direction):
        target = self.get_selected_row_data(self.current_products)
        if not target: return
        
        row = self.table.currentRow()
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.current_products): return

        item_b = self.current_products[new_row]
        order_map = {target.id: item_b.display_order, item_b.id: target.display_order}
        
        if self.repo.update_display_order(order_map):
            self.load_data()
            self.table.selectRow(new_row)