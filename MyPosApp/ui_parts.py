from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
                               QFrame, QTabWidget, QDialog, QLineEdit, QDialogButtonBox,
                               QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

class HeaderWidget(QFrame):
    """(変更なし)"""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #333; color: white; border-radius: 5px; margin-bottom: 5px;")
        layout = QHBoxLayout(self)
        self.labels = {}
        for key in ["総売上", "経費計", "現在利益", "黒字まで"]:
            lbl = QLabel(f"{key}: ---")
            lbl.setFont(QFont("Meiryo", 12, QFont.Bold))
            layout.addWidget(lbl)
            self.labels[key] = lbl

    def update_stats(self, sales, expenses, profit, target_msg, is_red):
        self.labels["総売上"].setText(f"総売上: ¥{sales:,}")
        self.labels["経費計"].setText(f"経費計: ¥{expenses:,}")
        self.labels["現在利益"].setText(f"現在利益: ¥{profit:,}")
        self.labels["黒字まで"].setText(target_msg)
        color = "#ff5252" if is_red else "#69f0ae"
        self.labels["黒字まで"].setStyleSheet(f"color: {color};")


class CartWidget(QWidget):
    # シグナル定義
    item_qty_changed = Signal(int, int) # 行, 新しい個数
    item_decrease = Signal(int)         # 行 (1減らす)
    item_removed = Signal(int)          # 行 (削除)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 情報ボックス
        self.info_box = QLabel("いらっしゃいませ")
        self.info_box.setFixedHeight(50)
        self.update_message("いらっしゃいませ", "info")
        layout.addWidget(self.info_box)

        # カートテーブル
        self.table = QTableWidget()
        # カラム構成: 商品名, 個数, 単価, 小計, [-], [×]
        self.table.setColumnCount(6) 
        self.table.setHorizontalHeaderLabels(["商品", "個", "単価", "小計", "", ""])
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.Fixed) # マイナスボタン列
        h.setSectionResizeMode(5, QHeaderView.Fixed) # 削除ボタン列
        self.table.setColumnWidth(4, 35)
        self.table.setColumnWidth(5, 35)
        
        layout.addWidget(self.table)

        # 合計
        self.total_label = QLabel("合計: ¥ 0")
        self.total_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("background-color: #000; color: #0f0; padding: 10px;")
        layout.addWidget(self.total_label)

        # 編集イベント
        self.table.cellChanged.connect(self._on_cell_changed)
        self.is_updating = False

        # ★追加: 表示順マッピング (表示行 -> データ行)
        self.display_map = [] 

    def update_cart_view(self, cart_items, total_amount):
        """
        データを並び替えて表示する (割引を下に)
        """
        self.is_updating = True
        self.table.blockSignals(True)

        # 1. 表示順序を決定する (インデックスのリストを作る)
        # 通常商品(価格>=0)を先、割引(価格<0)を後に
        normal_indices = [i for i, x in enumerate(cart_items) if x['price'] >= 0]
        discount_indices = [i for i, x in enumerate(cart_items) if x['price'] < 0]
        
        # マッピングリストを更新 (表示行[0] は データ行[normal_indices[0]] を指す)
        self.display_map = normal_indices + discount_indices

        # テーブル更新
        self.table.setRowCount(len(self.display_map))
        
        for view_row, data_index in enumerate(self.display_map):
            item = cart_items[data_index]
            self._render_row(view_row, item, data_index)

        self.total_label.setText(f"合計: ¥ {total_amount:,}")
        self.table.blockSignals(False)
        self.is_updating = False

    def _render_row(self, view_row, item, data_index):
        """1行分の描画処理"""
        subtotal = item['price'] * item['qty']
        
        # 0: 商品名
        name_item = QTableWidgetItem(str(item['name']))
        name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
        # 割引なら文字色を変える
        if item['price'] < 0: name_item.setForeground(QColor("red"))
        self.table.setItem(view_row, 0, name_item)

        # 1: 個数 (編集可)
        self.table.setItem(view_row, 1, QTableWidgetItem(str(item['qty'])))

        # 2: 単価
        self.table.setItem(view_row, 2, QTableWidgetItem(str(item['price'])))

        # 3: 小計
        sub_item = QTableWidgetItem(f"¥{subtotal:,}")
        sub_item.setFlags(sub_item.flags() ^ Qt.ItemIsEditable)
        if item['price'] < 0: sub_item.setForeground(QColor("red"))
        self.table.setItem(view_row, 3, sub_item)

        # 4: マイナスボタン [-]
        minus_btn = QPushButton("-")
        minus_btn.setStyleSheet("color: blue; font-weight: bold;")
        # ★重要: クリック時に元のデータ行(data_index)を渡す
        minus_btn.clicked.connect(lambda _, idx=data_index: self.item_decrease.emit(idx))
        minus_btn.setFocusPolicy(Qt.NoFocus)
        self.table.setCellWidget(view_row, 4, minus_btn)

        # 5: 削除ボタン [×]
        del_btn = QPushButton("×")
        del_btn.setStyleSheet("color: red; font-weight: bold;")
        del_btn.clicked.connect(lambda _, idx=data_index: self.item_removed.emit(idx))
        del_btn.setFocusPolicy(Qt.NoFocus)
        self.table.setCellWidget(view_row, 5, del_btn)

    def _on_cell_changed(self, row, column):
        """セル編集時の処理"""
        if self.is_updating: return
        
        # 表示行(row)からデータ行(data_index)へ変換
        if row < len(self.display_map):
            data_index = self.display_map[row]
            
            if column == 1: # 個数変更
                try:
                    val = int(self.table.item(row, column).text())
                    self.item_qty_changed.emit(data_index, val)
                except ValueError: pass

    def update_message(self, text, type_):
        style = "padding: 10px; border-radius: 5px; font-size: 14px; font-weight: bold;"
        if type_ == "warning":
            style += "background-color: #ffebee; color: #b71c1c; border: 2px solid #f44336;"
        else:
            style += "background-color: #e3f2fd; color: #333333; border: 1px solid #2196f3;"
        self.info_box.setText(text)
        self.info_box.setStyleSheet(style)

