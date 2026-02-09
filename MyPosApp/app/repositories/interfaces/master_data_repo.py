from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IMasterDataRepository(ABC):
    """
    マスタデータ同期（JSON Import/Export）に対応するためのインターフェース
    """

    @abstractmethod
    def get_master_key(self) -> str:
        """
        JSONファイル内のキー名 (例: 'products', 'users') を返す
        """
        pass

    @abstractmethod
    def export_all_data(self) -> List[Dict[str, Any]]:
        """
        全データを辞書リスト形式で返す (JSON出力用)
        """
        pass

    @abstractmethod
    def import_all_data(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        辞書リストを受け取り、DBに反映させる
        """
        pass

    @abstractmethod
    def delete_not_in(self, active_ids: List[int]) -> None:
        """
        指定されたIDリストに含まれないレコードを削除する
        active_ids が空の場合は全削除を行う。
        （JSONに記述がないデータをDBから消去するためのメソッド）
        """
        pass