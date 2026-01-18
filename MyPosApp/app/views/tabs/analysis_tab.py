from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTabWidget, 
                               QTableWidget, QTableWidgetItem)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

class AnalysisTab(QWidget):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # 案内ラベル
        layout.addWidget(QLabel("【詳細クロス集計】", font=QFont("Meiryo", 12, QFont.Bold)))

        # ネストしたタブを作成
        self.inner_tabs = QTabWidget()
        self.inner_tabs.setStyleSheet("QTabWidget::pane { border: none; } QTabBar::tab { background: #555; } QTabBar::tab:selected { background: #00897b; }")
        
        self.table_time_prod = QTableWidget()
        self.table_cust_prod = QTableWidget()
        self.table_time_cust = QTableWidget()
        self.table_cashier_sales = QTableWidget() # ★追加: レジ係ごとの売上
        
        self.inner_tabs.addTab(self.table_time_prod, "時間 × 商品")
        self.inner_tabs.addTab(self.table_cust_prod, "客層 × 商品")
        self.inner_tabs.addTab(self.table_time_cust, "時間 × 客層 (客数)")
        self.inner_tabs.addTab(self.table_cashier_sales, "担当 × 売上") # ★追加
        
        layout.addWidget(self.inner_tabs)

    def update_data(self):
        pivots = self.service.get_pivot_data()
        if pivots:
            self._fill_pivot_table(self.table_time_prod, pivots['time_prod'])
            self._fill_pivot_table(self.table_cust_prod, pivots['cust_prod'])
            self._fill_pivot_table(self.table_time_cust, pivots['time_cust'])
            self._fill_pivot_table(self.table_cashier_sales, pivots['cashier_sales'])

    def _fill_pivot_table(self, table_widget, df):
        if df.empty: return
        table_widget.setRowCount(len(df.index))
        table_widget.setColumnCount(len(df.columns))
        table_widget.setHorizontalHeaderLabels([str(c) for c in df.columns])
        table_widget.setVerticalHeaderLabels([str(i) for i in df.index])
        
        for r in range(len(df.index)):
            for c in range(len(df.columns)):
                val = df.iloc[r, c]
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if val == 0:
                    item.setForeground(QColor("#777"))
                table_widget.setItem(r, c, item)