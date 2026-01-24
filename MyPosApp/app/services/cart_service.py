from typing import List, Tuple, Optional
import json
from PySide6.QtCore import QObject, Signal

# Models
from app.models.product import Product
from app.models.customer import Customer
from app.models.cart_item import CartItem
from app.models.transaction import Transaction, TransactionItem, TransactionPayment
from app.models.discount import AppliedDiscount

# Repositories
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository

# Logic
from app.logic.calculator import PriceCalculator
from app.logic.discount_manager import DiscountManager

class CartService(QObject):
    cart_updated = Signal()
    message_updated = Signal(str, str)
    stats_updated = Signal(int, int, int, str, bool)
    checkout_completed = Signal(int, int, str)
    user_changed = Signal(str)
    customer_selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.trans_repo = TransactionRepository()
        self.expense_repo = ExpenseRepository()
        self.payment_repo = PaymentRepository()

        self.user_repo = UserRepository()
        self.prod_repo = ProductRepository()
        self.disc_repo = DiscountRepository()
        self.log_repo = LogRepository()
        
        self.calculator = PriceCalculator()
        self.discount_manager = DiscountManager()
        
        self.cart_items: List[CartItem] = []
        self.applied_discounts: List[AppliedDiscount] = []
        
        self.current_user_name: str = "Admin"
        self.current_user_role: str = "admin"
        self.selected_customer: Optional[Customer] = None
        
        # 統計用キャッシュ
        self.total_sales_today = 0
        self.current_expenses = 0
        self.avg_price_target = 0
        
        self._init_sales_data()

    def _init_sales_data(self):
        """起動時に本日の売上・経費・目標単価を取得"""
        self.total_sales_today = self.trans_repo.get_total_sales_today()
        self.current_expenses = self.expense_repo.get_total_expenses()
        self.avg_price_target = self._calculate_avg_price()

    def _calculate_avg_price(self) -> int:
        products = self.prod_repo.fetch_all_as_models()
        if not products:
            return 1000
        total_p = sum(p.price for p in products if p.is_active)
        count = sum(1 for p in products if p.is_active)
        return int(total_p / count) if count > 0 else 1000

    def add_product(self, product: Product):
        """商品リストからの追加"""
        for item in self.cart_items:
            if item.id == product.id:
                item.qty += 1
                self.recalculate()
                # ★追加
                self._notify_message(f"数量追加: {item.name} (計{item.qty}個)", "info")
                return
        
        new_item = CartItem(
            id=product.id,
            name=product.name,
            price=product.price,
            qty=1,
            category=product.category
        )
        self.cart_items.append(new_item)
        self.recalculate()
        # ★追加
        self._notify_message(f"カートに追加: {product.name}", "info")

    def add_manual_item(self, price: int, name: str):
        """手入力商品の追加"""
        new_item = CartItem(
            id=None,
            name=name,
            price=price,
            qty=1,
            category="手入力",
            is_manual=True
        )
        self.cart_items.append(new_item)
        self.recalculate()
        # ★追加
        self._notify_message(f"手入力追加: {name} (¥{price})", "info")

    def remove_item(self, index: int):
        if 0 <= index < len(self.cart_items):
            item = self.cart_items.pop(index)
            self.recalculate()
            # ★追加
            self._notify_message(f"削除: {item.name}", "warning")

    def update_item_qty(self, index: int, qty: int):
        """数量を直接指定"""
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            if qty > 0:
                item.qty = qty
                self._notify_message(f"数量変更: {item.name} -> {qty}個", "info")
            else:
                self.cart_items.pop(index)
                self._notify_message(f"削除: {item.name}", "warning")
            self.recalculate()

    def decrease_item_qty(self, index: int):
        """数量を1減らす"""
        self._change_qty_delta(index, -1)

    def _change_qty_delta(self, index: int, delta: int):
        """数量を差分で変更"""
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            new_qty = item.qty + delta
            
            if new_qty > 0:
                item.qty = new_qty
                msg = "数量追加" if delta > 0 else "数量減少"
                self._notify_message(f"{msg}: {item.name} (計{new_qty}個)", "info")
            else:
                self.cart_items.pop(index)
                self._notify_message(f"削除: {item.name}", "warning")
                
            self.recalculate()

    def update_item_price(self, index: int, new_price: int):
        """単価の変更"""
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            old_price = item.price
            item.price = new_price
            self.recalculate()
            # ★追加
            self._notify_message(f"単価変更: {item.name} (¥{old_price}→¥{new_price})", "info")

    def refresh_prices(self, active_products: List[Product]):
        """マスタ更新時の価格同期"""
        product_map = {p.id: p.price for p in active_products}
        updated = False
        for item in self.cart_items:
            if item.id is not None and item.id in product_map:
                if item.price != product_map[item.id]:
                    item.price = product_map[item.id]
                    updated = True
        if updated:
            self.recalculate()
            self._notify_message("商品マスタに合わせて価格を更新しました", "info")

    def clear_cart(self):
        self.cart_items = []
        self.applied_discounts = []
        self.recalculate()
        # ★追加
        self._notify_message("カートをクリアしました", "warning")

    def set_user(self, user_name: str, role: str = "staff"):
        self.current_user_name = user_name
        self.current_user_role = role
        self.user_changed.emit(user_name)
        # ★追加
        self._notify_message(f"担当者変更: {user_name}", "info")

    def set_current_user(self, user_name: str):
        self.set_user(user_name)

    def set_customer(self, customer: Optional[Customer]):
        self.selected_customer = customer
        self.customer_selected.emit(customer)
        self.recalculate()
        # ★追加
        if customer:
            self._notify_message(f"客層選択: {customer.label}", "info")
        else:
            self._notify_message("客層選択を解除しました", "info")

    def get_total_amount(self) -> int:
        sub_prod = sum(item.price * item.qty for item in self.cart_items)
        sub_disc = sum(d.amount for d in self.applied_discounts) 
        return max(0, sub_prod + sub_disc)

    def finalize_checkout(self, payments: List[Tuple[str, int]], change: int) -> None:
        """会計確定処理"""
        if not self.cart_items or not self.selected_customer:
            self._notify_message("カートが空か、客層が未選択です", "warning")
            return
        
        total = self.get_total_amount()
        
        # 1. 明細リスト作成
        tx_items: List[TransactionItem] = []
        
        for item in self.cart_items:
            tx_items.append(TransactionItem(
                id=None, 
                transaction_id=None,
                product_name=item.name,
                unit_price=item.price,
                quantity=item.qty,
                subtotal=item.price * item.qty
            ))
            
        for d in self.applied_discounts:
            qty = d.qty if d.qty > 0 else 1
            total_disc = d.amount
            unit_price = int(total_disc / qty)

            tx_items.append(TransactionItem(
                id=None, 
                transaction_id=None,
                product_name=d.name,
                unit_price=unit_price,
                quantity=qty,
                subtotal=total_disc
            ))

        # 2. 決済リスト作成
        tx_payments: List[TransactionPayment] = []
        remaining_change = change
        
        for method, amount in payments:
            actual_pay = amount
            if remaining_change > 0 and amount >= remaining_change:
                actual_pay = amount - remaining_change
                remaining_change = 0
            
            if actual_pay > 0:
                tx_payments.append(TransactionPayment(
                    id=None, 
                    transaction_id=None,
                    payment_method=method,
                    amount=actual_pay
                ))

        # 3. ヘッダー作成
        current_customer_name = self.selected_customer.label
        
        transaction = Transaction(
            id=None,
            total_amount=total,
            change=change,
            customer_label=current_customer_name,
            cashier_name=self.current_user_name,
            items=tx_items,
            payments=tx_payments
        )

        self.trans_repo.save(transaction)
        
        self.total_sales_today += total
        grand_total = self.get_total_amount()

        self.cart_items = []
        self.applied_discounts = []
        self.selected_customer = None
        
        self.checkout_completed.emit(grand_total, change, current_customer_name)
        self.recalculate()
        
        self.log_repo.add_log("info", f"会計完了: ¥{total}")

    def recalculate(self):
        """カート状態の再計算"""
        rules = self.disc_repo.fetch_active_rules()
        self.applied_discounts = self.discount_manager.calculate_discounts(self.cart_items, rules)
        
        grand_total = self.get_total_amount()
        
        self.cart_updated.emit()
        
        est_profit, is_red, msg = self.calculator.calculate_profit_metrics(
            grand_total,
            self.total_sales_today,
            self.current_expenses, 
            self.avg_price_target
        )
        self.stats_updated.emit(self.total_sales_today, self.current_expenses, est_profit, msg, is_red)
   
    def is_discount_target(self, product_id: int) -> bool:
        """商品が何らかの割引対象になり得るか判定"""
        rules = self.disc_repo.fetch_active_rules()
        product = self.prod_repo.get_product_by_id(product_id)
        if not product: return False
        
        for r in rules:
            t_val = r.target_value
            if r.apply_type == 'category':
                if t_val == product.category: return True
            elif r.apply_type == 'item':
                if t_val == product.name: return True
            elif r.apply_type == 'bundle':
                try:
                    data = json.loads(t_val)
                    if data.get('mode') == 'select':
                        targets = data.get('targets', [])
                        if product.name in targets: return True
                        if product.category in targets: return True
                    elif data.get('mode') == 'combo':
                        for cond in data.get('conditions', []):
                            c_target = cond.get('target')
                            if c_target == product.name: return True
                            if c_target == product.category: return True
                except:
                    if t_val and product.name in t_val: return True
        return False

    def _notify_message(self, text: str, msg_type: str) -> None:
        self.message_updated.emit(text, msg_type)

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")