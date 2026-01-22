from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QListWidget, QPushButton, QGridLayout, QInputDialog, QFrame, QScrollArea, QWidget)
from PySide6.QtCore import Qt
from app.views.components.custom_buttons import StyledButton

class PaymentDialog(QDialog):
    def __init__(self, total_amount: int, payment_methods: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("決済選択")
        self.resize(800, 550) # 少し大きく
        
        self.total_amount = total_amount
        # payment_methods は、MainWindowから「全件」渡される前提です
        self.payment_methods = payment_methods
        self.current_payments = [] 

        self._init_ui()
        self._update_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 1. ヘッダー (請求額・残り)
        status_layout = QHBoxLayout()
        self.lbl_total = QLabel(f"請求額\n¥{self.total_amount:,}")
        self.lbl_total.setStyleSheet("font-size: 20px; color: #555; font-weight: bold;")
        self.lbl_total.setAlignment(Qt.AlignCenter)
        
        self.lbl_remaining = QLabel()
        self.lbl_remaining.setStyleSheet("font-size: 32px; font-weight: bold;")
        self.lbl_remaining.setAlignment(Qt.AlignCenter)
        
        status_layout.addWidget(self.lbl_total)
        status_layout.addWidget(self.lbl_remaining)
        layout.addLayout(status_layout)
        
        layout.addWidget(self._create_line())

        # 2. ボディ (左右分割)
        body = QHBoxLayout()
        
        # --- 左：支払い済みリスト ---
        left = QVBoxLayout()
        left.addWidget(QLabel("【内訳】"))
        self.payment_list = QListWidget()
        self.payment_list.setStyleSheet("font-size: 16px; border: 1px solid #ccc;")
        left.addWidget(self.payment_list)
        
        btn_undo = QPushButton("1つ取り消す")
        btn_undo.setFocusPolicy(Qt.NoFocus)
        btn_undo.setStyleSheet("background-color: #607d8b; color: white; padding: 10px; font-weight: bold;")
        btn_undo.clicked.connect(self._undo_payment)
        left.addWidget(btn_undo)
        body.addLayout(left, stretch=3)

        # --- 右：決済ボタン一覧 (スクロール対応) ---
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("【決済方法】"))
        
        # グリッドレイアウト
        grid = QGridLayout()
        grid.setSpacing(10)
        
        row, col = 0, 0
        for pm in self.payment_methods:
            # is_activeキーがない場合はTrue扱い
            is_active = pm.get('is_active', True)
            
            # 色とスタイルの決定
            if not is_active:
                # 無効: グレーアウト
                btn = QPushButton(f"{pm['name']}\n(取扱停止)")
                btn.setEnabled(False)
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e0e0e0; color: #9e9e9e; 
                        border: 1px solid #bdbdbd; border-radius: 8px; font-weight: bold; font-size: 14px;
                    }
                """)
            else:
                # 有効: 現金とキャッシュレスで色分け
                color = "#4caf50" if pm['is_cash'] else "#2196f3" # 緑 vs 青
                btn = StyledButton(pm['name'], color)
                btn.clicked.connect(lambda _, m=pm: self._add_payment(m))
            
            btn.setFixedSize(130, 80)
            grid.addWidget(btn, row, col)
            
            col += 1
            if col > 2: # 3列で折り返し
                col = 0
                row += 1

        right_layout.addLayout(grid)
        right_layout.addStretch() # 下に詰める
        
        # スクロールエリアに入れる (ボタンが増えても大丈夫なように)
        scroll = QScrollArea()
        scroll.setWidget(right_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        body.addWidget(scroll, stretch=7)
        layout.addLayout(body)

        # 3. フッター：完了ボタン
        self.btn_finish = QPushButton("決 済 完 了")
        self.btn_finish.setFixedHeight(70)
        self.btn_finish.clicked.connect(self.accept)
        layout.addWidget(self.btn_finish)

    def _create_line(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def _add_payment(self, method : dict) -> None:
        remaining = self.total_amount - sum(p['amount'] for p in self.current_payments)
        if remaining <= 0:
            return

        # 現金の場合は入力ダイアログ、キャッシュレスは即時満額
        if method['is_cash']:
            val, ok = QInputDialog.getInt(self, method['name'], "金額:", value=remaining, minValue=1, maxValue=9999999)
            if ok and val > 0:
                self.current_payments.append({"name": method['name'], "amount": val})
                self._update_ui()
        else:
            # キャッシュレスは残額ぴったりで追加
            self.current_payments.append({"name": method['name'], "amount": remaining})
            self._update_ui()

    def _undo_payment(self) -> None:
        if self.current_payments:
            self.current_payments.pop()
            self._update_ui()

    def _update_ui(self) -> None:
        paid = sum(p['amount'] for p in self.current_payments)
        remaining = self.total_amount - paid
        
        # リスト更新
        self.payment_list.clear()
        for p in self.current_payments:
            self.payment_list.addItem(f"{p['name']}: ¥{p['amount']:,}")

        # 残高表示とボタン制御
        if remaining > 0:
            self.lbl_remaining.setText(f"残り\n¥{remaining:,}")
            self.lbl_remaining.setStyleSheet("color: #d32f2f; font-size: 32px; font-weight: bold;")
            self.btn_finish.setEnabled(False)
            self.btn_finish.setText("未完了 (残高あり)")
            self.btn_finish.setStyleSheet("background-color: #ccc; color: #666; font-size: 20px; font-weight: bold; border-radius: 8px;")
        else:
            change = abs(remaining)
            self.lbl_remaining.setText(f"お釣り\n¥{change:,}")
            self.lbl_remaining.setStyleSheet("color: #2196f3; font-size: 32px; font-weight: bold;")
            self.btn_finish.setEnabled(True)
            self.btn_finish.setText("決 済 完 了 (Enter)")
            self.btn_finish.setStyleSheet("background-color: #ff5722; color: white; font-size: 24px; font-weight: bold; border-radius: 8px;")
            self.btn_finish.setFocus()

    def get_result(self) -> tuple[list[tuple[str, int]], int]:
        paid = sum(p['amount'] for p in self.current_payments)
        change = paid - self.total_amount
        # タプルのリストに変換して返す
        return [(p['name'], p['amount']) for p in self.current_payments], change