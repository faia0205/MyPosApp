from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QPushButton, QMessageBox, QLabel, QWidget)
# from PySide6.QtCore import Qt
from app.services.master_data_service import MasterDataService
from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.services.customer_service import CustomerService
from app.services.payment_service import PaymentService
from app.services.expense_service import ExpenseService
from app.services.discount_service import DiscountService

# 各設定タブをインポート
from app.views.settings_tabs.product_setting_tab import ProductSettingTab
from app.views.settings_tabs.user_setting_tab import UserSettingTab
from app.views.settings_tabs.customer_setting_tab import CustomerSettingTab
from app.views.settings_tabs.payment_setting_tab import PaymentSettingTab
from app.views.settings_tabs.expense_setting_tab import ExpenseSettingTab
from app.views.settings_tabs.discount_setting_tab import DiscountSettingTab

from app.repositories.product_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository

class SettingsWindow(QDialog):
    """設定管理・マスタ編集ウィンドウ"""
    def __init__(self,
                 product_service: ProductService,
                 user_service: UserService,
                 customer_service: CustomerService,
                 payment_service: PaymentService,
                 expense_service: ExpenseService,
                 discount_service: DiscountService,
                 master_service: MasterDataService,
                 parent=None):
        super().__init__(parent)

        self.product_service = product_service
        self.user_service = user_service
        self.customer_service = customer_service
        self.payment_service = payment_service
        self.expense_service = expense_service
        self.discount_service = discount_service
        self.master_service = master_service

        self.setWindowTitle("システム設定・マスタ管理")
        self.resize(1000, 700)
        
        # 全体スタイル
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QTabWidget::pane { border: 1px solid #444; top: -1px; }
            QTabBar::tab { background: #333; color: #aaa; padding: 10px 20px; border: 1px solid #444; }
            QTabBar::tab:selected { background: #546e7a; color: white; font-weight: bold; border-bottom: 1px solid #546e7a; }
            QLabel { color: white; }
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- ヘッダー ---
        header = QHBoxLayout()
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("MASTER SETTINGS")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #90caf9;")
        lbl_desc = QLabel("設定はDBに即時保存されます。「JSON出力」でバックアップと初期化用ファイルを作成します。")
        lbl_desc.setStyleSheet("color: #ccc; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_desc)
        
        header.addLayout(title_box)
        header.addStretch()
        
        # アクションボタン
        btn_export = QPushButton("💾 設定を保存してJSON出力")
        btn_export.setFixedSize(220, 50)
        btn_export.setStyleSheet("""
            QPushButton { 
                background-color: #c62828; color: white; font-weight: bold; font-size: 14px; 
                border-radius: 5px; 
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        btn_export.clicked.connect(self._export_to_json)
        header.addWidget(btn_export)
        
        layout.addLayout(header)

        # --- タブエリア ---
        self.tabs = QTabWidget()
        
        # 1. 商品管理
        self.tab_product = ProductSettingTab(self.product_service)
        self.tabs.addTab(self.tab_product, "商品管理")

        # 2. ユーザー管理
        self.tab_user = UserSettingTab(self.user_service)
        self.tabs.addTab(self.tab_user, "ユーザー管理")
        
        # 3. 客層
        self.tab_cust = CustomerSettingTab(self.customer_service)
        self.tabs.addTab(self.tab_cust, "客層管理")
        
        # 4. 支払方法
        self.tab_pay = PaymentSettingTab(self.payment_service)
        self.tabs.addTab(self.tab_pay, "支払方法")
        
        # 5. 経費
        self.tab_exp = ExpenseSettingTab(self.expense_service)
        self.tabs.addTab(self.tab_exp, "経費履歴")

        # 6. 割引設定
        self.tab_disc = DiscountSettingTab(self.discount_service, self.product_service)
        self.tabs.addTab(self.tab_disc, "割引設定")

        layout.addWidget(self.tabs)

    def _export_to_json(self):
        """DBの内容をJSONに書き出す"""
        msg = "現在のデータベースの設定内容で `master_data.json` を上書きします。\n\nこれにより、次回「初期化」を行った際にもこの設定が復元されます。\n実行しますか？"
        if QMessageBox.question(self, "確認", msg) != QMessageBox.Yes:
            return

        if self.master_service.save_db_to_json():
            QMessageBox.information(self, "完了", "JSONファイルへの出力が完了しました。\nバックアップファイルも作成されました。")
        else:
            QMessageBox.critical(self, "エラー", "出力に失敗しました。ログを確認してください。")