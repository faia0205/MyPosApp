import pandas as pd
from abc import ABC, abstractmethod
from typing import Any
from .enums import AnalysisAxis, AnalysisMetric

class IAnalysisStrategy(ABC):
    """
    [OCP] 分析ロジックのインターフェース
    """
    @abstractmethod
    def execute(self, df: pd.DataFrame, 
                row_axis: Any, # Enum または str (動的カラム名)
                col_axis: Any, # Enum または str (動的カラム名)
                metric: AnalysisMetric) -> pd.DataFrame:
        pass

class CrossTabStrategy(IAnalysisStrategy):
    """
    [SRP] 通常のクロス集計（またはリスト集計）を担当
    """
    def execute(self, df: pd.DataFrame, 
                row_axis: Any, 
                col_axis: Any, 
                metric: AnalysisMetric) -> pd.DataFrame:
        
        # --- 1. 軸の値を文字列として取り出すヘルパー ---
        def get_val(axis):
            if isinstance(axis, AnalysisAxis):
                return axis.value
            return axis # 文字列ならそのまま返す

        row_val = get_val(row_axis)
        col_val = get_val(col_axis)

        # --- 2. 集計値のカラム決定 ---
        value_col = 'subtotal'
        agg_func = 'sum'
        
        if metric == AnalysisMetric.QUANTITY:
            value_col = 'quantity'
        elif metric == AnalysisMetric.TX_COUNT:
            value_col = 'tx_id'
            agg_func = 'nunique' # ユニークカウント
            
        # --- 3. 軸の決定 (NONEの場合は空リスト) ---
        # row_axis が AnalysisAxis.NONE (Enum) の場合のみ除外
        index_cols = [row_val] if row_axis != AnalysisAxis.NONE else []
        columns_cols = [col_val] if col_axis != AnalysisAxis.NONE else []
        
        # --- ケース1: 総計 (なし x なし) ---
        if not index_cols and not columns_cols:
            total = df[value_col].nunique() if metric == AnalysisMetric.TX_COUNT else df[value_col].sum()
            return pd.DataFrame({metric.name: [total]}, index=["Total"])

        # --- ケース2: 1次元集計 (片方のみ) ---
        if not columns_cols:
            # groupby で集計
            return df.groupby(index_cols)[value_col].agg(agg_func).to_frame()
        
        if not index_cols:
            # 横のみ指定はあまりないが、転置して返す
            return df.groupby(columns_cols)[value_col].agg(agg_func).to_frame().T

        # --- ケース3: クロス集計 (Row x Col) ---
        # 該当データがない場合に備えて pivot_table のエラーを防ぐ
        if df.empty:
            return pd.DataFrame()

        return df.pivot_table(
            index=index_cols,
            columns=columns_cols,
            values=value_col,
            aggfunc=agg_func,
            fill_value=0,
            margins=True,       # 合計行・列を表示
            margins_name='合計'
        )

class BasketAnalysisStrategy(IAnalysisStrategy):
    """
    [SRP] バスケット分析（同時購入分析）を担当
    """
    def execute(self, df: pd.DataFrame, 
                row_axis: Any, 
                col_axis: Any, 
                metric: AnalysisMetric) -> pd.DataFrame:
        
        # ヘルパーで値を取得
        def get_val(axis):
            if isinstance(axis, AnalysisAxis):
                return axis.value
            return axis

        target_col = get_val(row_axis) # 縦・横同じはず
        
        # 必要な列のみに絞る
        if df.empty or 'tx_id' not in df.columns or target_col not in df.columns:
            return pd.DataFrame()

        subset = df[['tx_id', target_col]].drop_duplicates()
        
        # 自己結合 (Self-Join)
        merged = pd.merge(subset, subset, on='tx_id', suffixes=('_row', '_col'))
        
        # クロス集計 (Count)
        result = pd.crosstab(
            merged[f'{target_col}_row'], 
            merged[f'{target_col}_col']
        )
        
        return result