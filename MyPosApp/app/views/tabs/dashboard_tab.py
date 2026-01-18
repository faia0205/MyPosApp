from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

class DashboardTab(QWidget):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 上段: 財務カード
        cards = QHBoxLayout()
        self.lbl_sales = self._create_card("総売上", "#0288d1")
        self.lbl_profit = self._create_card("純利益", "#2e7d32")
        self.lbl_avg = self._create_card("客単価", "#f9a825")
        cards.addWidget(self.lbl_sales)
        cards.addWidget(self.lbl_profit)
        cards.addWidget(self.lbl_avg)
        layout.addLayout(cards)

        # 下段: 決済内訳 と 経費
        bottom = QHBoxLayout()
        
        # 左: 決済方法別
        left = QVBoxLayout()
        left.addWidget(QLabel("【決済方法別売上】"))
        self.table_payment = QTableWidget()
        self.table_payment.setColumnCount(2)
        self.table_payment.setHorizontalHeaderLabels(["方法", "金額"])
        self.table_payment.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left.addWidget(self.table_payment)
        bottom.addLayout(left)

        # 右: 経費一覧
        right = QVBoxLayout()
        right.addWidget(QLabel("【経費一覧】"))
        self.table_expenses = QTableWidget()
        self.table_expenses.setColumnCount(3)
        self.table_expenses.setHorizontalHeaderLabels(["日時", "用途", "金額"])
        self.table_expenses.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        right.addWidget(self.table_expenses)
        
        self.lbl_expenses = QLabel("合計: ¥0")
        self.lbl_expenses.setStyleSheet("font-size: 18px; color: #ef5350; font-weight: bold; margin-top: 5px;")
        self.lbl_expenses.setAlignment(Qt.AlignRight)
        right.addWidget(self.lbl_expenses)
        
        bottom.addLayout(right)
        layout.addLayout(bottom)

    def _create_card(self, title, color):
        lbl = QLabel(f"{title}\n¥0")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Meiryo", 14, QFont.Bold))
        lbl.setStyleSheet(f"background-color: {color}; border-radius: 8px; padding: 10px;")
        return lbl

    def update_data(self):
        """データの更新処理"""
        summary = self.service.get_dashboard_summary()
        self.lbl_sales.setText(f"総売上\n¥{summary['sales']:,}")
        self.lbl_profit.setText(f"純利益\n¥{summary['profit']:,}")
        self.lbl_avg.setText(f"客単価\n¥{summary['avg_spend']:,}")
        self.lbl_expenses.setText(f"経費計: ¥{summary['expenses']:,}")

        # 決済内訳
        pays = summary['payments']
        self.table_payment.setRowCount(len(pays))
        for i, (m, amt) in enumerate(pays.items()):
            self.table_payment.setItem(i, 0, QTableWidgetItem(m))
            self.table_payment.setItem(i, 1, QTableWidgetItem(f"¥{amt:,}"))

        # 経費リスト
        exp_list = self.service.get_expense_list()
        self.table_expenses.setRowCount(len(exp_list))
        for i, ex in enumerate(exp_list):
            self.table_expenses.setItem(i, 0, QTableWidgetItem(str(ex['time'])))
            self.table_expenses.setItem(i, 1, QTableWidgetItem(ex['title']))
            self.table_expenses.setItem(i, 2, QTableWidgetItem(f"¥{ex['amount']:,}"))