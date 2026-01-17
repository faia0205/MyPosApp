# 売上保存や、決済方法、経費の取得などを担当します。
from app.repositories.base_repo import BaseRepository

class TransactionRepository(BaseRepository):
    
    def fetch_payment_methods(self):
        """決済方法リストを取得 (辞書型で返すが、将来的にはクラス化も可)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, is_cash FROM payment_methods WHERE is_active=1")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "is_cash": bool(r[2])} for r in rows]

    def get_total_expenses(self) -> int:
        """経費合計"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM expenses")
        res = cursor.fetchone()
        conn.close()
        return res[0] if res[0] else 0

    def save_transaction(self, total_amount, customer_label, cart_items, payments):
        """取引保存 (トランザクション処理)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. ヘッダー
            cursor.execute("INSERT INTO transactions (total_amount, status) VALUES (?, 'completed')", (total_amount,))
            transaction_id = cursor.lastrowid
            
            # 2. 商品明細 (cart_itemsはProductオブジェクトの辞書表現か、辞書そのものか要確認。
            # Logic層でどう扱うかによりますが、ここでは辞書アクセスとして書きます)
            for item in cart_items:
                # 手入力商品はID=Noneの場合がある
                prod_id = item.get('id')
                cursor.execute("""
                    INSERT INTO transaction_items (transaction_id, product_name, unit_price, quantity, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (transaction_id, item['name'], item['price'], item['qty'], item['price'] * item['qty']))

            # 3. 決済明細
            for method_name, amount in payments:
                if amount > 0:
                    cursor.execute("""
                        INSERT INTO transaction_payments (transaction_id, payment_method, amount)
                        VALUES (?, ?, ?)
                    """, (transaction_id, method_name, amount))

            conn.commit()
            return transaction_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()