import sqlite3

class Repository:
    """データベース操作を一手に引き受けるクラス (Repository Pattern)"""
    
    def __init__(self, db_name="pos_system.db"):
        self.db_name = db_name

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def fetch_active_products(self):
        """有効な商品リストを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = """
            SELECT id, name, price, category, color, note 
            FROM products 
            WHERE is_active=1 
            ORDER BY category DESC, display_order ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        # 辞書のリストに変換して返す（依存性逆転のため、呼び出し元はSQLを知らなくて済む）
        return [
            {
                "id": r[0], 
                "name": r[1], 
                "price": r[2], 
                "category": r[3], 
                "color": r[4], 
                "note": r[5]
            } 
            for r in rows
        ]

    def fetch_customer_presets(self):
        """客層プリセットを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, attributes FROM customer_presets WHERE is_active=1 ORDER BY display_order")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "label": r[1], "attributes": r[2]} for r in rows]

    def get_total_expenses(self):
        """経費合計を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM expenses")
        res = cursor.fetchone()
        conn.close()
        return res[0] if res[0] else 0