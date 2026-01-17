# すべてのリポジトリの親となる、接続処理を担当するクラスです。
import sqlite3
from app.config import DB_PATH

class BaseRepository:
    """データベース接続の共通処理"""
    
    def get_connection(self):
        """DB接続を返す"""
        return sqlite3.connect(DB_PATH)