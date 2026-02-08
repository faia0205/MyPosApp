from typing import List, Tuple, Dict
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QListWidget, QGridLayout, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from app.models.payment_method import PaymentMethod
# ★ Logicクラスのインポート
from app.logic.payment_session import PaymentSession

class PaymentDialog(QDialog):
    """
    決済画面 (キーボード操作特化版)
    UIレイアウトは変更せず、ロジックのみPaymentSessionに移譲
    """
    def __init__(self, total_amount: int, payment_methods: list[PaymentMethod], parent=None):
        super().__init__(parent)
        self.setWindowTitle("お会計")
        self.resize(900, 550)
        self.setStyleSheet("background-color: #2b2b2b; color: white;")

        # ★ 状態管理を Session に委譲
        self.session = PaymentSession(total_amount)
        
        self.payment_methods = payment_methods
        
        # UI制御用の状態はViewに残す
        self.selected_method = None
        self.input_buffer = ""
        self.is_initial_input = False

        # 初期選択（現金があればデフォルト）
        cash_opts = [m for m in self.payment_methods if m.is_cash]
        if cash_opts:
            self.selected_method = cash_opts[0]
        elif self.payment_methods:
            self.selected_method = self.payment_methods[0]

        self._init_ui() # 既存のUI構築メソッドを呼ぶ
        self._update_ui()
        self._set_buffer_to_remaining()

    # ==========================================================
    # UI構築部分 (変更なし)
    # ==========================================================
    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        # --- 左パネル: 請求・内訳・残高 ---
        left_panel = QVBoxLayout()

        # 請求額
        lbl_title = QLabel("ご請求額")
        lbl_title.setStyleSheet("font-size: 18px; color: #ccc;")
        left_panel.addWidget(lbl_title)

        self.lbl_total = QLabel(f"¥{self.session.total_amount:,}") # sessionから取得
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

        # 削除ボタン
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

        self.lbl_status_amount = QLabel(f"¥{self.session.total_amount:,}")
        self.lbl_status_amount.setStyleSheet("font-size: 42px; font-weight: bold; color: #ff8a80;")
        self.lbl_status_amount.setAlignment(Qt.AlignRight)
        left_panel.addWidget(self.lbl_status_amount)

        main_layout.addLayout(left_panel, 40)

        # --- 右パネル: 入力表示・決済選択・完了 ---
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
            is_active = method.is_active
            name = method.name
            
            if not is_active:
                btn = QPushButton(f"{name}\n(停止中)")
                btn.setEnabled(False)
                btn.setStyleSheet("background-color: #555; color: #888; border-radius: 6px;")
            else:
                base_color = "#2e7d32" if method.is_cash else "#1565c0"
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
        
        self.btn_enter = QPushButton("支払追加 (Enter)")
        self.btn_enter.setFixedHeight(90)
        self.btn_enter.setFocusPolicy(Qt.NoFocus)
        self.btn_enter.setStyleSheet("""
            QPushButton { background-color: #0288d1; color: white; font-size: 20px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background-color: #039be5; }
        """)
        self.btn_enter.clicked.connect(self._add_payment)
        action_layout.addWidget(self.btn_enter, 1)

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

    # ==========================================================
    # イベントハンドラ & ロジック (ここを修正)
    # ==========================================================
    
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
            # ★ Sessionの状態を確認
            if not self.session.is_complete():
                self._add_payment()
            else:
                if self.btn_finish.isEnabled():
                    self.accept()
        
        # ESC -> 戻る
        elif key == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def _select_method(self, method):
        self.selected_method = method
        self._update_method_buttons()
        self._set_buffer_to_remaining()

    def _set_buffer_to_remaining(self):
        remain = self.session.get_remaining()
        if remain != 0:
            self.input_buffer = str(abs(remain))
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
        if len(self.input_buffer + text) > 10: return
        
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
        """支払いの追加 (Logicへ委譲)"""
        if not self.selected_method: return

        amount_val = int(self.input_buffer) if self.input_buffer else 0
        if amount_val <= 0: return

        # ★ ロジック呼び出し
        success = self.session.add_payment(
            method_name=self.selected_method.name, 
            amount=amount_val,
            is_cash=self.selected_method.is_cash
        )

        if success:
            self.input_buffer = ""
            self.is_initial_input = False
            self._update_input_display()
            self._update_ui()

    def _remove_selected_row(self):
        row = self.payment_list_widget.currentRow()
        if row >= 0:
            # ★ ロジック呼び出し
            self.session.remove_payment(row)
            self._update_ui()

    def _update_ui(self):
        """画面表示の更新 (Sessionの状態を反映)"""
        self.payment_list_widget.clear()
        
        # ★ Sessionからリスト取得
        for p in self.session.payments:
            self.payment_list_widget.addItem(f"{p['name']}: ¥{p['amount']:,}")

        # ★ Sessionから計算結果取得
        remaining = self.session.get_remaining()
        change = self.session.get_change()

        if remaining != 0:
            self.lbl_status_title.setText("不足金額" if remaining > 0 else "要返金額")
            self.lbl_status_title.setStyleSheet("font-size: 18px; color: #ff8a80;")
            
            self.lbl_status_amount.setText(f"¥{remaining:,}")
            self.lbl_status_amount.setStyleSheet("font-size: 42px; font-weight: bold; color: #ff8a80;")

            self.btn_finish.setEnabled(False)
            self.btn_finish.setText("金額不足" if remaining > 0 else "返金未了")
            self.btn_finish.setStyleSheet("background-color: #555; color: #aaa; font-size: 24px; font-weight: bold; border-radius: 10px;")

            self.btn_enter.setEnabled(True)
            self.btn_enter.setText("支払追加 (Enter)")
        else:
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
            
            self.btn_enter.setText("支払追加")
            self.btn_enter.setEnabled(True)

        self._update_method_buttons()

    def _update_method_buttons(self):
        for btn, method in self.method_btn_group:
            base_color = btn.property("base_color")
            
            if self.selected_method and method.name == self.selected_method.name:
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
        """MainWindowに結果を返すための互換メソッド"""
        # SessionのデータをTuple形式に変換して返す
        result_list = [(p['name'], p['amount']) for p in self.session.payments]
        change = self.session.get_change()
        return result_list, change