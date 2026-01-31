import json
import shutil
import os
import datetime
from typing import Dict

# Config
from app.config import DATA_DIR

# 定数をここで定義
MASTER_JSON_PATH = os.path.join(DATA_DIR, 'master_data.json')

# Models
from app.models.product import Product
from app.models.user import User
from app.models.customer import Customer
from app.models.payment_method import PaymentMethod
from app.models.expense import Expense
from app.models.discount import DiscountRule

# Repositories
from app.repositories.product_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.discount_repo import DiscountRepository

class MasterDataService:
    """
    マスターデータ(JSON)とデータベースの同期・変換を担当するサービス
    SRP対応: データ変換ロジックは各Modelの to_dict / from_dict に委譲済み
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

            # 2. 各リポジトリからデータを収集し、モデルの to_dict() で変換
            master_data = {
                "products": [p.to_dict() for p in self.prod_repo.fetch_all_as_models()],
                "users": [u.to_dict() for u in self.user_repo.fetch_all_users()],
                "customer_presets": [c.to_dict() for c in self.cust_repo.fetch_all()],
                "payment_methods": [p.to_dict() for p in self.pay_repo.fetch_all()],
                "initial_expenses": [e.to_dict() for e in self.exp_repo.fetch_all()],
                "discount_rules": [r.to_dict() for r in self.disc_repo.fetch_all_rules()]
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
        モデルの from_dict() を使用してオブジェクトを生成し、リポジトリで保存
        """
        data = self._load_json_safe()
        if not data:
            return

        print("Syncing JSON to DB...")

        # --- A. Products (商品) ---
        for p_data in data.get("products", []):
            prod = Product.from_dict(p_data)
            # 名前でIDを検索して更新か新規かを判定
            exists_id = self.prod_repo.find_id_by_name(prod.name)
            prod.id = exists_id # IDがあればセット
            
            if exists_id:
                self.prod_repo.update_product(prod)
            else:
                self.prod_repo.add_product(prod)

        # --- B. Users (ユーザー) ---
        for u_data in data.get("users", []):
            user = User.from_dict(u_data)
            # user_code をキーに upsert
            self.user_repo.upsert_user(user)

        # --- C. Payment Methods (決済方法) ---
        for pm_data in data.get("payment_methods", []):
            pm = PaymentMethod.from_dict(pm_data)
            if pm.id:
                if not self.pay_repo.update(pm):
                    self.pay_repo.add(pm)
            else:
                self.pay_repo.add(pm)

        # --- D. Customer Presets (客層) ---
        for c_data in data.get("customer_presets", []):
            cust = Customer.from_dict(c_data)
            if cust.id:
                if not self.cust_repo.update(cust):
                    self.cust_repo.add(cust)
            else:
                self.cust_repo.add(cust)

        # --- E. Initial Expenses (経費項目) ---
        # 起動時の初期経費登録などは運用に合わせて実装（今回はスキップまたは追加のみ）
        # for e_data in data.get("initial_expenses", []):
        #     self.exp_repo.add(e_data['title'], e_data['amount'])
        pass

        # --- F. Discount Rules (割引) ---
        for r_data in data.get("discount_rules", []):
            rule = DiscountRule.from_dict(r_data)
            if rule.id:
                if not self.disc_repo.update(rule):
                    self.disc_repo.add(rule)
            else:
                self.disc_repo.add(rule)

        print("Sync completed.")