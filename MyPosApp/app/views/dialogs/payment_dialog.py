from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QListWidget, QPushButton, QGridLayout, QInputDialog, QFrame)
from PySide6.QtCore import Qt
from app.views.components.custom_buttons import StyledButton

class PaymentDialog(QDialog):
    def __init__(self, total_amount: int, payment_methods: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("決済選択")
        self.resize(700, 500)
        
        self.total_amount = total_amount
        self.payment_methods = payment_methods
        self.current_payments = [] # 積み上げリスト

        self._init_ui()
        self._update_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ヘッダー (請求額・残り)
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

        # ボディ
        body = QHBoxLayout()
        
        # 左：支払い済みリスト
        left = QVBoxLayout()
        left.addWidget(QLabel("【内訳】"))
        self.payment_list = QListWidget()
        self.payment_list.setStyleSheet("font-size: 16px;")
        left.addWidget(self.payment_list)
        
        btn_undo = QPushButton("1つ取り消す")
        btn_undo.setFocusPolicy(Qt.NoFocus)
        btn_undo.clicked.connect(self._undo_payment)
        left.addWidget(btn_undo)
        body.addLayout(left, stretch=4)

        # 右：決済ボタン
        right = QVBoxLayout()
        right.addWidget(QLabel("【決済方法】"))
        grid = QGridLayout()
        for i, pm in enumerate(self.payment_methods):
            color = "#4caf50" if pm['is_cash'] else "#2196f3"
            btn = StyledButton(pm['name'], color)
            btn.setFixedSize(140, 80)
            # ラムダで変数をキャプチャ
            btn.clicked.connect(lambda _, m=pm: self._add_payment(m))
            grid.addWidget(btn, i//2, i%2)
        right.addLayout(grid)
        right.addStretch()
        body.addLayout(right, stretch=6)
        
        layout.addLayout(body)

        # フッター：完了ボタン
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
        if remaining <= 0: return

        val, ok = QInputDialog.getInt(self, method['name'], "金額:", value=remaining, minValue=1, maxValue=999999)
        if ok and val > 0:
            self.current_payments.append({"name": method['name'], "amount": val})
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