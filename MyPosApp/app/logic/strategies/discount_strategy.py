from abc import ABC, abstractmethod
from typing import List, Dict
from app.models.discount import DiscountRule, AppliedDiscount

class DiscountStrategy(ABC):
    """
    割引計算の戦略インターフェース
    """
    
    # 実行フェーズ定数
    PHASE_STANDARD = 0  # 在庫消費型（バンドル、商品、カテゴリなど）
    PHASE_POST = 1      # 最終計算型（カート全体割引など、小計確定後に実行）

    @property
    def phase(self) -> int:
        """実行フェーズ（デフォルトは標準）"""
        return self.PHASE_STANDARD

    @property
    def priority(self) -> int:
        """同フェーズ内の優先順位（小さいほど優先）"""
        return 50

    @abstractmethod
    def apply(self, inventory: List[Dict], rule: DiscountRule, current_net_total: int = 0) -> List[AppliedDiscount]:
        pass