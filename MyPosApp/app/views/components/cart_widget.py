import urllib.parse
from typing import List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QLabel, QPushButton, QMessageBox, 
                               QDialog, QListWidget, QAbstractItemView) # ★追加
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from app.services.cart_service import CartService

class CartWidget(QWidget):
    """カート（商品一覧＋割引＋合計）を表示・操作するウィジェット"""
    
    def __init__(self, cart_service: CartService, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service
        self.current_indices_map: List[int] = [] 
        self._init_ui()
        self.cart_service.cart_updated.connect(self._render_cart)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 案内ウィンドウ (HTMLリンク対応)
        self.info_box = QLabel("いらっしゃいませ")
        self.info_box.setFixedHeight(85)
        self.info_box.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.info_box.setWordWrap(True)
        self.info_box.setOpenExternalLinks(False) # 外部ブラウザで開かせない
        self.info_box.linkActivated.connect(self._on_link_activated) # ★リンクハンドラ接続
        
        self.info_box.setStyleSheet("""
            background-color: #37474f; 
            color: #fff; 
            border: 2px solid #90caf9; 
            padding: 8px; 
            font-size: 14px;
        """)
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
            sub = d.amount
            
            def create_disc_item(text):
                it = QTableWidgetItem(str(text))
                it.setForeground(QColor("#ff8a80"))
                it.setFlags(it.flags() ^ Qt.ItemIsEditable)
                return it
                
            self.discount_table.setItem(i, 0, create_disc_item(d.name))
            self.discount_table.setItem(i, 1, create_disc_item(f"{d.qty}回"))
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
        border_color = "#90caf9" if msg_type == "info" else "#ff5252"
        bg_color = "#37474f" if msg_type == "info" else "#5d4037"
        
        self.info_box.setStyleSheet(f"""
            background-color: {bg_color}; 
            color: #fff; 
            border: 2px solid {border_color}; 
            padding: 8px;
            font-size: 14px;
        """)
        self.info_box.setText(text)

    # ★追加: リンククリック時の処理
    def _on_link_activated(self, link: str):
        if link.startswith("discount_details:"):
            # データをデコードしてリスト化
            encoded_data = link.replace("discount_details:", "")
            decoded_data = urllib.parse.unquote(encoded_data)
            rules = decoded_data.split("|")
            
            self._show_discount_details(rules)

    # ★追加: 詳細ポップアップ表示
    def _show_discount_details(self, rules: List[str]):
        dlg = QDialog(self)
        dlg.setWindowTitle("対象の割引ルール")
        dlg.setFixedSize(300, 250)
        dlg.setStyleSheet("background-color: #424242; color: white;")
        
        layout = QVBoxLayout(dlg)
        
        lbl = QLabel("この商品に適用可能な割引:")
        lbl.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        layout.addWidget(lbl)
        
        lst = QListWidget()
        lst.addItems(rules)
        lst.setStyleSheet("""
            QListWidget { background-color: #333; border: 1px solid #666; font-size: 14px; }
            QListWidget::item { padding: 5px; }
        """)
        lst.setSelectionMode(QAbstractItemView.NoSelection) # 選択不可
        layout.addWidget(lst)
        
        btn = QPushButton("閉じる")
        btn.setStyleSheet("""
            QPushButton { background-color: #0277bd; color: white; padding: 8px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background-color: #039be5; }
        """)
        btn.clicked.connect(dlg.accept)
        layout.addWidget(btn)
        
        dlg.exec()