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
        cursor.execute("""
            SELECT id, label, attributes, color 
            FROM customer_presets 
            WHERE is_active=1 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "label": r[1], "attributes": r[2], "color": r[3]} for r in rows]

    def fetch_payment_methods(self):
        """有効な決済方法を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # id, name, is_cash (1=現金, 0=その他)
        cursor.execute("SELECT id, name, is_cash FROM payment_methods WHERE is_active=1")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "is_cash": bool(r[2])} for r in rows]
    
    def get_total_expenses(self):
        """経費合計を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(amount) FROM expenses")
        res = cursor.fetchone()
        conn.close()
        return res[0] if res[0] else 0

    def save_transaction(self, total_amount, customer_label, cart_items, payments):
        """
        取引データを保存する（トランザクション処理付き）
        payments: [('現金', 1000), ('PayPay', 500)] のようなリスト
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. 取引ヘッダー保存
            cursor.execute("""
                INSERT INTO transactions (total_amount, status) 
                VALUES (?, 'completed')
            """, (total_amount,))
            
            transaction_id = cursor.lastrowid # 今保存したIDを取得
            
            # 2. 客層情報の記録（今回は簡易的にnoteや別テーブル、あるいはJSONで保存も可）
            # ここではシンプルにするため transaction_payments に 'Customer:男性' のようなタグで残すか、
            # あるいは transactions テーブルに customer_column を追加するのが本来は良いです。
            # 今回は既存の transactions テーブル構造に合わせて進めます。

            # 3. 商品明細の保存
            for item in cart_items:
                # 手入力商品はIDがないのでNULLまたは0で処理
                prod_id = item.get('id')
                cursor.execute("""
                    INSERT INTO transaction_items (transaction_id, product_name, unit_price, quantity, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                """, (transaction_id, item['name'], item['price'], item['qty'], item['price'] * item['qty']))

            # 4. 決済情報の保存
            for method, amount in payments:
                if amount > 0:
                    cursor.execute("""
                        INSERT INTO transaction_payments (transaction_id, payment_method, amount)
                        VALUES (?, ?, ?)
                    """, (transaction_id, method, amount))

            conn.commit()
            print(f"Transaction {transaction_id} saved successfully.")
            return transaction_id

        except Exception as e:
            conn.rollback()
            print(f"Error saving transaction: {e}")
            raise e
        finally:
            conn.close()