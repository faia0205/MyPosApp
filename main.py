import sys
import sqlite3
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                               QTableWidgetItem, QGridLayout, QScrollArea, QFrame,
                               QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor

# --- データベース設定 ---
DB_NAME = "pos_system.db"

# --- ご提示いただいたスタイル生成クラス ---
class StyleGenerator:
    """ウィジェットのスタイルシート(QSS)を生成するクラス"""

    def create_button_style(self, base_color: str) -> str:
        """基準色からボタンのQSSを生成する"""
        if not base_color: base_color = "#e0e0e0" # デフォルト色
        
        hover_bg_color = self._darken_color(base_color, 0.1)
        pressed_bg_color = self._darken_color(base_color, 0.2)
        
        text_color = self._get_text_color(base_color)
        hover_text_color = self._get_text_color(hover_bg_color)
        pressed_text_color = self._get_text_color(pressed_bg_color)

        return f"""
            QPushButton {{
                background-color: {base_color};
                color: {text_color};
                border: 1px solid #888;
                border-radius: 8px;
                padding: 5px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_bg_color};
                color: {hover_text_color};
                border: 2px solid #007acc;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg_color};
                color: {pressed_text_color};
                border: 2px solid #0056b3;
            }}
        """

    def _darken_color(self, hex_color: str, factor: float) -> str:
        """16進数カラーコードを暗くする"""
        if not hex_color.startswith('#') or len(hex_color) != 7: return hex_color
        try:
            r, g, b = (int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            r, g, b = (max(0, int(c * (1 - factor))) for c in (r, g, b))
            return f'#{r:02x}{g:02x}{b:02x}'
        except ValueError:
            return hex_color

    def _get_text_color(self, background_color: str) -> str:
        """背景色に基づいて最適な文字色（黒または白）を返す"""
        if not background_color.startswith('#') or len(background_color) != 7: return "#000000"
        try:
            r, g, b = (int(background_color[i:i+2], 16) for i in (1, 3, 5))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#ffffff"
        except ValueError:
            return "#000000"

# --- メインウィンドウ ---
class POSMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自作POSシステム 2026")
        self.resize(1280, 800)
        self.style_gen = StyleGenerator()

        # メインコンテナ
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)

        # 1. ヘッダー（経営分析エリア）
        self.create_header()

        # 2. メインボディ（3カラム構成）
        body_layout = QHBoxLayout()
        self.main_layout.addLayout(body_layout)

        # 左パネル：カート
        self.create_left_panel(body_layout)
        # 中央パネル：商品グリッド
        self.create_center_panel(body_layout)
        # 右パネル：操作盤
        self.create_right_panel(body_layout)

        # 初期データの読み込み
        self.load_products_from_db()
        self.load_customers_from_db()

        # --- データ管理用変数の初期化 ---
        self.cart_items = []     # カートの中身: [{"name":..., "price":..., "qty":...}, ...]
        self.current_expenses = 0 # 経費合計
        self.total_sales = 0      # 今日の総売上
        self.average_price = 500  # 黒字計算用の仮平均単価（後でDBから計算も可）
        
        # 経費をDBから読み込んでセット
        self.load_expenses()
        
        # 画面の数値を初期更新
        self.update_header_stats()

    def create_header(self):
        """上部の経営ステータス表示"""
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #333; color: white; border-radius: 5px;")
        header_layout = QHBoxLayout(header_frame)
        
        # 表示項目（ラベルを保持しておく辞書）
        self.status_labels = {}
        items = ["総売上: ¥0", "経費計: ¥0", "現在利益: ¥0", "黒字まで: ---"]
        
        for text in items:
            lbl = QLabel(text)
            lbl.setFont(QFont("Meiryo", 14, QFont.Bold))
            header_layout.addWidget(lbl)
            # キーを取り出して辞書に保存（更新用）
            key = text.split(":")[0]
            self.status_labels[key] = lbl
            
        self.main_layout.addWidget(header_frame)

    def create_left_panel(self, parent_layout):
        """左側：購入リスト（カート）"""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        
        # 情報ボックス
        self.info_box = QLabel("いらっしゃいませ\n商品を選択してください")
        self.info_box.setStyleSheet("""
            background-color: #e3f2fd; 
            color: #333333; 
            border: 1px solid #2196f3; 
            padding: 10px; 
            border-radius: 5px;
            font-size: 14px;
            """)
        self.info_box.setFixedHeight(80)
        layout.addWidget(self.info_box)

        # カートテーブル
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(3)
        self.cart_table.setHorizontalHeaderLabels(["商品名", "個", "金額"])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.cart_table)

        # 合計金額表示
        self.total_label = QLabel("合計: ¥ 0")
        self.total_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setStyleSheet("background-color: #000; color: #0f0; padding: 10px;")
        layout.addWidget(self.total_label)

        parent_layout.addWidget(left_widget, stretch=3)

    def create_center_panel(self, parent_layout):
        """中央：商品ボタンエリア（スクロール可能）"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.product_container = QWidget()
        self.product_grid = QGridLayout(self.product_container)
        self.product_grid.setSpacing(10)
        
        scroll_area.setWidget(self.product_container)
        parent_layout.addWidget(scroll_area, stretch=5)

    def create_right_panel(self, parent_layout):
        """右側：客層選択と操作盤"""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)

        # 客層エリア（ここも動的に追加）
        layout.addWidget(QLabel("【客層選択】"))
        self.customer_grid_widget = QWidget()
        self.customer_grid = QGridLayout(self.customer_grid_widget)
        layout.addWidget(self.customer_grid_widget)

        layout.addStretch() # スペース調整

        # テンキーと機能ボタン
        numpad_layout = QGridLayout()
        keys = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0), ('00', 3, 1), ('C', 3, 2),
        ]
        for text, r, c in keys:
            btn = QPushButton(text)
            btn.setFixedSize(60, 60)
            # テンキーはシンプルなスタイルで
            btn.setStyleSheet("font-size: 18px; font-weight: bold;")
            numpad_layout.addWidget(btn, r, c)
            
        layout.addLayout(numpad_layout)

        # 会計ボタン
        checkout_btn = QPushButton("会 計")
        checkout_btn.setFixedHeight(80)
        checkout_btn.setStyleSheet("""
            background-color: #ff5722; color: white; 
            font-size: 24px; font-weight: bold; border-radius: 10px;
        """)
        layout.addWidget(checkout_btn)

        parent_layout.addWidget(right_widget, stretch=2)

    # --- データ読み込みロジック ---

    def load_products_from_db(self):
        """DBから商品を読み込み、StyleGeneratorで着色してボタン配置"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, color, note FROM products WHERE is_active=1")
        products = cursor.fetchall()
        conn.close()

        # グリッド配置の計算
        col_max = 3 # 3列で折り返し
        for i, (pid, name, price, color, note) in enumerate(products):
            btn_text = f"{name}\n¥{price}"
            btn = QPushButton(btn_text)
            btn.setFixedSize(140, 100)
            
            # ★ここでStyleGeneratorを使用！★
            # DBの色コードを使ってスタイルを生成・適用
            style = self.style_gen.create_button_style(color)
            btn.setStyleSheet(style)

            # ★追加: クリックイベントの接続
            # lambdaを使って、引数(name, price, note)を渡す
            btn.clicked.connect(lambda checked, n=name, p=price, note=note: self.add_product_to_cart(n, p, note))
            
            # グリッドに追加
            row = i // col_max
            col = i % col_max
            self.product_grid.addWidget(btn, row, col)

    def load_customers_from_db(self):
        """DBから客層プリセットを読み込みボタン配置"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, display_order FROM customer_presets WHERE is_active=1 ORDER BY display_order")
        customers = cursor.fetchall()
        conn.close()

        col_max = 2
        for i, (cid, label, order) in enumerate(customers):
            btn = QPushButton(label)
            btn.setFixedHeight(50)
            # 客層ボタンは少し落ち着いた色で統一（あるいはDBに色カラムを追加してもOK）
            btn.setStyleSheet(self.style_gen.create_button_style("#b0bec5")) 
            
            row = i // col_max
            col = i % col_max
            self.customer_grid.addWidget(btn, row, col)
    
    def add_product_to_cart(self, name, price, note):
        """商品をカートに追加し、表示を更新する"""
        
        # 1. カートに同じ商品があれば個数を増やす
        found = False
        for item in self.cart_items:
            if item["name"] == name and item["price"] == price:
                item["qty"] += 1
                found = True
                break
        
        # 2. なければ新規追加
        if not found:
            self.cart_items.append({"name": name, "price": price, "qty": 1})
            
        # 3. 情報ウィンドウの更新（注意書きがあれば表示）
        if note:
            self.info_box.setText(f"⚠️ {name}: {note}")
            self.info_box.setStyleSheet("""
                background-color: #ffebee; color: #b71c1c; 
                border: 2px solid #f44336; padding: 10px; border-radius: 5px; font-weight: bold;
            """)
        else:
            self.info_box.setText(f"【追加】 {name}")
            self.info_box.setStyleSheet("""
                background-color: #e3f2fd; color: #333333; 
                border: 1px solid #2196f3; padding: 10px; border-radius: 5px;
            """)

        # 4. 画面更新
        self.refresh_cart_display()
        self.update_header_stats() # 経営数値の更新（シミュレーション用）

    def refresh_cart_display(self):
        """カートリスト(QTableWidget)の再描画"""
        self.cart_table.setRowCount(0) # 一旦クリア
        total_price = 0
        
        for row, item in enumerate(self.cart_items):
            self.cart_table.insertRow(row)
            subtotal = item["price"] * item["qty"]
            total_price += subtotal
            
            # 各セルに値をセット
            self.cart_table.setItem(row, 0, QTableWidgetItem(item["name"]))
            self.cart_table.setItem(row, 1, QTableWidgetItem(str(item["qty"])))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"¥{subtotal:,}"))
        
        # 合計ラベルの更新
        self.total_label.setText(f"合計: ¥ {total_price:,}")
    
    def load_expenses(self):
        """DBから経費合計を取得"""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM expenses")
        result = cursor.fetchone()
        self.current_expenses = result[0] if result[0] else 0
        conn.close()

    def update_header_stats(self):
        """ヘッダーの数字を更新"""
        # 現在のカート内合計を「仮の売上」として計算に含めるか、
        # あるいは「確定した売上(self.total_sales)」のみを使うかですが、
        # ここでは「確定売上」ベースで表示します。
        
        current_profit = self.total_sales - self.current_expenses
        
        # 黒字までの必要個数計算
        # (経費 - 売上) / 平均単価
        items_needed = 0
        if current_profit < 0:
            remaining_loss = abs(current_profit)
            items_needed = (remaining_loss // self.average_price) + 1
            status_text = f"あと {items_needed} 個で黒字!"
            self.status_labels["黒字まで"].setStyleSheet("color: #ff5252;") # 赤字警告
        else:
            status_text = "黒字達成! 🎉"
            self.status_labels["黒字まで"].setStyleSheet("color: #69f0ae;") # 緑色で祝福

        # テキスト更新
        self.status_labels["総売上"].setText(f"総売上: ¥{self.total_sales:,}")
        self.status_labels["経費計"].setText(f"経費計: ¥{self.current_expenses:,}")
        self.status_labels["現在利益"].setText(f"現在利益: ¥{current_profit:,}")
        self.status_labels["黒字まで"].setText(status_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # アプリ全体のフォント設定
    font = QFont("Yu Gothic UI", 12)
    app.setFont(font)

    window = POSMainWindow()
    window.show()
    sys.exit(app.exec())