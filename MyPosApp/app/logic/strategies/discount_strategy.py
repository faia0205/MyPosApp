from abc import ABC, abstractmethod
from typing import List, Dict
from app.models.discount import DiscountRule, AppliedDiscount

class DiscountStrategy(ABC):
    """
    割引計算の戦略インターフェース
    SOLID原則のOCP（開放閉鎖の原則）に基づき、
    新しい割引ルールが増えてもこのインターフェースを実装するだけで対応可能にします。
    """
    
    @abstractmethod
    def apply(self, inventory: List[Dict], rule: DiscountRule, current_net_total: int = 0) -> List[AppliedDiscount]:
        """
        割引ルールを適用し、結果を返すメソッド。
        
        Args:
            inventory: 計算用の在庫リスト（辞書形式）。
                       {'qty': int, ...} の値を直接書き換えて在庫消費を行います。
            rule: 適用する割引ルール定義 (DBモデル)
            current_net_total: 現在の小計（カート全体割引の計算用）

        Returns:
            List[AppliedDiscount]: 適用された割引のリスト
        """
        pass