from typing import List, Tuple, Dict
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QGridLayout, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

class PaymentDialog(QDialog):
    """
    決済画面 (キーボード操作特化版)
    - 画面上のテンキーを廃止
    - 全ボタンを NoFocus に設定
    - Enterキーの挙動に合わせてボタン表記を動的に変更
    """
    def __init__(self, total_amount: int, payment_methods: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("お会計")
        self.resize(900, 550)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        
        self.total_amount = total_amount
        self.payment_methods = payment_methods
        
        self.current_payments: List[Dict] = []
        self.selected_method = None
        self.input_buffer = ""
        self.is_initial_input = False
        
        # 初期選択（現金があればデフォルト）
        cash_opts = [m for m in self.payment_methods if m.get('is_cash')]
        if cash_opts:
            self.selected_method = cash_opts[0]
        elif self.payment_methods:
            self.selected_method = self.payment_methods[0]

        self._init_ui()
        self._update_ui()
        self._set_buffer_to_remaining()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # ==========================================
        # 左パネル: 請求・内訳・残高
        # ==========================================
        left_panel = QVBoxLayout()
        
        # 請求額
        lbl_title = QLabel("ご請求額")
        lbl_title.setStyleSheet("font-size: 18px; color: #ccc;")
        left_panel.addWidget(lbl_title)
        
        self.lbl_total = QLabel(f"¥{self.total_amount:,}")
        self.lbl_total.setStyleSheet("font-size: 48px; font-weight: bold; color: white;")
        self.lbl_total.setAlignment(Qt.AlignRight)
        left_panel.addWidget(self.lbl_total)
        
        left_panel.addSpacing(15)

        # 内訳リスト
        left_panel.addWidget(QLabel("【お支払い内訳】"))
        self.payment_list_widget = QListWidget()
        self.payment_list_widget.setFocusPolicy(Qt.NoFocus)
        self.payment_list_widget.setStyleSheet("""
            QListWidget { font-size: 18px; background-color: #333; border: 1px solid #555; color: white; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #444; }
            QListWidget::item:selected { background-color: #1976d2; color: white; }
        """)
        left_panel.addWidget(self.payment_list_widget)
        
        # 削除ボタン (★修正: (Del)表記を削除)
        btn_remove = QPushButton("選択した支払を削除")
        btn_remove.setFocusPolicy(Qt.NoFocus)
        btn_remove.setStyleSheet("background-color: #d32f2f; color: white; padding: 10px; border-radius: 4px;")
        btn_remove.clicked.connect(self._remove_selected_row)
        left_panel.addWidget(btn_remove)

        left_panel.addSpacing(15)

        # 不足/お釣り表示
        self.lbl_status_title = QLabel("不足金額")
        self.lbl_status_title.setStyleSheet("font-size: 18px; color: #ff8a80;")
        left_panel.addWidget(self.lbl_status_title)
        
        self.lbl_status_amount = QLabel(f"¥{self.total_amount:,}")
        self.lbl_status_amount.setStyleSheet("font-size: 42px; font-weight: bold; color: #ff8a80;")
        self.lbl_status_amount.setAlignment(Qt.AlignRight)
        left_panel.addWidget(self.lbl_status_amount)

        main_layout.addLayout(left_panel, 40)

        # ==========================================
        # 右パネル: 入力表示・決済選択・完了
        # ==========================================
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(20, 0, 0, 0)
        
        # 1. 入力値ディスプレイ
        right_panel.addWidget(QLabel("現在の入力金額:"))
        self.lbl_input = QLabel("0")
        self.lbl_input.setFixedHeight(80)
        self.lbl_input.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_input.setStyleSheet("""
            background-color: white; color: #333; 
            font-size: 48px; font-weight: bold; 
            padding-right: 20px; border-radius: 8px; border: 3px solid #0288d1;
        """)
        right_panel.addWidget(self.lbl_input)
        
        right_panel.addSpacing(20)

        # 2. 決済方法ボタン
        right_panel.addWidget(QLabel("【決済方法を選択】"))
        self.method_btn_group = []
        m_grid = QGridLayout()
        m_grid.setSpacing(15)
        
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
                btn.setFocusPolicy(Qt.NoFocus)
                btn.setProperty("base_color", base_color) 
                btn.clicked.connect(lambda _, m=method: self._select_method(m))
                
            btn.setFixedSize(140, 80)
            m_grid.addWidget(btn, r, c)
            
            if is_active:
                self.method_btn_group.append((btn, method))

            c += 1
            if c > 2:
                c = 0
                r += 1
        
        right_panel.addLayout(m_grid)
        right_panel.addStretch()

        # 3. アクションボタンエリア
        action_layout = QHBoxLayout()
        
        # 決定(追加)ボタン
        self.btn_enter = QPushButton("支払追加 (Enter)")
        self.btn_enter.setFixedHeight(90)
        self.btn_enter.setFocusPolicy(Qt.NoFocus)
        self.btn_enter.setStyleSheet("""
            QPushButton { background-color: #0288d1; color: white; font-size: 20px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #039be5; }
        """)
        self.btn_enter.clicked.connect(self._add_payment)
        action_layout.addWidget(self.btn_enter, 1)

        # 会計完了ボタン
        self.btn_finish = QPushButton("会計完了")
        self.btn_finish.setFixedHeight(90)
        self.btn_finish.setFocusPolicy(Qt.NoFocus)
        self.btn_finish.setEnabled(False)
        self.btn_finish.clicked.connect(self.accept)
        action_layout.addWidget(self.btn_finish, 2)
        
        right_panel.addLayout(action_layout)
        
        # 戻るボタン
        btn_cancel = QPushButton("戻る (Esc)")
        btn_cancel.setFocusPolicy(Qt.NoFocus)
        btn_cancel.setStyleSheet("background-color: #444; color: #ccc; padding: 10px; margin-top: 10px;")
        btn_cancel.clicked.connect(self.reject)
        right_panel.addWidget(btn_cancel)

        main_layout.addLayout(right_panel, 60)

    # ==========================================
    # キーボードイベント
    # ==========================================
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        text = event.text()

        # 数字キー
        if text.isdigit():
            self._on_numpad(text)
        
        # BackSpace / Delete -> 全消去
        elif key in (Qt.Key_Backspace, Qt.Key_Delete):
            self._clear_input()
        
        # Enter / Return -> 状態に応じて分岐
        elif key in (Qt.Key_Enter, Qt.Key_Return):
            paid = self._get_paid_total()
            if paid < self.total_amount:
                # まだ足りない -> 入力値を支払に追加
                self._add_payment()
            else:
                # 足りている -> 会計完了
                if self.btn_finish.isEnabled():
                    self.accept()
        
        # ESC -> 戻る
        elif key == Qt.Key_Escape:
            self.reject()
            
        else:
            super().keyPressEvent(event)

    # ==========================================
    # ロジック
    # ==========================================

    def _select_method(self, method):
        self.selected_method = method
        self._update_method_buttons()
        self._set_buffer_to_remaining()

    def _set_buffer_to_remaining(self):
        paid = self._get_paid_total()
        remain = self.total_amount - paid
        if remain > 0:
            self.input_buffer = str(remain)
            self.is_initial_input = True 
        else:
            self.input_buffer = ""
            self.is_initial_input = False
        self._update_input_display()

    def _on_numpad(self, text):
        if self.is_initial_input:
            self.input_buffer = ""
            self.is_initial_input = False

        if self.input_buffer == "0" and text == "0": return
        if self.input_buffer == "0" and text != "00": self.input_buffer = ""
        if len(self.input_buffer + text) > 8: return
        
        self.input_buffer += text
        self._update_input_display()

    def _clear_input(self):
        self.input_buffer = ""
        self.is_initial_input = False
        self._update_input_display()

    def _update_input_display(self):
        val = int(self.input_buffer) if self.input_buffer else 0
        self.lbl_input.setText(f"¥{val:,}")

    def _add_payment(self):
        if not self.selected_method: return
        
        amount_val = int(self.input_buffer) if self.input_buffer else 0
        if amount_val <= 0: return 

        if not self.selected_method.get('is_cash', False):
            paid_so_far = self._get_paid_total()
            remaining = self.total_amount - paid_so_far
            
            if amount_val > remaining:
                if remaining <= 0: return 
                amount_val = remaining

        method_name = self.selected_method['name']

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
        self.is_initial_input = False
        self._update_input_display()
        self._update_ui()

    def _remove_selected_row(self):
        row = self.payment_list_widget.currentRow()
        if row >= 0:
            self.current_payments.pop(row)
            self._update_ui()

    def _get_paid_total(self):
        return sum(p['amount'] for p in self.current_payments)

    def _update_ui(self):
        """画面表示の更新"""
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
            self.btn_enter.setEnabled(True)
            
            # ★修正: 不足時は「支払追加 (Enter)」
            self.btn_enter.setText("支払追加 (Enter)")
            
        else:
            change = abs(diff)
            title = "お釣り" if change > 0 else "過不足なし"
            self.lbl_status_title.setText(title)
            self.lbl_status_title.setStyleSheet("font-size: 18px; color: #69f0ae;")
            self.lbl_status_amount.setText(f"¥{change:,}")
            self.lbl_status_amount.setStyleSheet("font-size: 48px; font-weight: bold; color: #69f0ae;")
            
            self.btn_finish.setEnabled(True)
            self.btn_finish.setText("会計完了 (Enter)")
            self.btn_finish.setStyleSheet("""
                QPushButton { background-color: #ff9800; color: black; font-size: 32px; font-weight: bold; border-radius: 10px; }
                QPushButton:hover { background-color: #ffb74d; }
            """)
            
            # ★修正: 完了時は「支払追加」から (Enter) を消す
            self.btn_enter.setText("支払追加")
            # 完了可能なら追加ボタンを少し目立たなくする
            self.btn_enter.setEnabled(True) 

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