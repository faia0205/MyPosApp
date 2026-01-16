from PySide6.QtCore import QObject, Signal

class CartManager(QObject):
    cart_updated = Signal()      
    message_updated = Signal(str, str)
    
    # 統計情報の更新通知 (売上, 経費, 利益, 目標までの個数, 赤字フラグ)
    stats_updated = Signal(int, int, int, str, bool)

    def __init__(self, repository):
        super().__init__()
        self.repo = repository
        self.cart_items = []     # リスト構造: {'id':.., 'name':.., 'price':.., 'qty':.., 'is_manual':..}
        self.selected_customer = None
        self.current_expenses = self.repo.get_total_expenses()
        self.total_sales_today = 0 # 本日の確定売上（DBから取得または累積）
        self.avg_price = 500 # 簡易的な平均単価

    def add_product(self, product):
        """通常商品の追加"""
        # 既にカートにあるか確認
        found = False
        for item in self.cart_items:
            if item.get('id') == product['id'] and not item.get('is_manual'):
                item['qty'] += 1
                found = True
                break

        if not found:
            new_item = product.copy()
            new_item['qty'] = 1
            new_item['is_manual'] = False
            self.cart_items.append(new_item)
        
        # --- ★ここが復活・修正箇所★ ---
        # 注意書き判定を行い、UIへ通知を送る
        if product.get('note'):
            # 赤色の警告メッセージ
            self.message_updated.emit(f"⚠️ {product['name']}: {product['note']}", "warning")
        else:
            # 通常のメッセージ
            self.message_updated.emit(f"【追加】 {product['name']}", "info")
        # ---------------------------

        self._recalculate()

    def add_manual_item(self, price, name="手入力"):
        """手入力商品の追加"""
        new_item = {
            'id': None, # 手入力はIDなし
            'name': name,
            'price': price,
            'qty': 1,
            'color': '#ffffff',
            'is_manual': True
        }
        self.cart_items.append(new_item)
        self._recalculate()

    def update_item(self, index, new_qty, new_price):
        """カート内の指定行の商品を変更"""
        if 0 <= index < len(self.cart_items):
            self.cart_items[index]['qty'] = new_qty
            self.cart_items[index]['price'] = new_price
            self._recalculate()

    def remove_item(self, index):
        """カート内の指定行を削除"""
        if 0 <= index < len(self.cart_items):
            del self.cart_items[index]
            self._recalculate()

    def _recalculate(self):
        """合計計算 & 自動割引 & 統計更新"""
        # 1. 自動割引ロジック (例: 特定の商品があったら割引アイテムを自動挿入するなどの高度な処理はここ)
        # 今回はシンプルに合計計算のみ行います
        
        current_cart_total = sum(item["price"] * item["qty"] for item in self.cart_items)
        
        # 2. 統計情報の計算
        # 「現在の利益」 = (確定売上 + カート内予定売上) - 経費
        estimated_profit = (self.total_sales_today + current_cart_total) - self.current_expenses
        
        msg = "黒字達成!"
        is_red = False
        if estimated_profit < 0:
            is_red = True
            needed = (abs(estimated_profit) // self.avg_price) + 1
            msg = f"あと {needed} 個"

        # 通知
        self.cart_updated.emit()
        self.stats_updated.emit(
            self.total_sales_today + current_cart_total, 
            self.current_expenses, 
            estimated_profit, 
            msg, 
            is_red
        )

    def get_total_amount(self):
        return sum(item["price"] * item["qty"] for item in self.cart_items)