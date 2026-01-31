from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Expense:
    id: int
    title: str
    amount: int
    timestamp: str # DBからは文字列で来るため

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "amount": self.amount,
            "timestamp": self.timestamp
        }
    
    # 経費は通常マスタデータとしてインポート/エクスポートする対象としては優先度が低いですが
    # 初期データ投入などで使う場合に備えて実装します
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Expense':
        return Expense(
            id=data.get("id", 0),
            title=data["title"],
            amount=data["amount"],
            timestamp=data.get("timestamp", "")
        )