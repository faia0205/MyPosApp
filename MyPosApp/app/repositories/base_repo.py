from app.utils.database import IDatabaseProvider

class BaseRepository:
    """
    データベース接続とトランザクション管理を行う基底クラス
    """
    def __init__(self, db_provider: IDatabaseProvider):
        self.db = db_provider

    def get_connection(self):
        """プロバイダ経由で接続を取得"""
        return self.db.get_connection()

    def transaction(self):
        """プロバイダ経由でトランザクションを実行"""
        return self.db.transaction()