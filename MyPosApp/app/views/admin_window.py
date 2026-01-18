from typing import List, Dict, Any
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QTabWidget, QWidget, QSplitter, 
                               QTextEdit, QFileDialog, QMessageBox, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from app.services.analytics_service import AnalyticsService

class AdminWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理・分析ダッシュボード")
        self.resize(1100, 750)
        
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #444; color: #aaa; padding: 10px; }
            QTabBar::tab:selected { background: #0d47a1; color: white; font-weight: bold; }
            QTableWidget { background-color: #333; gridline-color: #555; color: white; }
            QHeaderView::section { background-color: #444; color: white; padding: 4px; border: 1px solid #555; }
            QLabel { color: white; }
            QTextEdit { background-color: #333; color: white; font-family: Consolas, monospace; border: 1px solid #555; }
            QSplitter::handle { background-color: #555; }
        """)

        self.service = AnalyticsService()
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ツールバー
        toolbar = QHBoxLayout()
        title = QLabel("売上分析レポート")
        title.setFont(QFont("Meiryo", 18, QFont.Bold))
        toolbar.addWidget(title)
        toolbar.addStretch()
        
        btn_refresh = QPushButton("再読み込み")
        btn_refresh.setFixedSize(120, 40)
        btn_refresh.setStyleSheet("background-color: #00695c; color: white; font-weight: bold; border-radius: 4px;")
        btn_refresh.clicked.connect(self._load_data)
        toolbar.addWidget(btn_refresh)

        btn_export = QPushButton("Excel出力")
        btn_export.setFixedSize(120, 40)
        btn_export.setStyleSheet("background-color: #1b5e20; color: white; font-weight: bold; border-radius: 4px;")
        btn_export.clicked.connect(self._export_excel)
        toolbar.addWidget(btn_export)
        layout.addLayout(toolbar)

        # メインタブ
        self.tabs = QTabWidget()
        
        self.tab_dashboard = QWidget()
        self._init_tab_dashboard()
        self.tabs.addTab(self.tab_dashboard, "ダッシュボード")

        self.tab_analysis = QWidget()
        self._init_tab_analysis()
        self.tabs.addTab(self.tab_analysis, "詳細分析(クロス集計)")

        self.tab_transactions = QWidget()
        self._init_tab_transactions()
        self.tabs.addTab(self.tab_transactions, "伝票一覧")

        self.tab_logs = QWidget()
        self._init_tab_logs()
        self.tabs.addTab(self.tab_logs, "操作ログ")

        layout.addWidget(self.tabs)

    # --- 1. ダッシュボード ---
    def _init_tab_dashboard(self):
        layout = QVBoxLayout(self.tab_dashboard)
        
        # カード
        cards = QHBoxLayout()
        self.lbl_sales = self._create_card("総売上", "#0288d1")
        self.lbl_profit = self._create_card("純利益", "#2e7d32")
        self.lbl_avg = self._create_card("客単価", "#f9a825")
        cards.addWidget(self.lbl_sales)
        cards.addWidget(self.lbl_profit)
        cards.addWidget(self.lbl_avg)
        layout.addLayout(cards)

        bottom = QHBoxLayout()
        
        # 左: 決済内訳
        left = QVBoxLayout()
        left.addWidget(QLabel("【決済方法別】"))
        self.table_payment = QTableWidget()
        self.table_payment.setColumnCount(2)
        self.table_payment.setHorizontalHeaderLabels(["方法", "金額"])
        self.table_payment.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left.addWidget(self.table_payment)
        bottom.addLayout(left)

        # ★修正: 右側を経費リストに変更
        right = QVBoxLayout()
        right.addWidget(QLabel("【経費一覧】"))
        
        self.table_expenses = QTableWidget()
        self.table_expenses.setColumnCount(3)
        self.table_expenses.setHorizontalHeaderLabels(["日時", "用途", "金額"])
        self.table_expenses.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        right.addWidget(self.table_expenses)
        
        # 合計表示も下に残す
        self.lbl_expenses = QLabel("合計: ¥0")
        self.lbl_expenses.setStyleSheet("font-size: 18px; color: #ef5350; font-weight: bold; margin-top: 5px;")
        self.lbl_expenses.setAlignment(Qt.AlignRight)
        right.addWidget(self.lbl_expenses)
        
        bottom.addLayout(right)
        layout.addLayout(bottom)

    # --- 2. 詳細分析 (ネストタブ実装) ---
    def _init_tab_analysis(self):
        layout = QVBoxLayout(self.tab_analysis)
        
        # ネストしたタブを作成
        self.inner_tabs = QTabWidget()
        self.inner_tabs.setStyleSheet("QTabWidget::pane { border: none; } QTabBar::tab { background: #555; } QTabBar::tab:selected { background: #00897b; }")
        
        # 3つのテーブルを用意
        self.table_time_prod = QTableWidget()
        self.table_cust_prod = QTableWidget()
        self.table_time_cust = QTableWidget()
        
        self.inner_tabs.addTab(self.table_time_prod, "時間 × 商品")
        self.inner_tabs.addTab(self.table_cust_prod, "客層 × 商品")
        self.inner_tabs.addTab(self.table_time_cust, "時間 × 客層(客数)")
        
        layout.addWidget(self.inner_tabs)

    # --- 3. 伝票一覧 ---
    def _init_tab_transactions(self):
        layout = QHBoxLayout(self.tab_transactions)
        splitter = QSplitter(Qt.Horizontal)
        
        left = QWidget()
        l_lay = QVBoxLayout(left)
        l_lay.setContentsMargins(0,0,0,0)
        l_lay.addWidget(QLabel("伝票リスト"))
        
        self.table_tx = QTableWidget()
        self.table_tx.setColumnCount(6) # +客層
        self.table_tx.setHorizontalHeaderLabels(["ID", "時間", "合計", "点数", "決済", "客層"])
        self.table_tx.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_tx.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_tx.cellClicked.connect(self._on_tx_clicked)
        self.table_tx.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        l_lay.addWidget(self.table_tx)
        splitter.addWidget(left)

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

    # --- 4. ログ ---
    def _init_tab_logs(self):
        layout = QVBoxLayout(self.tab_logs)
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(3)
        self.table_logs.setHorizontalHeaderLabels(["日時", "レベル", "内容"])
        h = self.table_logs.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table_logs)

    # --- データ読み込み ---
    def _load_data(self):
        # 1. ダッシュボード
        summary = self.service.get_dashboard_summary()
        self.lbl_sales.setText(f"総売上\n¥{summary['sales']:,}")
        self.lbl_profit.setText(f"純利益\n¥{summary['profit']:,}")
        self.lbl_avg.setText(f"客単価\n¥{summary['avg_spend']:,}")
        self.lbl_expenses.setText(f"¥{summary['expenses']:,}")

        pays = summary['payments']
        self.table_payment.setRowCount(len(pays))
        for i, (m, amt) in enumerate(pays.items()):
            self.table_payment.setItem(i, 0, QTableWidgetItem(m))
            self.table_payment.setItem(i, 1, QTableWidgetItem(f"¥{amt:,}"))

        # 2. 詳細分析 (Pivot表示)
        pivots = self.service.get_pivot_data()
        if pivots:
            self._fill_pivot_table(self.table_time_prod, pivots['time_prod'])
            self._fill_pivot_table(self.table_cust_prod, pivots['cust_prod'])
            self._fill_pivot_table(self.table_time_cust, pivots['time_cust'])

        # 3. 伝票一覧
        tx_list = self.service.get_transaction_list()
        self.table_tx.setRowCount(len(tx_list))
        for i, tx in enumerate(tx_list):
            id_item = QTableWidgetItem(str(tx['id']))
            id_item.setData(Qt.UserRole, tx['id'])
            self.table_tx.setItem(i, 0, id_item)
            self.table_tx.setItem(i, 1, QTableWidgetItem(str(tx['time']))) # JST
            self.table_tx.setItem(i, 2, QTableWidgetItem(f"¥{tx['total']:,}"))
            self.table_tx.setItem(i, 3, QTableWidgetItem(f"{tx['items']}点"))
            self.table_tx.setItem(i, 4, QTableWidgetItem(str(tx['payment'])))
            self.table_tx.setItem(i, 5, QTableWidgetItem(str(tx.get('customer', ''))))

        # 4. ログ
        logs = self.service.get_logs()
        self.table_logs.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.table_logs.setItem(i, 0, QTableWidgetItem(str(log['time']))) # JST
            lvl = QTableWidgetItem(log['level'])
            if log['level']=='error': lvl.setForeground(QColor("#ff5252"))
            self.table_logs.setItem(i, 1, lvl)
            self.table_logs.setItem(i, 2, QTableWidgetItem(log['msg']))
        
        # 経費リストのロード
        exp_list = self.service.get_expense_list()
        self.table_expenses.setRowCount(len(exp_list))
        for i, ex in enumerate(exp_list):
            self.table_expenses.setItem(i, 0, QTableWidgetItem(str(ex['time'])))
            self.table_expenses.setItem(i, 1, QTableWidgetItem(ex['title']))
            self.table_expenses.setItem(i, 2, QTableWidgetItem(f"¥{ex['amount']:,}"))

    def _fill_pivot_table(self, table_widget, df):
        """DataFrameをQTableWidgetに流し込むヘルパー"""
        if df.empty: return
        
        # ヘッダー設定
        table_widget.setRowCount(len(df.index))
        table_widget.setColumnCount(len(df.columns))
        table_widget.setHorizontalHeaderLabels([str(c) for c in df.columns])
        table_widget.setVerticalHeaderLabels([str(i) for i in df.index])
        
        for r in range(len(df.index)):
            for c in range(len(df.columns)):
                # ilocで位置指定アクセス
                val = df.iloc[r, c]
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if val == 0:
                    item.setForeground(QColor("#777")) # 0は薄く
                table_widget.setItem(r, c, item)

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
                
        # 商品ゾーン
        subtotal_prod = 0
        txt += "【購入商品】\n"
        for p in products:
            txt += f"{p['name']} x{p['qty']}  ¥{p['sub']:,}\n"
            subtotal_prod += p['sub']
        txt += f"  >> 商品小計: ¥{subtotal_prod:,}\n"
        txt += "-"*30 + "\n"
        
        # 割引ゾーン
        if discounts:
            subtotal_disc = 0
            txt += "【適用割引】\n"
            for d in discounts:
                txt += f"{d['name']} x{d['qty']}  ¥{d['sub']:,}\n"
                subtotal_disc += d['sub']
            txt += f"  >> 割引合計: ¥{subtotal_disc:,}\n"
            txt += "-"*30 + "\n"
            
        txt += f"支払合計: ¥{details['total']:,}\n"
        txt += "[決済]\n"
        for pay in details['payments']:
            txt += f"  {pay['method']}: ¥{pay['amount']:,}\n"
        self.text_detail.setText(txt)

    def _create_card(self, title, color):
        lbl = QLabel(f"{title}\n¥0")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Meiryo", 14, QFont.Bold))
        lbl.setStyleSheet(f"background-color: {color}; border-radius: 8px; padding: 10px;")
        return lbl

    def _export_excel(self):
        default = self.service.get_default_filename()
        fname, _ = QFileDialog.getSaveFileName(self, "Excel出力", default, "Excel Files (*.xlsx)")
        if fname:
            if not fname.endswith('.xlsx'): fname += '.xlsx'
            ok, msg = self.service.export_to_excel(fname)
            if ok: QMessageBox.information(self, "完了", msg)
            else: QMessageBox.warning(self, "エラー", msg)