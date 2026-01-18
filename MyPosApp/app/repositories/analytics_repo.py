from typing import List, Dict, Any
from app.repositories.base_repo import BaseRepository

class AnalyticsRepository(BaseRepository):
    """分析・集計用データアクセス"""

    def get_dashboard_stats(self) -> Dict[str, int]:
        """ダッシュボード用統計"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0), COUNT(id) FROM transactions")
        row = cursor.fetchone()
        conn.close()
        return {"sales": row[0], "customer_count": row[1]}

    def get_transaction_list(self) -> List[Dict[str, Any]]:
        """伝票一覧"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.id, t.timestamp, t.total_amount, 
                   (SELECT COUNT(*) FROM transaction_items WHERE transaction_id = t.id),
                   (SELECT payment_method FROM transaction_payments WHERE transaction_id = t.id LIMIT 1),
                   t.customer_label
            FROM transactions t
            ORDER BY t.timestamp DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "timestamp": r[1], "total": r[2], "items": r[3], "payment": r[4], "customer": r[5]} 
            for r in rows
        ]

    def get_transaction_details(self, transaction_id: int) -> Dict[str, Any]:
        """伝票詳細"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, timestamp, total_amount, cashier_name FROM transactions WHERE id=?", (transaction_id,))
        head = cursor.fetchone()
        
        cursor.execute("SELECT product_name, unit_price, quantity, subtotal FROM transaction_items WHERE transaction_id=?", (transaction_id,))
        items = cursor.fetchall()
        
        cursor.execute("SELECT payment_method, amount FROM transaction_payments WHERE transaction_id=?", (transaction_id,))
        payments = cursor.fetchall()
        conn.close()
        
        return {
            "id": head[0], "timestamp": head[1], "total": head[2], "cashier": head[3],
            "items": [{"name": r[0], "price": r[1], "qty": r[2], "sub": r[3]} for r in items],
            "payments": [{"method": r[0], "amount": r[1]} for r in payments]
        }

    def get_payment_summary(self):
        """決済集計"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT payment_method, SUM(amount) FROM transaction_payments GROUP BY payment_method")
        rows = cursor.fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}

    def get_raw_data_for_analysis(self):
        """分析用生データ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ★修正: クロス集計で「客数」を出すために t.id を追加
        cursor.execute("""
            SELECT 
                t.id,
                t.timestamp,
                t.customer_label,
                t.cashier_name,
                i.product_name,
                i.quantity,
                i.subtotal
            FROM transactions t
            JOIN transaction_items i ON t.id = i.transaction_id
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            # 戻り値の辞書に 'id' を追加
            {"id": r[0], "timestamp": r[1], "customer": r[2], "cashier": r[3], "product": r[4], "qty": r[5], "sales": r[6]}
            for r in rows
        ]