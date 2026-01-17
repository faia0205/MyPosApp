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
    - ダッシュボード（売上・経費・客単価・決済内訳）
    - 詳細分析（クロス集計の説明）
    - 伝票管理（一覧・詳細）
    - 操作ログ
    - Excelエクスポート
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("管理・分析ダッシュボード")
        self.resize(1100, 750)
        
        # ダークテーマ適用
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
        
        # タブ1: ダッシュボード
        self.tab_dashboard = QWidget()
        self._init_tab_dashboard()
        self.tabs.addTab(self.tab_dashboard, "ダッシュボード")

        # タブ2: 詳細分析 (案内)
        self.tab_analysis = QWidget()
        self._init_tab_analysis()
        self.tabs.addTab(self.tab_analysis, "詳細分析")

        # タブ3: 伝票一覧 (既存機能)
        self.tab_transactions = QWidget()
        self._init_tab_transactions()
        self.tabs.addTab(self.tab_transactions, "伝票一覧")

        # タブ4: 操作ログ
        self.tab_logs = QWidget()
        self._init_tab_logs()
        self.tabs.addTab(self.tab_logs, "操作ログ")

        layout.addWidget(self.tabs)

    # ----------------------------------------------------------------
    # タブ1: ダッシュボード初期化
    # ----------------------------------------------------------------
    def _init_tab_dashboard(self):
        layout = QVBoxLayout(self.tab_dashboard)
        
        # 上段: 財務カード (売上、利益、客単価)
        cards_layout = QHBoxLayout()
        self.lbl_sales = self._create_card("総売上", "#0288d1")
        self.lbl_profit = self._create_card("純利益", "#2e7d32")
        self.lbl_avg = self._create_card("客単価", "#f9a825")
        
        cards_layout.addWidget(self.lbl_sales)
        cards_layout.addWidget(self.lbl_profit)
        cards_layout.addWidget(self.lbl_avg)
        layout.addLayout(cards_layout)

        # 下段: 決済内訳 と 経費
        bottom_layout = QHBoxLayout()
        
        # 左: 決済方法別テーブル
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("【決済方法別売上】"))
        self.table_payment = QTableWidget()
        self.table_payment.setColumnCount(2)
        self.table_payment.setHorizontalHeaderLabels(["方法", "金額"])
        self.table_payment.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left_box.addWidget(self.table_payment)
        bottom_layout.addLayout(left_box)

        # 右: 経費合計表示
        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("【経費合計】"))
        self.lbl_expenses = QLabel("¥0")
        self.lbl_expenses.setStyleSheet("font-size: 36px; color: #ef5350; font-weight: bold;")
        self.lbl_expenses.setAlignment(Qt.AlignCenter)
        right_box.addWidget(self.lbl_expenses)
        right_box.addStretch()
        bottom_layout.addLayout(right_box)

        layout.addLayout(bottom_layout)

    def _create_card(self, title, color_code):
        lbl = QLabel(f"{title}\n¥0")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Meiryo", 14, QFont.Bold))
        lbl.setStyleSheet(f"background-color: {color_code}; border-radius: 8px; padding: 10px;")
        return lbl

    # ----------------------------------------------------------------
    # タブ2: 詳細分析初期化
    # ----------------------------------------------------------------
    def _init_tab_analysis(self):
        layout = QVBoxLayout(self.tab_analysis)
        layout.addWidget(QLabel("【詳細クロス集計】", font=QFont("Meiryo", 14, QFont.Bold)))
        
        info_text = (
            "画面上での複雑な分析機能は現在準備中です。\n"
            "右上の「Excel出力」ボタンを押すと、以下の高度な分析シートが自動作成されます。\n\n"
            "📊 出力される分析シート:\n"
            "  1. 時間帯 × 商品 (どの時間に何が売れたか)\n"
            "  2. 客層 × 商品 (誰が何を買ったか)\n"
            "  3. 時間帯 × 客層 (いつ誰が来たか)\n"
        )
        info_label = QLabel(info_text)
        info_label.setStyleSheet("font-size: 16px; line-height: 1.5; padding: 20px; background-color: #333; border: 1px solid #555; border-radius: 5px;")
        info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        layout.addWidget(info_label)
        layout.addStretch()

    # ----------------------------------------------------------------
    # タブ3: 伝票一覧初期化 (★ここは消さずに残します)
    # ----------------------------------------------------------------
    def _init_tab_transactions(self):
        layout = QHBoxLayout(self.tab_transactions)
        
        splitter = QSplitter(Qt.Horizontal)
        
        # 左: 一覧リスト
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.addWidget(QLabel("伝票リスト (クリックで詳細)"))
        
        self.table_tx = QTableWidget()
        self.table_tx.setColumnCount(5)
        self.table_tx.setHorizontalHeaderLabels(["ID", "時間", "合計", "点数", "決済"])
        self.table_tx.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_tx.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_tx.cellClicked.connect(self._on_tx_clicked)
        
        h = self.table_tx.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        
        left_layout.addWidget(self.table_tx)
        splitter.addWidget(left_widget)

        # 右: 詳細レシート
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.addWidget(QLabel("伝票詳細"))
        
        self.text_detail = QTextEdit()
        self.text_detail.setReadOnly(True)
        self.text_detail.setPlaceholderText("左のリストから伝票を選択してください")
        
        right_layout.addWidget(self.text_detail)
        splitter.addWidget(right_widget)
        
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter)

    # ----------------------------------------------------------------
    # タブ4: 操作ログ初期化
    # ----------------------------------------------------------------
    def _init_tab_logs(self):
        layout = QVBoxLayout(self.tab_logs)
        layout.addWidget(QLabel("システム操作ログ"))
        
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(3)
        self.table_logs.setHorizontalHeaderLabels(["日時", "レベル", "内容"])
        h = self.table_logs.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents) # 日時
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents) # レベル
        h.setSectionResizeMode(2, QHeaderView.Stretch)          # 内容
        
        layout.addWidget(self.table_logs)

    # ----------------------------------------------------------------
    # データ読み込み処理
    # ----------------------------------------------------------------
    def _load_data(self):
        """全データをサービスから取得して表示更新"""
        
        # 1. ダッシュボード情報の更新
        summary = self.service.get_dashboard_summary()
        self.lbl_sales.setText(f"総売上\n¥{summary['sales']:,}")
        self.lbl_profit.setText(f"純利益\n¥{summary['profit']:,}")
        self.lbl_avg.setText(f"客単価\n¥{summary['avg_spend']:,}")
        self.lbl_expenses.setText(f"¥{summary['expenses']:,}")

        # 決済内訳テーブル
        pays = summary['payments']
        self.table_payment.setRowCount(len(pays))
        for i, (method, amount) in enumerate(pays.items()):
            self.table_payment.setItem(i, 0, QTableWidgetItem(method))
            self.table_payment.setItem(i, 1, QTableWidgetItem(f"¥{amount:,}"))

        # 2. 伝票一覧の更新
        tx_list = self.service.get_transaction_list()
        self.table_tx.setRowCount(len(tx_list))
        for i, tx in enumerate(tx_list):
            id_item = QTableWidgetItem(str(tx['id']))
            id_item.setData(Qt.UserRole, tx['id']) # IDを隠しデータとして保持
            
            self.table_tx.setItem(i, 0, id_item)
            self.table_tx.setItem(i, 1, QTableWidgetItem(str(tx['time'])))
            self.table_tx.setItem(i, 2, QTableWidgetItem(f"¥{tx['total']:,}"))
            self.table_tx.setItem(i, 3, QTableWidgetItem(f"{tx['items']}点"))
            self.table_tx.setItem(i, 4, QTableWidgetItem(str(tx['payment'])))

        # 3. ログの更新
        logs = self.service.get_logs()
        self.table_logs.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.table_logs.setItem(i, 0, QTableWidgetItem(str(log['time'])))
            
            # レベルごとに色分け
            level_item = QTableWidgetItem(log['level'])
            if log['level'] == 'warning':
                level_item.setForeground(QColor("#ff9800"))
            elif log['level'] == 'error':
                level_item.setForeground(QColor("#f44336"))
            else:
                level_item.setForeground(QColor("#4caf50"))
            
            self.table_logs.setItem(i, 1, level_item)
            self.table_logs.setItem(i, 2, QTableWidgetItem(log['msg']))

    # ----------------------------------------------------------------
    # イベントハンドラ
    # ----------------------------------------------------------------
    def _on_tx_clicked(self, row, col):
        """伝票一覧がクリックされたら詳細を表示"""
        item = self.table_tx.item(row, 0)
        tx_id = item.data(Qt.UserRole)
        
        details = self.service.get_transaction_details(tx_id)
        
        # レシート風テキスト生成
        txt = f"=== 伝票 #{details['id']} ===\n"
        txt += f"日時: {details['time']}\n"
        txt += "-"*35 + "\n"
        
        for p in details['items']:
            txt += f"{p['name']} x{p['qty']}\n"
            txt += f"    @¥{p['price']:,} = ¥{p['sub']:,}\n"
            
        txt += "-"*35 + "\n"
        txt += f"合計: ¥{details['total']:,}\n"
        txt += "-"*35 + "\n"
        txt += "[決済]\n"
        for pay in details['payments']:
            txt += f"  {pay['method']}: ¥{pay['amount']:,}\n"
            
        self.text_detail.setText(txt)

    def _export_excel(self):
        """Excel出力処理"""
        default_name = self.service.get_default_filename()
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Excel出力", default_name, "Excel Files (*.xlsx)"
        )
        
        if file_name:
            if not file_name.endswith('.xlsx'):
                file_name += '.xlsx'
                
            success, msg = self.service.export_to_excel(file_name)
            if success:
                QMessageBox.information(self, "完了", msg)
            else:
                QMessageBox.warning(self, "エラー", f"出力失敗: {msg}")