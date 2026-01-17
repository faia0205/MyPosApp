# AnalyticsService: 画面表示用データ取得とExcel出力処理
import pandas as pd
from typing import Tuple
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.transaction_repo import TransactionRepository

class AnalyticsService:
    def __init__(self):
        self.ana_repo = AnalyticsRepository()
        self.trans_repo = TransactionRepository()

    def get_financial_summary(self) -> Tuple[int, int, int]:
        """財務サマリー（総売上、経費、利益）を取得"""
        # トランザクション一覧から総売上を計算（または専用SQLを作る）
        tx_list = self.ana_repo.get_transaction_list()
        total_sales = sum(tx['total'] for tx in tx_list)
        total_expenses = self.trans_repo.get_total_expenses()
        profit = total_sales - total_expenses
        return total_sales, total_expenses, profit

    def get_transaction_list(self) -> list[dict]:
        return self.ana_repo.get_transaction_list()

    def get_transaction_details(self, tx_id: int) -> dict:
        return self.ana_repo.get_transaction_details(tx_id)

    def get_hourly_sales(self) -> list[dict]:
        return self.ana_repo.get_sales_by_hour()

    def get_product_sales(self) -> list[dict]:
        return self.ana_repo.get_sales_by_product()

    def export_to_excel(self, file_path: str) -> Tuple[bool, str]:
        """全データをExcelに出力"""
        try:
            # データ取得
            tx_list = self.ana_repo.get_transaction_list()
            hourly = self.ana_repo.get_sales_by_hour()
            products = self.ana_repo.get_sales_by_product()
            
            # DataFrame化
            df_tx = pd.DataFrame(tx_list)
            df_hourly = pd.DataFrame(hourly)
            df_products = pd.DataFrame(products)

            # カラム名変更（見やすく）
            if not df_tx.empty:
                df_tx.rename(columns={'id': '伝票ID', 'time': '日時', 'total': '金額', 'items': '点数', 'payment': '決済'}, inplace=True)
            if not df_hourly.empty:
                df_hourly.rename(columns={'hour': '時', 'count': '客数', 'sales': '売上'}, inplace=True)
            if not df_products.empty:
                df_products.rename(columns={'name': '商品名', 'qty': '個数', 'total': '売上計'}, inplace=True)

            # Excel出力
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # データがあれば書き込む
                if not df_tx.empty: df_tx.to_excel(writer, sheet_name='伝票一覧', index=False)
                if not df_hourly.empty: df_hourly.to_excel(writer, sheet_name='時間帯別', index=False)
                if not df_products.empty: df_products.to_excel(writer, sheet_name='商品別', index=False)
            
            return True, "出力しました"
        except Exception as e:
            return False, str(e)