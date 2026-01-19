from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from app.repositories.product_repo import ProductRepository
from app.views.dialogs.product_edit_dialog import ProductEditDialog

class ProductSettingTab(QWidget):
    """商品管理タブ"""
    def __init__(self):
        super().__init__()
        self.repo = ProductRepository()
        self._init_ui()
        self.load_data()

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
        products = self.repo.fetch_all_as_models() # 全件取得(無効含む)
        self.table.setRowCount(len(products))
        
        # データ保持用 (行番号 -> Productオブジェクト)
        self.current_products = products

        for row, p in enumerate(products):
            # ID
            item_id = QTableWidgetItem(str(p.id))
            item_id.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, item_id)

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(p.name))

            # Price
            item_price = QTableWidgetItem(f"¥{p.price:,}")
            item_price.setTextAlignment(Qt.AlignRight)
            self.table.setItem(row, 2, item_price)

            # Category
            self.table.setItem(row, 3, QTableWidgetItem(p.category))

            # Color (セル自体に色をつける)
            item_color = QTableWidgetItem(p.color)
            item_color.setBackground(QColor(p.color))
            item_color.setForeground(QColor("black")) # 文字は見やすく黒固定
            self.table.setItem(row, 4, item_color)

            # Status (Active)
            status_text = "販売中" if p.is_active else "無効"
            item_status = QTableWidgetItem(status_text)
            if not p.is_active:
                item_status.setForeground(QColor("#ff5252")) # 赤文字
            else:
                item_status.setForeground(QColor("#69f0ae")) # 緑文字
            self.table.setItem(row, 5, item_status)

            # Note
            self.table.setItem(row, 6, QTableWidgetItem(p.note))

    def _add_product(self):
        """追加ダイアログを開く"""
        dialog = ProductEditDialog(parent=self)
        if dialog.exec():
            data = dialog.get_data()
            success = self.repo.add_product(
                data["name"], data["price"], data["category"], 
                data["color"], data["note"]
            )
            if success:
                self.load_data()
            else:
                QMessageBox.warning(self, "エラー", "追加に失敗しました")

    def _edit_selected(self):
        """選択行を編集"""
        row = self.table.currentRow()
        if row < 0: return
        
        target = self.current_products[row]
        dialog = ProductEditDialog(target, parent=self)
        
        if dialog.exec():
            data = dialog.get_data()
            success = self.repo.update_product(
                target.id, data["name"], data["price"], data["category"], 
                data["color"], data["note"], data["is_active"]
            )
            if success:
                self.load_data()
                # 編集していた行を再度選択状態にする
                self.table.selectRow(row)

    def _delete_selected(self):
        """論理削除（無効化）または物理削除"""
        row = self.table.currentRow()
        if row < 0: return
        target = self.current_products[row]

        msg = f"商品「{target.name}」を削除しますか？\n\n「Yes」= 完全に削除 (履歴等の整合性が壊れる可能性があります)\n「No」= 販売停止 (無効化) するのみ\n「Cancel」= やめる"
        res = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)

        if res == QMessageBox.Yes:
            # 物理削除
            if self.repo.delete_product(target.id):
                self.load_data()
        elif res == QMessageBox.No:
            # 無効化 (論理削除)
            if self.repo.update_product(target.id, target.name, target.price, target.category, target.color, target.note, False):
                self.load_data()

    def _move_row(self, direction):
        """
        表示順の入れ替え (display_orderをスワップする)
        direction: -1 (Up), 1 (Down)
        """
        row = self.table.currentRow()
        if row < 0: return
        
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.current_products):
            return

        # スワップ対象
        item_a = self.current_products[row]
        item_b = self.current_products[new_row]

        # orderの値を入れ替え
        # ※ DB上での一意性制約がない前提。あれば一時退避が必要だが今回は単純スワップ
        new_order_map = {
            item_a.id: item_b.display_order,
            item_b.id: item_a.display_order
        }

        if self.repo.update_display_order(new_order_map):
            self.load_data()
            self.table.selectRow(new_row)