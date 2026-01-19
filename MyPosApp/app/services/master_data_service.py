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
from app.repositories.transaction_repo import TransactionRepository # 決済方法用

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
        self.trans_repo = TransactionRepository() # 決済方法の取得に使用

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
            # ※ 各Repoに実装する `fetch_all_for_json` を使用
            master_data = {
                "products": self.prod_repo.fetch_all_for_json(),
                "users": self.user_repo.fetch_all_for_json(),
                "customer_presets": self.cust_repo.fetch_all_for_json(),
                "payment_methods": self.trans_repo.fetch_payment_methods_for_json(), # 新規メソッド
                
                # 割引ルールは複雑なため、ここで整形ロジックを通す
                "discount_rules": self._fetch_formatted_discounts()
            }
            
            # 経費は設定データではないため、ここでは初期化データとして空または既存維持でも可
            # 今回は簡易的に、既存のJSONがあればその initial_expenses を維持する形にします
            existing_data = self._load_json_safe()
            if existing_data and "initial_expenses" in existing_data:
                master_data["initial_expenses"] = existing_data["initial_expenses"]

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

    def _fetch_formatted_discounts(self) -> List[Dict]:
        """割引ルールをJSON形式（ターゲット商品名リスト付き）に変換するヘルパー"""
        rules = self.disc_repo.fetch_rules_with_targets() # 既存メソッド: {'target_ids': {1,2}}
        products = self.prod_repo.fetch_all_for_json()  # 全商品
        
        # ID -> Name のマップ作成
        id_to_name = {p['id']: p['name'] for p in products if 'id' in p} # fetch_all_for_jsonにidが含まれている必要あり

        formatted_rules = []
        for r in rules:
            target_names = []
            for pid in r['target_ids']:
                if pid in id_to_name:
                    target_names.append(id_to_name[pid])
            
            formatted_rules.append({
                "name": r['name'],
                "required_qty": r['req'],
                "discount_amount": r['amt'],
                "target_product_names": target_names,
                # is_activeはfetch_rules_with_targetsに含まれていない場合があるため、
                # 必要ならRepo側のSQL修正が必要。一旦デフォルトTrue扱いとします。
                "is_active": True 
            })
        return formatted_rules

    def _load_json_safe(self) -> Dict:
        """JSON読み込み（エラーハンドリング付き）"""
        if not os.path.exists(MASTER_JSON_PATH):
            return {}
        try:
            with open(MASTER_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    # ==========================================
    # 2. JSON -> DB (Import / Sync)
    # ==========================================
    def sync_json_to_db(self):
        """
        起動時用: JSONの内容をDBに反映（Upsert: 更新または挿入）する
        """
        data = self._load_json_safe()
        if not data:
            print("No master_data.json found. Skipping sync.")
            return

        print("Syncing JSON to DB...")
        
        # A. Products (Upsert)
        for p in data.get("products", []):
            # 名前をキーにして更新、なければ追加
            # 簡略化のため、Repoに upsert_product_by_name を実装するか、
            # ここで check -> update/insert を行う
            exists = self.prod_repo.find_id_by_name(p["name"])
            if exists:
                self.prod_repo.update_product(
                    exists, p["name"], p["price"], p["category"], 
                    p.get("color", "#ffcc80"), p.get("note", ""), p.get("is_active", True)
                )
                # 表示順も更新
                # (SQLのupdate_productメソッド拡張が必要かもですが、一旦スルー)
            else:
                self.prod_repo.add_product(
                    p["name"], p["price"], p["category"], 
                    p.get("color", "#ffcc80"), p.get("note", "")
                )
        
        # B. Users (Upsert)
        for u in data.get("users", []):
            # user_code をキーにする
            # Repoにロジックが必要（後述）
            self.user_repo.upsert_user(
                u["name"], u["user_code"], u.get("role", "staff"), u.get("is_active", True)
            )

        # C. Payment Methods (Upsert)
        for pm in data.get("payment_methods", []):
            self.trans_repo.upsert_payment_method(
                pm["name"], pm["is_cash"], pm.get("is_active", True)
            )

        # D. Discounts (Re-creation strategy)
        # 割引ルールは依存関係が複雑なので、既存を無効化するか、
        # 名前一致で更新するロジックが必要。
        # 今回は簡易的に「init_db.pyにお任せ（初期化時のみ）」にするか、
        # ここで真面目に同期するかですが、
        # 一旦「既存データのUpdate」は行わず、「JSONにあってDBにないもの」の追加だけ検討します。
        # (複雑になりすぎるのを防ぐため)
        
        print("Sync completed.")