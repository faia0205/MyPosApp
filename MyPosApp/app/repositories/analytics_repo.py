# 集計を行うためのSQLリポジトリ
from typing import List, Dict, Any
from app.repositories.base_repo import BaseRepository

class AnalyticsRepository(BaseRepository):
    """分析・集計用データアクセス"""

    def get_transaction_list(self) -> List[Dict[str, Any]]:
        """伝票一覧（簡易表示用）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.timestamp, t.total_amount, 
                   (SELECT COUNT(*) FROM transaction_items WHERE transaction_id = t.id) as item_count,
                   (SELECT payment_method FROM transaction_payments WHERE transaction_id = t.id LIMIT 1) as main_payment
            FROM transactions t
            ORDER BY t.timestamp DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "time": r[1], "total": r[2], "items": r[3], "payment": r[4]} 
            for r in rows
        ]

    def get_transaction_details(self, transaction_id: int) -> Dict[str, Any]:
        """伝票詳細（全表示用）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ヘッダー情報
        cursor.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
        head = cursor.fetchone()
        
        # 商品明細
        cursor.execute("SELECT product_name, unit_price, quantity, subtotal FROM transaction_items WHERE transaction_id=?", (transaction_id,))
        items = cursor.fetchall()
        
        # 決済明細
        cursor.execute("SELECT payment_method, amount FROM transaction_payments WHERE transaction_id=?", (transaction_id,))
        payments = cursor.fetchall()
        
        conn.close()
        
        return {
            "id": head[0], "time": head[1], "total": head[2],
            "items": [{"name": r[0], "price": r[1], "qty": r[2], "sub": r[3]} for r in items],
            "payments": [{"method": r[0], "amount": r[1]} for r in payments]
        }

    def get_sales_by_hour(self) -> List[Dict[str, Any]]:
        """時間別売上・客数"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # SQLiteの strftime で時間を切り出し
        cursor.execute("""
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count, SUM(total_amount) as sales
            FROM transactions
            GROUP BY hour
            ORDER BY hour
        """)
        rows = cursor.fetchall()
        conn.close()
        return [{"hour": r[0], "count": r[1], "sales": r[2]} for r in rows]

    def get_sales_by_product(self) -> List[Dict[str, Any]]  :
        """商品別売上（ランキング用）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_name, SUM(quantity) as qty, SUM(subtotal) as total
            FROM transaction_items
            GROUP BY product_name
            ORDER BY total DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [{"name": r[0], "qty": r[1], "total": r[2]} for r in rows]
    
    def get_payment_summary(self) -> Dict[str, int]:
        """決済方法ごとの売上合計"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT payment_method, SUM(amount) 
            FROM transaction_payments 
            GROUP BY payment_method
        """)
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}

    def get_raw_data_for_analysis(self) -> List[Dict[str, Any]]:
        """分析用に結合データを取得 (DataFrame化用)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 時間(H), 客層, 商品名, 個数, 小計 を一気に取得
        cursor.execute("""
            SELECT 
                strftime('%H', t.timestamp) as hour,
                t.customer_label,
                i.product_name,
                i.quantity,
                i.subtotal
            FROM transactions t
            JOIN transaction_items i ON t.id = i.transaction_id
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"hour": int(r[0]), "customer": r[1], "product": r[2], "qty": r[3], "sales": r[4]}
            for r in rows
        ]