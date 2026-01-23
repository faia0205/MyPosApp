from typing import List, Dict, Tuple, Optional
from PySide6.QtCore import QObject, Signal
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository
from app.models.product import Product
from app.models.customer import Customer
from app.models.cart_item import CartItem  # 新モデル
from app.logic.calculator import PriceCalculator
from app.logic.discount_manager import DiscountManager

class CartService(QObject):
    cart_updated = Signal()
    message_updated = Signal(str, str)
    stats_updated = Signal(int, int, int, str, bool)
    checkout_completed = Signal(str, int)
    user_changed = Signal(str)
    customer_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.repo = TransactionRepository()
        self.user_repo = UserRepository()
        self.prod_repo = ProductRepository()
        self.disc_repo = DiscountRepository()
        self.log_repo = LogRepository()
        
        self.calculator = PriceCalculator()
        self.discount_manager = DiscountManager()
        
        # ★変更: CartItemオブジェクトのリストで管理
        self.cart_items: List[CartItem] = []     
        self.applied_discounts: List[Dict] = []
        self.selected_customer: Optional[Customer] = None 
        self.current_user_name = "未設定"

        self.current_expenses: int = self.repo.get_total_expenses()
        self.total_sales_today: int = self.repo.get_total_sales_today()
        self.avg_price_target = self._calculate_avg_price()
        self.discount_rules = self.disc_repo.fetch_active_rules()

    def _calculate_avg_price(self) -> int:
        products = self.prod_repo.fetch_active_products()
        valid_prices = [p.price for p in products if p.price > 0]
        if not valid_prices: return 500
        return int(sum(valid_prices) / len(valid_prices))

    # --- 商品操作 ---
    def add_product(self, product: Product) -> None:
        # 既存チェック (属性アクセス)
        for item in self.cart_items:
            if item.id == product.id and not item.is_manual:
                item.qty += 1
                if item.price != product.price:
                    item.price = product.price
                self._notify_message(f"【追加】 {product.name} (+1)", "info")
                self._recalculate()
                return
        
        # 新規作成 (CartItemインスタンス)
        new_item = CartItem(
            id=product.id,
            name=product.name,
            price=product.price,
            category=product.category or "その他",
            qty=1,
            is_manual=False,
            note=product.note
        )
        self.cart_items.append(new_item)
        self._notify_message(f"【追加】 {product.name}", "info")
        self._recalculate()

    def update_item_qty(self, index: int, new_qty: int) -> None:
        if 0 <= index < len(self.cart_items):
            if new_qty <= 0:
                self.remove_item(index)
            else:
                self.cart_items[index].qty = new_qty
                self._recalculate()

    def update_item_price(self, index: int, new_price: int) -> None:
        if 0 <= index < len(self.cart_items):
            self.cart_items[index].price = new_price
            self._recalculate()

    def decrease_item_qty(self, index: int) -> None:
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            if item.qty > 1:
                item.qty -= 1
                self._recalculate()
            else:
                self.remove_item(index)

    def remove_item(self, index: int) -> None:
        if 0 <= index < len(self.cart_items):
            self.cart_items.pop(index)
            self._recalculate()

    def add_manual_item(self, price: int, name: str) -> None:
        new_item = CartItem(
            id=None,
            name=name,
            price=price,
            qty=1,
            category="その他",
            is_manual=True,
            note="手入力"
        )
        self.cart_items.append(new_item)
        self._recalculate()
        
    def refresh_prices(self, master_products: List[Product]) -> None:
        product_map = {p.id: p for p in master_products}
        updated_count = 0
        for item in self.cart_items:
            if not item.is_manual and item.id in product_map:
                new_price = product_map[item.id].price
                if item.price != new_price:
                    item.price = new_price
                    updated_count += 1
        if updated_count > 0:
            self._notify_message(f"{updated_count}件の価格情報を更新しました", "info")
            self._recalculate()

    # --- 計算処理 ---
    def get_total_amount(self) -> int:
        return self.calculator.calculate_grand_total(self.cart_items, self.applied_discounts)

    def _recalculate(self) -> None:
        self.discount_rules = self.disc_repo.fetch_active_rules()
        self.applied_discounts = self.discount_manager.calculate_discounts(
            self.cart_items, 
            self.discount_rules
        )
        grand_total = self.calculator.calculate_grand_total(
            self.cart_items, 
            self.applied_discounts
        )
        est_profit, is_red, msg = self.calculator.calculate_profit_metrics(
            grand_total,
            self.total_sales_today,
            self.current_expenses,
            self.avg_price_target
        )
        self.cart_updated.emit()
        self.stats_updated.emit(
            self.total_sales_today + grand_total,
            self.current_expenses,
            est_profit,
            msg,
            is_red
        )

    # --- その他 ---
    def set_customer(self, customer: Customer) -> None:
        self.selected_customer = customer
        self.customer_selected.emit(customer)

    def set_current_user(self, name: str):
        self.current_user_name = name
        self.user_changed.emit(name)
        self._notify_message(f"担当者: {name} さんでログインしました", "info")

    def finalize_checkout(self, payments: List[Tuple[str, int]], change: int) -> None:
        if not self.cart_items or not self.selected_customer: return
        
        total = self.get_total_amount()
        
        # 保存用に辞書へ変換
        final_items_dicts = []
        for item in self.cart_items:
            final_items_dicts.append({
                'name': item.name,
                'price': item.price,
                'qty': item.qty,
                'subtotal': item.price * item.qty
            })
            
        for d in self.applied_discounts:
            final_items_dicts.append({
                'name': d['name'],
                'price': d['amount'],
                'qty': d['qty'],
                'subtotal': d['amount'] # 合算済み金額
            })

        # お釣り調整
        adjusted_payments = []
        remaining_change = change
        for method, amount in payments:
            if remaining_change > 0 and amount >= remaining_change:
                adjusted_payments.append((method, amount - remaining_change))
                remaining_change = 0
            else:
                adjusted_payments.append((method, amount))

        self.repo.save_transaction(
            total, self.selected_customer.label, self.current_user_name, 
            final_items_dicts, adjusted_payments, change
        )
        
        self.total_sales_today += total
        self.cart_items = []
        self.applied_discounts = []
        self.selected_customer = None
        self.checkout_completed.emit(self.selected_customer.label if self.selected_customer else "", change)
        self._recalculate()
    
    def is_discount_target(self, product_id: int) -> bool:
        return False

    def _notify_message(self, text: str, msg_type: str) -> None:
        self.message_updated.emit(text, msg_type)
        if hasattr(self, 'log_repo'): self.log_repo.add_log(msg_type, text)

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")