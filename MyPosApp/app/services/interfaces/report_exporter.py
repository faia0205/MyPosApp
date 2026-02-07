from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
import pandas as pd

class IReportExporter(ABC):
    """帳票出力の抽象インターフェース"""

    @abstractmethod
    def export(self, file_path: str, tx_list: List[Dict], logs: List[Dict], pivots: Dict[str, pd.DataFrame]) -> Tuple[bool, str]:
        """
        データを指定されたパスに出力する
        Returns: (成功フラグ, メッセージ)
        """
        pass