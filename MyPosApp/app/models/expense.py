from dataclasses import dataclass

@dataclass
class Expense:
    id: int
    title: str
    amount: int
    timestamp: str  # DBからは文字列で来るため