import pandas as pd
import datetime
from typing import Tuple, Dict, Any, List
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.log_repo import LogRepository

class AnalyticsService:
    def __init__(self):
        self.ana_repo = AnalyticsRepository()
        self.trans_repo = TransactionRepository()
        self.log_repo = LogRepository()
        self.JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')

    def _to_jst_str(self, utc_str: str) -> str:
        if not utc_str: return ""
        try:
            dt = datetime.datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
            dt_jst = dt.replace(tzinfo=datetime.timezone.utc).astimezone(self.JST)
            return dt_jst.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return utc_str

    def get_dashboard_summary(self) -> Dict[str, Any]:
        stats = self.ana_repo.get_dashboard_stats()
        total_sales = stats['sales']
        customer_count = stats['customer_count']
        total_expenses = self.trans_repo.get_total_expenses()
        profit = total_sales - total_expenses
        payments = self.ana_repo.get_payment_summary()
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
        raw_list = self.ana_repo.get_transaction_list()
        for tx in raw_list:
            tx['time'] = self._to_jst_str(tx['timestamp'])
        return raw_list

    def get_transaction_details(self, tx_id):
        details = self.ana_repo.get_transaction_details(tx_id)
        details['time'] = self._to_jst_str(details['timestamp'])
        return details

    def get_logs(self):
        logs = self.log_repo.fetch_logs()
        for log in logs:
            log['time'] = self._to_jst_str(log['timestamp']) if 'timestamp' in log else ""
        return logs

    # --- Pivot Table (クロス集計) ---
    def get_pivot_data(self):
        raw_data = self.ana_repo.get_raw_data_for_analysis()
        if not raw_data:
            return None
        
        df = pd.DataFrame(raw_data)
        
        # JST変換
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tokyo')
        df['hour'] = df['timestamp'].dt.hour
        
        # ★修正: time_cust (時間x客層) は「IDのユニーク数(客数)」をカウントする
        # 'nunique' は重複しないデータの個数を数える機能です
        
        pivots = {
            "time_prod": df.pivot_table(index='product', columns='hour', values='qty', aggfunc='sum', fill_value=0),
            "cust_prod": df.pivot_table(index='product', columns='customer', values='qty', aggfunc='sum', fill_value=0),
            # ここを変更: values='id', aggfunc='nunique'
            "time_cust": df.pivot_table(index='customer', columns='hour', values='id', aggfunc='nunique', fill_value=0)
        }
        return pivots

    def get_default_filename(self) -> str:
        now_jst = datetime.datetime.now(self.JST)
        now_str = now_jst.strftime("%Y%m%d_%H%M")
        return f"売上レポート_{now_str}.xlsx"

    def export_to_excel(self, file_path: str) -> Tuple[bool, str]:
        try:
            tx_list = self.get_transaction_list()
            logs = self.get_logs()
            df_tx = pd.DataFrame(tx_list)
            df_logs = pd.DataFrame(logs)
            
            if 'timestamp' in df_tx.columns: df_tx = df_tx.drop(columns=['timestamp'])
            
            if not df_tx.empty:
                df_tx.rename(columns={'id':'伝票ID', 'time':'日時', 'total':'合計', 'items':'点数', 'payment':'決済', 'customer':'客層'}, inplace=True)
            if not df_logs.empty:
                df_logs.rename(columns={'time':'日時', 'level':'レベル', 'msg':'内容'}, inplace=True)

            pivots = self.get_pivot_data()

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                if df_tx.empty: pd.DataFrame(["データなし"]).to_excel(writer, sheet_name='伝票一覧')
                else: df_tx.to_excel(writer, sheet_name='伝票一覧', index=False)
                    
                if not df_logs.empty: df_logs.to_excel(writer, sheet_name='操作ログ', index=False)
                
                if pivots:
                    pivots['time_prod'].to_excel(writer, sheet_name='時間x商品(個数)')
                    pivots['cust_prod'].to_excel(writer, sheet_name='客層x商品(個数)')
                    # シート名を変更
                    pivots['time_cust'].to_excel(writer, sheet_name='時間x客層(客数)')
            
            return True, "出力しました"
        except Exception as e:
            return False, str(e)