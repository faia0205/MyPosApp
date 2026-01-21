from typing import List, Dict, Any
from app.repositories.base_repo import BaseRepository
import sqlite3

class UserRepository(BaseRepository):
    def fetch_active_users(self) -> List[Dict[str, Any]]:
        """有効なユーザーリストを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, user_code FROM users WHERE is_active=1 ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "code": r[2]} for r in rows]
    
    def fetch_all_for_json(self) -> List[Dict]:
        """JSON出力用: 全ユーザー取得"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name, user_code, role, is_active FROM users")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def fetch_all_users(self) -> List[Dict[str, Any]]:
        """設定画面用: 全ユーザー取得 (ID付き)"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, user_code, role, is_active FROM users ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def upsert_user(self, name: str, code: str, role: str, is_active: bool):
        """JSON同期用: コードが同じなら更新、なければ挿入"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # チェック
        cursor.execute("SELECT id FROM users WHERE user_code = ?", (code,))
        row = cursor.fetchone()
        
        if row:
            # 更新
            cursor.execute("""
                UPDATE users SET name=?, role=?, is_active=? WHERE id=?
            """, (name, role, int(is_active), row[0]))
        else:
            # 挿入
            cursor.execute("""
                INSERT INTO users (name, user_code, role, is_active)
                VALUES (?, ?, ?, ?)
            """, (name, code, role, int(is_active)))
        
        conn.commit()
        conn.close()
    
    def add_user(self, name: str, code: str, role: str) -> bool:
        """ユーザー新規追加"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, user_code, role, is_active) VALUES (?, ?, ?, 1)",
                           (name, code, role))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # コード重複などのエラー
            return False
        finally:
            conn.close()

    def update_user(self, user_id: int, name: str, code: str, role: str, is_active: bool) -> bool:
        """ユーザー更新"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users SET name=?, user_code=?, role=?, is_active=? WHERE id=?
            """, (name, code, role, int(is_active), user_id))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
            
    def delete_user(self, user_id: int) -> bool:
        """物理削除 (誤登録用)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error occurred: {e}")
            return False
        finally:
            conn.close()