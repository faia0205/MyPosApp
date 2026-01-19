# 客層データの読み込みを担当します。
from typing import List, Dict
import sqlite3
from app.repositories.base_repo import BaseRepository
from app.models.customer import Customer

class CustomerRepository(BaseRepository):
    
    def fetch_presets(self) -> List[Customer]:
        """客層プリセットを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, label, attributes, color, display_order
            FROM customer_presets 
            WHERE is_active=1 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()
        
        customers = []
        for r in rows:
            c = Customer(
                id=r[0], label=r[1], attributes_json=r[2], 
                color=r[3], display_order=r[4]
            )
            customers.append(c)
            
        return customers
    
    # ※ JSONパースが必要なため、Customerモデルではなく辞書で返すメソッド
    def fetch_all_for_json(self) -> List[Dict]:
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT label, attributes, color, display_order FROM customer_presets ORDER BY display_order")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            d = dict(row)
            # attributes はDB内では文字列(JSON)なので、辞書に戻す
            import json
            try:
                d['attributes'] = json.loads(d['attributes'])
            except:
                d['attributes'] = {}
            result.append(d)
        return result