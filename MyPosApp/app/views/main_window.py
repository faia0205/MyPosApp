from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QGridLayout, QScrollArea, QFrame, QLabel, QTableWidget, 
                               QTableWidgetItem, QHeaderView, QButtonGroup, QMessageBox, 
                               QDialog, QLineEdit, QSpinBox, QDialogButtonBox, QTabWidget, QPushButton)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from app.services.cart_service import CartService
from app.repositories.product_repo import ProductRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.transaction_repo import TransactionRepository
from app.models.product import Product
from app.models.customer import Customer
from app.utils.style import StyleGenerator
from app.views.components.custom_buttons import ProductButton, CustomerButton
from app.views.dialogs.payment_dialog import PaymentDialog
from app.views.admin_window import AdminWindow
from app.views.dialogs.login_dialog import LoginDialog

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Modular POS System")
        self.resize(1280, 800)
        
        # 全体の背景色を少し暗くして統一感を出す
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; } QWidget { color: #ffffff; }")

        self.cart_service: CartService = CartService()
        self.prod_repo: ProductRepository = ProductRepository()
        self.cust_repo: CustomerRepository = CustomerRepository()
        self.trans_repo: TransactionRepository = TransactionRepository()
        
        self.current_indices_map: List[int] = [] 

        self._init_ui()
        self._connect_signals()
        self._load_data()

        # (show()の後に出すと画面が表示されてからダイアログが出るので、
        #  本来は main.py で制御するのが綺麗ですが、簡易的にここで処理します)
        # ただし __init__ 内で exec() するとメイン画面が出る前にダイアログだけで止まるのでOK
        self._show_login_dialog()

    def _init_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # --- A. ヘッダー ---
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("background-color: #333; color: white; border-radius: 5px; padding: 5px;")
        header_layout = QHBoxLayout(self.header_frame)
        
        # 統計ラベル
        self.lbl_stats: Dict[str, QLabel] = {}
        for key in ["総売上", "経費計", "現在利益", "黒字まで"]:
            lbl = QLabel(f"{key}: ---")
            lbl.setFont(QFont("Meiryo", 12, QFont.Bold))
            lbl.setStyleSheet("border: none; color: white;")
            header_layout.addWidget(lbl)
            self.lbl_stats[key] = lbl
        
        header_layout.addStretch() # 余白
        
        # ★修正: 担当者表示をボタンに変更
        self.btn_cashier = QPushButton("担当: ---")
        self.btn_cashier.setFont(QFont("Meiryo", 10, QFont.Bold))
        # フラットなボタンデザイン（マウスホバーで少し明るくなる）
        self.btn_cashier.setStyleSheet("""
            QPushButton {
                color: #bbb; 
                background-color: transparent; 
                border: 1px solid #555; 
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #444;
                color: white;
            }
        """)
        self.btn_cashier.setCursor(Qt.PointingHandCursor) # マウスカーソルを指の形に
        self.btn_cashier.setFocusPolicy(Qt.NoFocus)
        self.btn_cashier.clicked.connect(self._show_login_dialog) # クリックで再ログイン
        header_layout.addWidget(self.btn_cashier)
        
        # 管理ボタン
        btn_admin = QPushButton("管理・分析")
        btn_admin.setFixedSize(100, 30)
        btn_admin.setStyleSheet("background-color: #607d8b; color: white; border: none; font-weight: bold;")
        btn_admin.setFocusPolicy(Qt.NoFocus)
        btn_admin.clicked.connect(self._open_admin_window)
        header_layout.addWidget(btn_admin)
            
        main_layout.addWidget(self.header_frame)

        # --- ボディ ---
        body = QHBoxLayout()
        
        # カートエリア
        cart_panel = QWidget()
        cart_layout = QVBoxLayout(cart_panel)
        
        self.info_box = QLabel("いらっしゃいませ")
        self.info_box.setFixedHeight(40)
        # 初期スタイル
        self.info_box.setStyleSheet("background-color: #37474f; color: #fff; border: 1px solid #90caf9; padding: 5px; font-weight: bold;")
        cart_layout.addWidget(self.info_box)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6) 
        self.cart_table.setHorizontalHeaderLabels(["商品", "個", "単価", "小計", "", ""])
        
        # ★修正: カートのダークテーマ化スタイルシート
        self.cart_table.setStyleSheet("""
            QTableWidget {
                background-color: #333333;   /* 背景: ダークグレー */
                gridline-color: #555555;     /* 枠線: 明るめのグレー */
                color: #ffffff;              /* 文字: 白 */
                selection-background-color: #0d47a1; /* 選択時: 濃い青 */
                border: 1px solid #555;
            }
            /* ヘッダーのスタイル */
            QHeaderView::section {
                background-color: #424242;
                color: white;
                padding: 4px;
                border: 1px solid #666;
                font-weight: bold;
            }
            /* 編集中の入力欄のスタイル (入力中も見やすく) */
            QLineEdit {
                color: #000000;              /* 入力中は黒文字 */
                background-color: #ffffff;   /* 背景は白 */
                border: 2px solid #2196f3;
                font-weight: bold;
            }
        """)

        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.cart_table.setColumnWidth(4, 35)
        self.cart_table.setColumnWidth(5, 35)
        
        self.cart_table.cellChanged.connect(self._on_cart_cell_changed)
        
        cart_layout.addWidget(self.cart_table, stretch=2)

        # 割引テーブル (小さめ)
        self.lbl_discount_title = QLabel("適用割引")
        self.lbl_discount_title.setStyleSheet("font-weight: bold; color: #ff8a80; margin-top: 5px;")
        cart_layout.addWidget(self.lbl_discount_title)

        self.discount_table = QTableWidget()
        self.discount_table.setColumnCount(3) # 名前, 回数, 小計
        self.discount_table.setHorizontalHeaderLabels(["割引名", "回数", "値引額"])
        self.discount_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.discount_table.verticalHeader().setVisible(False)
        self.discount_table.setFixedHeight(100) # 高さを固定
        self.discount_table.setStyleSheet("""
            QTableWidget { background-color: #424242; color: #ff8a80; border: 1px solid #d32f2f; }
            QHeaderView::section { background-color: #5d4037; color: white; }
        """)
        cart_layout.addWidget(self.discount_table, stretch=1)

        self.lbl_total = QLabel("合計: ¥0")
        self.lbl_total.setStyleSheet("font-size: 24px; font-weight: bold; background-color: #212121; color: #00e676; padding: 10px; border-radius: 4px;")
        self.lbl_total.setAlignment(Qt.AlignRight)
        cart_layout.addWidget(self.lbl_total)
        
        body.addWidget(cart_panel, stretch=3)

        # 商品タブエリア
        self.tabs = QTabWidget()
        # タブのスタイルは utils/style.py で定義済みだが、背景色との兼ね合いで調整が必要ならここで行う
        self.tabs.setStyleSheet(StyleGenerator.create_tab_style())
        body.addWidget(self.tabs, stretch=5)

        # 操作パネルエリア
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        self.customer_grid = QGridLayout()
        right_layout.addLayout(self.customer_grid)
        
        right_layout.addStretch()
        
        btn_manual = QPushButton("手入力商品")
        btn_manual.setFixedHeight(50)
        btn_manual.setStyleSheet(StyleGenerator.create_button_style("#5d4037")) # ダークブラウン
        btn_manual.setFocusPolicy(Qt.NoFocus)
        btn_manual.clicked.connect(self._open_manual_input)
        right_layout.addWidget(btn_manual)

        self.btn_checkout = QPushButton("会 計")
        self.btn_checkout.setFixedHeight(80)
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setStyleSheet(StyleGenerator.create_button_style("#d84315")) # 濃いオレンジ
        self.btn_checkout.clicked.connect(self._open_payment_dialog)
        right_layout.addWidget(self.btn_checkout)

        body.addWidget(right_panel, stretch=2)
        main_layout.addLayout(body)

    def _connect_signals(self) -> None:
        self.cart_service.cart_updated.connect(self._render_cart)
        self.cart_service.message_updated.connect(self._update_message)
        self.cart_service.stats_updated.connect(self._update_stats)
        self.cart_service.checkout_completed.connect(self._on_checkout_completed)

    def _load_data(self) -> None:
        # (変更なし) 前回のコードと同じ
        products: List[Product] = self.prod_repo.fetch_active_products()
        cat_totals: Dict[str, int] = {}
        categorized: Dict[str, List[Product]] = {}

        for p in products:
            cat = p.category or "その他"
            if cat not in categorized: 
                categorized[cat] = []
                cat_totals[cat] = 0
            categorized[cat].append(p)
            cat_totals[cat] += p.price

        sorted_categories = sorted(cat_totals.keys(), key=lambda x: cat_totals[x], reverse=True)
        
        for cat in sorted_categories:
            items = categorized[cat]
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            # ★追加: スクロールエリアの背景もダークに
            scroll.setStyleSheet("background-color: #424242;") 
            container = QWidget()
            container.setStyleSheet("background-color: #424242;") # コンテナも
            grid = QGridLayout(container)
            grid.setSpacing(10)
            
            for i, p in enumerate(items):
                btn = ProductButton(p)
                btn.clicked.connect(lambda _, x=p: self.cart_service.add_product(x))
                grid.addWidget(btn, i//3, i%3)
            
            grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            scroll.setWidget(container)
            self.tabs.addTab(scroll, cat)

        self.cust_group = QButtonGroup(self)
        self.cust_group.setExclusive(True)
        
        customers: List[Customer] = self.cust_repo.fetch_presets()
        for i, c in enumerate(customers):
            btn = CustomerButton(c)
            self.cust_group.addButton(btn)
            self.customer_grid.addWidget(btn, i//2, i%2)
            btn.clicked.connect(lambda _, x=c: self._on_customer_selected(x))
        
        self.cart_service._recalculate()

    # --- Event Handlers ---
    def _on_customer_selected(self, customer: Customer) -> None:
        self.cart_service.set_customer(customer)
        self.btn_checkout.setEnabled(True)
        self.btn_checkout.setText(f"会計\n({customer.label})")

    def _render_cart(self) -> None:
        # 1. 商品テーブル
        raw_items = self.cart_service.cart_items
        indices = list(range(len(raw_items)))
        indices.sort(key=lambda i: (
            raw_items[i]['price'] < 0,
            -raw_items[i]['price']
        ))
        
        self.current_indices_map = indices

        self.cart_table.blockSignals(True)
        self.cart_table.setRowCount(len(indices))

        for view_row, data_index in enumerate(indices):
            item = raw_items[data_index]
            
            # 色設定: 割引は明るい赤(ピンク寄り)、通常は白 (ダーク背景なので)
            text_color = QColor("#ff8a80") if item['price'] < 0 else QColor("white")
            # ★修正: 背景色の強制指定を削除 (スタイルシートに任せる)
            # ただし、QTableWidgetItemを作るときに背景を指定しないことでスタイルシートが効く

            def create_item(text, editable=False):
                it = QTableWidgetItem(str(text))
                it.setForeground(text_color)
                # it.setBackground(...) ←これを削除！
                if not editable:
                    it.setFlags(it.flags() ^ Qt.ItemIsEditable)
                return it

            self.cart_table.setItem(view_row, 0, create_item(item['name'], editable=False))
            self.cart_table.setItem(view_row, 1, create_item(item['qty'], editable=True))
            self.cart_table.setItem(view_row, 2, create_item(item['price'], editable=True))
            
            sub = item['price'] * item['qty']
            self.cart_table.setItem(view_row, 3, create_item(f"¥{sub:,}", editable=False))
            
            # ボタンのデザインもダーク系に
            btn_decr = QPushButton("-")
            btn_decr.setStyleSheet("color: #90caf9; font-weight: bold; background-color: #424242; border: 1px solid #666;")
            btn_decr.setFocusPolicy(Qt.NoFocus)
            btn_decr.clicked.connect(lambda _, idx=data_index: self.cart_service.decrease_item_qty(idx))
            self.cart_table.setCellWidget(view_row, 4, btn_decr)

            btn_del = QPushButton("×")
            btn_del.setStyleSheet("color: #ef9a9a; font-weight: bold; background-color: #424242; border: 1px solid #666;")
            btn_del.setFocusPolicy(Qt.NoFocus)
            btn_del.clicked.connect(lambda _, idx=data_index: self.cart_service.remove_item(idx))
            self.cart_table.setCellWidget(view_row, 5, btn_del)

        # 2. 割引テーブル
        discounts = self.cart_service.applied_discounts
        self.discount_table.setRowCount(len(discounts))
        
        # 割引があるなら表示、なければ隠すなどの制御も可能ですが、今回は常時表示
        for i, d in enumerate(discounts):
            sub = d['amount'] * d['qty']
            self.discount_table.setItem(i, 0, QTableWidgetItem(d['name']))
            self.discount_table.setItem(i, 1, QTableWidgetItem(f"{d['qty']}回"))
            self.discount_table.setItem(i, 2, QTableWidgetItem(f"¥{sub:,}"))
        
        self.cart_table.blockSignals(False)
        self.lbl_total.setText(f"合計: ¥{self.cart_service.get_total_amount():,}")

    def _on_cart_cell_changed(self, row: int, col: int) -> None:
        """入力バリデーション付きの変更処理"""
        if row >= len(self.current_indices_map): return
        data_index = self.current_indices_map[row]
        
        item_widget = self.cart_table.item(row, col)
        if not item_widget: return
        
        text_val = item_widget.text()
        
        # 数値変換を試みる（カンマや円マークを除去）
        clean_text = text_val.replace("¥", "").replace(",", "").strip()
        
        # 全角数字も許容するために unicodedata.normalize などを使う手もあるが、
        # ここではシンプルに int() トライで判定
        try:
            val = int(clean_text)
            
            # ★追加: 正常値ならService更新
            if col == 1: # 個数
                self.cart_service.update_item_qty(data_index, val)
            elif col == 2: # 単価
                self.cart_service.update_item_price(data_index, val)
                
        except ValueError:
            # ★追加: エラー処理
            # 警告を出して、強制的に再描画（元の値に戻す）する
            QMessageBox.warning(self, "入力エラー", "半角数字で入力してください。")
            self._render_cart() # モデルの値で上書きして元に戻す

    def _update_message(self, text: str, msg_type: str) -> None:
        # ダークテーマに合わせた色使い
        base_style = "padding: 5px; border-radius: 4px; font-weight: bold;"
        
        if msg_type == "info":
            bg_color = "#37474f" # 濃い青グレー
            text_color = "#ffffff"
            border = "1px solid #90caf9"
        else:
            bg_color = "#5d4037" # 濃い茶赤
            text_color = "#ff8a80" # 明るい赤
            border = "2px solid #ff5252"
            
        self.info_box.setText(text)
        self.info_box.setStyleSheet(f"background-color: {bg_color}; color: {text_color}; border: {border}; {base_style}")

    # ... (以下のメソッドは変更なし、前回のコードと同様) ...
    def _update_stats(self, sales: int, expenses: int, profit: int, msg: str, is_red: bool) -> None:
        self.lbl_stats["総売上"].setText(f"総売上: ¥{sales:,}")
        self.lbl_stats["経費計"].setText(f"経費計: ¥{expenses:,}")
        self.lbl_stats["現在利益"].setText(f"現在利益: ¥{profit:,}")
        self.lbl_stats["黒字まで"].setText(msg)
        color = "#ff5252" if is_red else "#69f0ae"
        self.lbl_stats["黒字まで"].setStyleSheet(f"color: {color}; border: none;")

    def _open_payment_dialog(self) -> None:
        # (変更なし)
        total = self.cart_service.get_total_amount()
        if total <= 0: return
        methods = self.trans_repo.fetch_payment_methods()
        dialog = PaymentDialog(total, methods, self)
        if dialog.exec():
            payments, change = dialog.get_result()
            self.cart_service.finalize_checkout(payments, change)

    def _on_checkout_completed(self, customer_name: str, change: int) -> None:
        """会計完了後の処理"""
        # ★修正: customer_name をメッセージに含めるようにしました
        msg = f"【客層: {customer_name}】\nお釣り: ¥{change:,}\n\n会計が完了しました。"
        QMessageBox.information(self, "完了", msg)
        
        # 客層ボタンのリセット
        self.cust_group.setExclusive(False)
        for btn in self.cust_group.buttons(): btn.setChecked(False)
        self.cust_group.setExclusive(True)
        
        self.btn_checkout.setEnabled(False)
        self.btn_checkout.setText("会 計")
        
        # 情報ウィンドウのリセット
        self.cart_service.reset_message()

    def _open_manual_input(self) -> None:
        # (変更なし)
        dialog = QDialog(self)
        dialog.setWindowTitle("手入力商品")
        layout = QVBoxLayout(dialog)
        name_input = QLineEdit(); name_input.setPlaceholderText("商品名"); layout.addWidget(name_input)
        price_input = QSpinBox(); price_input.setRange(0, 999999); price_input.setSingleStep(100); price_input.setValue(100); layout.addWidget(price_input)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept); btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        if dialog.exec():
            val = price_input.value()
            if val > 0: self.cart_service.add_manual_item(val, name_input.text() or "手入力")
    
    def _open_admin_window(self) -> None:
        """管理画面を開く"""
        admin = AdminWindow(self)
        admin.exec() # モーダルウィンドウとして開く
    
    def _show_login_dialog(self):
        """ログインダイアログ表示"""
        dialog = LoginDialog(self)
        
        # ★修正: キャンセルされたら変更しないようにロジック調整
        if dialog.exec():
            # ログイン成功時
            user_name = dialog.selected_user_name
            self.cart_service.set_current_user(user_name)
            self.btn_cashier.setText(f"担当: {user_name}")
            
            # アイコンや色を変えて「ログイン中」感を出す
            self.btn_cashier.setStyleSheet("""
                QPushButton {
                    color: #e0f7fa; 
                    background-color: #006064; 
                    border: 1px solid #0097a7; 
                    border-radius: 4px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #00838f;
                }
            """)
        else:
            # キャンセル時は何もしない（未設定のままか、前の人のまま）
            # ただし、初回起動時（まだ誰もいない時）だけは「未設定」にする必要があるなら
            if self.cart_service.current_user_name == "未設定":
                 self.btn_cashier.setText("担当: 未設定")