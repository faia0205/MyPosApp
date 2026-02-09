import json
import shutil
import os
import datetime
from typing import Dict, List

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
            print(f"JSON load error: {MASTER_JSON_PATH}")
            return {}

    # ==========================================
    # 2. JSON -> DB (Import / Sync)
    # ==========================================
    def sync_json_to_db(self):
        """
        JSONの内容をDBに完全同期（削除も反映）
        起動時および設定のリセット時に使用
        """
        data = self._load_json_safe()
        if not data:
            return

        print("Starting Full Sync (JSON -> DB)...")
        self._apply_data_to_repositories(data)
        print("Sync completed.")
        
        self.check_integrity()

    def restore_from_dict(self, data: Dict):
        """
        メモリ上の辞書データからDBを復元する (設定画面の「破棄」用)
        """
        print("Restoring DB from backup dictionary...")
        self._apply_data_to_repositories(data)
        print("Restore completed.")
    
    def _apply_data_to_repositories(self, data: Dict):
        """
        共通反映ロジック:
        1. JSON(辞書)にあるIDリストを抽出
        2. それ以外のIDをDBから削除 (Delete)
        3. JSON(辞書)のデータでDBを更新/追加 (Upsert)
        """
        for repo in self.repositories:
            key = repo.get_master_key()
            target_data = data.get(key, [])
            
            # 1. 有効なIDリストを作成 (IDを持っているものだけ)
            valid_ids = [item['id'] for item in target_data if item.get('id') is not None]
            
            # 2. リストにないIDを削除 (完全同期)
            try:
                repo.delete_not_in(valid_ids)
            except Exception as e:
                print(f"Failed to delete obsolete data for {key}: {e}")

            # 3. データの取り込み (Upsert)
            if target_data:
                repo.import_all_data(target_data)
    
    def get_current_data_as_dict(self) -> Dict:
        """現在のDBの状態を辞書として取得 (メモリバックアップ用)"""
        master_data = {}
        for repo in self.repositories:
            key = repo.get_master_key()
            master_data[key] = repo.export_all_data()
        return master_data
    
    def check_integrity(self):
        """整合性チェック: 存在しない商品を対象にしている割引ルールがないか確認"""
        print("Checking data integrity...")
        
        # 1. 比較用の正解データ（商品名セット、カテゴリ名セット）を作成
        # リポジトリリストからProductRepositoryを探す（安全策）
        product_repo = next((r for r in self.repositories if r.get_master_key() == 'products'), None)
        
        if not product_repo:
            print("Skipping integrity check: Product repository not found.")
            return

        products = product_repo.fetch_all_as_models()
        valid_product_names = {p.name for p in products}
        # カテゴリはNoneや空文字を除外してセット化
        valid_categories = {p.category for p in products if p.category}

        # 2. 割引ルールリポジトリを取得してチェック開始
        discount_repo = next((r for r in self.repositories if r.get_master_key() == 'discount_rules'), None)
        
        if discount_repo:
            rules = discount_repo.fetch_all_rules()
            
            for rule in rules:
                # 無効なルールも一応チェックしますが、ノイズになるなら if not rule.is_active: continue を入れてもOK
                
                # --- A. 商品指定 (Item) ---
                if rule.apply_type == 'item':
                    if rule.target_value not in valid_product_names:
                        print(f"⚠️ [整合性警告] ルールID:{rule.id}「{rule.name}」の対象商品「{rule.target_value}」が存在しません。")
                
                # --- B. カテゴリ指定 (Category) ---
                elif rule.apply_type == 'category':
                    if rule.target_value not in valid_categories:
                        print(f"⚠️ [整合性警告] ルールID:{rule.id}「{rule.name}」の対象カテゴリ「{rule.target_value}」が存在しません(商品未登録のカテゴリの可能性あり)。")

                # --- C. バンドル指定 (Bundle) ---
                elif rule.apply_type == 'bundle':
                    try:
                        data = json.loads(rule.target_value)
                        mode = data.get('mode')

                        # C-1. 選択式 (Select Mode) -> "targets": ["商品A", "カテゴリB"]
                        if mode == 'select':
                            targets = data.get('targets', [])
                            for t in targets:
                                # selectモードは配列に商品名とカテゴリ名が混在して入っている仕様
                                if t not in valid_product_names and t not in valid_categories:
                                    print(f"⚠️ [整合性警告] ルールID:{rule.id}「{rule.name}」のバンドル対象「{t}」が見つかりません。")

                        # C-2. 組み合わせ (Combo Mode) -> "conditions": [{"target": "...", "type": "item/category"}]
                        elif mode == 'combo':
                            conditions = data.get('conditions', [])
                            for cond in conditions:
                                target = cond.get('target')
                                t_type = cond.get('type') # 'item' or 'category'
                                
                                if t_type == 'item':
                                    if target not in valid_product_names:
                                        print(f"⚠️ [整合性警告] ルールID:{rule.id}「{rule.name}」のバンドル条件(商品)「{target}」が存在しません。")
                                elif t_type == 'category':
                                    if target not in valid_categories:
                                        print(f"⚠️ [整合性警告] ルールID:{rule.id}「{rule.name}」のバンドル条件(カテゴリ)「{target}」が存在しません。")
                                        
                    except json.JSONDecodeError:
                        print(f"⚠️ [JSONエラー] ルールID:{rule.id}「{rule.name}」の定義が破損しています。")
                    except Exception as e:
                        print(f"⚠️ [不明なエラー] ルールID:{rule.id}「{rule.name}」のチェック中にエラー: {e}")

        print("Integrity check completed.")