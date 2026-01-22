import json
import shutil
import os
import datetime
from typing import Dict, Any, List

from app.config import DATA_DIR
from app.repositories.product_repo import ProductRepository
from app.repositories.user_repo import UserRepository
from app.repositories.customer_repo import CustomerRepository
from app.repositories.discount_repo import DiscountRepository
from app.repositories.transaction_repo import TransactionRepository 

MASTER_JSON_PATH = os.path.join(DATA_DIR, 'master_data.json')

class MasterDataService:
    """
    マスターデータ(JSON)とデータベースの同期・変換を担当するサービス
    """
    def __init__(self):
        self.prod_repo = ProductRepository()
        self.user_repo = UserRepository()
        self.cust_repo = CustomerRepository()
        self.disc_repo = DiscountRepository()
        self.trans_repo = TransactionRepository() 

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
            products = self.prod_repo.fetch_all_for_json()
            
            # ユーザー
            users = self.user_repo.fetch_all_for_json()
            
            # 客層 (is_active含む)
            customers = self.cust_repo.fetch_all_for_json()
            
            # 決済方法
            payment_methods = self.trans_repo.fetch_payment_methods_for_json()
            
            # 経費 (DBの経費履歴を保存)
            expenses = self.trans_repo.fetch_expenses_for_json()

            # 割引ルール (新しいテーブル構造をそのまま取得)
            discount_rules = self.disc_repo.fetch_all_rules()

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
        ※ 基本的には init_db.py で初期化される想定ですが、
           アプリ起動時にJSONの変更を取り込みたい場合に使用
        """
        data = self._load_json_safe()
        if not data:
            return

        # A. Products
        for p in data.get("products", []):
            exists = self.prod_repo.find_id_by_name(p["name"])
            if exists:
                self.prod_repo.update_product(
                    exists, p["name"], p["price"], p["category"], 
                    p.get("color", "#ffcc80"), p.get("note", ""), p.get("is_active", True)
                )
            else:
                self.prod_repo.add_product(
                    p["name"], p["price"], p["category"], 
                    p.get("color", "#ffcc80"), p.get("note", "")
                )
        
        # B. Users
        for u in data.get("users", []):
            self.user_repo.upsert_user(
                u["name"], u["user_code"], u.get("role", "staff"), u.get("is_active", True)
            )

        # C. Payment Methods
        for pm in data.get("payment_methods", []):
            self.trans_repo.upsert_payment_method(
                pm["name"], pm["is_cash"], pm.get("is_active", True)
            )
        
        # 客層、経費、割引ルールについては構造変更があったため、
        # 中途半端な同期よりも「設定保存 -> JSON作成 -> init_db.pyでDB再構築」のフローが安全です。
        # したがってここでは同期スキップします。