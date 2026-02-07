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
            SELECT t.id, t.timestamp, t.total_amount, t.change,
                   (SELECT COUNT(*) FROM transaction_items WHERE transaction_id = t.id),
                   (SELECT payment_method FROM transaction_payments WHERE transaction_id = t.id LIMIT 1),
                   t.customer_label
            FROM transactions t
            ORDER BY t.timestamp DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0], 
                "timestamp": r[1], 
                "total": r[2], 
                "change": r[3], # ★追加
                "items": r[4], 
                "payment": r[5], 
                "customer": r[6]
            } 
            for r in rows
        ]

    def get_transaction_details(self, transaction_id: int) -> Dict[str, Any]:
        """伝票詳細"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, timestamp, total_amount, change, cashier_name FROM transactions WHERE id=?", (transaction_id,))
        head = cursor.fetchone()
        
        cursor.execute("SELECT product_name, unit_price, quantity, subtotal FROM transaction_items WHERE transaction_id=?", (transaction_id,))
        items = cursor.fetchall()
        
        cursor.execute("SELECT payment_method, amount FROM transaction_payments WHERE transaction_id=?", (transaction_id,))
        payments = cursor.fetchall()
        conn.close()

        if not head:
            return {}
        
        return {
            "id": head[0], "timestamp": head[1], "total": head[2], "change": head[3], "cashier": head[4],
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

    def get_cashier_payment_data(self):
        """担当者ごとの決済内訳分析用データ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 担当者名、決済方法、金額 を取得
        cursor.execute("""
            SELECT 
                t.cashier_name,
                p.payment_method,
                p.amount
            FROM transactions t
            JOIN transaction_payments p ON t.id = p.transaction_id
        """)
        rows = cursor.fetchall()
        conn.close()
        return [
            {"cashier": r[0], "method": r[1], "amount": r[2]}
            for r in rows
        ]

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
    
    def get_comprehensive_raw_data(self, start_date: str = None, end_date: str = None):
        """
        分析に必要な全項目を含むフラットなデータを取得
        ※ 期間指定があれば WHERE 句を追加する拡張が可能
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # JSON属性なども含めて取得するが、SQLite側では文字列として取得し、
        # Python側でパースする方が汎用性が高い。
        query = """
            SELECT
                t.id as tx_id,
                t.timestamp,
                t.customer_label,
                t.cashier_name,
                c.attributes as customer_attrs,  -- Customerテーブルと結合
                i.product_name,
                i.quantity,
                i.unit_price,
                i.subtotal,
                p.category,                      -- Productsテーブルと結合
                pay.payment_method
            FROM transactions t
            LEFT JOIN transaction_items i ON t.id = i.transaction_id
            LEFT JOIN products p ON i.product_name = p.name -- 名前で結合(ID推奨だが現状スキーマに合わせる)
            LEFT JOIN customer_presets c ON t.customer_label = c.label
            LEFT JOIN transaction_payments pay ON t.id = pay.transaction_id
            WHERE 1=1
        """
        
        # 必要に応じて date(t.timestamp) BETWEEN ? AND ? を追加
        params = []
        if start_date and end_date:
            query += " AND date(t.timestamp) >= ? AND date(t.timestamp) <= ?"
            params.extend([start_date, end_date])
            
        cursor.execute(query, params)
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(zip(cols, row)) for row in rows]
    
    def get_min_timestamp(self) -> str:
        """最も古い取引の日時を取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MIN(timestamp) FROM transactions")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    
    def get_customer_attribute_keys(self) -> list[str]:
        """
        客層マスタ(customer_presets)に含まれるJSON属性キー
        （sex, ageなど）のユニーク一覧を取得して返します。
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # attributesカラム（JSON文字列）を取得
            cursor.execute("SELECT attributes FROM customer_presets WHERE is_active=1")
            rows = cursor.fetchall()
        except Exception:
            # テーブルが存在しない場合などのエラー回避
            conn.close()
            return []
            
        conn.close()

        import json
        keys = set()
        
        for r in rows:
            json_str = r[0]
            if not json_str:
                continue
                
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    # 辞書のキー（"sex", "age"など）をセットに追加
                    keys.update(data.keys())
            except:
                pass
                
        return sorted(list(keys))