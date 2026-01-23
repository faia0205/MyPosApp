from typing import Tuple, List, Optional
from app.repositories.base_repo import BaseRepository

class TransactionRepository(BaseRepository):
    """
    取引（売上）の保存・集計・履歴取得のみを担当するクラス
    ※経費(Expense)や決済設定(Payment)は専用リポジトリへ移動済み
    """

    def get_total_sales_today(self) -> int:
        """本日の売上合計を取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT SUM(total_amount) FROM transactions")
            row = cursor.fetchone()
            return row[0] if row[0] is not None else 0
    
    def save_transaction(self, total_amount: int, customer_label: str, cashier_name: str, 
                         items_data: list[dict], payments: list[Tuple[str, int]], change: int = 0) -> int:
        """取引を保存（ヘッダー、明細、決済内訳）"""
        with self.transaction() as (conn, cursor):
            # 1. ヘッダー
            cursor.execute("""
                INSERT INTO transactions (total_amount, change, customer_label, cashier_name, status) 
                VALUES (?, ?, ?, ?, 'completed')
            """, (total_amount, change, customer_label, cashier_name))
            
            transaction_id = cursor.lastrowid
            
            # 2. 明細 (items_dataは辞書リストの想定)
            for item in items_data:
                cursor.execute("""
                    INSERT INTO transaction_items (transaction_id, product_name, unit_price, quantity, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (transaction_id, item['name'], item['price'], item['qty'], item['subtotal']))

            # 3. 決済
            for method_name, amount in payments:
                if amount > 0:
                    cursor.execute("""
                        INSERT INTO transaction_payments (transaction_id, payment_method, amount)
                        VALUES (?, ?, ?)
                    """, (transaction_id, method_name, amount))
            
            return transaction_id

    def fetch_history(self, limit: int = 50) -> List[dict]:
        """取引履歴を取得（履歴タブ表示用）"""
        # ※ここはまだUIが辞書を期待している可能性が高いため、辞書リストで返します
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, total_amount, customer_label, created_at, cashier_name, status 
                FROM transactions 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
    def get_transaction_details(self, transaction_id: int) -> dict:
        """特定の取引の詳細を取得（レシート再発行や詳細確認用）"""
        with self.transaction() as (conn, cursor):
            # ヘッダー
            cursor.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
            head = cursor.fetchone()
            if not head:
                return {}
            
            # 明細
            cursor.execute("SELECT product_name, unit_price, quantity, subtotal FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            items = [dict(r) for r in cursor.fetchall()]
            
            # 決済
            cursor.execute("SELECT payment_method, amount FROM transaction_payments WHERE transaction_id=?", (transaction_id,))
            payments = [dict(r) for r in cursor.fetchall()]
            
            return {
                "header": dict(head),
                "items": items,
                "payments": payments
            }