from typing import List, Dict

class PaymentSession:
    """
    会計の支払い状態と計算ロジックを管理するクラス
    UI（PaymentDialog）から分離され、単体テストが可能
    """
    def __init__(self, total_amount: int):
        self._total_amount = total_amount
        self._payments: List[Dict] = [] # [{'name': str, 'amount': int}]

    @property
    def total_amount(self) -> int:
        return self._total_amount

    @property
    def payments(self) -> List[Dict]:
        return self._payments

    def get_total_paid(self) -> int:
        """支払い済み総額"""
        return sum(p['amount'] for p in self._payments)

    def get_remaining(self) -> int:
        """不足金額"""
        paid = self.get_total_paid()
        return max(0, self._total_amount - paid)

    def get_change(self) -> int:
        """お釣り"""
        paid = self.get_total_paid()
        return max(0, paid - self._total_amount)

    def is_complete(self) -> bool:
        """支払いが完了しているか"""
        return self.get_total_paid() >= self._total_amount

    def add_payment(self, method_name: str, amount: int, is_cash: bool) -> bool:
        """
        支払いを追加する
        Returns: 追加されたかどうか (金額0以下や、非現金での過払いの場合はFalse)
        """
        if amount <= 0:
            return False

        # 非現金の場合、残額を超える支払いは自動的に残額に丸める（あるいは拒否する）
        if not is_cash:
            remaining = self.get_remaining()
            if amount > remaining:
                amount = remaining
            
            if amount <= 0: # 既に支払い完了している場合など
                return False

        # 既存の支払い方法があれば加算、なければ新規追加
        for pay in self._payments:
            if pay['name'] == method_name:
                pay['amount'] += amount
                return True

        self._payments.append({
            'name': method_name,
            'amount': amount
        })
        return True

    def remove_payment(self, index: int):
        """指定インデックスの支払いを削除"""
        if 0 <= index < len(self._payments):
            self._payments.pop(index)