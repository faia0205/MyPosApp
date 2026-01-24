from typing import List, Dict, Tuple, Optional
from PySide6.QtCore import QObject, Signal

# Models
from app.models.product import Product
from app.models.customer import Customer
from app.models.cart_item import CartItem
from app.models.transaction import Transaction, TransactionItem, TransactionPayment

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
        self.applied_discounts: List[Dict] = []
        
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

    # ★修正: ProductListWidgetからの呼び出しに合わせてリネーム (add_item -> add_product)
    def add_product(self, product: Product):
        """商品リストからの追加"""
        for item in self.cart_items:
            # 既存なら数量+1
            if item.id == product.id:
                item.qty += 1
                self.recalculate()
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

    # ★追加: MainWindowの手入力用
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

    def remove_item(self, index: int):
        if 0 <= index < len(self.cart_items):
            self.cart_items.pop(index)
            self.recalculate()

    # ★追加: CartWidgetの入力欄(絶対値指定)用
    def update_item_qty(self, index: int, qty: int):
        """数量を直接指定"""
        if 0 <= index < len(self.cart_items):
            if qty > 0:
                self.cart_items[index].qty = qty
            else:
                self.cart_items.pop(index)
            self.recalculate()

    # ★追加: CartWidgetのマイナスボタン用
    def decrease_item_qty(self, index: int):
        """数量を1減らす"""
        self._change_qty_delta(index, -1)

    def _change_qty_delta(self, index: int, delta: int):
        """数量を差分で変更（内部ロジック）"""
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            new_qty = item.qty + delta
            if new_qty > 0:
                item.qty = new_qty
            else:
                self.cart_items.pop(index)
            self.recalculate()

    # ★追加: CartWidgetの単価変更用
    def update_item_price(self, index: int, new_price: int):
        """単価の変更"""
        if 0 <= index < len(self.cart_items):
            self.cart_items[index].price = new_price
            self.recalculate()

    # ★追加: MainWindowの設定変更反映用
    def refresh_prices(self, active_products: List[Product]):
        """マスタ更新時の価格同期"""
        product_map = {p.id: p.price for p in active_products}
        updated = False
        for item in self.cart_items:
            # 手入力商品(id=None)や、マスタにない商品は無視
            if item.id is not None and item.id in product_map:
                if item.price != product_map[item.id]:
                    item.price = product_map[item.id]
                    updated = True
        if updated:
            self.recalculate()

    def clear_cart(self):
        self.cart_items = []
        self.applied_discounts = []
        self.recalculate()

    def set_user(self, user_name: str, role: str = "staff"):
        self.current_user_name = user_name
        self.current_user_role = role
        self.user_changed.emit(user_name)

    # LoginDialog等の互換性用
    def set_current_user(self, user_name: str):
        # ロール取得ロジックを入れるのがベストだが、簡易的に
        # 必要なら user_repo から引く
        self.set_user(user_name)

    def set_customer(self, customer: Optional[Customer]):
        self.selected_customer = customer
        self.customer_selected.emit(customer)
        self.recalculate()

    def get_total_amount(self) -> int:
        sub_prod = sum(item.price * item.qty for item in self.cart_items)
        sub_disc = sum(d['amount'] for d in self.applied_discounts) # amountは負数
        return max(0, sub_prod + sub_disc)

    def finalize_checkout(self, payments: List[Tuple[str, int]], change: int) -> None:
        """会計確定処理"""
        if not self.cart_items or not self.selected_customer:
            self._notify_message("カートが空か、客層が未選択です", "warning")
            return
        
        total = self.get_total_amount()
        
        # 1. 明細リスト作成
        tx_items: List[TransactionItem] = []
        
        # 商品明細
        for item in self.cart_items:
            tx_items.append(TransactionItem(
                id=None, 
                transaction_id=None,
                product_name=item.name,
                unit_price=item.price,
                quantity=item.qty,
                subtotal=item.price * item.qty
            ))
            
        # 割引明細
        for d in self.applied_discounts:
            qty = d['qty'] if d['qty'] > 0 else 1
            total_disc = d['amount']
            unit_price = int(total_disc / qty)

            tx_items.append(TransactionItem(
                id=None, 
                transaction_id=None,
                product_name=d['name'],
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

        # 保存実行
        self.trans_repo.save(transaction)
        
        # 状態更新
        self.total_sales_today += total
        grand_total = self.calculator.calculate_grand_total(self.cart_items, self.applied_discounts)

        # カートクリア
        self.cart_items = []
        self.applied_discounts = []
        self.selected_customer = None
        
        self.checkout_completed.emit(grand_total, change, current_customer_name)
        self.recalculate()
        
        self.log_repo.add_log("info", f"会計完了: ¥{total}")

    def recalculate(self):
        """カート状態の再計算とシグナル発火"""
        # 1. 割引適用計算
        rules = self.disc_repo.fetch_active_rules()
        self.applied_discounts = self.discount_manager.calculate_discounts(self.cart_items, rules)
        
        # 2. 合計計算
        grand_total = self.get_total_amount()
        
        # 3. カート更新通知
        self.cart_updated.emit()
        
        # 4. 統計更新通知
        est_profit, is_red, msg = self.calculator.calculate_profit_metrics(
            grand_total,
            self.total_sales_today,
            self.current_expenses, 
            self.avg_price_target
        )
        self.stats_updated.emit(self.total_sales_today, self.current_expenses, est_profit, msg, is_red)
   
    def is_discount_target(self, product_id: int) -> bool:
        """商品が何らかの割引対象になり得るか判定（UIのバッジ表示用）"""
        rules = self.disc_repo.fetch_active_rules()
        product = self.prod_repo.get_product_by_id(product_id)
        if not product: return False
        
        for r in rules:
            t_val = r['target_value']
            if (r['apply_type'] == 'category' and t_val == product.category):
                return True
            if (r['apply_type'] == 'item' and t_val == product.name):
                return True
            if (r['apply_type'] == 'bundle'):
                if t_val and product.name in t_val: 
                    return True
        return False

    def _notify_message(self, text: str, msg_type: str) -> None:
        self.message_updated.emit(text, msg_type)

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")