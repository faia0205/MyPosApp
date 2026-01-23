from typing import List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QLabel, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.services.cart_service import CartService

class CartWidget(QWidget):
    """カート（商品一覧＋割引＋合計）を表示・操作するウィジェット"""
    
    def __init__(self, cart_service: CartService, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service
        self.current_indices_map: List[int] = [] 
        self._init_ui()
        
        # シグナル接続
        self.cart_service.cart_updated.connect(self._render_cart)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 案内ラベル
        self.info_box = QLabel("いらっしゃいませ")
        self.info_box.setFixedHeight(40)
        self.info_box.setStyleSheet("background-color: #37474f; color: #fff; border: 1px solid #90caf9; padding: 5px; font-weight: bold;")
        layout.addWidget(self.info_box)
        
        self.cart_service.message_updated.connect(self._update_message)

        # 2. カートテーブル
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels(["商品", "個", "単価", "小計", "", ""])
        
        self.cart_table.setStyleSheet("""
            QTableWidget {
                background-color: #333333; gridline-color: #555555; color: #ffffff;
                selection-background-color: #0d47a1; border: 1px solid #555;
            }
            QHeaderView::section {
                background-color: #424242; color: white; padding: 4px; border: 1px solid #666; font-weight: bold;
            }
            QLineEdit {
                color: #000000; background-color: #ffffff; border: 2px solid #2196f3; font-weight: bold;
            }
        """)

        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(4, 35)
        self.cart_table.setColumnWidth(5, 35)
        
        self.cart_table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self.cart_table, stretch=2)

        # 3. 割引テーブル
        self.lbl_discount_title = QLabel("適用割引")
        self.lbl_discount_title.setStyleSheet("font-weight: bold; color: #ff8a80; margin-top: 5px;")
        layout.addWidget(self.lbl_discount_title)

        self.discount_table = QTableWidget()
        self.discount_table.setColumnCount(3)
        self.discount_table.setHorizontalHeaderLabels(["割引名", "回数", "値引額"])
        self.discount_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.discount_table.verticalHeader().setVisible(False)
        self.discount_table.setFixedHeight(100)
        self.discount_table.setStyleSheet("""
            QTableWidget { background-color: #424242; color: #ff8a80; border: 1px solid #d32f2f; }
            QHeaderView::section { background-color: #5d4037; color: white; }
        """)
        layout.addWidget(self.discount_table, stretch=1)

        # 4. 合計ラベル
        self.lbl_total = QLabel("合計: ¥0")
        self.lbl_total.setStyleSheet("font-size: 24px; font-weight: bold; background-color: #212121; color: #00e676; padding: 10px; border-radius: 4px;")
        self.lbl_total.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_total)

    def _render_cart(self):
        items = self.cart_service.cart_items
        
        # ソート: マイナス価格(値引)は下に、それ以外は価格順
        indices = list(range(len(items)))
        indices.sort(key=lambda i: (items[i].price < 0, -items[i].price))
        self.current_indices_map = indices

        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(indices))

        def create_item(text, color, editable=False):
            it = QTableWidgetItem(str(text))
            it.setForeground(color)
            if not editable:
                it.setFlags(it.flags() ^ Qt.ItemIsEditable)
            return it

        for view_row, data_index in enumerate(indices):
            item = items[data_index]
            
            display_name = item.name
            text_color = QColor("white")
            if item.price < 0:
                text_color = QColor("#ff8a80")
            elif self.cart_service.is_discount_target(item.id):
                display_name = "★ " + display_name
                text_color = QColor("#ffeb3b")

            self.cart_table.setItem(view_row, 0, create_item(display_name, text_color, False))
            self.cart_table.setItem(view_row, 1, create_item(item.qty, text_color, True))
            self.cart_table.setItem(view_row, 2, create_item(item.price, text_color, True))
            self.cart_table.setItem(view_row, 3, create_item(f"¥{item.subtotal:,}", text_color, False))
            
            # ボタン
            btn_decr = QPushButton("-")
            btn_decr.setStyleSheet("color: #90caf9; font-weight: bold; background-color: #424242; border: 1px solid #666;")
            btn_decr.setFocusPolicy(Qt.NoFocus)
            btn_decr.clicked.connect(lambda _, idx=data_index: self.cart_service.decrease_item_qty(idx))
            self.cart_table.setCellWidget(view_row, 4, btn_decr)

            btn_del = QPushButton("×")
            btn_del.setStyleSheet("color: #ef9a9a; font-weight: bold; background-color: #424242; border: 1px solid #666;")
            btn_del.setFocusPolicy(Qt.NoFocus)
            btn_del.clicked.connect(lambda _, idx=data_index: self.cart_service.remove_item(idx))
            self.cart_table.setCellWidget(view_row, 5, btn_del)

        self.cart_table.blockSignals(False)
        
        # 割引テーブル描画
        discounts = self.cart_service.applied_discounts
        self.discount_table.setRowCount(len(discounts))
        for i, d in enumerate(discounts):
            sub = d['amount'] * d['qty']
            def create_disc_item(text):
                it = QTableWidgetItem(str(text))
                it.setForeground(QColor("#ff8a80"))
                it.setFlags(it.flags() ^ Qt.ItemIsEditable)
                return it
            self.discount_table.setItem(i, 0, create_disc_item(d['name']))
            self.discount_table.setItem(i, 1, create_disc_item(f"{d['qty']}回"))
            self.discount_table.setItem(i, 2, create_disc_item(f"¥{sub:,}"))

        # 合計更新
        total = self.cart_service.get_total_amount()
        self.lbl_total.setText(f"合計: ¥{total:,}")

    def _on_cell_changed(self, row: int, col: int) -> None:
        if row >= len(self.current_indices_map): return
        data_index = self.current_indices_map[row]
        item_widget = self.cart_table.item(row, col)
        if not item_widget: return
        
        clean_text = item_widget.text().replace("¥", "").replace(",", "").strip()
        try:
            val = int(clean_text)
            if col == 1: self.cart_service.update_item_qty(data_index, val)
            elif col == 2: self.cart_service.update_item_price(data_index, val)
        except ValueError:
            QMessageBox.warning(self, "入力エラー", "半角数字で入力してください。")
            self._render_cart()

    def _update_message(self, text: str, msg_type: str) -> None:
        base_style = "padding: 5px; border-radius: 4px; font-weight: bold;"
        if msg_type == "info":
            bg_color = "#37474f"
            text_color = "#ffffff"
            border = "1px solid #90caf9"
        else:
            bg_color = "#5d4037"
            text_color = "#ff8a80"
            border = "2px solid #ff5252"
        self.info_box.setText(text)
        self.info_box.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; border: {border}; {base_style}")