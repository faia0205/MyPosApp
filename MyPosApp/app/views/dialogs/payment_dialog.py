from typing import List, Tuple, Dict
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QGridLayout, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

# もし StyledButton が使えない環境でも動くように標準ボタンで実装
try:
    from app.views.components.custom_buttons import StyledButton
except ImportError:
    class StyledButton(QPushButton):
        def __init__(self, text, color):
            super().__init__(text)
            self.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold; border-radius: 5px;")

class PaymentDialog(QDialog):
    """
    決済画面
    - 複数の支払方法の併用に対応
    - 同一支払方法の合算に対応
    - テンキー/物理キーボードによる金額入力
    - キャッシュレス決済時の過剰入金防止
    """
    def __init__(self, total_amount: int, payment_methods: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("お会計")
        self.resize(950, 600)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        self.total_amount = total_amount
        self.payment_methods = payment_methods
        
        # 入力済み支払いリスト
        self.current_payments: List[Dict] = []
        
        # 選択中の決済方法
        self.selected_method = None
        
        # テンキー入力バッファ
        self.input_buffer = ""
        
        # 初期選択（現金があればデフォルト）
        cash_opts = [m for m in self.payment_methods if m.get('is_cash')]
        if cash_opts:
            self.selected_method = cash_opts[0]
        elif self.payment_methods:
            self.selected_method = self.payment_methods[0]

        self._init_ui()
        self._update_ui()
        
        # 初期状態で入力バッファに残額をセット
        self._set_buffer_to_remaining()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # --- 左パネル: 集計・リスト ---
        left_panel = QVBoxLayout()
        
        lbl_title = QLabel("ご請求額")
        lbl_title.setStyleSheet("font-size: 18px; color: #ccc;")
        left_panel.addWidget(lbl_title)
        
        self.lbl_total = QLabel(f"¥{self.total_amount:,}")
        self.lbl_total.setStyleSheet("font-size: 48px; font-weight: bold; color: white;")
        self.lbl_total.setAlignment(Qt.AlignRight)
        left_panel.addWidget(self.lbl_total)
        
        left_panel.addSpacing(15)

        left_panel.addWidget(QLabel("【お支払い内訳】"))
        self.payment_list_widget = QListWidget()
        self.payment_list_widget.setStyleSheet("""
            QListWidget { font-size: 18px; background-color: #333; border: 1px solid #555; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #444; }
        """)
        left_panel.addWidget(self.payment_list_widget)
        
        btn_remove = QPushButton("選択した支払を削除")
        btn_remove.setStyleSheet("background-color: #d32f2f; color: white; padding: 10px; border-radius: 4px;")
        btn_remove.clicked.connect(self._remove_selected_row)
        left_panel.addWidget(btn_remove)

        left_panel.addSpacing(15)

        self.lbl_status_title = QLabel("不足金額")
        self.lbl_status_title.setStyleSheet("font-size: 18px; color: #ff8a80;")
        left_panel.addWidget(self.lbl_status_title)
        
        self.lbl_status_amount = QLabel(f"¥{self.total_amount:,}")
        self.lbl_status_amount.setStyleSheet("font-size: 42px; font-weight: bold; color: #ff8a80;")
        self.lbl_status_amount.setAlignment(Qt.AlignRight)
        left_panel.addWidget(self.lbl_status_amount)

        main_layout.addLayout(left_panel, 35)

        # --- 中央パネル: テンキー ---
        center_panel = QVBoxLayout()
        center_panel.setContentsMargins(10, 0, 10, 0)

        self.lbl_input = QLabel("0")
        self.lbl_input.setFixedHeight(70)
        self.lbl_input.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_input.setStyleSheet("""
            background-color: white; color: #333; 
            font-size: 36px; font-weight: bold; 
            padding-right: 15px; border-radius: 6px; border: 2px solid #0288d1;
        """)
        center_panel.addWidget(self.lbl_input)

        grid = QGridLayout()
        grid.setSpacing(8)
        keys = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('0', 3, 0), ('00', 3, 1), ('C', 3, 2),
        ]
        
        for text, r, c in keys:
            btn = QPushButton(text)
            btn.setFixedSize(70, 70)
            bg = "#424242"
            if text == 'C': 
                bg = "#c62828"
                btn.clicked.connect(self._clear_input)
            else:
                btn.clicked.connect(lambda _, t=text: self._on_numpad(t))

            btn.setStyleSheet(f"""
                QPushButton {{ background-color: {bg}; color: white; font-size: 24px; font-weight: bold; border-radius: 8px; }}
                QPushButton:pressed {{ background-color: #666; }}
            """)
            grid.addWidget(btn, r, c)
        
        center_panel.addLayout(grid)

        self.btn_enter = QPushButton("決定 (追加)")
        self.btn_enter.setFixedHeight(80)
        self.btn_enter.setStyleSheet("""
            QPushButton { background-color: #0288d1; color: white; font-size: 22px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #039be5; }
        """)
        self.btn_enter.clicked.connect(self._add_payment)
        center_panel.addWidget(self.btn_enter)

        main_layout.addLayout(center_panel, 30)

        # --- 右パネル: 決済選択 & 完了 ---
        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("【決済方法を選択】"))
        
        self.method_btn_group = []
        m_grid = QGridLayout()
        m_grid.setSpacing(10)
        
        r, c = 0, 0
        for method in self.payment_methods:
            is_active = method.get('is_active', True)
            name = method['name']
            
            if not is_active:
                btn = QPushButton(f"{name}\n(停止中)")
                btn.setEnabled(False)
                btn.setStyleSheet("background-color: #555; color: #888; border-radius: 6px;")
            else:
                base_color = "#2e7d32" if method.get('is_cash') else "#1565c0"
                btn = QPushButton(name)
                btn.setCheckable(True)
                btn.setProperty("base_color", base_color) 
                btn.clicked.connect(lambda _, m=method: self._select_method(m))
                
            btn.setFixedSize(110, 70)
            m_grid.addWidget(btn, r, c)
            
            if is_active:
                self.method_btn_group.append((btn, method))

            c += 1
            if c > 1:
                c = 0
                r += 1
        
        right_panel.addLayout(m_grid)
        right_panel.addStretch()

        self.btn_finish = QPushButton("会計完了")
        self.btn_finish.setFixedHeight(100)
        self.btn_finish.setEnabled(False)
        self.btn_finish.clicked.connect(self.accept)
        right_panel.addWidget(self.btn_finish)
        
        btn_cancel = QPushButton("戻る")
        btn_cancel.setStyleSheet("background-color: #444; color: #ccc; padding: 10px;")
        btn_cancel.clicked.connect(self.reject)
        right_panel.addWidget(btn_cancel)

        main_layout.addLayout(right_panel, 35)

    # --- キーボードイベント処理 ---
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        # 数字キー (0-9)
        if text.isdigit():
            self._on_numpad(text)
        # BackSpace / Delete
        elif key in (Qt.Key_Backspace, Qt.Key_Delete):
            self.input_buffer = self.input_buffer[:-1]
            self._update_input_display()
        # Enter / Return
        elif key in (Qt.Key_Enter, Qt.Key_Return):
            # 完了ボタンが有効かつフォーカスがある場合は完了処理へ
            if self.btn_finish.isEnabled() and self.btn_finish.hasFocus():
                self.accept()
            else:
                self._add_payment()
        # ESC
        elif key == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    # --- ロジック ---

    def _select_method(self, method):
        self.selected_method = method
        self._update_method_buttons()
        self._set_buffer_to_remaining()

    def _set_buffer_to_remaining(self):
        paid = self._get_paid_total()
        remain = self.total_amount - paid
        if remain > 0:
            self.input_buffer = str(remain)
        else:
            self.input_buffer = ""
        self._update_input_display()

    def _on_numpad(self, text):
        if self.input_buffer == "0" and text == "0": return
        if self.input_buffer == "0" and text != "00": self.input_buffer = ""
        if len(self.input_buffer + text) > 8: return
        
        self.input_buffer += text
        self._update_input_display()

    def _clear_input(self):
        self.input_buffer = ""
        self._update_input_display()

    def _update_input_display(self):
        val = int(self.input_buffer) if self.input_buffer else 0
        self.lbl_input.setText(f"¥{val:,}")

    def _add_payment(self):
        """「決定」ボタン: 現在の入力金額を追加"""
        if not self.selected_method: return
        
        amount_val = int(self.input_buffer) if self.input_buffer else 0
        if amount_val <= 0: return 

        # ★キャッシュレス過剰入力防止ロジック
        if not self.selected_method.get('is_cash', False):
            # 不足金額(支払うべき額)を計算
            paid_so_far = self._get_paid_total()
            remaining = self.total_amount - paid_so_far
            
            # 入力額が残りを超えていたら、残りの額に補正する
            if amount_val > remaining:
                # 既に払いすぎている(remaining < 0)場合は追加できない
                if remaining <= 0:
                    return 
                amount_val = remaining

        method_name = self.selected_method['name']

        # 合算チェック
        existing_index = -1
        for i, pay in enumerate(self.current_payments):
            if pay['name'] == method_name:
                existing_index = i
                break
        
        if existing_index >= 0:
            self.current_payments[existing_index]['amount'] += amount_val
        else:
            self.current_payments.append({
                'name': method_name,
                'amount': amount_val
            })

        self.input_buffer = ""
        self._update_input_display()
        self._update_ui()
        
        if self._get_paid_total() >= self.total_amount:
            self.btn_finish.setFocus()

    def _remove_selected_row(self):
        row = self.payment_list_widget.currentRow()
        if row >= 0:
            self.current_payments.pop(row)
            self._update_ui()

    def _get_paid_total(self):
        return sum(p['amount'] for p in self.current_payments)

    def _update_ui(self):
        self.payment_list_widget.clear()
        for p in self.current_payments:
            self.payment_list_widget.addItem(f"{p['name']}: ¥{p['amount']:,}")

        paid = self._get_paid_total()
        diff = self.total_amount - paid
        
        if diff > 0:
            self.lbl_status_title.setText("不足金額")
            self.lbl_status_title.setStyleSheet("font-size: 18px; color: #ff8a80;")
            self.lbl_status_amount.setText(f"¥{diff:,}")
            self.lbl_status_amount.setStyleSheet("font-size: 42px; font-weight: bold; color: #ff8a80;")
            
            self.btn_finish.setEnabled(False)
            self.btn_finish.setText("金額不足")
            self.btn_finish.setStyleSheet("background-color: #555; color: #aaa; font-size: 24px; font-weight: bold; border-radius: 10px;")
        else:
            change = abs(diff)
            title = "お釣り" if change > 0 else "過不足なし"
            self.lbl_status_title.setText(title)
            self.lbl_status_title.setStyleSheet("font-size: 18px; color: #69f0ae;")
            self.lbl_status_amount.setText(f"¥{change:,}")
            self.lbl_status_amount.setStyleSheet("font-size: 48px; font-weight: bold; color: #69f0ae;")
            
            self.btn_finish.setEnabled(True)
            self.btn_finish.setText("会計完了 ⏎")
            self.btn_finish.setStyleSheet("""
                QPushButton { background-color: #ff9800; color: black; font-size: 32px; font-weight: bold; border-radius: 10px; }
                QPushButton:hover { background-color: #ffb74d; }
            """)

        self._update_method_buttons()

    def _update_method_buttons(self):
        for btn, method in self.method_btn_group:
            base_color = btn.property("base_color")
            if self.selected_method and method['name'] == self.selected_method['name']:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    QPushButton {{ 
                        background-color: {base_color}; color: white; 
                        border: 3px solid #ffeb3b; border-radius: 6px; font-weight: bold; font-size: 14px;
                    }}
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(f"""
                    QPushButton {{ 
                        background-color: {base_color}; color: white; 
                        border: 1px solid #444; border-radius: 6px; font-size: 14px;
                        opacity: 0.8;
                    }}
                    QPushButton:hover {{ background-color: #ddd; color: black; }}
                """)

    def get_result(self) -> Tuple[List[Tuple[str, int]], int]:
        paid = self._get_paid_total()
        change = max(0, paid - self.total_amount)
        result_list = [(p['name'], p['amount']) for p in self.current_payments]
        return result_list, change