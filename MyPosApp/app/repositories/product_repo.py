from typing import List, Dict, Optional
import sqlite3
from app.repositories.base_repo import BaseRepository
from app.models.product import Product

class ProductRepository(BaseRepository):
    """
    商品データのCRUD操作を担当するリポジトリ
    """

    def fetch_active_products(self) -> List[Product]:
        """
        販売画面用: 有効(is_active=1)な商品のみを取得し、display_order順に返す
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price, category, color, note, display_order, is_active
            FROM products 
            WHERE is_active = 1 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append(Product(
                id=row[0],
                name=row[1],
                price=row[2],
                category=row[3],
                color=row[4],
                note=row[5],
                display_order=row[6],
                is_active=bool(row[7])
            ))
        return products

    def fetch_all_for_json(self) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # ★ id を追加しました
        cursor.execute("""
            SELECT id, name, price, category, color, display_order, is_active, note 
            FROM products 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def find_id_by_name(self, name: str) -> Optional[int]:
        """名前からIDを検索（同期用）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM products WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def fetch_all_as_models(self) -> List[Product]:
        """
        設定画面一覧表示用: 全商品をProductモデルのリストとして取得
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price, category, color, note, display_order, is_active
            FROM products 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append(Product(
                id=row[0],
                name=row[1],
                price=row[2],
                category=row[3],
                color=row[4],
                note=row[5],
                display_order=row[6],
                is_active=bool(row[7])
            ))
        return products

    def add_product(self, name: str, price: int, category: str, color: str = "#ffcc80", note: str = "") -> bool:
        """
        新規商品の追加
        display_orderは現在の最大値+1を自動設定します。
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 現在の最大 display_order を取得
            cursor.execute("SELECT MAX(display_order) FROM products")
            result = cursor.fetchone()
            max_order = result[0] if result[0] is not None else 0
            
            cursor.execute("""
                INSERT INTO products (name, price, category, color, note, display_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (name, price, category, color, note, max_order + 1))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding product: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_product(self, product_id: int, name: str, price: int, category: str, 
                       color: str, note: str, is_active: bool) -> bool:
        """
        既存商品の更新
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE products 
                SET name=?, price=?, category=?, color=?, note=?, is_active=?
                WHERE id=?
            """, (name, price, category, color, note, int(is_active), product_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating product: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_product(self, product_id: int) -> bool:
        """
        商品の完全削除（注意: 過去の取引履歴との整合性が崩れる可能性があります）
        基本的には is_active=False での運用を推奨しますが、誤登録削除用に用意します。
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting product: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
            
    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        """
        表示順の一括更新
        args:
            order_map: {product_id: new_order_index, ...}
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for pid, order in order_map.items():
                cursor.execute("UPDATE products SET display_order=? WHERE id=?", (order, pid))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating orders: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()