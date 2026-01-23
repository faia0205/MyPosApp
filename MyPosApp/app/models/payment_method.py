from dataclasses import dataclass

@dataclass
class PaymentMethod:
    id: int
    name: str
    is_cash: bool
    is_active: bool