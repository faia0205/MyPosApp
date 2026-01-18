from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QFileDialog, QMessageBox)
from PySide6.QtGui import QFont
from app.services.analytics_service import AnalyticsService

# 分割したタブをインポート
from app.views.tabs.dashboard_tab import DashboardTab
from app.views.tabs.analysis_tab import AnalysisTab
from app.views.tabs.transaction_tab import TransactionTab
from app.views.tabs.log_tab import LogTab

class AdminWindow(QDialog):
    """
    管理者・分析画面 (リファクタリング版)
    各タブの責務を別ファイルに委譲し、ここでは統合管理のみを行う。
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
        
        # タブのインスタンス化 (Serviceを渡す)
        self.tab_dashboard = DashboardTab(self.service)
        self.tab_analysis = AnalysisTab(self.service)
        self.tab_transactions = TransactionTab(self.service)
        self.tab_logs = LogTab(self.service)

        # タブに追加
        self.tabs.addTab(self.tab_dashboard, "ダッシュボード")
        self.tabs.addTab(self.tab_analysis, "詳細分析")
        self.tabs.addTab(self.tab_transactions, "伝票一覧")
        self.tabs.addTab(self.tab_logs, "操作ログ")

        layout.addWidget(self.tabs)

    def _load_data(self):
        """全タブのデータ更新メソッドを呼ぶ"""
        self.tab_dashboard.update_data()
        self.tab_analysis.update_data()
        self.tab_transactions.update_data()
        self.tab_logs.update_data()

    def _export_excel(self):
        default = self.service.get_default_filename()
        fname, _ = QFileDialog.getSaveFileName(self, "Excel出力", default, "Excel Files (*.xlsx)")
        if fname:
            if not fname.endswith('.xlsx'): fname += '.xlsx'
            ok, msg = self.service.export_to_excel(fname)
            if ok: QMessageBox.information(self, "完了", msg)
            else: QMessageBox.warning(self, "エラー", msg)