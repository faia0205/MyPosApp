from PySide6.QtCore import QObject, Signal

class CartManager(QObject):
    # シグナル定義
    cart_updated = Signal()      
    message_updated = Signal(str, str)
    stats_updated = Signal(int, int, int, str, bool)
    
    # ★追加: 会計完了通知 (UIのリセット用)
    checkout_completed = Signal(str, int) 

    def __init__(self, repository):
        super().__init__()
        self.repo = repository
        self.cart_items = []
        self.selected_customer = None
        self.current_expenses = self.repo.get_total_expenses()
        self.total_sales_today = 0
        self.avg_price = 500

    def add_product(self, product):
        """通常商品の追加"""
        # 重複チェック(手入力以外)
        for item in self.cart_items:
            if item.get('id') == product['id'] and not item.get('is_manual'):
                item['qty'] += 1
                self._notify_add(product) # メッセージ通知
                self._recalculate()
                return

        new_item = product.copy()
        new_item['qty'] = 1
        new_item['is_manual'] = False
        self.cart_items.append(new_item)
        self._notify_add(product)
        self._recalculate()

    def add_manual_item(self, price, name):
        """手入力商品の追加"""
        new_item = {
            'id': None, 'name': name, 'price': price, 
            'qty': 1, 'color': '#795548', 'is_manual': True
        }
        self.cart_items.append(new_item)
        # ★追加: 手入力も情報ボックスに表示
        self.message_updated.emit(f"【手入力】 {name}: ¥{price}", "info")
        self._recalculate()

    def update_item_qty(self, row, new_qty):
        """個数変更 (0以下なら削除はUI側またはここで行うが、今回は変更のみ)"""
        if 0 <= row < len(self.cart_items):
            self.cart_items[row]['qty'] = new_qty
            self._recalculate()

    def decrease_item(self, row):
        """★追加: 個数を1減らす"""
        if 0 <= row < len(self.cart_items):
            if self.cart_items[row]['qty'] > 1:
                self.cart_items[row]['qty'] -= 1
            else:
                # 1個なら削除
                del self.cart_items[row]
            self._recalculate()

    def remove_item(self, row):
        """削除"""
        if 0 <= row < len(self.cart_items):
            del self.cart_items[row]
            self._recalculate()

    def process_checkout(self):
        """★追加: 会計処理を実行し、データをリセットする"""
        if not self.cart_items: return

        total = self.get_total_amount()
        customer_label = self.selected_customer['label'] if self.selected_customer else "未選択"

        # TODO: ここで self.repo.save_transaction(...) を呼ぶ

        # 状態リセット
        self.cart_items = []
        self.selected_customer = None
        self.total_sales_today += total # 今日の売上加算
        
        # 完了通知
        self.checkout_completed.emit(customer_label, total)
        self._recalculate()

    def get_total_amount(self):
        return sum(item["price"] * item["qty"] for item in self.cart_items)

    def _notify_add(self, product):
        """追加時のメッセージ判定"""
        if product.get('note'):
            self.message_updated.emit(f"⚠️ {product['name']}: {product['note']}", "warning")
        else:
            self.message_updated.emit(f"【追加】 {product['name']}", "info")

    def _recalculate(self):
        """計算と通知"""
        current_total = self.get_total_amount()
        # 利益予想
        profit = (self.total_sales_today + current_total) - self.current_expenses
        
        msg, is_red = "黒字達成!", False
        if profit < 0:
            is_red = True
            needed = (abs(profit) // self.avg_price) + 1
            msg = f"あと {needed} 個"

        self.cart_updated.emit()
        self.stats_updated.emit(
            self.total_sales_today + current_total, 
            self.current_expenses, profit, msg, is_red
        )