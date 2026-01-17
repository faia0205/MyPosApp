# ボタンの見た目や挙動（フォーカスを持たない等）を定義する再利用可能な部品です。
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import Qt
from app.utils.style import StyleGenerator

class StyledButton(QPushButton):
    """スタイル適用済みボタン（フォーカスを持たない設定）"""
    def __init__(self, text, color="#e0e0e0", parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.NoFocus) # クリック後に枠を残さない
        self.apply_style(color)

    def apply_style(self, color):
        self.setStyleSheet(StyleGenerator.create_button_style(color))

class ProductButton(StyledButton):
    """商品用ボタン"""
    def __init__(self, product, parent=None):
        label = f"{product.name}\n{product.display_price}"
        super().__init__(label, product.color, parent)
        self.setFixedSize(130, 90)
        self.product = product # データを保持

class CustomerButton(StyledButton):
    """客層用ボタン"""
    def __init__(self, customer, parent=None):
        super().__init__(customer.label, customer.color, parent)
        self.setFixedSize(130, 60)
        self.setCheckable(True) # 選択状態を持てるようにする
        self.customer = customer