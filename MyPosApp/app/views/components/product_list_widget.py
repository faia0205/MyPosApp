from typing import List, Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QScrollArea, 
                               QGridLayout, QLabel)
from PySide6.QtCore import Qt

from app.services.cart_service import CartService
from app.services.product_service import ProductService # ★追加
from app.views.components.custom_buttons import ProductButton
from app.utils.style import StyleGenerator
from app.models.product import Product

class ProductListWidget(QWidget):
    """カテゴリ別商品タブを表示するウィジェット"""

    def __init__(self, cart_service: CartService, product_service: ProductService, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service
        self.product_service = product_service # ★追加: RepoではなくServiceを受け取る
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        # (変更なし)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(StyleGenerator.create_tab_style())
        layout.addWidget(self.tabs)

    def refresh_data(self):
        """Serviceから商品を再取得して描画"""
        self.tabs.clear()
        
        # ★変更: Service経由で取得
        products: List[Product] = self.product_service.get_all_products()
        
        # (以下、描画ロジックは変更なし)
        categorized: Dict[str, List[Product]] = {}
        cat_totals: Dict[str, int] = {}

        for p in products:
            cat = p.category or "その他"
            if cat not in categorized:
                categorized[cat] = []
                cat_totals[cat] = 0
            categorized[cat].append(p)
            if p.is_active:
                cat_totals[cat] += p.price

        sorted_categories = sorted(cat_totals.keys(), key=lambda x: cat_totals[x], reverse=True)

        for cat in sorted_categories:
            items = categorized[cat]
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("background-color: #424242;")
            
            container = QWidget()
            container.setStyleSheet("background-color: #424242;")
            grid = QGridLayout(container)
            grid.setSpacing(10)

            for i, p in enumerate(items):
                btn = ProductButton(p)
                if not p.is_active:
                    btn.setEnabled(False)
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #616161; color: #9e9e9e;
                            border: 1px solid #757575; border-radius: 8px;
                        }
                    """)
                    btn.setText(f"{p.name}\n(停止中)")
                else:
                    btn.clicked.connect(lambda _, x=p: self.cart_service.add_product(x))
                
                grid.addWidget(btn, i//3, i%3)
            
            grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            scroll.setWidget(container)
            self.tabs.addTab(scroll, cat)