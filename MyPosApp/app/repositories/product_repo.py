from typing import List, Optional, Dict
from app.repositories.base_repo import BaseRepository
from app.models.product import Product

class ProductRepository(BaseRepository):
    """
    商品データのCRUD操作を担当するリポジトリ
    """

    def fetch_active_products(self) -> List[Product]:
        """販売画面用: 有効(is_active=1)な商品のみを取得し、display_order順に返す"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, price, category, color, note, display_order, is_active
                FROM products 
                WHERE is_active = 1 
                ORDER BY display_order
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def fetch_all_as_models(self) -> List[Product]:
        """設定画面・JSON出力用: 全商品をProductモデルのリストとして取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, price, category, color, note, display_order, is_active
                FROM products 
                ORDER BY display_order
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def find_id_by_name(self, name: str) -> Optional[int]:
        """名前からIDを検索（同期用）"""
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
            row = cursor.fetchone()
            return row[0] if row else None

    def get_product_by_id(self, pid: int) -> Optional[Product]:
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, price, category, color, note, display_order, is_active 
                FROM products WHERE id=?
            """, (pid,))
            row = cursor.fetchone()
            return self._map_to_model(row) if row else None

    def add_product(self, product: Product) -> bool:
        """新規商品の追加 (オブジェクト受け取りに変更)"""
        try:
            with self.transaction() as (conn, cursor):
                # 現在の最大 display_order を取得
                cursor.execute("SELECT MAX(display_order) FROM products")
                result = cursor.fetchone()
                max_order = result[0] if result[0] is not None else 0
                
                cursor.execute("""
                    INSERT INTO products (name, price, category, color, note, display_order, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (product.name, product.price, product.category, product.color, 
                      product.note, max_order + 1, int(product.is_active)))
            # コンテキストを抜ける際に自動commit/closeされます
            return True
        except Exception as e:
            print(f"Error adding product: {e}")
            return False

    def update_product(self, product: Product) -> bool:
        """既存商品の更新 (オブジェクト受け取りに変更)"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("""
                    UPDATE products 
                    SET name=?, price=?, category=?, color=?, note=?, is_active=?
                    WHERE id=?
                """, (product.name, product.price, product.category, product.color, 
                      product.note, int(product.is_active), product.id))
            return True
        except Exception as e:
            print(f"Error updating product: {e}")
            return False

    def delete_product(self, product_id: int) -> bool:
        """完全削除"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
            return True
        except Exception as e:
            print(f"Error deleting product: {e}")
            return False

    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        """表示順の一括更新"""
        try:
            with self.transaction() as (conn, cursor):
                for pid, order in order_map.items():
                    cursor.execute("UPDATE products SET display_order=? WHERE id=?", (order, pid))
            return True
        except Exception as e:
            print(f"Error updating orders: {e}")
            return False

    def _map_to_model(self, row) -> Product:
        """DBの行データをProductモデルに変換"""
        # rowはタプルまたはsqlite3.Row
        if row is None: return None
        # インデックスアクセス前提 (SELECTの順序に依存)
        return Product(
            id=row[0],
            name=row[1],
            price=row[2],
            category=row[3],
            color=row[4],
            note=row[5],
            display_order=row[6],
            is_active=bool(row[7])
        )