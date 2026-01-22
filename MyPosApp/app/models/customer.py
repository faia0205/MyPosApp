from dataclasses import dataclass
import json

@dataclass
class Customer:
    """客層データモデル"""
    id: int
    label: str
    attributes_json: str # DBからはJSON文字列で来る
    color: str
    display_order: int = 0

    @property
    def attributes(self) -> dict:
        """JSON文字列を辞書として取得"""
        try:
            return json.loads(self.attributes_json)
        except Exception:
            return {}