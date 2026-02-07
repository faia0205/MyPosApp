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
from app.repositories.interfaces.master_data_repo import IMasterDataRepository

class MasterDataService:
    """
    マスターデータ(JSON)とデータベースの同期・変換を担当するサービス
    SRP対応: データ変換ロジックは各Modelの to_dict / from_dict に委譲済み
    """

    def __init__(self, 
                 repositories: list[IMasterDataRepository]):
        """
        Args:
            repositories (list[IMasterDataRepository]): 同期対象のリポジトリ群(順序が重要ならその順で渡す)
        """

        # 依存性の注入 (Dependency Injection)
        self.repositories = repositories

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
            master_data = {}
            for repo in self.repositories:
                key = repo.get_master_key()
                data = repo.export_all_data()
                master_data[key] = data

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
        詳細な判定ロジックは各リポジトリの import_data に委譲
        """
        data = self._load_json_safe()
        if not data:
            return

        print("Syncing JSON to DB...")

        for repo in self.repositories:
            key = repo.get_master_key()
            target_data = data.get(key, [])
            if target_data:
                repo.import_all_data(target_data)
        print("Sync completed.")