from typing import List, Dict, Any
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QTabWidget, QWidget, QSplitter, 
                               QTextEdit, QFileDialog, QMessageBox, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from app.services.analytics_service import AnalyticsService

class AdminWindow(QDialog):
    """
    管理者・分析画面
    - ダッシュボード（売上・時間帯）
    - 伝票管理（一覧・詳細）
    - 商品分析（ランキング）
    - Excelエクスポート
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理・分析ダッシュボード")
        self.resize(1000, 700)
        
        # ダークテーマ適用
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #444; color: #aaa; padding: 10px; }
            QTabBar::tab:selected { background: #0d47a1; color: white; font-weight: bold; }
            QTableWidget { background-color: #333; gridline-color: #555; color: white; }
            QHeaderView::section { background-color: #444; color: white; padding: 4px; border: 1px solid #555; }
            QLabel { color: white; }
            QTextEdit { background-color: #333; color: white; font-family: Consolas, monospace; }
        """)

        self.service = AnalyticsService()
        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- 上部ツールバー ---
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

        # --- メインタブ ---
        self.tabs = QTabWidget()
        
        # タブ1: ダッシュボード (財務 + 時間帯)
        self.tab_dashboard = QWidget()
        self._init_tab_dashboard()
        self.tabs.addTab(self.tab_dashboard, "ダッシュボード")

        # タブ2: 伝票一覧 (簡易表示 + 詳細表示)
        self.tab_transactions = QWidget()
        self._init_tab_transactions()
        self.tabs.addTab(self.tab_transactions, "伝票一覧")

        # タブ3: 商品分析
        self.tab_products = QWidget()
        self._init_tab_products()
        self.tabs.addTab(self.tab_products, "商品分析")

        layout.addWidget(self.tabs)

    # ----------------------------------------------------------------
    # タブ1: ダッシュボード初期化
    # ----------------------------------------------------------------
    def _init_tab_dashboard(self):
        layout = QVBoxLayout(self.tab_dashboard)
        
        # 1. 財務カード (売上・経費・利益)
        cards_layout = QHBoxLayout()
        self.lbl_sales = self._create_card("総売上", "#0288d1")
        self.lbl_expenses = self._create_card("経費計", "#c62828")
        self.lbl_profit = self._create_card("純利益", "#2e7d32")
        
        cards_layout.addWidget(self.lbl_sales)
        cards_layout.addWidget(self.lbl_expenses)
        cards_layout.addWidget(self.lbl_profit)
        layout.addLayout(cards_layout)

        layout.addWidget(QLabel("【時間帯別データ】"))

        # 2. 時間帯別テーブル
        self.table_hourly = QTableWidget()
        self.table_hourly.setColumnCount(3)
        self.table_hourly.setHorizontalHeaderLabels(["時間", "客数", "売上"])
        header = self.table_hourly.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table_hourly)

    def _create_card(self, title, color_code):
        """カード風ラベルを作成するヘルパー"""
        lbl = QLabel(f"{title}\n¥0")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Meiryo", 14, QFont.Bold))
        lbl.setStyleSheet(f"background-color: {color_code}; border-radius: 8px; padding: 10px;")
        return lbl

    # ----------------------------------------------------------------
    # タブ2: 伝票一覧初期化
    # ----------------------------------------------------------------
    def _init_tab_transactions(self):
        layout = QHBoxLayout(self.tab_transactions)
        
        # スプリッター (左右分割)
        splitter = QSplitter(Qt.Horizontal)
        
        # 左: 一覧テーブル
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.addWidget(QLabel("伝票リスト (クリックで詳細)"))
        
        self.table_tx = QTableWidget()
        self.table_tx.setColumnCount(5)
        self.table_tx.setHorizontalHeaderLabels(["ID", "時間", "合計", "点数", "決済"])
        self.table_tx.setSelectionBehavior(QTableWidget.SelectRows) # 行選択
        self.table_tx.setEditTriggers(QTableWidget.NoEditTriggers) # 編集不可
        self.table_tx.cellClicked.connect(self._on_tx_clicked) # クリックイベント
        
        h = self.table_tx.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        
        left_layout.addWidget(self.table_tx)
        splitter.addWidget(left_widget)

        # 右: 詳細表示エリア (レシート風)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.addWidget(QLabel("伝票詳細"))
        
        self.text_detail = QTextEdit()
        self.text_detail.setReadOnly(True)
        self.text_detail.setPlaceholderText("左のリストから伝票を選択してください")
        
        right_layout.addWidget(self.text_detail)
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 6) # 左6割
        splitter.setStretchFactor(1, 4) # 右4割

        layout.addWidget(splitter)

    # ----------------------------------------------------------------
    # タブ3: 商品分析初期化
    # ----------------------------------------------------------------
    def _init_tab_products(self):
        layout = QVBoxLayout(self.tab_products)
        layout.addWidget(QLabel("【商品別売上ランキング】"))
        
        self.table_prod = QTableWidget()
        self.table_prod.setColumnCount(3)
        self.table_prod.setHorizontalHeaderLabels(["商品名", "販売数", "売上合計"])
        h = self.table_prod.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.table_prod)

    # ----------------------------------------------------------------
    # データ読み込み処理
    # ----------------------------------------------------------------
    def _load_data(self):
        """全データをリロードして表示更新"""
        # 1. 財務サマリー
        sales, exp, profit = self.service.get_financial_summary()
        self.lbl_sales.setText(f"総売上\n¥{sales:,}")
        self.lbl_expenses.setText(f"経費計\n¥{exp:,}")
        self.lbl_profit.setText(f"純利益\n¥{profit:,}")

        # 2. 時間帯データ
        hourly = self.service.get_hourly_sales()
        self.table_hourly.setRowCount(len(hourly))
        for i, row in enumerate(hourly):
            self.table_hourly.setItem(i, 0, QTableWidgetItem(f"{row['hour']}時"))
            self.table_hourly.setItem(i, 1, QTableWidgetItem(f"{row['count']}人"))
            self.table_hourly.setItem(i, 2, QTableWidgetItem(f"¥{row['sales']:,}"))

        # 3. 伝票一覧
        tx_list = self.service.get_transaction_list()
        self.table_tx.setRowCount(len(tx_list))
        for i, tx in enumerate(tx_list):
            # IDを隠しデータとして持たせる
            id_item = QTableWidgetItem(str(tx['id']))
            id_item.setData(Qt.UserRole, tx['id']) # IDを保存
            
            self.table_tx.setItem(i, 0, id_item)
            self.table_tx.setItem(i, 1, QTableWidgetItem(str(tx['time'])))
            self.table_tx.setItem(i, 2, QTableWidgetItem(f"¥{tx['total']:,}"))
            self.table_tx.setItem(i, 3, QTableWidgetItem(f"{tx['items']}点"))
            self.table_tx.setItem(i, 4, QTableWidgetItem(str(tx['payment'])))

        # 4. 商品ランキング
        prods = self.service.get_product_sales()
        self.table_prod.setRowCount(len(prods))
        for i, p in enumerate(prods):
            self.table_prod.setItem(i, 0, QTableWidgetItem(p['name']))
            self.table_prod.setItem(i, 1, QTableWidgetItem(f"{p['qty']}個"))
            self.table_prod.setItem(i, 2, QTableWidgetItem(f"¥{p['total']:,}"))

    def _on_tx_clicked(self, row, col):
        """伝票行クリック時の詳細表示"""
        item = self.table_tx.item(row, 0)
        tx_id = item.data(Qt.UserRole)
        
        details = self.service.get_transaction_details(tx_id)
        
        # レシート風のテキストを作成
        txt = f"=== 伝票 #{details['id']} ===\n"
        txt += f"日時: {details['time']}\n"
        txt += "-"*30 + "\n"
        
        for p in details['items']:
            txt += f"{p['name']} x{p['qty']}\n"
            txt += f"    @¥{p['price']:,} = ¥{p['sub']:,}\n"
            
        txt += "-"*30 + "\n"
        txt += f"合計: ¥{details['total']:,}\n"
        txt += "-"*30 + "\n"
        txt += "[決済方法]\n"
        for pay in details['payments']:
            txt += f"  {pay['method']}: ¥{pay['amount']:,}\n"
            
        self.text_detail.setText(txt)

    def _export_excel(self):
        """Excel出力"""
        file_name, _ = QFileDialog.getSaveFileName(self, "Excel出力", "", "Excel Files (*.xlsx)")
        if file_name:
            if not file_name.endswith('.xlsx'):
                file_name += '.xlsx'
                
            success, msg = self.service.export_to_excel(file_name)
            if success:
                QMessageBox.information(self, "完了", msg)
            else:
                QMessageBox.warning(self, "エラー", f"出力失敗: {msg}")