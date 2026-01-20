from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView, 
                               QSplitter, QTextEdit)
from PySide6.QtCore import Qt

class TransactionTab(QWidget):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        
        # --- 左: リスト (元の構成に戻しました) ---
        left = QWidget()
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0,0,0,0)
        l_lay.addWidget(QLabel("伝票リスト"))
        
        self.table_tx = QTableWidget()
        # カラム: 元の6列構成
        columns = ["ID", "時間", "合計", "点数", "決済", "客層"]
        self.table_tx.setColumnCount(len(columns))
        self.table_tx.setHorizontalHeaderLabels(columns)
        self.table_tx.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_tx.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_tx.cellClicked.connect(self._on_tx_clicked)
        
        # ヘッダー幅の調整
        header = self.table_tx.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch) # 時間を伸ばす
        
        l_lay.addWidget(self.table_tx)
        splitter.addWidget(left)

        # --- 右: 詳細 (お釣り表示用に拡張) ---
        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0,0,0,0)
        r_lay.addWidget(QLabel("伝票詳細"))
        
        self.text_detail = QTextEdit()
        self.text_detail.setReadOnly(True)
        # 等幅フォントで見やすく
        self.text_detail.setStyleSheet("font-family: Consolas, monospace; line-height: 120%;")
        r_lay.addWidget(self.text_detail)
        
        splitter.addWidget(right)
        
        # 分割比率 (リスト:詳細 = 6:4)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)
        layout.addWidget(splitter)

    def update_data(self):
        tx_list = self.service.get_transaction_list()
        self.table_tx.setRowCount(len(tx_list))
        for i, tx in enumerate(tx_list):
            id_item = QTableWidgetItem(str(tx['id']))
            id_item.setData(Qt.UserRole, tx['id'])
            
            self.table_tx.setItem(i, 0, id_item)
            self.table_tx.setItem(i, 1, QTableWidgetItem(str(tx['time'])))
            self.table_tx.setItem(i, 2, QTableWidgetItem(f"¥{tx['total']:,}"))
            self.table_tx.setItem(i, 3, QTableWidgetItem(f"{tx['items']}点"))
            self.table_tx.setItem(i, 4, QTableWidgetItem(str(tx['payment'])))
            self.table_tx.setItem(i, 5, QTableWidgetItem(str(tx.get('customer', ''))))

    def _on_tx_clicked(self, row, col):
        """セルクリック時に詳細を表示 (こちらにはお釣り情報を表示)"""
        item = self.table_tx.item(row, 0)
        tx_id = item.data(Qt.UserRole)
        details = self.service.get_transaction_details(tx_id)
        
        # --- 詳細テキスト生成 ---
        txt = f"=== 伝票 #{details['id']} ===\n"
        txt += f"担当: {details.get('cashier', '不明')}\n"
        txt += f"日時: {details.get('time', '')}\n"
        txt += "="*32 + "\n"
        
        # 商品と割引を分離
        products = []
        discounts = []
        for item in details['items']:
            if item['price'] < 0:
                discounts.append(item)
            else:
                products.append(item)
                
        # 商品
        subtotal_prod = 0
        txt += "【購入商品】\n"
        for p in products:
            txt += f" {p['name']:<12} x{p['qty']:>2}  ¥{p['sub']:,}\n"
            subtotal_prod += p['sub']
        txt += f" >> 商品小計:      ¥{subtotal_prod:,}\n"
        txt += "-"*32 + "\n"
        
        # 割引
        if discounts:
            subtotal_disc = 0
            txt += "【適用割引】\n"
            for d in discounts:
                txt += f" {d['name']:<12} x{d['qty']:>2}  ¥{d['sub']:,}\n"
                subtotal_disc += d['sub']
            txt += f" >> 割引合計:      ¥{subtotal_disc:,}\n"
            txt += "-"*32 + "\n"
            
        # 支払情報 (ここにお釣り情報を追加)
        total = details['total']
        change = details.get('change', 0)
        paid = total + change # 預かり金額 = 売上 + お釣り
        
        txt += f"合計金額:        ¥{total:,}\n"
        txt += f"お預かり:        ¥{paid:,}\n"
        txt += f"お釣り  :        ¥{change:,}\n"
        txt += "="*32 + "\n"
        
        txt += "[決済内訳]\n"
        for pay in details['payments']:
            amount = pay['amount']
            method = pay['method']
            
            # 現金払いの場合、見た目を「預り金額」に戻して表示する
            if change > 0 and method == "現金":
                amount += change
                
            txt += f" {method}: ¥{amount:,}\n"
            
        self.text_detail.setText(txt)