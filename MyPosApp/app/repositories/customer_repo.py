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
        # Customerモデル内で attributes プロパティが自動的にJSONパースしてくれるため、ここではそのまま渡してOK
        return [Customer(r[0], r[1], r[2], r[3], r[4]) for r in rows]

    def fetch_all_for_json(self) -> List[Dict]:
        """JSON出力用"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT label, attributes, color, display_order, is_active FROM customer_presets ORDER BY display_order")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            d = dict(row)
            try:
                d['attributes'] = json.loads(d['attributes'])
            except Exception:
                d['attributes'] = {}
            result.append(d)
        return result

    def fetch_all_presets(self) -> List[Dict]:
        """
        設定画面用: 全て取得 (無効含む)
        ★修正: ここで辞書型に変換して返すように変更
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, label, attributes, color, display_order, is_active 
            FROM customer_presets 
            ORDER BY display_order
        """)
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            # ★修正ポイント: JSON文字列を辞書に変換
            attr_str = r[2]
            try:
                attr_dict = json.loads(attr_str) if attr_str else {}
            except json.JSONDecodeError:
                attr_dict = {}

            results.append({
                "id": r[0], 
                "label": r[1], 
                "attributes": attr_dict,  # 文字列ではなく辞書を入れる
                "color": r[3], 
                "display_order": r[4], 
                "is_active": bool(r[5])
            })
        return results

    def add_preset(self, label: str, attributes: dict, color: str) -> bool:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # 最大並び順取得
            cursor.execute("SELECT MAX(display_order) FROM customer_presets")
            res = cursor.fetchone()
            max_ord = res[0] if res and res[0] is not None else 0
            
            attr_json = json.dumps(attributes, ensure_ascii=False)
            cursor.execute("""
                INSERT INTO customer_presets (label, attributes, color, display_order, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (label, attr_json, color, max_ord + 1))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding preset: {e}")
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
            print(f"Error updating preset: {e}")
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
        except Exception as e:
            print(f"Error updating order: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()