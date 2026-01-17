# AnalyticsService: 画面表示用データ取得とExcel出力処理
import pandas as pd
import datetime
from typing import Tuple, Dict, Any, List
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.log_repo import LogRepository

class AnalyticsService:
    def __init__(self):
        # 3つのリポジトリを使用します
        self.ana_repo = AnalyticsRepository()
        self.trans_repo = TransactionRepository()
        self.log_repo = LogRepository()

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """ダッシュボード表示用のサマリー情報を一括取得"""
        # 1. 財務情報
        tx_list = self.ana_repo.get_transaction_list()
        total_sales = sum(tx['total'] for tx in tx_list)
        total_expenses = self.trans_repo.get_total_expenses()
        profit = total_sales - total_expenses
        
        # 2. 決済方法ごとの内訳
        payments = self.ana_repo.get_payment_summary()
        
        # 3. 客単価 (売上 ÷ 伝票数)
        customer_count = len(tx_list)
        avg_spend = int(total_sales / customer_count) if customer_count > 0 else 0

        return {
            "sales": total_sales,
            "expenses": total_expenses,
            "profit": profit,
            "payments": payments,
            "customer_count": customer_count,
            "avg_spend": avg_spend
        }

    def get_transaction_list(self):
        """伝票一覧を取得"""
        return self.ana_repo.get_transaction_list()

    def get_transaction_details(self, tx_id):
        """伝票詳細を取得"""
        return self.ana_repo.get_transaction_details(tx_id)

    def get_hourly_sales(self):
        """時間帯別データ"""
        return self.ana_repo.get_sales_by_hour()

    def get_product_sales(self):
        """商品別ランキング"""
        return self.ana_repo.get_sales_by_product()

    def get_logs(self):
        """操作ログを取得"""
        return self.log_repo.fetch_logs()

    # --- Pivot Table (クロス集計) 生成ロジック ---
    def get_pivot_data(self):
        """各種分析用のDataFrameを作成して返す"""
        raw_data = self.ana_repo.get_raw_data_for_analysis()
        if not raw_data:
            return None
        
        df = pd.DataFrame(raw_data)
        
        # Pandasのピボット機能でクロス集計表を作成
        # fill_value=0 は、データがないセルを0で埋める設定
        
        # 1. 時間 x 商品 (個数)
        pivot_time_prod = df.pivot_table(index='product', columns='hour', values='qty', aggfunc='sum', fill_value=0)
        
        # 2. 客層 x 商品 (個数)
        pivot_cust_prod = df.pivot_table(index='product', columns='customer', values='qty', aggfunc='sum', fill_value=0)
        
        # 3. 時間 x 客層 (売上金額)
        pivot_time_cust = df.pivot_table(index='customer', columns='hour', values='sales', aggfunc='sum', fill_value=0)

        return {
            "time_prod": pivot_time_prod,
            "cust_prod": pivot_cust_prod,
            "time_cust": pivot_time_cust
        }

    def get_default_filename(self) -> str:
        """デフォルトファイル名生成 (例: 売上レポート_20260118_1530.xlsx)"""
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        return f"売上レポート_{now_str}.xlsx"

    def export_to_excel(self, file_path: str) -> Tuple[bool, str]:
        """全データをExcelに出力 (複数シート対応)"""
        try:
            # --- データの準備 ---
            tx_list = self.ana_repo.get_transaction_list()
            logs = self.log_repo.fetch_logs()
            
            # リストをDataFrameに変換
            df_tx = pd.DataFrame(tx_list)
            df_logs = pd.DataFrame(logs)
            
            # カラム名を日本語にリネーム
            if not df_tx.empty:
                df_tx.rename(columns={'id':'伝票ID', 'time':'日時', 'total':'合計金額', 'items':'点数', 'payment':'主な決済'}, inplace=True)
            
            if not df_logs.empty:
                df_logs.rename(columns={'time':'日時', 'level':'レベル', 'msg':'内容'}, inplace=True)

            # ピボットデータ取得
            pivots = self.get_pivot_data()

            # --- Excel書き出し処理 (openpyxlエンジン) ---
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. 基本シート
                if not df_tx.empty:
                    df_tx.to_excel(writer, sheet_name='伝票一覧', index=False)
                else:
                    # データがない場合でも空シートを作る（エラー回避）
                    pd.DataFrame(["データなし"]).to_excel(writer, sheet_name='伝票一覧')

                if not df_logs.empty:
                    df_logs.to_excel(writer, sheet_name='操作ログ', index=False)
                
                # 2. 分析シート (データがある場合のみ)
                if pivots:
                    pivots['time_prod'].to_excel(writer, sheet_name='時間x商品(個数)')
                    pivots['cust_prod'].to_excel(writer, sheet_name='客層x商品(個数)')
                    pivots['time_cust'].to_excel(writer, sheet_name='時間x客層(売上)')
            
            return True, "出力しました"
            
        except Exception as e:
            return False, str(e)