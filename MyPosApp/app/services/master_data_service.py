import json
import shutil
import os
import datetime
from typing import Dict, Any, List
from dataclasses import asdict

from app.config import DATA_DIR

# Models
from app.models.product import Product
from app.models.user import User
from app.models.customer import Customer
from app.models.payment_method import PaymentMethod
from app.models.expense import Expense
from app.models.discount import DiscountRule  # ★追加

# Repositories
from app.repositories.product_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.discount_repo import DiscountRepository

MASTER_JSON_PATH = os.path.join(DATA_DIR, 'master_data.json')

class MasterDataService:
    """
    マスターデータ(JSON)とデータベースの同期・変換を担当するサービス
    """
    def __init__(self):
        self.prod_repo = ProductRepository()
        self.user_repo = UserRepository()
        self.cust_repo = CustomerRepository()
        self.pay_repo = PaymentRepository()
        self.exp_repo = ExpenseRepository()
        self.disc_repo = DiscountRepository()

    # ==========================================
    # 1. DB -> JSON (Export / Backup)
    # ==========================================
    def save_db_to_json(self) -> bool:
        """
        現在のDBの状態をJSONファイルに書き出す（バックアップ作成含む）
        """
        try:
            # 1. バックアップを作成 (YYYYMMDD_HHMMSS)
            if os.path.exists(MASTER_JSON_PATH):
                now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = os.path.join(DATA_DIR, "backups")
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                backup_path = os.path.join(backup_dir, f"master_backup_{now_str}.json")
                shutil.copy(MASTER_JSON_PATH, backup_path)
                print(f"Backup created: {backup_path}")

            # 2. 各リポジトリからJSON用データを収集
            
            # 商品
            products_objs = self.prod_repo.fetch_all_as_models()
            products = [asdict(p) for p in products_objs]
            
            # ユーザー
            users_objs = self.user_repo.fetch_all_users()
            users = [asdict(u) for u in users_objs]
            
            # 客層 (Dataclass -> Dict変換と属性の整形)
            customers_objs = self.cust_repo.fetch_all()
            customers = []
            for c in customers_objs:
                c_dict = asdict(c)
                # JSONファイル仕様では "attributes": {dict} が求められるため
                # モデルのプロパティ(.attributes)を使って上書きし、不要な_jsonフィールドを消す
                c_dict['attributes'] = c.attributes 
                if 'attributes_json' in c_dict:
                    del c_dict['attributes_json']
                customers.append(c_dict)
            
            # 決済方法
            payment_methods = [asdict(pm) for pm in self.pay_repo.fetch_all()]
            
            # 経費項目
            expenses = []
            for ex in self.exp_repo.fetch_all():
                d = asdict(ex)
                expenses.append(d)

            # 割引ルール
            # ★修正: fetch_all_rules() はオブジェクトを返すようになったため、asdictで変換が必要
            discount_rules_objs = self.disc_repo.fetch_all_rules()
            discount_rules = [asdict(r) for r in discount_rules_objs]

            # データ構築
            master_data = {
                "products": products,
                "users": users,
                "customer_presets": customers,
                "payment_methods": payment_methods,
                "initial_expenses": expenses, 
                "discount_rules": discount_rules
            }
            
            # 3. JSON書き出し
            with open(MASTER_JSON_PATH, 'w', encoding='utf-8') as f:
                json.dump(master_data, f, ensure_ascii=False, indent=4)
            
            print("Master data exported to JSON successfully.")
            return True

        except Exception as e:
            print(f"Error exporting DB to JSON: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_json_safe(self) -> Dict:
        """JSON読み込み（エラーハンドリング付き）"""
        if not os.path.exists(MASTER_JSON_PATH):
            return {}
        try:
            with open(MASTER_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    # ==========================================
    # 2. JSON -> DB (Import / Sync)
    # ==========================================
    def sync_json_to_db(self):
        """
        起動時用: JSONの内容をDBに反映（簡易同期）
        既にデータがある場合、IDが一致すれば更新、なければ追加を行います。
        """
        data = self._load_json_safe()
        if not data:
            return

        print("Syncing JSON to DB...")

        # --- A. Products (商品) ---
        for p in data.get("products", []):
            exists_id = self.prod_repo.find_id_by_name(p["name"])
            
            target_product = Product(
                id=exists_id, 
                name=p["name"],
                price=p["price"],
                category=p["category"],
                color=p.get("color", "#ffcc80"),
                note=p.get("note", ""),
                is_active=p.get("is_active", True),
                display_order=p.get("display_order", 0)
            )
            # barcode対応
            if "barcode" in p:
                target_product.barcode = p["barcode"]

            if exists_id:
                self.prod_repo.update_product(target_product)
            else:
                self.prod_repo.add_product(target_product)
        
        # --- B. Users (ユーザー) ---
        for u in data.get("users", []):
            target_user = User(
                id=u.get("id"),
                name=u["name"],
                user_code=u["user_code"],
                role=u.get("role", "staff"),
                is_active=u.get("is_active", True)
            )
            self.user_repo.upsert_user(target_user)

        # --- C. Payment Methods (決済方法) ---
        for pm in data.get("payment_methods", []):
            target_pm = PaymentMethod(
                id=pm.get("id"),
                name=pm["name"],
                is_cash=pm.get("is_cash", False),
                is_active=pm.get("is_active", True)
            )
            # 簡易upsertロジック
            if target_pm.id:
                if not self.pay_repo.update(target_pm):
                    self.pay_repo.add(target_pm)
            else:
                self.pay_repo.add(target_pm)

        # --- D. Customer Presets (客層) ---
        for c in data.get("customer_presets", []):
            target_cust = Customer(
                id=c.get("id"),
                label=c["label"],
                attributes_json="", 
                color=c.get("color", "#ffffff"),
                display_order=c.get("display_order", 0),
                is_active=c.get("is_active", True)
            )
            target_cust.set_attributes(c.get("attributes", {}))

            if target_cust.id:
                if not self.cust_repo.update(target_cust):
                     self.cust_repo.add(target_cust)
            else:
                self.cust_repo.add(target_cust)

        # --- E. Initial Expenses (経費項目) ---
        # 起動時にJSONにある経費を追加するかは運用次第だが、
        # ここではマスタ定義的なものがもしあれば追加するロジック（今回は省略または最小限）
        pass 

        # --- F. Discount Rules (割引) ---
        # ★修正: 新しい DiscountRule オブジェクトを使って同期
        for r in data.get("discount_rules", []):
            target_rule = DiscountRule(
                id=r.get('id'),
                name=r['name'],
                discount_type=r['discount_type'],
                discount_value=r['discount_value'],
                apply_type=r['apply_type'],
                target_value=r.get('target_value', ""),
                is_auto=bool(r.get('is_auto', False)),
                is_active=bool(r.get('is_active', True))
            )
            
            # Repositoryの実装に合わせて upsert 的な処理
            if target_rule.id:
                if not self.disc_repo.update(target_rule):
                    self.disc_repo.add(target_rule)
            else:
                self.disc_repo.add(target_rule)

        print("Sync completed.")