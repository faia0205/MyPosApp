from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, Signal
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository  # ★追加
from app.models.product import Product
from app.models.customer import Customer

class CartService(QObject):
    # シグナル定義
    cart_updated = Signal()
    message_updated = Signal(str, str)
    stats_updated = Signal(int, int, int, str, bool)
    checkout_completed = Signal(str, int)
    user_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.repo: TransactionRepository = TransactionRepository()
        self.user_repo = UserRepository()
        self.prod_repo = ProductRepository() # ★追加: 商品情報を取得するため
        
        self.cart_items: List[Dict[str, Any]] = []     
        self.selected_customer: Optional[Customer] = None 
        self.current_user_name = "未設定"

        self.current_expenses: int = self.repo.get_total_expenses()
        self.total_sales_today: int = self.repo.get_total_sales_today()
        
        # ★修正: 商品の平均単価を計算して目標値にする
        self.avg_price_target = self._calculate_avg_price()

    def _calculate_avg_price(self) -> int:
        """登録されている商品(プラス価格のみ)の平均単価を計算"""
        products = self.prod_repo.fetch_active_products()
        
        # 0円より高い商品の価格リストを作る（割引などのマイナスは除外）
        valid_prices = [p.price for p in products if p.price > 0]
        
        if not valid_prices:
            return 500 # 商品がない場合のデフォルト値
            
        # 平均を計算 (整数に丸める)
        return int(sum(valid_prices) / len(valid_prices))

    def add_product(self, product: Product) -> None:
        for item in self.cart_items:
            if item.get('id') == product.id and not item.get('is_manual'):
                item['qty'] += 1
                self._notify_message(f"【追加】 {product.name} (+1)", "info")
                self._recalculate()
                return

        new_item: Dict[str, Any] = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'qty': 1,
            'is_manual': False,
            'note': product.note
        }
        self.cart_items.append(new_item)
        
        if product.note:
            self._notify_message(f"⚠️ {product.name}: {product.note}", "warning")
        else:
            self._notify_message(f"【追加】 {product.name}", "info")
            
        self._recalculate()

    def add_manual_item(self, price: int, name: str) -> None:
        new_item: Dict[str, Any] = {
            'id': None,
            'name': name,
            'price': price,
            'qty': 1,
            'is_manual': True,
            'note': "手入力"
        }
        self.cart_items.append(new_item)
        self._notify_message(f"【手入力】 {name}: ¥{price:,}", "info")
        self._recalculate()

    def update_item_qty(self, index: int, new_qty: int) -> None:
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            old_qty = item['qty']
            
            if new_qty <= 0:
                self.remove_item(index)
            else:
                item['qty'] = new_qty
                self._notify_message(f"【変更】 {item['name']}: {old_qty}個 → {new_qty}個", "info")
                self._recalculate()

    def update_item_price(self, index: int, new_price: int) -> None:
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            old_price = item['price']
            item['price'] = new_price
            self._notify_message(f"【変更】 {item['name']}: ¥{old_price:,} → ¥{new_price:,}", "info")
            self._recalculate()

    def decrease_item_qty(self, index: int) -> None:
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            if item['qty'] > 1:
                item['qty'] -= 1
                self._notify_message(f"【減少】 {item['name']} (-1)", "info")
                self._recalculate()
            else:
                self.remove_item(index)

    def remove_item(self, index: int) -> None:
        if 0 <= index < len(self.cart_items):
            item = self.cart_items.pop(index)
            self._notify_message(f"【削除】 {item['name']}", "info")
            self._recalculate()

    def set_customer(self, customer: Customer) -> None:
        self.selected_customer = customer

    def get_total_amount(self) -> int:
        return sum(item['price'] * item['qty'] for item in self.cart_items)

    def set_current_user(self, name: str):
        self.current_user_name = name
        self.user_changed.emit(name)
        self._notify_message(f"担当者: {name} さんでログインしました", "info")

    def finalize_checkout(self, payments: List[Tuple[str, int]], change: int) -> None:
        if not self.cart_items or not self.selected_customer:
            return

        total = self.get_total_amount()
        customer_label = self.selected_customer.label

        try:
            self.repo.save_transaction(total, customer_label, self.current_user_name, self.cart_items, payments)
            self.total_sales_today += total
            
            self.cart_items = []
            self.selected_customer = None
            
            self.checkout_completed.emit(customer_label, change)
            self._recalculate()
            
        except Exception as e:
            self._notify_message(f"エラー: 保存に失敗しました {str(e)}", "warning")
            print(f"Checkout Error: {e}")

    def _recalculate(self) -> None:
        current_cart_total = self.get_total_amount()
        estimated_profit = (self.total_sales_today + current_cart_total) - self.current_expenses
        
        msg = "黒字達成!"
        is_red = False
        if estimated_profit < 0:
            is_red = True
            # 計算した平均単価を使用
            needed = (abs(estimated_profit) // self.avg_price_target) + 1
            msg = f"あと {needed} 個"

        self.cart_updated.emit()
        self.stats_updated.emit(
            self.total_sales_today + current_cart_total,
            self.current_expenses,
            estimated_profit,
            msg,
            is_red
        )

    def _notify_message(self, text: str, msg_type: str) -> None:
        self.message_updated.emit(text, msg_type)

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")