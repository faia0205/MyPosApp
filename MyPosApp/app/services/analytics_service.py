import pandas as pd
import datetime
from dataclasses import asdict
from typing import Tuple, Dict, Any, List

from app.repositories.analytics_repo import AnalyticsRepository
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.expense_repo import ExpenseRepository
from app.repositories.log_repo import LogRepository
from app.repositories.product_repo import ProductRepository

from app.services.analytics.enums import AnalysisAxis, AnalysisMetric
from app.services.analytics.processor import DataProcessor
from app.services.analytics.strategies import CrossTabStrategy, BasketAnalysisStrategy
from app.services.interfaces.report_exporter import IReportExporter
from app.services.csv_exporter import CsvTransactionExporter

class AnalyticsService:
    def __init__(
        self,
        ana_repo: AnalyticsRepository,
        trans_repo: TransactionRepository,
        expense_repo: ExpenseRepository,
        log_repo: LogRepository,
        prod_repo: ProductRepository, # ★追加: 商品マスタ参照用
        exporter: IReportExporter
    ):
        self.ana_repo = ana_repo
        self.trans_repo = trans_repo
        self.expense_repo = expense_repo
        self.log_repo = log_repo
        self.prod_repo = prod_repo # ★保持
        self.exporter = exporter
        
        self.JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')
        self.strategies = {
            "standard": CrossTabStrategy(),
            "basket": BasketAnalysisStrategy()
        }

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
        
        total_expenses = self.expense_repo.get_total_expenses()
        
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
            timestamp = log.get('timestamp') or log.get('time') or ""
            log['time'] = self._to_jst_str(timestamp)
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
        """
        Excel出力処理
        データの準備のみを行い、実際のファイル生成はExporterに任せる
        """
        # 1. データの準備 (Data Fetching / Analysis)
        tx_list = self.get_transaction_list()
        logs = self.get_logs()
        pivots = self.get_pivot_data()
        
        # 2. 書き出しの委譲 (File Export)
        return self.exporter.export(file_path, tx_list, logs, pivots)
    
    def analyze_dynamic(self, 
                        row_axis_key: str, 
                        col_axis_key: str, 
                        metric_key: str,
                        start_date=None, 
                        end_date=None) -> Dict[str, Any]:
        """
        動的分析のエントリーポイント
        """
        # 1. データの取得
        raw_data = self.ana_repo.get_comprehensive_raw_data(start_date, end_date)
        if not raw_data:
            return {"df": pd.DataFrame(), "max_val": 0, "min_val": 0}

        # 2. データ加工
        df = DataProcessor.process(raw_data)

        # 3. 軸の決定ロジック
        def get_axis(key):
            if isinstance(key, str) and key.startswith("cust_attr:"):
                attr_name = key.split(":", 1)[1]
                col_name = f"cust_{attr_name}"
                if col_name not in df.columns:
                    df[col_name] = "未設定"
                return col_name
            
            try:
                return AnalysisAxis(key)
            except ValueError:
                return AnalysisAxis.NONE

        row_axis = get_axis(row_axis_key)
        col_axis = get_axis(col_axis_key)
        
        try:
            metric = AnalysisMetric(metric_key)
        except ValueError:
            return {"df": pd.DataFrame(), "error": "Invalid metric parameters"}

        # 4. Strategy選択
        is_basket = (row_axis == col_axis) and (row_axis != AnalysisAxis.NONE)
        strategy = self.strategies['basket'] if is_basket else self.strategies['standard']

        # 5. 実行
        try:
            result_df = strategy.execute(df, row_axis, col_axis, metric)
            
            # ★変更: 行・列それぞれで「商品名」が選択されていればマスタ順にソートする
            if not result_df.empty:
                # 行 (Index) のソート
                if row_axis == AnalysisAxis.PRODUCT_NAME:
                    result_df = self._sort_by_product_master(result_df, axis=0)
                
                # 列 (Columns) のソート
                if col_axis == AnalysisAxis.PRODUCT_NAME:
                    result_df = self._sort_by_product_master(result_df, axis=1)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"df": pd.DataFrame(), "error": f"Calculation Error: {str(e)}"}

        # 6. View用の付加情報 (ヒートマップ用)
        numeric_df = result_df.select_dtypes(include=['number'])
        if '合計' in numeric_df.index:
            numeric_df = numeric_df.drop('合計', axis=0)
        if '合計' in numeric_df.columns:
            numeric_df = numeric_df.drop('合計', axis=1)

        max_val = numeric_df.max().max() if not numeric_df.empty else 0
        min_val = numeric_df.min().min() if not numeric_df.empty else 0

        return {
            "df": result_df,
            "max_val": float(max_val),
            "min_val": float(min_val),
            "mode": "basket" if is_basket else "standard"
        }
    
    def _sort_by_product_master(self, df: pd.DataFrame, axis: int = 0) -> pd.DataFrame:
        """
        DataFrameのインデックス(axis=0) または カラム(axis=1) を並び替える。
        順序: [カテゴリの並び順] > [単価(高い順)]
        """
        # 1. 全商品をモデルとして取得
        products = self.prod_repo.fetch_all_as_models()
        
        # --- カテゴリの並び順を決定するロジック ---
        # カテゴリごとに、そのカテゴリに含まれる商品の「最小 display_order」を探す。
        # これにより、「設定画面で上に置いている商品が多いカテゴリ」が先頭に来る。
        category_rank = {}
        for p in products:
            cat = p.category or "未分類"
            current_min = category_rank.get(cat, 999999)
            if p.display_order < current_min:
                category_rank[cat] = p.display_order
        
        # 2. ソートキー作成
        # 第1キー: カテゴリのランク (display_orderが小さい商品が含まれるカテゴリほど先)
        # 第2キー: 価格の降順 (高い順。割引などのマイナスは最後になる)
        products.sort(key=lambda p: (
            category_rank.get(p.category or "未分類", 999999),
            -p.price
        ))
        
        # 3. ソート済み商品名のリストを作成
        sorted_names = [p.name for p in products]
        
        # 4. 現在のDataFrameにあるラベル（インデックス or カラム）を取得
        if axis == 0:
            current_labels = df.index.tolist()
        else:
            current_labels = df.columns.tolist()
        
        # '合計' 行/列 があれば一時的に除外して確保
        has_total = '合計' in current_labels
        if has_total:
            current_labels.remove('合計')
            
        # 5. マスタにある順序で並べる + マスタにないもの(手入力等)を後ろに追加
        new_order = [n for n in sorted_names if n in current_labels]
        remaining = [n for n in current_labels if n not in new_order]
        new_order.extend(remaining)
        
        # '合計' を最後尾に戻す
        if has_total:
            new_order.append('合計')
            
        # 6. Reindex実行 (指定したaxisに対して並び替え適用)
        return df.reindex(new_order, axis=axis)
    
    def get_initial_date_range(self):
        """データの最小日時と現在日時を返す"""
        min_ts = self.ana_repo.get_min_timestamp()
        
        now = datetime.datetime.now()
        start_date = now
        
        if min_ts:
            try:
                # 文字列を日付型に変換
                start_date = datetime.datetime.strptime(min_ts, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass
        
        return start_date, now
    
    def get_axis_categories(self) -> list[str]:
        """大分類のリストを返す"""
        return ["全体", "時間", "商品", "客層", "客層(属性)", "運用"]

    def get_axis_details(self, category: str) -> list[tuple[str, str]]:
        """
        大分類に応じた小分類リストを返す
        Return: [(表示名, 内部キー), ...]
        """
        if category == "全体":
            return [("指定なし (総計)", AnalysisAxis.NONE.value)]
            
        elif category == "時間":
            return [
                ("月別", AnalysisAxis.TIME_MONTH.value),
                ("曜日別", AnalysisAxis.TIME_DOW.value),
                ("時間帯別", AnalysisAxis.TIME_HOUR.value),
            ]
            
        elif category == "商品":
            return [
                ("カテゴリ", AnalysisAxis.PRODUCT_CAT.value),
                ("商品名", AnalysisAxis.PRODUCT_NAME.value),
            ]
            
        elif category == "客層":
            return [
                ("客層ラベル (ボタン名)", AnalysisAxis.CUSTOMER_LBL.value),
            ]
            
        elif category == "客層(属性)":
            # DBから動的キーを取得
            attr_keys = self.ana_repo.get_customer_attribute_keys()
            results = []
            for k in attr_keys:
                # 表示名: sex, 内部キー: cust_attr:sex
                results.append((k, f"cust_attr:{k}"))
            
            if not results:
                results.append(("(属性データなし)", AnalysisAxis.NONE.value))
            return results
            
        elif category == "運用":
            return [
                ("担当者", AnalysisAxis.CASHIER.value),
                ("決済方法", AnalysisAxis.PAYMENT.value),
            ]
            
        return []
    
    def get_default_csv_filename(self) -> str:
        now_jst = datetime.datetime.now(self.JST)
        now_str = now_jst.strftime("%Y%m%d_%H%M")
        return f"伝票データ_{now_str}.csv"
    
    def export_to_csv(self, file_path: str) -> Tuple[bool, str]:
        """
        全期間の伝票データをCSV出力する
        """
        try:
            csv_exporter = CsvTransactionExporter(self.trans_repo)
            csv_exporter.export_all_transactions(file_path)
            return True, "CSVを出力が完了しました"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"CSV出力エラー: {str(e)}"