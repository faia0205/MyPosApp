from typing import Dict
import logging
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QFrame, QLabel, QPushButton, QMessageBox,
                               QDialog, QLineEdit, QSpinBox, QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.config import DB_PATH

logger = logging.getLogger('MyPosApp')

# Repositories
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.discount_repo import DiscountRepository
from app.repositories.user_repo import UserRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.log_repo import LogRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.interfaces.master_data_repo import IMasterDataRepository

# Service/Logic
from app.services.user_service import UserService
from app.services.payment_service import PaymentService
from app.services.expense_service import ExpenseService
from app.services.discount_service import DiscountService
from app.services.master_data_service import MasterDataService
from app.services.cart_service import CartService
from app.services.checkout_service import CheckoutService
from app.services.product_service import ProductService
from app.services.customer_service import CustomerService
from app.services.analytics_service import AnalyticsService
from app.services.excel_exporter import ExcelReportExporter
from app.logic.discount_manager import DiscountManager

# Strategies
from app.logic.strategies.item_strategy import ItemDiscountStrategy
from app.logic.strategies.category_strategy import CategoryDiscountStrategy
from app.logic.strategies.bundle_strategy import BundleDiscountStrategy
from app.logic.strategies.cart_strategy import CartDiscountStrategy

# Views
from app.views.components.cart_widget import CartWidget
from app.views.components.product_list_widget import ProductListWidget
from app.views.components.customer_panel import CustomerPanel
from app.views.dialogs.payment_dialog import PaymentDialog
from app.views.admin_window import AdminWindow
from app.views.dialogs.login_dialog import LoginDialog
from app.views.dialogs.transaction_cancel_dialog import TransactionCancelDialog
from app.views.settings_window import SettingsWindow
from app.utils.style import StyleGenerator
from app.utils.database import SQLiteProvider

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Modular POS System")
        self.resize(1280, 800)
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; } QWidget { color: #ffffff; }")

        # --- 依存関係の構築 (Composition Root) ---
        self.db_provider = SQLiteProvider(DB_PATH)
        # 1. Repositories (データアクセス層)
        self.trans_repo = TransactionRepository(self.db_provider)
        self.prod_repo = ProductRepository(self.db_provider)
        self.payment_repo = PaymentRepository(self.db_provider)
        self.disc_repo = DiscountRepository(self.db_provider)
        self.user_repo = UserRepository(self.db_provider)
        self.expense_repo = ExpenseRepository(self.db_provider)
        self.log_repo = LogRepository(self.db_provider)
        self.cust_repo = CustomerRepository(self.db_provider)
        self.ana_repo = AnalyticsRepository(self.db_provider)

        # 2. Strategies (割引ロジックの部品)
        strategies = {
            'item': ItemDiscountStrategy(),
            'category': CategoryDiscountStrategy(),
            'bundle': BundleDiscountStrategy(),
            'cart': CartDiscountStrategy()
        }
        
        # 3. Manager (ロジック統括)
        # Strategyを注入してManagerを生成
        self.discount_manager = DiscountManager(strategies)

        # 4. Services (アプリケーション層)
        # CheckoutServiceにRepoを注入
        self.checkout_service = CheckoutService(self.trans_repo, self.log_repo)
        self.excel_exporter = ExcelReportExporter()
        # UI用のデータ提供サービスを作成
        self.product_service = ProductService(self.prod_repo, self.log_repo)
        self.customer_service = CustomerService(self.cust_repo, self.log_repo)
        self.payment_service = PaymentService(self.payment_repo, self.log_repo)
        self.expense_service = ExpenseService(self.expense_repo, self.log_repo)
        self.discount_service = DiscountService(self.disc_repo, self.log_repo)
        self.user_service = UserService(self.user_repo, self.log_repo)
        
        master_repos: list[IMasterDataRepository] = [
            self.prod_repo,
            self.user_repo,
            self.cust_repo,
            self.payment_repo,
            self.expense_repo,
            self.disc_repo
        ]

        self.master_data_service = MasterDataService(
            repositories=master_repos
        )

        self.master_data_service.sync_json_to_db()

        # AnalyticsServiceにRepoを注入
        self.analytics_service = AnalyticsService(
            ana_repo=self.ana_repo,
            trans_repo=self.trans_repo,
            expense_repo=self.expense_repo,
            log_repo=self.log_repo,
            prod_repo=self.prod_repo,
            exporter=self.excel_exporter
        )

        # CartServiceに全ての依存関係を注入 (DI)
        self.cart_service = CartService(
            prod_repo=self.prod_repo,
            disc_repo=self.disc_repo,
            discount_manager=self.discount_manager,
            checkout_service=self.checkout_service,
            user_repo=self.user_repo,
            expense_repo=self.expense_repo,
            payment_repo=self.payment_repo,
            log_repo=self.log_repo,
            trans_repo=self.trans_repo
        )

        # UI初期化
        self._init_ui()
        self._connect_signals()
        
        # 初期表示（ログイン）
        self._show_login_dialog()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- ヘッダー ---
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background-color: #333; color: white; border-radius: 5px; padding: 5px;")
        header_layout = QHBoxLayout(self.header_frame)
        
        self.lbl_stats: Dict[str, QLabel] = {}
        for key in ["総売上", "経費計", "現在利益", "黒字まで"]:
            lbl = QLabel(f"{key}: ---")
            lbl.setFont(QFont("Meiryo", 12, QFont.Bold))
            lbl.setStyleSheet("border: none; color: white;")
            header_layout.addWidget(lbl)
            self.lbl_stats[key] = lbl
        
        header_layout.addStretch()

        self.btn_cashier = QPushButton("担当: ---")
        self.btn_cashier.setFont(QFont("Meiryo", 10, QFont.Bold))
        self.btn_cashier.setStyleSheet("QPushButton { color: #bbb; background-color: transparent; border: 1px solid #555; border-radius: 4px; padding: 5px 10px; } QPushButton:hover { background-color: #444; color: white; }")
        self.btn_cashier.setCursor(Qt.PointingHandCursor)
        self.btn_cashier.setFocusPolicy(Qt.NoFocus)
        self.btn_cashier.clicked.connect(self._show_login_dialog)
        header_layout.addWidget(self.btn_cashier)

        btn_admin = QPushButton("管理・分析")
        btn_admin.setFixedSize(100, 30)
        btn_admin.setStyleSheet("background-color: #607d8b; color: white; border: none; font-weight: bold;")
        btn_admin.setFocusPolicy(Qt.NoFocus)
        btn_admin.clicked.connect(self._open_admin_window)
        header_layout.addWidget(btn_admin)

        btn_cancel_tx = QPushButton("伝票取消")
        btn_cancel_tx.setFixedSize(80, 30)
        btn_cancel_tx.setStyleSheet("background-color: #d32f2f; color: white; border: none; font-weight: bold;")
        btn_cancel_tx.setFocusPolicy(Qt.NoFocus)
        btn_cancel_tx.clicked.connect(self._open_transaction_cancel_dialog)
        header_layout.addWidget(btn_cancel_tx)

        btn_settings = QPushButton("⚙ 設定")
        btn_settings.setFixedSize(80, 30)
        btn_settings.setStyleSheet("background-color: #546e7a; color: white; border: none;")
        btn_settings.clicked.connect(self._open_settings_window)
        header_layout.addWidget(btn_settings)

        main_layout.addWidget(self.header_frame)

        # --- ボディ ---
        body = QHBoxLayout()
        
        # 1. カート Widget
        self.cart_widget = CartWidget(self.cart_service)
        body.addWidget(self.cart_widget, stretch=3)

        # 2. 商品リスト Widget
        self.product_list_widget = ProductListWidget(self.cart_service, self.product_service)
        body.addWidget(self.product_list_widget, stretch=5)

        # 3. 操作パネル (右側)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.customer_panel = CustomerPanel(self.cart_service, self.customer_service)
        right_layout.addWidget(self.customer_panel)
        
        right_layout.addStretch()
        
        btn_manual = QPushButton("手入力商品")
        btn_manual.setFixedHeight(50)
        btn_manual.setStyleSheet(StyleGenerator.create_button_style("#5d4037"))
        btn_manual.setFocusPolicy(Qt.NoFocus)
        btn_manual.clicked.connect(self._open_manual_input)
        right_layout.addWidget(btn_manual)

        self.btn_checkout = QPushButton("会 計")
        self.btn_checkout.setFixedHeight(80)
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setStyleSheet(StyleGenerator.create_button_style("#d84315"))
        self.btn_checkout.clicked.connect(self._open_payment_dialog)
        right_layout.addWidget(self.btn_checkout)

        body.addWidget(right_panel, stretch=2)
        main_layout.addLayout(body)

    def _connect_signals(self) -> None:
        self.cart_service.stats_updated.connect(self._update_stats)
        self.cart_service.checkout_completed.connect(self._on_checkout_completed)
        self.cart_service.user_changed.connect(lambda n: self.btn_cashier.setText(f"担当: {n}"))
        self.cart_service.cart_updated.connect(self._check_checkout_button)
        self.cart_service.customer_selected.connect(self._check_checkout_button)

    def _check_checkout_button(self):
        cust = self.cart_service.selected_customer
        has_user = self.cart_service.current_user_name not in [None, "", "Guest"]
        if cust and has_user:
            self.btn_checkout.setEnabled(True)
            self.btn_checkout.setText(f"会計\n({cust.label})")
        else:
            self.btn_checkout.setEnabled(False)
            if not has_user:
                self.btn_checkout.setText("会計\n(担当者未選択)")
            else:
                self.btn_checkout.setText("会 計")

    def _update_stats(self, sales: int, expenses: int, profit: int, msg: str, is_red: bool) -> None:
        self.lbl_stats["総売上"].setText(f"総売上: ¥{sales:,}")
        self.lbl_stats["経費計"].setText(f"経費計: ¥{expenses:,}")
        self.lbl_stats["現在利益"].setText(f"現在利益: ¥{profit:,}")
        self.lbl_stats["黒字まで"].setText(msg)
        color = "#ff5252" if is_red else "#69f0ae"
        self.lbl_stats["黒字まで"].setStyleSheet(f"color: {color}; border: none;")

    def _open_payment_dialog(self) -> None:
        total = self.cart_service.get_total_amount()
        
        methods = self.payment_repo.fetch_all()
        dialog = PaymentDialog(total, methods, self)
        
        if dialog.exec():
            payments, change = dialog.get_result()
            self.cart_service.finalize_checkout(payments, change)

    def _on_checkout_completed(self, total_amount: int, change: int, customer_name: str) -> None:
        msg_text = (
            f"会計が完了しました。\n\n"
            f"合計: ¥{total_amount:,}\n"
            f"お釣り: ¥{change:,}\n"
            f"客層: {customer_name}\n"
        )
        QMessageBox.information(self, "完了", msg_text)
        self.cart_service.reset_message()
        self._check_checkout_button()

    def _open_manual_input(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("手入力商品")
        layout = QVBoxLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("商品名")
        layout.addWidget(name_input)
        
        price_input = QSpinBox()
        price_input.setRange(-999999999, 999999999)
        price_input.setSingleStep(100)
        price_input.setValue(100)
        layout.addWidget(price_input)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec():
            val = price_input.value()
            self.cart_service.add_manual_item(val, name_input.text() or "手入力")

    def _open_admin_window(self) -> None:
        admin = AdminWindow(self.analytics_service, self)
        admin.exec()

    def _show_login_dialog(self):
        dialog = LoginDialog(self.user_repo, self)
        if dialog.exec():
            user_name = dialog.selected_user_name
            self.cart_service.set_current_user(user_name)
            self.btn_cashier.setText(f"担当: {user_name}")
            self.btn_cashier.setStyleSheet("QPushButton { color: #e0f7fa; background-color: #006064; border: 1px solid #0097a7; border-radius: 4px; padding: 5px 10px; } QPushButton:hover { background-color: #00838f; }")
            # ログに記録
            log_msg = f"ユーザーログイン: {user_name}"
            self.log_repo.add_log("info", log_msg)
            logger.info(log_msg)
            self._check_checkout_button()

    def _open_settings_window(self):
        win = SettingsWindow(
            product_service=self.product_service,
            user_service=self.user_service,
            customer_service=self.customer_service,
            payment_service=self.payment_service,
            expense_service=self.expense_service,
            discount_service=self.discount_service,
            master_service=self.master_data_service,
            parent=self
        )
        win.exec()
        # 設定画面から戻ったらデータをリフレッシュ
        active_products = self.product_service.get_active_products()
        self.cart_service.refresh_prices(active_products)
        self.cart_service.recalculate()
        self.product_list_widget.refresh_data()
        self.customer_panel.refresh_data()
    
    def _open_transaction_cancel_dialog(self):
        dialog = TransactionCancelDialog(self.analytics_service, self.checkout_service, self)
        dialog.exec()
        # 伝票取消後はデータをリフレッシュ
        self.cart_service._init_sales_data()
        self.cart_service.recalculate()