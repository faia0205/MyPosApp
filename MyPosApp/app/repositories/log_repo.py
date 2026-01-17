# ログを読み書きするクラスです。
from app.repositories.base_repo import BaseRepository

class LogRepository(BaseRepository):
    def add_log(self, level: str, message: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO operation_logs (level, message) VALUES (?, ?)", (level, message))
        conn.commit()
        conn.close()

    def fetch_logs(self) -> list[dict]:
        """すべてのログを取得"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, level, message FROM operation_logs ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return [{"time": r[0], "level": r[1], "msg": r[2]} for r in rows]