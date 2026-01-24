from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class TransactionItem:
    """取引明細（商品・割引）"""
    id: Optional[int]
    transaction_id: Optional[int]
    product_name: str
    unit_price: int
    quantity: int
    subtotal: int

@dataclass
class TransactionPayment:
    """決済内訳"""
    id: Optional[int]
    transaction_id: Optional[int]
    payment_method: str
    amount: int

@dataclass
class Transaction:
    """取引ヘッダー"""
    id: Optional[int]
    total_amount: int
    change: int
    customer_label: str
    cashier_name: str
    status: str = "completed"
    created_at: str = "" # DB保存時は自動生成、取得時は文字列
    
    # 関連データ (明細と決済)
    items: List[TransactionItem] = field(default_factory=list)
    payments: List[TransactionPayment] = field(default_factory=list)