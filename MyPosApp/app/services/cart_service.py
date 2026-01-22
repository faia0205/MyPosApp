from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, Signal
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.user_repo import UserRepository
from app.repositories.product_repo import ProductRepository
from app.repositories.discount_repo import DiscountRepository
from app.models.product import Product
from app.models.customer import Customer
# ★新規インポート
from app.logic.calculator import PriceCalculator
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
        # ★計算ロジッククラスのインスタンス化
        self.calculator = PriceCalculator()
        
        self.cart_items: List[Dict[str, Any]] = []     
        self.applied_discounts: List[Dict[str, Any]] = []
        self.selected_customer: Optional[Customer] = None 
        self.current_user_name = "未設定"

        self.current_expenses: int = self.repo.get_total_expenses()
        self.total_sales_today: int = self.repo.get_total_sales_today()
        
        # 平均単価の計算も本来はLogicに移せますが、Repo依存があるので一旦ここで計算
        self.avg_price_target = self._calculate_avg_price()
        
        # ルール読み込み
        self.discount_rules = self.disc_repo.fetch_rules_with_targets()

    def _calculate_avg_price(self) -> int:
        products = self.prod_repo.fetch_active_products()
        valid_prices = [p.price for p in products if p.price > 0]
        if not valid_prices:
            return 500
        return int(sum(valid_prices) / len(valid_prices))

    # --- 商品追加・削除系 ---
    def add_product(self, product: Product) -> None:
        for item in self.cart_items:
            if item.get('id') == product.id and not item.get('is_manual'):
                item['qty'] += 1
                
                # ★修正: カート内の単価を、マスタの最新価格に更新する
                # これにより「追加ボタンを押すと新価格が適用される」ようになります
                if item['price'] != product.price:
                    item['price'] = product.price
                    self._notify_message(f"【更新】 {product.name} の価格を更新しました", "info")
                
                self._notify_message(f"【追加】 {product.name} (+1)", "info")
                self._recalculate()
                return
        
        # 新規追加
        new_item = {'id': product.id, 'name': product.name, 'price': product.price, 'qty': 1, 'is_manual': False, 'note': product.note}
        self.cart_items.append(new_item)
        if product.note:
            self._notify_message(f"⚠️ {product.name}: {product.note}", "warning")
        else:
            self._notify_message(f"【追加】 {product.name}", "info")
        self._recalculate()
    
    # ★新規追加メソッド: マスタデータを受け取り、カート内の価格を一括更新する
    def refresh_prices(self, master_products: List[Product]) -> None:
        """
        設定変更後などに呼び出し、カートに入っている商品の価格を最新マスタに合わせる
        """
        # ID -> Product のマップを作成
        product_map = {p.id: p for p in master_products}
        
        updated_count = 0
        for item in self.cart_items:
            # 手入力商品(is_manual)はIDがない/Noneなので対象外
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

    # --- 計算・会計系 (修正) ---

    def get_total_amount(self) -> int:
        """計算機に委譲"""
        return self.calculator.calculate_grand_total(self.cart_items, self.applied_discounts)

    def _recalculate(self) -> None:
        """状態更新とシグナル発行 (計算機を使用)"""
        
        # 1. 割引計算 (Logicに委譲)
        self.applied_discounts = self.calculator.process_discounts(
            self.cart_items, 
            self.discount_rules
        )

        # 2. 合計金額計算 (Logicに委譲)
        grand_total = self.calculator.calculate_grand_total(
            self.cart_items, 
            self.applied_discounts
        )
        
        # 3. 利益予測 (Logicに委譲)
        est_profit, is_red, msg = self.calculator.calculate_profit_metrics(
            grand_total,
            self.total_sales_today,
            self.current_expenses,
            self.avg_price_target
        )

        # シグナル発行
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

        # 保存用リスト作成 (商品 + 割引)
        final_items = self.cart_items.copy()
        for d in self.applied_discounts:
            final_items.append({
                'name': d['name'],
                'price': d['amount'],
                'qty': d['qty'],
                'subtotal': d['amount'] * d['qty']
            })
        
        # ★重要: DB保存用に決済情報を「預かり金額」から「売上充当額」に変換する
        # 例: 合計300円に対し、現金1000円預かり(お釣り700円)の場合
        # paymentsは [('現金', 1000)] だが、DBには [('現金', 300)] と記録したい。
        # (そうしないと、売上集計で1000円売り上げたことになってしまうため)
        
        adjusted_payments = []
        remaining_change = change
        
        # 逆順で処理（通常は1種類ですが、複数決済の場合も考慮）
        # 現金払いがお釣り発生源と仮定して調整します
        for method, amount in payments:
            if remaining_change > 0 and amount >= remaining_change:
                # この決済方法からお釣りを捻出したとみなして減算
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
            
            # リセット
            self.cart_items = []
            self.applied_discounts = []
            self.selected_customer = None
            
            self.checkout_completed.emit(customer_label, change)
            self._recalculate()
            
        except Exception as e:
            self._notify_message(f"エラー: 保存に失敗しました {str(e)}", "warning")
            print(f"Checkout Error: {e}")

    def _notify_message(self, text: str, msg_type: str) -> None:
        """メッセージ通知 + ログ保存を行う"""
        
        # 1. 画面への通知 (スナックバーや履歴ウィンドウ用)
        self.message_updated.emit(text, msg_type)
        
        # 2. ★追加: データベースへの操作ログ保存
        # msg_type (info, warning, error) をそのままログレベルとして保存します
        try:
            # log_repo が初期化されていない場合のガード（念のため）
            if hasattr(self, 'log_repo'):
                self.log_repo.add_log(msg_type, text)
        except Exception as e:
            print(f"Log Error: {e}")
    
    def is_discount_target(self, product_id: int) -> bool:
        """指定された商品IDが、いずれかの割引ルールの対象か判定"""
        if product_id is None:
            return False
        
        for rule in self.discount_rules:
            if product_id in rule['target_ids']:
                return True
        return False

    def reset_message(self):
        self._notify_message("次の会計をお願いします", "info")