from typing import Optional
from PySide6.QtWidgets import QPushButton, QWidget
from PySide6.QtCore import Qt
from app.utils.style import StyleGenerator
from app.models.product import Product
from app.models.customer import Customer

class StyledButton(QPushButton):
    """
    スタイル適用済みボタンの基底クラス
    フォーカスを持たない設定などを共通化
    """
    def __init__(self, text: str, color: str = "#e0e0e0", parent: Optional[QWidget] = None) -> None:
        """
        Args:
            text (str): ボタンのラベルテキスト
            color (str): 背景色コード (Hex)
            parent (Optional[QWidget]): 親ウィジェット
        """
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.NoFocus) # クリック後に枠を残さない
        self.apply_style(color)

    def apply_style(self, color: str) -> None:
        """スタイルシートを適用する"""
        self.setStyleSheet(StyleGenerator.create_button_style(color))

class ProductButton(StyledButton):
    """
    商品用ボタン
    Productモデルを保持し、クリック時に参照できるようにする
    """
    def __init__(self, product: Product, parent: Optional[QWidget] = None) -> None:
        """
        Args:
            product (Product): 商品データモデル
            parent (Optional[QWidget]): 親ウィジェット
        """
        # ボタンのラベルを作成 (名前 + 改行 + 価格)
        label = f"{product.name}\n{product.display_price}"
        
        # 親クラスの初期化 (色は商品データから取得)
        super().__init__(label, product.color, parent)
        
        self.setFixedSize(130, 90)
        
        # データを保持 (型ヒント付き)
        self.product: Product = product 

class CustomerButton(StyledButton):
    """
    客層用ボタン
    Customerモデルを保持し、選択状態(Checkable)を持つ
    """
    def __init__(self, customer: Customer, parent: Optional[QWidget] = None) -> None:
        """
        Args:
            customer (Customer): 客層データモデル
            parent (Optional[QWidget]): 親ウィジェット
        """
        # 親クラスの初期化
        super().__init__(customer.label, customer.color, parent)
        
        self.setFixedSize(130, 60)
        self.setCheckable(True) # 選択状態を持てるようにする
        
        # データを保持 (型ヒント付き)
        self.customer: Customer = customer