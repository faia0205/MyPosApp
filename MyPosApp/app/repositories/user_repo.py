from typing import List, Optional, Dict
from app.repositories.base_repo import BaseRepository
from app.models.user import User

class UserRepository(BaseRepository):
    """
    ユーザーデータのCRUD。
    transaction() を使用して安全にDB操作を行います。
    """

    def fetch_active_users(self) -> List[User]:
        """販売画面・ログイン用: 有効なユーザーリストを取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, user_code, role, is_active 
                FROM users WHERE is_active=1 ORDER BY id
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def fetch_all_users(self) -> List[User]:
        """設定画面・JSON出力用: 全ユーザー取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("""
                SELECT id, name, user_code, role, is_active 
                FROM users ORDER BY id
            """)
            rows = cursor.fetchall()
            return [self._map_to_model(row) for row in rows]

    def upsert_user(self, user: User) -> bool:
        """JSON同期用: コードが同じなら更新、なければ挿入"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("SELECT id FROM users WHERE user_code = ?", (user.user_code,))
                row = cursor.fetchone()
                
                if row:
                    # 更新
                    cursor.execute("""
                        UPDATE users SET name=?, role=?, is_active=? WHERE id=?
                    """, (user.name, user.role, int(user.is_active), row[0]))
                else:
                    # 挿入
                    cursor.execute("""
                        INSERT INTO users (name, user_code, role, is_active)
                        VALUES (?, ?, ?, ?)
                    """, (user.name, user.user_code, user.role, int(user.is_active)))
            return True
        except Exception as e:
            print(f"Error upserting user: {e}")
            return False

    def add_user(self, user: User) -> bool:
        """ユーザー新規追加"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("""
                    INSERT INTO users (name, user_code, role, is_active) 
                    VALUES (?, ?, ?, ?)
                """, (user.name, user.user_code, user.role, int(user.is_active)))
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    def update_user(self, user: User) -> bool:
        """ユーザー更新"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("""
                    UPDATE users SET name=?, user_code=?, role=?, is_active=?
                    WHERE id=?
                """, (user.name, user.user_code, user.role, int(user.is_active), user.id))
            return True
        except Exception as e:
            print(f"Error updating user: {e}")
            return False

    def delete_user(self, user_id: int) -> bool:
        """物理削除"""
        try:
            with self.transaction() as (conn, cursor):
                cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def _map_to_model(self, row) -> User:
        if row is None: return None
        return User(
            id=row[0],
            name=row[1],
            user_code=row[2],
            role=row[3],
            is_active=bool(row[4])
        )
    
    def import_data(self, data: Dict) -> bool:
        """辞書データを取り込み (UserCodeでUpsert)"""
        try:
            user = User.from_dict(data)
            return self.upsert_user(user)
        except Exception as e:
            print(f"Error importing user: {e}")
            return False