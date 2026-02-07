import pandas as pd
import json
from .enums import AnalysisAxis

class DataProcessor:
    """[SRP] 生データ(Dict List)をPandas DataFrameに変換・加工する責務"""
    
    @staticmethod
    def process(raw_data: list) -> pd.DataFrame:
        if not raw_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(raw_data)
        
        # 1. 日時加工
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            # JST変換 (UTCの場合)
            if df['timestamp'].dt.tz is None:
                df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Tokyo')
            
            df[AnalysisAxis.TIME_MONTH.value] = df['timestamp'].dt.strftime('%Y-%m')
            df[AnalysisAxis.TIME_DOW.value] = df['timestamp'].dt.strftime('%a')
            df[AnalysisAxis.TIME_HOUR.value] = df['timestamp'].dt.hour
            
        # 2. JSON属性展開
        if 'customer_attrs' in df.columns:
            def parse_attr(x):
                try: return json.loads(x)
                except: return {}
            
            attrs = df['customer_attrs'].apply(parse_attr).tolist()
            attr_df = pd.json_normalize(attrs)
            # カラム名にプレフィックスをつける (例: sex -> cust_sex)
            attr_df.columns = [f"cust_{c}" for c in attr_df.columns]
            
            df = pd.concat([df, attr_df], axis=1)

        # 3. カラム名のマッピング調整 (Enum定義に合わせる)
        rename_map = {
            'product_name': AnalysisAxis.PRODUCT_NAME.value,
            'category': AnalysisAxis.PRODUCT_CAT.value,
            'customer_label': AnalysisAxis.CUSTOMER_LBL.value,
            'cashier_name': AnalysisAxis.CASHIER.value,
            'payment_method': AnalysisAxis.PAYMENT.value
        }
        df.rename(columns=rename_map, inplace=True)

        # ★追加修正: 存在しない分析軸カラムがあれば、空値で作成してエラーを防ぐ
        # Enumに定義されているすべてのカラムをチェック
        expected_columns = [
            AnalysisAxis.CUSTOMER_SEX.value,
            AnalysisAxis.CUSTOMER_AGE.value,
            AnalysisAxis.CUSTOMER_LBL.value
            # 必要に応じて他のカスタム属性もここに追加
        ]
        
        for col in expected_columns:
            if col not in df.columns:
                df[col] = "未設定" # または None, np.nan

        # 欠損値を埋める（PivotTableでのエラー防止）
        df = df.fillna("未設定")
        
        return df