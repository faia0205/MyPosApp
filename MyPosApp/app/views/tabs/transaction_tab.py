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
        
        # 左: リスト
        left = QWidget()
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0,0,0,0)
        l_lay.addWidget(QLabel("伝票リスト"))
        
        self.table_tx = QTableWidget()
        self.table_tx.setColumnCount(6)
        self.table_tx.setHorizontalHeaderLabels(["ID", "時間", "合計", "点数", "決済", "客層"])
        self.table_tx.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_tx.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_tx.cellClicked.connect(self._on_tx_clicked)
        self.table_tx.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        l_lay.addWidget(self.table_tx)
        splitter.addWidget(left)

        # 右: 詳細
        right = QWidget()
        r_lay = QVBoxLayout(right)
        r_lay.setContentsMargins(0,0,0,0)
        r_lay.addWidget(QLabel("伝票詳細"))
        self.text_detail = QTextEdit()
        self.text_detail.setReadOnly(True)
        r_lay.addWidget(self.text_detail)
        splitter.addWidget(right)
        
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
        item = self.table_tx.item(row, 0)
        tx_id = item.data(Qt.UserRole)
        details = self.service.get_transaction_details(tx_id)
        
        txt = f"=== 伝票 #{details['id']} ===\n"
        txt += f"担当: {details.get('cashier', '不明')}\n"
        txt += f"日時: {details['time']}\n"
        txt += "="*30 + "\n"
        
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
            txt += f"{p['name']} x{p['qty']}  ¥{p['sub']:,}\n"
            subtotal_prod += p['sub']
        txt += f"  >> 商品小計: ¥{subtotal_prod:,}\n"
        txt += "-"*30 + "\n"
        
        # 割引
        if discounts:
            subtotal_disc = 0
            txt += "【適用割引】\n"
            for d in discounts:
                txt += f"{d['name']} x{d['qty']}  ¥{d['sub']:,}\n"
                subtotal_disc += d['sub']
            txt += f"  >> 割引合計: ¥{subtotal_disc:,}\n"
            txt += "-"*30 + "\n"
            
        txt += f"支払合計: ¥{details['total']:,}\n"
        txt += "-"*30 + "\n"
        txt += "[決済]\n"
        for pay in details['payments']:
            txt += f"  {pay['method']}: ¥{pay['amount']:,}\n"
            
        self.text_detail.setText(txt)