from dataclasses import dataclass
from typing import Optional
import json

@dataclass
class Customer:
    """客層データモデル"""
    id: Optional[int]
    label: str
    attributes_json: str = "{}" # DBのTEXTカラム(JSON文字列)に対応
    color: str = "#ffffff"
    display_order: int = 0
    is_active: bool = True

    @property
    def attributes(self) -> dict:
        """JSON文字列を辞書として取得（読み取り専用）"""
        try:
            return json.loads(self.attributes_json)
        except Exception:
            return {}

    def set_attributes(self, data: dict):
        """辞書からJSON文字列を設定するヘルパー"""
        self.attributes_json = json.dumps(data, ensure_ascii=False)