from typing import List, Dict
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QScrollArea, 
                               QGridLayout, QLabel)
from PySide6.QtCore import Qt
from app.services.cart_service import CartService
from app.repositories.product_repo import ProductRepository
from app.views.components.custom_buttons import ProductButton
from app.utils.style import StyleGenerator
from app.models.product import Product

class ProductListWidget(QWidget):
    """カテゴリ別商品タブを表示するウィジェット"""

    def __init__(self, cart_service: CartService, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service
        self.repo = ProductRepository()
        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(StyleGenerator.create_tab_style())
        layout.addWidget(self.tabs)

    def refresh_data(self):
        """DBから商品を再取得して描画"""
        self.tabs.clear()
        
        # ★修正1: 有効な商品だけでなく、全ての商品を取得する
        products: List[Product] = self.repo.fetch_all_as_models() 

        # カテゴリごとのグルーピング
        categorized: Dict[str, List[Product]] = {}
        cat_totals: Dict[str, int] = {}

        for p in products:
            cat = p.category or "その他"
            if cat not in categorized: 
                categorized[cat] = []
                cat_totals[cat] = 0
            categorized[cat].append(p)
            
            # 並び順の目安として有効な商品の価格合計を使う（既存ロジック踏襲）
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
                
                # ★修正2: 無効な商品はグレーアウト表示にし、クリック不可にはしない（または必要ならsetEnabled(False)）
                if not p.is_active:
                    btn.setEnabled(False) # クリック不可にする
                    # グレーアウト用のスタイル適用
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #616161; color: #9e9e9e; 
                            border: 1px solid #757575; border-radius: 8px;
                        }
                    """)
                    btn.setText(f"{p.name}\n(停止中)")
                else:
                    # 有効な商品はクリックでカート追加
                    btn.clicked.connect(lambda _, x=p: self.cart_service.add_product(x))
                
                grid.addWidget(btn, i//3, i%3)
            
            grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            scroll.setWidget(container)
            self.tabs.addTab(scroll, cat)