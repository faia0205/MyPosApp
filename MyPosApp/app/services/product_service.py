import logging
from typing import List, Dict
from app.repositories.product_repo import ProductRepository
from app.repositories.log_repo import LogRepository
from app.models.product import Product

logger = logging.getLogger("MyPosApp")

class ProductService:
    def __init__(self, repo: ProductRepository, log_repo: LogRepository):
        self.repo = repo
        self.log_repo = log_repo

    def get_active_products(self) -> List[Product]:
        try:
            return self.repo.fetch_active_products()
        except RuntimeError as e:
            logger.error(f"Service Error (get_active_products): {e}")
            raise

    def get_all_products(self) -> List[Product]:
        try:
            return self.repo.fetch_all_as_models()
        except RuntimeError as e:
            logger.error(f"Service Error (get_all_products): {e}")
            raise

    def add_product(self, product: Product) -> bool:
        try:
            if self.repo.add_product(product):
                self.log_repo.add_log("info", f"商品追加: {product.name}")
                return True
            return False
        except RuntimeError as e:
            logger.error(f"Service Error (add_product): {e}")
            self.log_repo.add_log("error", f"商品追加失敗: {product.name} ({e})")
            raise

    def update_product(self, product: Product) -> bool:
        try:
            if self.repo.update_product(product):
                self.log_repo.add_log("info", f"商品変更: {product.name}")
                return True
            return False
        except RuntimeError as e:
            logger.error(f"Service Error (update_product): {e}")
            self.log_repo.add_log("error", f"商品変更失敗: {product.name} ({e})")
            raise

    def delete_product(self, product: Product) -> bool:
        # 完全削除
        try:
            if self.repo.delete_product(product.id):
                self.log_repo.add_log("warning", f"商品完全削除: {product.name}")
                return True
            return False
        except RuntimeError as e:
            logger.error(f"Sevice Error (delete_product): {e}")
            self.log_repo.add_log("error", f"商品消去失敗: {product.name} ({e})")
            raise

    def disable_product(self, product: Product) -> bool:
        # 無効化（論理削除的な扱い）
        product.is_active = False
        try:
            if self.repo.update_product(product):
                self.log_repo.add_log("info", f"商品無効化: {product.name}")
                return True
            return False
        except RuntimeError as e:
            logger.error(f"Service Error (disable_product): {e}")
            self.log_repo.add_log("error", f"商品無効化失敗: {product.name} ({e})")
            raise

    def update_display_order(self, order_map: Dict[int, int]) -> bool:
        try:
            return self.repo.update_display_order(order_map)
        except RuntimeError as e:
            logger.error(f"Service Error (update_display_order): {e}")
            self.log_repo.add_log("error", f"表示順更新失敗({e})")
            raise