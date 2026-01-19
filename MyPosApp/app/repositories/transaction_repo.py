# 売上保存や、決済方法、経費の取得などを担当します。
from app.repositories.base_repo import BaseRepository
from typing import List, Dict
import sqlite3

class TransactionRepository(BaseRepository):
    
    def fetch_payment_methods(self) -> list[dict]:
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
    
    def fetch_expense_list(self):
        """経費の明細リストを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        # 時間は後でPython側でJST変換するのでそのまま取得
        cursor.execute("SELECT id, title, amount, created_at FROM expenses ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "title": r[1], "amount": r[2], "timestamp": r[3]} for r in rows]

    def get_total_sales_today(self) -> int:
        """今日の売上合計を取得 (再起動時の復元用)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 本来は日付で絞り込むべきですが、イベント期間中は全データ＝売上とみなしてシンプルに実装します
        # もし日付を厳密に分けたい場合は WHERE date(...) を追加します
        cursor.execute("SELECT SUM(total_amount) FROM transactions")
        row = cursor.fetchone()
        
        conn.close()
        # データがない(None)場合は0を返す
        return row[0] if row[0] is not None else 0
    
    def save_transaction(self, total_amount: int, customer_label: str, cashier_name: str, cart_items: list[dict], payments: list[tuple[str, int]]) -> int:
        """取引保存 (トランザクション処理)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. ヘッダー
            cursor.execute("""
                INSERT INTO transactions (total_amount, customer_label, cashier_name, status) 
                VALUES (?, ?, ?, 'completed')
            """, (total_amount, customer_label, cashier_name))
            
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

    def fetch_payment_methods_for_json(self) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name, is_cash, is_active FROM payment_methods")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def upsert_payment_method(self, name: str, is_cash: bool, is_active: bool):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM payment_methods WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        if row:
            cursor.execute("UPDATE payment_methods SET is_cash=?, is_active=? WHERE id=?", 
                           (int(is_cash), int(is_active), row[0]))
        else:
            cursor.execute("INSERT INTO payment_methods (name, is_cash, is_active) VALUES (?, ?, ?)",
                           (name, int(is_cash), int(is_active)))
        conn.commit()
        conn.close()