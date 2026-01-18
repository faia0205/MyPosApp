from typing import List, Dict, Any
from app.repositories.base_repo import BaseRepository

class UserRepository(BaseRepository):
    def fetch_active_users(self) -> List[Dict[str, Any]]:
        """有効なユーザーリストを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, user_code FROM users WHERE is_active=1 ORDER BY id")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "code": r[2]} for r in rows]