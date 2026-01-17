# 商品データの読み込みを担当します。
from typing import List
from app.repositories.base_repo import BaseRepository
from app.models.product import Product

class ProductRepository(BaseRepository):
    
    def fetch_active_products(self) -> List[Product]:
        """有効な商品をカテゴリ・表示順で取得し、Productオブジェクトのリストで返す"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 辞書型ではなく、クラスのインスタンスを作るためのデータを取得
        cursor.execute("""
            SELECT id, name, price, category, color, note, display_order 
            FROM products 
            WHERE is_active=1 
            ORDER BY category DESC, display_order ASC
        """)
        rows = cursor.fetchall()
        conn.close()
        
        products = []
        for r in rows:
            # 取得したデータを Product クラスに流し込む
            p = Product(
                id=r[0], name=r[1], price=r[2], category=r[3], 
                color=r[4], note=r[5], display_order=r[6]
            )
            products.append(p)
            
        return products