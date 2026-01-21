from typing import List, Dict, Any
import sqlite3
import json
from app.repositories.base_repo import BaseRepository
from app.models.customer import Customer

class CustomerRepository(BaseRepository):
    """客層データのCRUD"""

    def fetch_presets(self) -> List[Customer]:
        """販売画面用: 有効なプリセットを取得"""
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
        return [Customer(r[0], r[1], r[2], r[3], r[4]) for r in rows]

    def fetch_all_for_json(self) -> List[Dict]:
        """JSON出力用"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT label, attributes, color, display_order FROM customer_presets ORDER BY display_order")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            d = dict(row)
            try: d['attributes'] = json.loads(d['attributes'])
            except: d['attributes'] = {}
            result.append(d)
        return result

    def fetch_all_presets(self) -> List[Customer]:
        """設定画面用: 全て取得 (無効含む)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, label, attributes, color, display_order, is_active 
            FROM customer_presets 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()
        # Customerモデルに is_active フィールドがない場合は拡張が必要ですが、
        # ここでは簡易的にモデルを使いつつ、呼び出し元で is_active を判定できるようにします
        # 本来は Customer モデルにも is_active を足すべきですが、辞書で返します
        return [
            {
                "id": r[0], "label": r[1], "attributes": r[2], 
                "color": r[3], "display_order": r[4], "is_active": bool(r[5])
            }
            for r in rows
        ]

    def add_preset(self, label: str, attributes: dict, color: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 最大並び順取得
            cursor.execute("SELECT MAX(display_order) FROM customer_presets")
            max_ord = cursor.fetchone()[0] or 0
            
            attr_json = json.dumps(attributes, ensure_ascii=False)
            cursor.execute("""
                INSERT INTO customer_presets (label, attributes, color, display_order, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (label, attr_json, color, max_ord + 1))
            conn.commit()
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            conn.close()

    def update_preset(self, preset_id: int, label: str, attributes: dict, color: str, is_active: bool) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            attr_json = json.dumps(attributes, ensure_ascii=False)
            cursor.execute("""
                UPDATE customer_presets SET label=?, attributes=?, color=?, is_active=?
                WHERE id=?
            """, (label, attr_json, color, int(is_active), preset_id))
            conn.commit()
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            conn.close()
            
    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        """並び順更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            for pid, order in order_map.items():
                cursor.execute("UPDATE customer_presets SET display_order=? WHERE id=?", (order, pid))
            conn.commit()
            return True
        except:
            conn.rollback()
            return False
        finally:
            conn.close()