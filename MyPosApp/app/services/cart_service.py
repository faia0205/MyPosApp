from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, Signal
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.discount_repo import DiscountRepository
from app.models.product import Product
from app.models.customer import Customer
from app.logic.calculator import PriceCalculator
from app.logic.discount_manager import DiscountManager
from app.repositories.log_repo import LogRepository

class CartService(QObject):
    # シグナル定義
    cart_updated = Signal()
    message_updated = Signal(str, str)
    stats_updated = Signal(int, int, int, str, bool)
    checkout_completed = Signal(str, int)
    user_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.repo = TransactionRepository()
        self.user_repo = UserRepository()
        self.prod_repo = ProductRepository()
        self.disc_repo = DiscountRepository()
        self.log_repo = LogRepository()
        self.calculator = PriceCalculator()
        self.discount_manager = DiscountManager()
        
        self.cart_items: List[Dict[str, Any]] = []     
        self.applied_discounts: List[Dict[str, Any]] = []
        self.selected_customer: Optional[Customer] = None 
        self.current_user_name = "未設定"

        self.current_expenses: int = self.repo.get_total_expenses()
        self.total_sales_today: int = self.repo.get_total_sales_today()
        
        self.avg_price_target = self._calculate_avg_price()
        
        # ★修正: 新しいリポジトリメソッドを使用
        self.discount_rules = self.disc_repo.fetch_active_rules()

    def _calculate_avg_price(self) -> int:
        products = self.prod_repo.fetch_active_products()
        valid_prices = [p.price for p in products if p.price > 0]
        if not valid_prices:
            return 500
        return int(sum(valid_prices) / len(valid_prices))

    # --- 商品追加・削除系 ---
    def add_product(self, product: Product) -> None:
        for item in self.cart_items:
            # 手入力(is_manual=True)以外でIDが一致すれば個数増加
            if item.get('id') == product.id and not item.get('is_manual'):
                item['qty'] += 1
                if item['price'] != product.price:
                    item['price'] = product.price
                    self._notify_message(f"【更新】 {product.name} の価格を更新しました", "info")
                
                self._notify_message(f"【追加】 {product.name} (+1)", "info")
                self._recalculate()
                return
        
        # 新規追加
        new_item = {
            'id': product.id, 
            'name': product.name, 
            'price': product.price, 
            'category': product.category or "その他", # ★ここ
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
    
    def refresh_prices(self, master_products: List[Product]) -> None:
        """マスタデータ更新時にカート内の価格を最新化"""
        product_map = {p.id: p for p in master_products}
        updated_count = 0
        for item in self.cart_items:
            if not item.get('is_manual') and item.get('id') in product_map:
                new_price = product_map[item['id']].price
                if item['price'] != new_price:
                    item['price'] = new_price
                    updated_count += 1
        if updated_count > 0:
            self._notify_message(f"{updated_count}件の価格情報を更新しました", "info")

    def add_manual_item(self, price: int, name: str) -> None:
        new_item = {'id': None, 'name': name, 'price': price, 'qty': 1, 'is_manual': True, 'note': "手入力"}
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

    def set_current_user(self, name: str):
        self.current_user_name = name
        self.user_changed.emit(name)
        self._notify_message(f"担当者: {name} さんでログインしました", "info")

    # --- ★新規追加: 手動割引適用ロジック ---
    def apply_manual_discount(self, rule: Dict[str, Any]) -> None:
        """手動で選択された割引ルールを適用する"""
        name = rule['name']
        d_type = rule['discount_type'] # 'fixed', 'percent'
        d_val = rule['discount_value']
        a_type = rule['apply_type']    # 'cart', 'category', 'item'
        target = rule['target_value']
        
        discount_amount = 0

        # A. カート全体割引 -> マイナスの商品として追加
        if a_type == 'cart':
            current_total = self.get_total_amount() # 現在の小計
            if d_type == 'fixed':
                discount_amount = d_val
            else: # percent
                import math
                discount_amount = math.floor(current_total * (d_val / 100))
            
            if discount_amount > 0:
                self.cart_items.append({
                    'id': None,
                    'name': f"【割】{name}",
                    'price': -discount_amount, # マイナス
                    'qty': 1,
                    'is_manual': True,
                    'note': f"全体{d_val}{'%' if d_type=='percent' else '円'}引"
                })
                self._notify_message(f"割引適用: {name} (-¥{discount_amount:,})", "info")
                self._recalculate()
                return

        # B. カテゴリ/商品割引
        elif a_type in ['category', 'item']:
            target_subtotal = 0
            for item in self.cart_items:
                is_target = False
                if a_type == 'item':
                    if item['name'] == target: is_target = True
                elif a_type == 'category':
                    # 商品IDからカテゴリを確認 (本来はitemにcategoryを持たせるのが理想)
                    if item.get('id'):
                        prod = self.prod_repo.get_product_by_id(item['id'])
                        if prod and prod.category == target:
                            is_target = True
                
                if is_target:
                    target_subtotal += (item['price'] * item['qty'])

            if target_subtotal > 0:
                if d_type == 'fixed':
                    discount_amount = d_val
                else:
                    import math
                    discount_amount = math.floor(target_subtotal * (d_val / 100))
                
                if discount_amount > 0:
                    self.cart_items.append({
                        'id': None,
                        'name': f"【割】{name} ({target})",
                        'price': -discount_amount,
                        'qty': 1,
                        'is_manual': True,
                        'note': f"対象計¥{target_subtotal}から"
                    })
                    self._notify_message(f"割引適用: {name} (-¥{discount_amount:,})", "info")
                    self._recalculate()
            else:
                self._notify_message("割引対象の商品がカートにありません", "warning")

    # --- 計算・会計系 ---

    def get_total_amount(self) -> int:
        return self.calculator.calculate_grand_total(self.cart_items, self.applied_discounts)

    def _recalculate(self) -> None:
        """状態更新とシグナル発行"""
        
        # 1. 自動割引計算 (★修正: DiscountManagerを使用)
        # activeなルールを最新化しても良いが、パフォーマンス次第
        # self.discount_rules = self.disc_repo.fetch_active_rules() 
        self.applied_discounts = self.discount_manager.calculate_discounts(
            self.cart_items, 
            self.discount_rules
        )

        # 2. 合計金額計算
        grand_total = self.calculator.calculate_grand_total(
            self.cart_items, 
            self.applied_discounts
        )
        
        # 3. 利益予測
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

    def finalize_checkout(self, payments: List[Tuple[str, int]], change: int) -> None:
        if not self.cart_items or not self.selected_customer:
            return

        total = self.get_total_amount()
        customer_label = self.selected_customer.label

        final_items = self.cart_items.copy()
        for d in self.applied_discounts:
            final_items.append({
                'name': d['name'],
                'price': d['amount'],
                'qty': d['qty'],
                'subtotal': d['amount'] * d['qty']
            })
        
        adjusted_payments = []
        remaining_change = change
        
        for method, amount in payments:
            if remaining_change > 0 and amount >= remaining_change:
                real_sales_amount = amount - remaining_change
                adjusted_payments.append((method, real_sales_amount))
                remaining_change = 0
            else:
                adjusted_payments.append((method, amount))

        try:
            self.repo.save_transaction(
                total, customer_label, self.current_user_name, 
                final_items, adjusted_payments, change
            )
            self.total_sales_today += total
            
            self.cart_items = []
            self.applied_discounts = []
            self.selected_customer = None
            
            self.checkout_completed.emit(customer_label, change)
            self._recalculate()
            
        except Exception as e:
            self._notify_message(f"エラー: 保存に失敗しました {str(e)}", "warning")
            print(f"Checkout Error: {e}")

    def _notify_message(self, text: str, msg_type: str) -> None:
        self.message_updated.emit(text, msg_type)
        try:
            if hasattr(self, 'log_repo'):
                self.log_repo.add_log(msg_type, text)
        except Exception as e:
            print(f"Log Error: {e}")
    
    def is_discount_target(self, product_id: int) -> bool:
        """指定された商品IDが、いずれかの割引ルールの対象か判定"""
        # ★修正: データ構造が変わったため、一旦 False を返してクラッシュを防ぐ
        # 将来的には is_auto=True のルールをチェックするロジックを実装
        return False

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")