from abc import ABC, abstractmethod
from contextlib import contextmanager
import sqlite3
import logging
from typing import Generator, Tuple

logger = logging.getLogger("MyPosApp")

class IDatabaseProvider(ABC):
    """データベース接続を提供する抽象インターフェース"""
    
    @abstractmethod
    def get_connection(self):
        pass

    @abstractmethod
    @contextmanager
    def transaction(self):
        pass

class SQLiteProvider(IDatabaseProvider):
    """SQLite用の具体的な接続プロバイダ"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # カラム名アクセスを有効化
        return conn

    @contextmanager
    def transaction(self) -> Generator[Tuple[sqlite3.Connection, sqlite3.Cursor], None, None]:
        """トランザクション管理付きのカーソルを提供"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield conn, cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction error: {e}", exc_info=True)
            raise RuntimeError(f"データベース処理中にエラーが発生しました: {e}") from e
        finally:
            conn.close()