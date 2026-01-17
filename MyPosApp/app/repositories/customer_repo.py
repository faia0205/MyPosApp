# 客層データの読み込みを担当します。
from typing import List
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