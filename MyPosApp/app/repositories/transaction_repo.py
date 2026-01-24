from typing import List, Optional
from app.repositories.base_repo import BaseRepository
from app.models.transaction import Transaction, TransactionItem, TransactionPayment

class TransactionRepository(BaseRepository):
    """
    取引（売上）の保存・集計・履歴取得を担当
    """

    def get_total_sales_today(self) -> int:
        """本日の売上合計"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT SUM(total_amount) 
                FROM transactions 
                WHERE date(timestamp, 'localtime') = date('now', 'localtime')
            """)
            row = cursor.fetchone()
            return row[0] if row[0] is not None else 0
    
    def save(self, tx: Transaction) -> int:
        """取引を保存（オブジェクトを受け取って一括保存）"""
        with self.transaction() as (conn, cursor):
            # 1. ヘッダー保存
            cursor.execute("""
                INSERT INTO transactions (total_amount, change, customer_label, cashier_name, status) 
                VALUES (?, ?, ?, ?, ?)
            """, (tx.total_amount, tx.change, tx.customer_label, tx.cashier_name, tx.status))
            
            new_id = cursor.lastrowid
            tx.id = new_id # IDを書き戻す（必要であれば）
            
            # 2. 明細保存
            if tx.items:
                items_data = [
                    (new_id, item.product_name, item.unit_price, item.quantity, item.subtotal)
                    for item in tx.items
                ]
                cursor.executemany("""
                    INSERT INTO transaction_items (transaction_id, product_name, unit_price, quantity, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, items_data)

            # 3. 決済保存
            if tx.payments:
                payments_data = [
                    (new_id, pay.payment_method, pay.amount)
                    for pay in tx.payments
                    if pay.amount > 0 # 金額0円の決済は保存しない
                ]
                if payments_data:
                    cursor.executemany("""
                        INSERT INTO transaction_payments (transaction_id, payment_method, amount)
                        VALUES (?, ?, ?)
                    """, payments_data)
            
            return new_id

    def fetch_history(self, limit: int = 50) -> List[dict]:
        """
        取引履歴を取得（履歴タブ表示用）
        ※View側がまだ辞書を期待しているため、辞書リストで返す既存仕様を維持
        """
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, total_amount, customer_label, timestamp as created_at, cashier_name, status 
                FROM transactions 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            # RowFactoryを使わない簡易辞書化
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
            
    def get_transaction_details(self, transaction_id: int) -> dict:
        """
        特定の取引の詳細を取得（レシート再発行や詳細確認用）
        ※こちらもViewの互換性のため辞書構造を維持
        """
        with self.transaction() as (conn, cursor):
            # ヘッダー
            cursor.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
            row = cursor.fetchone()
            if not row:
                return {}
            # カラム名マッピング
            cols = [c[0] for c in cursor.description]
            head = dict(zip(cols, row))
            
            # 明細
            cursor.execute("SELECT product_name, unit_price, quantity, subtotal FROM transaction_items WHERE transaction_id=?", (transaction_id,))
            items = []
            for r in cursor.fetchall():
                items.append({
                    "product_name": r[0],
                    "unit_price": r[1],
                    "quantity": r[2],
                    "subtotal": r[3]
                })
            
            # 決済
            cursor.execute("SELECT payment_method, amount FROM transaction_payments WHERE transaction_id=?", (transaction_id,))
            payments = []
            for r in cursor.fetchall():
                payments.append({
                    "payment_method": r[0],
                    "amount": r[1]
                })
            
            return {
                "header": head,
                "items": items,
                "payments": payments
            }