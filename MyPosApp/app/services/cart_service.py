from typing import List, Tuple, Optional
import json
import urllib.parse
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

# services
from app.services.checkout_service import CheckoutService

class CartService(QObject):
    cart_updated = Signal()
    message_updated = Signal(str, str)
    stats_updated = Signal(int, int, int, str, bool)
    checkout_completed = Signal(int, int, str)
    user_changed = Signal(str)
    customer_selected = Signal(object)

    def __init__(self, 
                 prod_repo: ProductRepository,
                 disc_repo: DiscountRepository,
                 discount_manager: DiscountManager,
                 checkout_service: CheckoutService,
                 user_repo: UserRepository,     # 必要なRepoは注入
                 expense_repo: ExpenseRepository,
                 payment_repo: PaymentRepository, # PaymentDialog呼び出し等で使う場合
                 log_repo: LogRepository,
                 trans_repo: TransactionRepository
                 ) -> None:
        super().__init__()
        self.expense_repo = expense_repo
        self.payment_repo = payment_repo

        self.user_repo = user_repo
        self.prod_repo = prod_repo
        self.disc_repo = disc_repo
        self.log_repo = log_repo
        self.trans_repo = trans_repo
        
        self.discount_manager = discount_manager
        self.checkout_service = checkout_service
        self.calculator = PriceCalculator()
        
        self.cart_items: List[CartItem] = []
        self.applied_discounts: List[AppliedDiscount] = []
        
        self.current_user_name: str = "Admin"
        self.current_user_role: str = "admin"
        self.selected_customer: Optional[Customer] = None
        
        self.total_sales_today = 0
        self.current_expenses = 0
        self.avg_price_target = 0

        self._init_sales_data()

    def _init_sales_data(self):
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

    def get_applicable_rule_names(self, product: Product) -> List[str]:
        """商品に適用可能な割引ルール名を取得"""
        rules = self.disc_repo.fetch_active_rules()
        names = []
        
        for r in rules:
            t_val = r.target_value
            is_match = False
            
            if r.apply_type == 'cart':
                continue
            
            if r.apply_type == 'category':
                if t_val == product.category: is_match = True
            elif r.apply_type == 'item':
                if t_val == product.name: is_match = True
            elif r.apply_type == 'bundle':
                try:
                    data = json.loads(t_val)
                    if data.get('mode') == 'select':
                        targets = data.get('targets', [])
                        if product.name in targets or product.category in targets:
                            is_match = True
                    elif data.get('mode') == 'combo':
                        for cond in data.get('conditions', []):
                            c_target = cond.get('target')
                            if c_target == product.name or c_target == product.category:
                                is_match = True
                                break
                except:
                    if t_val and product.name in t_val: is_match = True
            
            if is_match:
                names.append(r.name)
        
        return names

    def add_product(self, product: Product):
        """商品リストからの追加"""
        
        # UIメッセージ用
        note_html = ""
        if product.note:
            note_html = f"<br><span style='color:#81d4fa'>※ {product.note}</span>"
            
        discount_html = ""
        rule_names = self.get_applicable_rule_names(product)
        if rule_names:
            joined_names = "|".join(rule_names)
            encoded_names = urllib.parse.quote(joined_names)
            count = len(rule_names)
            discount_html = (
                f"<br><span style='color:#ffeb3b'>★ {count}件の割引対象 "
                f"<a href='discount_details:{encoded_names}' style='color:#ffffff; text-decoration:underline; font-weight:bold;'>(詳細...)</a></span>"
            )

        for item in self.cart_items:
            if item.id == product.id:
                item.qty += 1
                self.recalculate()
                
                msg = f"<b>{item.name}</b> を追加しました (計{item.qty}個){note_html}{discount_html}"
                self._notify_message(msg, "info")
                # ★追加: DBログ
                self.log_repo.add_log("info", f"カート追加: {item.name} (計{item.qty}個)")
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
        
        msg = f"<b>{product.name}</b> をカートに入れました{note_html}{discount_html}"
        self._notify_message(msg, "info")
        # ★追加: DBログ
        self.log_repo.add_log("info", f"カート追加: {product.name}")

    def add_manual_item(self, price: int, name: str):
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
        
        self._notify_message(f"手入力追加: {name} (¥{price})", "info")
        # ★追加: DBログ
        self.log_repo.add_log("info", f"手入力追加: {name} (¥{price})")

    def remove_item(self, index: int):
        if 0 <= index < len(self.cart_items):
            item = self.cart_items.pop(index)
            self.recalculate()
            
            self._notify_message(f"削除: {item.name}", "warning")
            # ★追加: DBログ
            self.log_repo.add_log("info", f"カート削除: {item.name}")

    def update_item_qty(self, index: int, qty: int):
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            old_qty = item.qty
            if qty > 0:
                item.qty = qty
                self._notify_message(f"数量変更: {item.name} -> {qty}個", "info")
                # ★追加: DBログ
                self.log_repo.add_log("info", f"数量変更: {item.name} ({old_qty}->{qty})")
            else:
                self.cart_items.pop(index)
                self._notify_message(f"削除: {item.name}", "warning")
                self.log_repo.add_log("info", f"カート削除(数量0): {item.name}")
            self.recalculate()

    def decrease_item_qty(self, index: int):
        self._change_qty_delta(index, -1)

    def _change_qty_delta(self, index: int, delta: int):
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            new_qty = item.qty + delta
            
            if new_qty > 0:
                item.qty = new_qty
                msg = "数量追加" if delta > 0 else "数量減少"
                self._notify_message(f"{msg}: {item.name} (計{new_qty}個)", "info")
                self.log_repo.add_log("info", f"{msg}: {item.name} (計{new_qty}個)")
            else:
                self.cart_items.pop(index)
                self._notify_message(f"削除: {item.name}", "warning")
                self.log_repo.add_log("info", f"カート削除: {item.name}")
                
            self.recalculate()

    def update_item_price(self, index: int, new_price: int):
        if 0 <= index < len(self.cart_items):
            item = self.cart_items[index]
            old_price = item.price
            item.price = new_price
            self.recalculate()
            
            self._notify_message(f"単価変更: {item.name} (¥{old_price}→¥{new_price})", "info")
            # ★追加: DBログ
            self.log_repo.add_log("info", f"単価変更: {item.name} (¥{old_price}→¥{new_price})")

    def refresh_prices(self, active_products: List[Product]):
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
            self.log_repo.add_log("info", "カート内単価更新(マスタ同期)")

    def clear_cart(self):
        self.cart_items = []
        self.applied_discounts = []
        self.recalculate()
        self._notify_message("カートをクリアしました", "warning")
        self.log_repo.add_log("info", "カートクリア")

    def set_user(self, user_name: str, role: str = "staff"):
        self.current_user_name = user_name
        self.current_user_role = role
        self.user_changed.emit(user_name)
        self._notify_message(f"担当者変更: {user_name}", "info")
        self.log_repo.add_log("info", f"担当者変更: {user_name}")

    def set_current_user(self, user_name: str):
        self.set_user(user_name)

    def set_customer(self, customer: Optional[Customer]):
        self.selected_customer = customer
        self.customer_selected.emit(customer)
        self.recalculate()
        if customer:
            self._notify_message(f"客層選択: {customer.label}", "info")
            self.log_repo.add_log("info", f"客層選択: {customer.label}")
        else:
            self._notify_message("客層選択を解除しました", "info")

    def get_total_amount(self) -> int:
        sub_prod = sum(item.price * item.qty for item in self.cart_items)
        sub_disc = sum(d.amount for d in self.applied_discounts) 
        return sub_prod + sub_disc

    def finalize_checkout(self, payments: List[Tuple[str, int]], change: int) -> None:
        """会計確定処理"""

        if self.current_user_name in [None, "", "Guest"]:
            self._notify_message("担当者が選択されていません。会計できません。", "error")
            return
        
        if not self.cart_items or not self.selected_customer:
            self._notify_message("カートが空か、客層が未選択です", "warning")
            return

        total = self.get_total_amount()

        # 1. 明細リスト作成
        tx_items: List[TransactionItem] = []
        # カート商品
        for item in self.cart_items:
            tx_items.append(TransactionItem(
                id=None,
                transaction_id=None,
                product_name=item.name,
                unit_price=item.price,
                quantity=item.qty,
                subtotal=item.price * item.qty
            ))
        # 割引
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

        # 2. 決済リスト作成 (★修正箇所)
        tx_payments: List[TransactionPayment] = []
        
        # どの支払い方法が現金なのかを特定する
        # (DBに問い合わせてキャッシュする)
        all_methods = self.payment_repo.fetch_all()
        cash_method_names = {m.name for m in all_methods if m.is_cash}

        remaining_change = change
        
        # 計算用に一時リストを作成 (名前, 金額)
        temp_payments = [{'method': p[0], 'amount': p[1]} for p in payments]

        # お釣りがある場合、現金支払いからのみ減算する
        if remaining_change > 0:
            for p in temp_payments:
                if p['method'] in cash_method_names:
                    if p['amount'] >= remaining_change:
                        p['amount'] -= remaining_change
                        remaining_change = 0
                    else:
                        # 現金支払いが複数に分かれていて、1つ目でお釣りが引ききれない場合
                        remaining_change -= p['amount']
                        p['amount'] = 0
                    
                    if remaining_change == 0:
                        break
        
        # 0円より大きい支払いのみを保存対象にする
        for p in temp_payments:
            if p['amount'] != 0:
                tx_payments.append(TransactionPayment(
                    id=None,
                    transaction_id=None,
                    payment_method=p['method'],
                    amount=p['amount']
                ))

        # 3. ヘッダー作成
        current_customer_name = self.selected_customer.label
        transaction = Transaction(
            id=None,
            total_amount=total,
            change=change,
            customer_label=current_customer_name,
            cashier_name=self.current_user_name,
            status="completed",
            items=tx_items,
            payments=tx_payments
        )

        # 保存実行
        self.checkout_service.process_checkout(transaction)

        # 状態更新
        self.total_sales_today += total
        
        # カートクリア
        self.cart_items = []
        self.applied_discounts = []
        self.selected_customer = None
        
        self.checkout_completed.emit(total, change, current_customer_name)
        self.recalculate()
        

    def recalculate(self):
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
        """バッジ表示用"""
        product = self.prod_repo.get_product_by_id(product_id)
        if not product: return False
        rule_names = self.get_applicable_rule_names(product)
        return len(rule_names) > 0

    def _notify_message(self, text: str, msg_type: str) -> None:
        self.message_updated.emit(text, msg_type)

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")