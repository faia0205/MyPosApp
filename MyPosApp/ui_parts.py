from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView, 
                               QFrame, QTabWidget, QGridLayout, QScrollArea, QAbstractItemView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

class HeaderWidget(QFrame):
    """上部の経営分析ヘッダー"""
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #333; color: white; border-radius: 5px; margin-bottom: 5px;")
        layout = QHBoxLayout(self)
        
        # 辞書でラベルを管理
        self.labels = {}
        # 初期表示
        items = ["総売上", "経費計", "現在利益", "黒字まで"]
        
        for key in items:
            # 見出しと値を分けるなどレイアウトは好みで調整可
            lbl = QLabel(f"{key}: ---")
            lbl.setFont(QFont("Meiryo", 14, QFont.Bold))
            layout.addWidget(lbl)
            self.labels[key] = lbl

    def update_stats(self, sales, expenses, profit, target_msg, is_red):
        """Logic層からの通知を受けて表示を更新する"""
        self.labels["総売上"].setText(f"総売上: ¥{sales:,}")
        self.labels["経費計"].setText(f"経費計: ¥{expenses:,}")
        self.labels["現在利益"].setText(f"現在利益: ¥{profit:,}")
        self.labels["黒字まで"].setText(target_msg)
        
        # 赤字なら赤色、黒字なら緑色
        color = "#ff5252" if is_red else "#69f0ae"
        self.labels["黒字まで"].setStyleSheet(f"color: {color};")

class CartWidget(QWidget):
    # 行番号、変更後の個数、変更後の単価 を通知するシグナル
    item_changed = Signal(int, int, int)
    item_removed = Signal(int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        # 情報ボックス
        self.info_box = QLabel("いらっしゃいませ")
        self.info_box.setFixedHeight(50)
        self.update_message("いらっしゃいませ", "info")
        layout.addWidget(self.info_box)

        # カートテーブル (編集可能にする)
        self.table = QTableWidget()
        self.table.setColumnCount(5) # 商品名, 個数, 単価, 小計, 削除
        self.table.setHorizontalHeaderLabels(["商品", "個", "単価", "小計", ""])
        
        # ヘッダー調整
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 40)
        
        layout.addWidget(self.table)

        # 合計ラベル
        self.total_label = QLabel("合計: ¥ 0")
        self.total_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("background-color: #000; color: #0f0; padding: 10px;")
        layout.addWidget(self.total_label)

        # イベント接続: セルの値が変わったら発火
        self.table.cellChanged.connect(self._on_cell_changed)
        
        self.is_updating = False # ループ防止用フラグ

    def update_cart_view(self, cart_items, total_amount):
        """ロジック層からのデータで表示を更新（★スマート更新版）"""
        
        # テーブルからのシグナルを一時停止（無限ループ防止）
        self.table.blockSignals(True)
        
        current_row_count = self.table.rowCount()
        new_row_count = len(cart_items)

        # 行数が違う場合のみ、テーブルを作り直す
        if current_row_count != new_row_count:
            self.table.setRowCount(new_row_count)
            # 全行作り直し
            for row, item in enumerate(cart_items):
                self._create_row_items(row, item)
        else:
            # 行数が同じなら、既存のセルの中身だけ更新する (これでエラーが消える)
            for row, item in enumerate(cart_items):
                self._update_row_items(row, item)

        self.total_label.setText(f"合計: ¥ {total_amount:,}")
        
        # シグナル再開
        self.table.blockSignals(False)

    def _create_row_items(self, row, item):
        """行を新規作成する内部関数"""
        subtotal = item['price'] * item['qty']
        
        # 1. 商品名
        name_item = QTableWidgetItem(str(item['name']))
        name_item.setFlags(name_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 0, name_item)
        
        # 2. 個数
        self.table.setItem(row, 1, QTableWidgetItem(str(item['qty'])))
        
        # 3. 単価
        self.table.setItem(row, 2, QTableWidgetItem(str(item['price'])))
        
        # 4. 小計
        sub_item = QTableWidgetItem(f"¥{subtotal:,}")
        sub_item.setFlags(sub_item.flags() ^ Qt.ItemIsEditable)
        self.table.setItem(row, 3, sub_item)
        
        # 5. 削除ボタン
        del_btn = QPushButton("×")
        del_btn.setStyleSheet("color: red; font-weight: bold;")
        del_btn.clicked.connect(lambda _, r=row: self.item_removed.emit(r))
        self.table.setCellWidget(row, 4, del_btn)

    def _update_row_items(self, row, item):
        """既存行のテキストだけ更新する内部関数"""
        subtotal = item['price'] * item['qty']
        
        # 各セルのテキストを書き換え
        if self.table.item(row, 0): self.table.item(row, 0).setText(str(item['name']))
        if self.table.item(row, 1): self.table.item(row, 1).setText(str(item['qty']))
        if self.table.item(row, 2): self.table.item(row, 2).setText(str(item['price']))
        if self.table.item(row, 3): self.table.item(row, 3).setText(f"¥{subtotal:,}")
        
        # 削除ボタンのlambdaの再接続が必要（行番号がずれる可能性があるため念の為）
        # ただし今回は行数不変なので、既存ボタンの接続はそのままでOK

    def _on_cell_changed(self, row, column):
        """ユーザーがセルを書き換えた時の処理"""
        if self.is_updating: return
        
        # 個数(1) または 単価(2) の変更のみ監視
        if column not in [1, 2]: return

        try:
            qty_item = self.table.item(row, 1)
            price_item = self.table.item(row, 2)
            
            qty = int(qty_item.text())
            price = int(price_item.text())
            
            # ロジック層へ通知
            self.item_changed.emit(row, qty, price)
        except ValueError:
            # 数値以外が入ったら無視（または元の値に戻す処理などを入れる）
            pass

    def update_message(self, text, type_):
        style = """
            padding: 10px; border-radius: 5px; font-size: 14px; font-weight: bold;
        """
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