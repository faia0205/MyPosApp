from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.models.product import Product
from app.repositories.product_repo import ProductRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.product_edit_dialog import ProductEditDialog

class ProductSettingTab(QWidget):
    """商品管理タブ"""
    def __init__(self):
        super().__init__()
        self.repo = ProductRepository()
        # ★追加: ログリポジトリの初期化
        self.log_repo = LogRepository()
        
        self._init_ui()
        self.load_data()

    # ... (_init_ui, load_data などは変更なし) ...
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # --- 操作ボタン群 ---
        btn_layout = QHBoxLayout()
        
        btn_add = QPushButton("＋ 新規追加")
        btn_add.setFixedSize(120, 40)
        btn_add.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold;")
        btn_add.clicked.connect(self._add_product)
        btn_layout.addWidget(btn_add)

        btn_edit = QPushButton("編集")
        btn_edit.clicked.connect(self._edit_selected)
        btn_layout.addWidget(btn_edit)

        # 並び替えボタン
        btn_up = QPushButton("▲ 上へ")
        btn_up.clicked.connect(lambda: self._move_row(-1))
        btn_layout.addWidget(btn_up)

        btn_down = QPushButton("▼ 下へ")
        btn_down.clicked.connect(lambda: self._move_row(1))
        btn_layout.addWidget(btn_down)

        btn_layout.addStretch()

        btn_del = QPushButton("削除 (無効化)")
        btn_del.setStyleSheet("background-color: #c62828; color: white;")
        btn_del.clicked.connect(self._delete_selected)
        btn_layout.addWidget(btn_del)

        layout.addLayout(btn_layout)

        # --- 一覧テーブル ---
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "商品名", "価格", "カテゴリ", "色", "状態", "メモ"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows) # 行選択
        self.table.setSelectionMode(QTableWidget.SingleSelection) # 単一選択
        self.table.doubleClicked.connect(self._edit_selected) # ダブルクリックで編集
        
        # スタイル設定
        self.table.setStyleSheet("""
            QTableWidget { background-color: #222; gridline-color: #444; color: white; }
            QHeaderView::section { background-color: #333; color: white; border: 1px solid #444; }
            QTableWidget::item:selected { background-color: #0d47a1; }
        """)

        layout.addWidget(self.table)
        
        # ヒント
        layout.addWidget(QLabel("※ 削除ボタンは物理削除ではなく「無効化」を推奨します。並び順は「上へ」「下へ」で変更可能です。"))

    def load_data(self):
        """DBから全データを読み込んで表示"""
        products = self.repo.fetch_all_as_models()
        self.table.setRowCount(len(products))
        self.current_products = products

        # ★追加: 現在使われているカテゴリの一覧を取得（ダイアログに渡すため）
        self.existing_categories = sorted(list({p.category for p in products if p.category}))
        if "フード" not in self.existing_categories:
            self.existing_categories.insert(0, "フード")
        if "ドリンク" not in self.existing_categories:
            self.existing_categories.insert(1, "ドリンク")

        for row, p in enumerate(products):
            # 共通のフラグ設定関数: 選択はできるが編集は不可
            def create_readonly_item(text):
                item = QTableWidgetItem(str(text))
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled) # Editable を外す
                return item

            # ID
            item_id = create_readonly_item(p.id)
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            # Name
            self.table.setItem(row, 1, create_readonly_item(p.name))

            # Price
            item_price = create_readonly_item(f"¥{p.price:,}")
            item_price.setTextAlignment(Qt.AlignRight)
            self.table.setItem(row, 2, item_price)

            # Category
            self.table.setItem(row, 3, create_readonly_item(p.category))

            # Color
            item_color = create_readonly_item(p.color)
            item_color.setBackground(QColor(p.color))
            item_color.setForeground(QColor("black"))
            self.table.setItem(row, 4, item_color)

            # Status (★見やすく変更)
            # 文字色だけでなく、アイコンや記号で状態を示す
            status_text = "● 販売中" if p.is_active else "× 停止中"
            item_status = create_readonly_item(status_text)
            if p.is_active:
                item_status.setForeground(QColor("#69f0ae")) # 明るい緑
                item_status.setBackground(QColor("#1b5e20")) # 背景を濃い緑に
            else:
                item_status.setForeground(QColor("#bdbdbd")) # グレー
                item_status.setBackground(QColor("#424242")) # 背景も暗く
            item_status.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 5, item_status)

            # Note
            self.table.setItem(row, 6, create_readonly_item(p.note))

    # _add_product / _edit_selected でダイアログを呼ぶ際にカテゴリリストを渡す
    def _add_product(self):
        dialog = ProductEditDialog(parent=self)
        dialog.set_category_list(self.existing_categories)
        if dialog.exec():
            data = dialog.get_data()
            
            # オブジェクト作成 (IDはNone)
            new_product = Product(
                id=None,
                name=data["name"],
                price=data["price"],
                category=data["category"],
                color=data["color"],
                note=data["note"],
                is_active=data["is_active"]
            )
            
            # Repositoryへオブジェクトを渡す
            success = self.repo.add_product(new_product)
            
            if success:
                self.log_repo.add_log("info", f"商品追加: {new_product.name}")
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "追加に失敗しました")

    def _edit_selected(self):
        """選択行を編集"""
        row = self.table.currentRow()
        if row < 0:
            return
        
        target = self.current_products[row]
        dialog = ProductEditDialog(target, parent=self)
        dialog.set_category_list(self.existing_categories)
        
        if dialog.exec():
            data = dialog.get_data()

            # 更新用オブジェクト作成 (ID維持)
            updated_product = Product(
                id=target.id,
                name=data["name"],
                price=data["price"],
                category=data["category"],
                color=data["color"],
                note=data["note"],
                is_active=data["is_active"],
                display_order=target.display_order # 順序は維持
            )

            success = self.repo.update_product(updated_product)
            
            if success:
                self.log_repo.add_log("info", f"商品変更: {target.name} -> {updated_product.name}")
                self.load_data()
                self.table.selectRow(row)

    def _delete_selected(self):
        """論理削除（無効化）または物理削除"""
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.current_products[row]

        msg = f"商品「{target.name}」を削除しますか？\n\n「Yes」= 完全に削除 (履歴等の整合性が壊れる可能性があります)\n「No」= 販売停止 (無効化) するのみ\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if res == QMessageBox.Yes:
            # 物理削除
            if self.repo.delete_product(target.id):
                self.log_repo.add_log("warning", f"商品完全削除: {target.name}")
                self.load_data()
        elif res == QMessageBox.No:
            # 無効化
            target.is_active = False
            if self.repo.update_product(target):
                self.log_repo.add_log("info", f"商品無効化: {target.name}")
                self.load_data()

    def _move_row(self, direction):
        """
        表示順の入れ替え (display_orderをスワップする)
        direction: -1 (Up), 1 (Down)
        """
        row = self.table.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.current_products):
            return

        item_a = self.current_products[row]
        item_b = self.current_products[new_row]

        # orderの値を入れ替え
        # ※ DB上での一意性制約がない前提。あれば一時退避が必要だが今回は単純スワップ
        new_order_map = {
            item_a.id: item_b.display_order,
            item_b.id: item_a.display_order
        }

        if self.repo.update_display_order(new_order_map):
            # 並び替えは頻繁に行うのでログは出さないか、出すならレベルを下げる
            # self.log_repo.add_log("info", "商品並び替え実施") 
            self.load_data()
            self.table.selectRow(new_row)