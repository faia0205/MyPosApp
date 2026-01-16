import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QScrollArea, QPushButton, 
                               QButtonGroup, QInputDialog, QMessageBox, QDialog,
                               QLabel, QLineEdit, QSpinBox, QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# 分割した自作モジュールをインポート
from database import Repository
from logic import CartManager
from style import StyleGenerator
from ui_parts import HeaderWidget, CartWidget, ProductTabWidget

class POSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自作POSシステム (SOLID原則版)")
        self.resize(1280, 800)

        # 1. 依存性の注入 (Dependency Injection)
        # データベース操作とビジネスロジック、スタイル生成を初期化
        self.repo = Repository()
        self.cart_manager = CartManager(self.repo)
        self.style_gen = StyleGenerator()

        # 2. UIの構築
        self._init_ui()

        # 3. シグナルとスロットの接続 (Observer Pattern)
        self._connect_signals()

        # 4. 初期データの読み込みと表示
        self._load_products_into_tabs()
        self._load_customers()
        
        # 5. 初期状態の計算（経費などをヘッダーに反映させるため）
        self.cart_manager._recalculate()

    def _init_ui(self):
        """画面レイアウトの作成"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 全体のレイアウト (縦方向)
        main_layout = QVBoxLayout(central_widget)

        # --- A. ヘッダー (経営分析情報) ---
        self.header = HeaderWidget()
        main_layout.addWidget(self.header)

        # --- B. メインボディ (横並び: カート | 商品タブ | 操作盤) ---
        body_layout = QHBoxLayout()
        main_layout.addLayout(body_layout)

        # 1. 左カラム: カート (ui_parts.pyで定義)
        self.cart_widget = CartWidget()
        body_layout.addWidget(self.cart_widget, stretch=3)

        # 2. 中央カラム: 商品タブ
        self.tabs = ProductTabWidget()
        self.tabs.setStyleSheet(self.style_gen.create_tab_style())
        body_layout.addWidget(self.tabs, stretch=5)

        # 3. 右カラム: 客層選択 & 操作ボタン
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        
        # 客層グリッドエリア
        self.customer_grid = QGridLayout()
        self.right_layout.addLayout(self.customer_grid)
        
        # 余白 (ボタンを下部に寄せるため)
        self.right_layout.addStretch()

        # 手入力ボタン
        manual_btn = QPushButton("手入力商品")
        manual_btn.setFixedHeight(50)
        manual_btn.setStyleSheet("background-color: #795548; color: white; font-weight: bold; border-radius: 5px;")
        manual_btn.clicked.connect(self._open_manual_input)
        self.right_layout.addWidget(manual_btn)

        # 会計ボタン
        self.checkout_btn = QPushButton("会 計")
        self.checkout_btn.setFixedHeight(80)
        # 初期状態は無効（客層未選択のため）→ style.py の :disabled 設定によりグレーアウトされる
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setStyleSheet(self.style_gen.create_button_style("#ff5722"))
        self.checkout_btn.clicked.connect(self._process_checkout)
        self.right_layout.addWidget(self.checkout_btn)

        body_layout.addWidget(right_panel, stretch=2)

    def _connect_signals(self):
        """各クラス間のイベント接続"""
        # Logic -> UI: カートの中身が変わったら表示を更新
        self.cart_manager.cart_updated.connect(self._on_cart_updated)
        
        # Logic -> UI: メッセージ（注意書きなど）があれば表示
        self.cart_manager.message_updated.connect(self.cart_widget.update_message)
        
        # Logic -> UI: 売上・利益計算の結果をヘッダーに反映
        self.cart_manager.stats_updated.connect(self.header.update_stats)

        # UI -> Logic: カート内の編集（個数変更、削除）をロジックに反映
        self.cart_widget.item_changed.connect(self.cart_manager.update_item)
        self.cart_widget.item_removed.connect(self.cart_manager.remove_item)

    def _load_products_into_tabs(self):
        """DBから商品を読み込み、カテゴリごとのタブに配置"""
        # database.py で ORDER BY category, display_order されている前提
        products = self.repo.fetch_active_products()
        
        # カテゴリごとにリストに振り分け
        categorized_products = {}
        for p in products:
            cat = p['category'] if p['category'] else "その他"
            if cat not in categorized_products:
                categorized_products[cat] = []
            categorized_products[cat].append(p)
            
        # カテゴリごとにタブを作成
        for cat_name, items in categorized_products.items():
            # スクロールエリアの作成
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            
            container = QWidget()
            grid = QGridLayout(container)
            grid.setSpacing(10) # ボタン間の隙間
            
            col_max = 3 # 1行に置くボタンの数
            
            for i, p in enumerate(items):
                # ボタンのテキスト作成 (改行コードを入れて見やすく)
                label_text = f"{p['name']}\n¥{p['price']}"
                if p['price'] < 0: # 割引の場合
                    label_text = f"{p['name']}\n{p['price']}円"
                
                btn = QPushButton(label_text)
                btn.setFixedSize(130, 90)
                
                # DBの色情報を使ってスタイル生成
                btn.setStyleSheet(self.style_gen.create_button_style(p['color']))
                
                # クリックイベント: ラムダ式で p (商品データ) を渡す
                btn.clicked.connect(lambda _, x=p: self.cart_manager.add_product(x))
                
                grid.addWidget(btn, i // col_max, i % col_max)
            
            # グリッドの余白詰め（ボタンが少ない時に間延びしないように）
            grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            
            scroll.setWidget(container)
            self.tabs.add_category_tab(cat_name, scroll)

    def _load_customers(self):
        """DBから客層プリセットを読み込み、排他選択ボタンとして配置"""
        presets = self.repo.fetch_customer_presets()
        
        # QButtonGroup: どれか1つしか選べないようにする仕組み
        self.customer_group = QButtonGroup(self)
        self.customer_group.setExclusive(True)

        col_max = 2
        for i, customer in enumerate(presets):
            btn = QPushButton(customer['label'])
            btn.setFixedHeight(50)
            btn.setCheckable(True) # 押した状態を保持できる
            
            # DBの色情報を使用 (デフォルトはグレー)
            color = customer.get('color', '#b0bec5')
            btn.setStyleSheet(self.style_gen.create_button_style(color))
            
            self.customer_group.addButton(btn)
            self.customer_grid.addWidget(btn, i // col_max, i % col_max)
            
            # クリック時の動作
            btn.clicked.connect(lambda _, c=customer: self._on_customer_selected(c))

    def _open_manual_input(self):
        """★修正: 商品名と金額を入力するダイアログ"""
        dialog = QDialog(self)
        dialog.setWindowTitle("手入力商品")
        dialog.setFixedSize(300, 200)
        
        layout = QVBoxLayout(dialog)
        
        # 商品名入力
        layout.addWidget(QLabel("商品名:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("例: 特注弁当")
        layout.addWidget(name_input)
        
        # 金額入力
        layout.addWidget(QLabel("金額:"))
        price_input = QSpinBox()
        price_input.setRange(0, 1000000)
        price_input.setSingleStep(10)
        price_input.setValue(500)
        # スピンボックスの文字を大きく
        price_input.setStyleSheet("font-size: 18px; padding: 5px;") 
        layout.addWidget(price_input)
        
        # OK/Cancelボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec():
            name = name_input.text().strip()
            if not name: name = "手入力"
            price = price_input.value()
            
            if price > 0:
                # name引数を追加した add_manual_item を呼ぶ
                self.cart_manager.add_manual_item(price, name)

    def _on_customer_selected(self, customer_data):
        """客層が選択された時の処理"""
        # ロジックに選択された客層をセット
        self.cart_manager.selected_customer = customer_data
        
        # 会計ボタンを有効化 (色は通常色に戻す)
        self.checkout_btn.setEnabled(True)
        self.checkout_btn.setText(f"会 計\n({customer_data['label']})")
        # 有効化されたのでスタイルを再適用（グレーアウト解除）
        self.checkout_btn.setStyleSheet(self.style_gen.create_button_style("#ff5722"))

    def _on_cart_updated(self):
        """Logicからの通知を受け、Viewを更新"""
        self.cart_widget.update_cart_view(
            self.cart_manager.cart_items, 
            self.cart_manager.get_total_amount()
        )

    def _process_checkout(self):
        """会計ボタンが押された時の処理（今回はモック）"""
        total = self.cart_manager.get_total_amount()
        customer = self.cart_manager.selected_customer['label']
        
        # 本来はここでDBへの保存処理(transactionsテーブルへのINSERT)を行う
        # 今回はメッセージボックスで完了を表示
        QMessageBox.information(self, "会計完了", f"¥{total:,} の会計を完了しました。\n客層: {customer}")
        
        # 画面リセットなどの処理が必要ならここに追加
        # self.cart_manager.clear_cart() など

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # アプリ全体のフォント設定 (Windowsで見やすいフォント)
    font = QFont("Yu Gothic UI", 12)
    app.setFont(font)

    window = POSMainWindow()
    window.show()
    sys.exit(app.exec())