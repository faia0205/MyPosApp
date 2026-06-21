# ログを読み書きするクラスです。
from app.repositories.base_repo import BaseRepository

class LogRepository(BaseRepository):
    def add_log(self, level: str, message: str):
        with self.transaction() as (conn, cursor):
            cursor.execute("INSERT INTO operation_logs (level, message) VALUES (?, ?)", (level, message))

    def fetch_logs(self) -> list[dict]:
        """すべてのログを取得"""
        with self.transaction() as (conn, cursor):
            cursor.execute("SELECT timestamp, level, message FROM operation_logs ORDER BY id DESC")
            rows = cursor.fetchall()
        return [{"timestamp": r[0], "time": r[0], "level": r[1], "msg": r[2]} for r in rows]