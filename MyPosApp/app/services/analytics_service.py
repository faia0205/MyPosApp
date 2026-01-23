import pandas as pd
import datetime
from dataclasses import asdict
from typing import Tuple, Dict, Any, List
from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.log_repo import LogRepository

class AnalyticsService:
    def __init__(self):
        self.ana_repo = AnalyticsRepository()
        self.trans_repo = TransactionRepository()
        self.expense_repo = ExpenseRepository()
        self.log_repo = LogRepository()
        self.JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')

    def _to_jst_str(self, utc_str: str) -> str:
        if not utc_str:
            return ""
        try:
            dt = datetime.datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
            dt_jst = dt.replace(tzinfo=datetime.timezone.utc).astimezone(self.JST)
            return dt_jst.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return utc_str
    
    def get_expense_list(self):
        """経費一覧を取得 (JST変換付き)"""
        expenses_objs = self.expense_repo.fetch_all()
        
        # UI表示用に辞書リストへ変換 & タイムゾーン処理
        raw_list = []
        for ex in expenses_objs:
            # dataclass -> dict 変換
            d = asdict(ex)
            # タイムスタンプのJST変換
            d['time'] = self._to_jst_str(d['timestamp'])
            raw_list.append(d)
            
        return raw_list

    def get_dashboard_summary(self) -> Dict[str, Any]:
        stats = self.ana_repo.get_dashboard_stats()
        total_sales = stats['sales']
        customer_count = stats['customer_count']
        
        total_expenses = self.expense_repo.get_total_amount()
        
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
        """各種分析用のDataFrameを作成して返す"""
        
        # -------------------------------------------------------
        # 1. 商品・客層・時間の分析 (既存のデータを使用)
        # -------------------------------------------------------
        raw_data = self.ana_repo.get_raw_data_for_analysis()
        
        # データがなければ空で初期化
        pivots = {}
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            
            # JST変換
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tokyo')
            df['hour'] = df['timestamp'].dt.hour
            
            # 時間 x 商品 (販売数)
            pivots["time_prod"] = df.pivot_table(
                index='product', columns='hour', values='qty', 
                aggfunc='sum', fill_value=0, 
                margins=True, margins_name='合計'
            )
            
            # 客層 x 商品 (販売数)
            pivots["cust_prod"] = df.pivot_table(
                index='product', columns='customer', values='qty', 
                aggfunc='sum', fill_value=0, 
                margins=True, margins_name='合計'
            )
            
            # 時間 x 客層 (客数: IDのユニーク数)
            pivots["time_cust"] = df.pivot_table(
                index='customer', columns='hour', values='id', 
                aggfunc='nunique', fill_value=0, 
                margins=True, margins_name='合計'
            )
        else:
            # データがない場合の空DataFrame
            pivots["time_prod"] = pd.DataFrame()
            pivots["cust_prod"] = pd.DataFrame()
            pivots["time_cust"] = pd.DataFrame()

        # -------------------------------------------------------
        # 2. 担当者 × 決済方法の分析 (★ここを修正・追加)
        # -------------------------------------------------------
        # 商品データとは別に、決済専用データを取得します
        raw_cashier = self.ana_repo.get_cashier_payment_data()
        
        if raw_cashier:
            df_cashier = pd.DataFrame(raw_cashier)
            
            # index=担当者, columns=決済方法, values=金額
            # margins=True にすると、右端と下端に「合計」列が自動追加されます
            pivots["cashier_payment"] = df_cashier.pivot_table(
                index='cashier', 
                columns='method', 
                values='amount', 
                aggfunc='sum', 
                fill_value=0,
                margins=True,       # ★ 合計行・列を追加
                margins_name='合計' # ★ 合計のラベル名
            )
        else:
            pivots["cashier_payment"] = pd.DataFrame()

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
            
            if 'timestamp' in df_tx.columns:
                df_tx = df_tx.drop(columns=['timestamp'])
            
            if not df_tx.empty:
                df_tx.rename(columns={'id':'伝票ID', 'time':'日時', 'total':'合計', 'items':'点数', 'payment':'決済', 'customer':'客層'}, inplace=True)
            if not df_logs.empty:
                df_logs.rename(columns={'time':'日時', 'level':'レベル', 'msg':'内容'}, inplace=True)

            pivots = self.get_pivot_data()

            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                if df_tx.empty:
                    pd.DataFrame(["データなし"]).to_excel(writer, sheet_name='伝票一覧')
                else:
                    df_tx.to_excel(writer, sheet_name='伝票一覧', index=False)
                    
                if not df_logs.empty:
                    df_logs.to_excel(writer, sheet_name='操作ログ', index=False)
                
                if pivots:
                    pivots['time_prod'].to_excel(writer, sheet_name='時間x商品(個数)')
                    pivots['cust_prod'].to_excel(writer, sheet_name='客層x商品(個数)')
                    # シート名を変更
                    pivots['time_cust'].to_excel(writer, sheet_name='時間x客層(客数)')
                    pivots['cashier_payment'].to_excel(writer, sheet_name='担当者x決済(売上)')
            
            return True, "出力しました"
        except Exception as e:
            return False, str(e)