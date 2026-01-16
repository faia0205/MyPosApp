import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QGridLayout, QScrollArea, QPushButton, 
                               QButtonGroup, QInputDialog, QMessageBox, QDialog, 
                               QLabel, QLineEdit, QSpinBox, QDialogButtonBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from database import Repository
from logic import CartManager
from style import StyleGenerator
from ui_parts import HeaderWidget, CartWidget, ProductTabWidget

class POSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("POS System Final")
        self.resize(1280, 800)

        self.repo = Repository()
        self.cart_manager = CartManager(self.repo)
        self.style_gen = StyleGenerator()

        self._init_ui()
        self._connect_signals()
        
        self._load_products_into_tabs()
        self._load_customers()
        
        self.cart_manager._recalculate()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ヘッダー
        self.header = HeaderWidget()
        main_layout.addWidget(self.header)

        # ボディ
        body_layout = QHBoxLayout()
        main_layout.addLayout(body_layout)

        # 左：カート
        self.cart_widget = CartWidget()
        body_layout.addWidget(self.cart_widget, stretch=3)

        # 中央：商品
        self.tabs = ProductTabWidget()
        self.tabs.setStyleSheet(self.style_gen.create_tab_style())
        body_layout.addWidget(self.tabs, stretch=5)

        # 右：操作系
        right_panel = QWidget()
        self.right_layout = QVBoxLayout(right_panel)
        
        self.customer_grid = QGridLayout()
        self.right_layout.addLayout(self.customer_grid)
        self.right_layout.addStretch()

        manual_btn = QPushButton("手入力商品")
        manual_btn.setFixedHeight(50)
        manual_btn.setStyleSheet("background-color: #795548; color: white; font-weight: bold; border-radius: 5px;")
        manual_btn.clicked.connect(self._open_manual_input)
        self.right_layout.addWidget(manual_btn)

        self.checkout_btn = QPushButton("会 計")
        self.checkout_btn.setFixedHeight(80)
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setStyleSheet(self.style_gen.create_button_style("#ff5722"))
        # Logicの会計処理を呼ぶ
        self.checkout_btn.clicked.connect(self.cart_manager.process_checkout)
        self.right_layout.addWidget(self.checkout_btn)

        body_layout.addWidget(right_panel, stretch=2)

    def _connect_signals(self):
        # Logic -> View
        self.cart_manager.cart_updated.connect(self._on_cart_updated)
        self.cart_manager.message_updated.connect(self.cart_widget.update_message)
        self.cart_manager.stats_updated.connect(self.header.update_stats)
        
        # ★追加: 会計完了時のリセット処理
        self.cart_manager.checkout_completed.connect(self._on_checkout_completed)

        # View -> Logic
        self.cart_widget.item_qty_changed.connect(self.cart_manager.update_item_qty)
        self.cart_widget.item_decrease.connect(self.cart_manager.decrease_item) # マイナス
        self.cart_widget.item_removed.connect(self.cart_manager.remove_item)    # 削除

    def _load_products_into_tabs(self):
        products = self.repo.fetch_active_products()
        
        # 1. 商品をカテゴリごとに分類
        categorized = {}
        category_totals = {} # ★追加: カテゴリごとの「重要度」計算用

        for p in products:
            cat = p['category'] or "その他"
            if cat not in categorized: 
                categorized[cat] = []
                category_totals[cat] = 0 # 初期化
            
            categorized[cat].append(p)
            
            # 重要度の計算: ここではシンプルに「商品単価の合計」が高い順にします
            # （「割引」はマイナスなので自然と一番後ろになります）
            category_totals[cat] += p['price']

        # 2. カテゴリ（キー）を並び替え
        # sorted関数を使って、category_totalsの値が大きい順に並べます
        sorted_categories = sorted(categorized.keys(), key=lambda x: category_totals[x], reverse=True)

        # 3. 並び替えた順にタブを作成
        for cat_name in sorted_categories:
            items = categorized[cat_name]
            
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            container = QWidget()
            grid = QGridLayout(container)
            grid.setSpacing(10)
            
            col_max = 3
            for i, p in enumerate(items):
                label = f"{p['name']}\n¥{p['price']}"
                if p['price'] < 0: label = f"{p['name']}\n{p['price']}"
                
                btn = QPushButton(label)
                btn.setFixedSize(130, 90)
                btn.setStyleSheet(self.style_gen.create_button_style(p['color']))
                # 商品ボタンもフォーカス枠が残らないように修正
                btn.setFocusPolicy(Qt.NoFocus) 
                
                btn.clicked.connect(lambda _, x=p: self.cart_manager.add_product(x))
                grid.addWidget(btn, i // col_max, i % col_max)
            
            grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            scroll.setWidget(container)
            self.tabs.add_category_tab(cat_name, scroll)

    def _load_customers(self):
        presets = self.repo.fetch_customer_presets()
        self.customer_group = QButtonGroup(self)
        self.customer_group.setExclusive(True)

        for i, customer in enumerate(presets):
            btn = QPushButton(customer['label'])
            btn.setFixedHeight(50)
            btn.setCheckable(True)
            color = customer.get('color', '#b0bec5')
            btn.setStyleSheet(self.style_gen.create_button_style(color))
            
            self.customer_group.addButton(btn)
            self.customer_grid.addWidget(btn, i // 2, i % 2)
            btn.clicked.connect(lambda _, c=customer: self._on_customer_selected(c))

    def _on_customer_selected(self, customer):
        self.cart_manager.selected_customer = customer
        self.checkout_btn.setEnabled(True)
        self.checkout_btn.setText(f"会 計\n({customer['label']})")
        self.checkout_btn.setStyleSheet(self.style_gen.create_button_style("#ff5722"))

    def _on_cart_updated(self):
        self.cart_widget.update_cart_view(
            self.cart_manager.cart_items, 
            self.cart_manager.get_total_amount()
        )

    def _on_checkout_completed(self, customer_name, total):
        """会計完了後のUIリセット"""
        QMessageBox.information(self, "完了", f"¥{total:,} の会計完了\n客層: {customer_name}")
        
        # 客層ボタンの選択解除 (Exclusiveを一時的に切る必要がある)
        self.customer_group.setExclusive(False)
        for btn in self.customer_group.buttons():
            btn.setChecked(False)
        self.customer_group.setExclusive(True)
        
        # 会計ボタンの無効化
        self.checkout_btn.setEnabled(False)
        self.checkout_btn.setText("会 計")
        self.checkout_btn.setStyleSheet(self.style_gen.create_button_style("#ff5722"))
        
        # 情報ボックス
        self.cart_widget.update_message("次の会計をお願いします", "info")

    def _open_manual_input(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("手入力")
        layout = QVBoxLayout(dialog)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("商品名")
        layout.addWidget(name_input)
        
        price_input = QSpinBox()
        price_input.setRange(0, 999999)
        price_input.setSingleStep(100)
        price_input.setValue(100)
        layout.addWidget(price_input)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dialog.accept)
        btns.rejected.connect(dialog.reject)
        layout.addWidget(btns)
        
        if dialog.exec():
            name = name_input.text().strip() or "手入力"
            price = price_input.value()
            if price > 0:
                self.cart_manager.add_manual_item(price, name)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Yu Gothic UI", 12))
    window = POSMainWindow()
    window.show()
    sys.exit(app.exec())