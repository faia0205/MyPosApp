import sqlite3
from contextlib import contextmanager
from typing import Generator, Tuple
from app.config import DB_PATH

class BaseRepository:
    """
    データベース接続とトランザクション管理を行う基底クラス
    """

    def get_connection(self) -> sqlite3.Connection:
        """従来の接続メソッド（互換性維持のため残す場合は利用可）"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # カラム名アクセスを可能に
        return conn

    @contextmanager
    def transaction(self) -> Generator[Tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
        """
        【推奨】安全なトランザクション管理を行うコンテキストマネージャ
        Usage:
            with self.transaction() as (conn, cursor):
                cursor.execute(...)
        Error時は自動Rollback、終了時は自動Closeを行います。
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield conn, cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()