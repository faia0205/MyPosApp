import pandas as pd
import os
from typing import List, Dict, Tuple, Optional
from openpyxl import load_workbook

from app.services.interfaces.report_exporter import IReportExporter

# 循環参照回避のためのTYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.analytics_service import AnalyticsService

class ExcelReportExporter(IReportExporter):
    """
    Excel帳票出力クラス
    - 固定レポートの一括出力 (export)
    - 分析結果の追記出力 (export_analysis_result)
    の両方に対応
    """

    def __init__(self, analytics_service: Optional['AnalyticsService'] = None):
        """
        Args:
            analytics_service: 生データ取得用。MainWindowでの初期化時はNoneで、
                               AnalysisTabで利用する際にインスタンスを渡して生成するか、
                               後からセットすることを想定。
        """
        self.analytics_service = analytics_service

    def export(self, file_path: str, tx_list: List[Dict], logs: List[Dict], pivots: Dict[str, pd.DataFrame]) -> Tuple[bool, str]:
        """
        [既存機能] 全データを新規ファイルとして出力する
        """
        try:
            # 1. データフレーム変換と整形
            df_tx = self._process_transaction_list(tx_list)
            df_logs = self._process_logs(logs)

            # 2. Excelファイルへの書き込み (新規作成)
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 伝票一覧
                self._write_sheet(writer, df_tx, '伝票一覧')
                
                # 操作ログ
                self._write_sheet(writer, df_logs, '操作ログ')

                # クロス集計シート
                if pivots:
                    if 'time_prod' in pivots:
                        pivots['time_prod'].to_excel(writer, sheet_name='時間x商品(個数)')
                    if 'cust_prod' in pivots:
                        pivots['cust_prod'].to_excel(writer, sheet_name='客層x商品(個数)')
                    if 'time_cust' in pivots:
                        pivots['time_cust'].to_excel(writer, sheet_name='時間x客層(客数)')
                    if 'cashier_payment' in pivots:
                        pivots['cashier_payment'].to_excel(writer, sheet_name='担当者x決済(売上)')

            return True, "出力しました"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, str(e)

    def export_analysis_result(self, 
                               df: pd.DataFrame, 
                               sheet_name: str, 
                               file_path: str, 
                               include_raw_data: bool = False) -> Tuple[bool, str]:
        """
        [新機能] 分析結果(DataFrame)をExcelに出力する。
        ファイルが存在する場合は追記(Append)、存在しない場合は新規作成する。
        
        Args:
            df: 分析結果のDataFrame
            sheet_name: シート名（例: "商品-時間帯"）
            file_path: 保存先パス
            include_raw_data: Trueの場合、伝票一覧・ログなどの固定シートも出力/更新する
        """
        try:
            # シート名のサニタイズ（Excel制限対応）
            safe_sheet_name = self._sanitize_sheet_name(sheet_name)
            
            # 書き込むデータの準備
            data_map = {safe_sheet_name: df}

            # 生データを含める場合（AnalyticsServiceが必要）
            if include_raw_data and self.analytics_service:
                raw_datasets = self._get_raw_datasets()
                data_map.update(raw_datasets)

            # ファイルの存在確認
            mode = 'w'
            if_sheet_exists = None
            
            if os.path.exists(file_path):
                mode = 'a' # 追記モード
                if_sheet_exists = 'replace' # 同名シートは上書き (Pandas 1.3+)

            # 書き込み実行
            # ※ Pandasのバージョンが古いと if_sheet_exists でエラーになる可能性があります
            #    その場合は try-except で mode='w' にフォールバックするか、
            #    openpyxlで直接シート削除する処理が必要です。
            with pd.ExcelWriter(file_path, engine='openpyxl', mode=mode, if_sheet_exists=if_sheet_exists) as writer:
                for s_name, d_frame in data_map.items():
                    d_frame.to_excel(writer, sheet_name=s_name)

            return True, "出力しました"

        except ValueError as ve:
            # Pandasのバージョンが古くて if_sheet_exists が使えない場合などの対応
            if "if_sheet_exists" in str(ve):
                return False, "Excel追記エラー: Pandasのバージョンを1.3以上に更新してください"
            return False, str(ve)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"出力エラー: {str(e)}"

    # --- 内部ヘルパーメソッド ---

    def _get_raw_datasets(self) -> Dict[str, pd.DataFrame]:
        """AnalyticsServiceから生データを取得してDataFrame化"""
        datasets = {}
        
        # 伝票一覧
        tx_list = self.analytics_service.get_transaction_list()
        df_tx = self._process_transaction_list(tx_list)
        datasets['伝票一覧'] = df_tx
        
        # 操作ログ
        logs = self.analytics_service.get_logs()
        df_logs = self._process_logs(logs)
        datasets['操作ログ'] = df_logs
        
        return datasets

    def _process_transaction_list(self, tx_list: List[Dict]) -> pd.DataFrame:
        """伝票リストの整形・カラム名変更"""
        df = pd.DataFrame(tx_list)
        if 'timestamp' in df.columns:
            df = df.drop(columns=['timestamp'])
        
        if not df.empty:
            rename_map = {
                'id': '伝票ID',
                'time': '日時',
                'total': '合計',
                'items': '点数',
                'payment': '決済',
                'customer': '客層',
                'change': 'お釣り'
            }
            df.rename(columns=rename_map, inplace=True)
        return df

    def _process_logs(self, logs: List[Dict]) -> pd.DataFrame:
        """ログリストの整形"""
        df = pd.DataFrame(logs)
        if not df.empty:
            df.rename(columns={'time': '日時', 'level': 'レベル', 'msg': '内容'}, inplace=True)
        return df

    def _write_sheet(self, writer, df, sheet_name):
        """空データ対応のシート書き込み"""
        if df.empty:
            pd.DataFrame(["データなし"]).to_excel(writer, sheet_name=sheet_name)
        else:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    def _sanitize_sheet_name(self, name: str) -> str:
        """Excelシート名に使用できない文字を除去し、31文字以内に収める"""
        invalid_chars = ['\\', '/', '?', '*', '[', ']', ':']
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name[:31]