class ProductTabWidget(QTabWidget):
    """カテゴリごとに商品を分けるタブウィジェット"""
    def __init__(self):
        super().__init__()
        pass
        #self.setStyleSheet("""
        #    QTabBar::tab { height: 40px; width: 100px; font-size: 14px; }
        #    QTabBar::tab:selected { font-weight: bold; background-color: #fff; }
        #""")

    def add_category_tab(self, category_name, widget):
        self.addTab(widget, category_name)

class PaymentDialog(QDialog):
    """決済画面：現金とその他決済（PayPay等）の金額を入力"""
    def __init__(self, total_amount, parent=None):
        super().__init__(parent)
        self.setWindowTitle("お会計")
        self.setFixedSize(400, 350)
        self.total_amount = total_amount
        
        layout = QVBoxLayout(self)

        # 合計金額表示
        lbl_total = QLabel(f"合計: ¥{total_amount:,}")
        lbl_total.setStyleSheet("font-size: 32px; font-weight: bold; color: #d32f2f;")
        lbl_total.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_total)

        # 入力フォームエリア
        form_layout = QGridLayout()
        
        # PayPay入力
        form_layout.addWidget(QLabel("PayPay等:"), 0, 0)
        self.input_other = QLineEdit("0")
        self.input_other.setStyleSheet("font-size: 20px;")
        self.input_other.setAlignment(Qt.AlignRight)
        form_layout.addWidget(self.input_other, 0, 1)

        # 現金入力
        form_layout.addWidget(QLabel("現金お預り:"), 1, 0)
        self.input_cash = QLineEdit("0")
        self.input_cash.setStyleSheet("font-size: 20px;")
        self.input_cash.setAlignment(Qt.AlignRight)
        self.input_cash.setFocus() # 初期フォーカス
        form_layout.addWidget(self.input_cash, 1, 1)

        layout.addLayout(form_layout)

        # お釣り表示エリア
        self.lbl_change = QLabel("お釣り: ¥0")
        self.lbl_change.setStyleSheet("font-size: 24px; font-weight: bold; color: blue;")
        self.lbl_change.setAlignment(Qt.AlignRight)
        layout.addWidget(self.lbl_change)

        # ボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # イベント接続: 入力があるたびにお釣りを計算
        self.input_cash.textChanged.connect(self._calculate_change)
        self.input_other.textChanged.connect(self._calculate_change)

    def _calculate_change(self):
        try:
            cash = int(self.input_cash.text() or 0)
            other = int(self.input_other.text() or 0)
            
            paid_total = cash + other
            change = paid_total - self.total_amount
            
            if change >= 0:
                self.lbl_change.setText(f"お釣り: ¥{change:,}")
                self.lbl_change.setStyleSheet("font-size: 24px; font-weight: bold; color: blue;")
            else:
                short = abs(change)
                self.lbl_change.setText(f"不足: ¥{short:,}")
                self.lbl_change.setStyleSheet("font-size: 24px; font-weight: bold; color: red;")
                
            return cash, other, change
        except ValueError:
            return 0, 0, -self.total_amount

    def get_payment_data(self):
        """入力された決済情報を返す"""
        cash, other, change = self._calculate_change()
        return {
            'cash': cash,
            'other': other,
            'change': change
        }