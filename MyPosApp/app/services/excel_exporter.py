import pandas as pd
from typing import List, Dict, Tuple
from app.services.interfaces.report_exporter import IReportExporter

class ExcelReportExporter(IReportExporter):
    """
    Excel帳票出力の責務を持つクラス
    IReportExporter インターフェースを実装
    """

    def export(self, file_path: str, tx_list: List[Dict], logs: List[Dict], pivots: Dict[str, pd.DataFrame]) -> Tuple[bool, str]:
        try:
            # 1. データフレーム変換と整形
            df_tx = pd.DataFrame(tx_list)
            df_logs = pd.DataFrame(logs)

            # タイムスタンプ列の調整
            if 'timestamp' in df_tx.columns:
                df_tx = df_tx.drop(columns=['timestamp'])

            # カラム名の日本語化
            if not df_tx.empty:
                rename_map = {
                    'id': '伝票ID',
                    'time': '日時',
                    'total': '合計',
                    'items': '点数',
                    'payment': '決済',
                    'customer': '客層',
                    'change': 'お釣り'
                }
                df_tx.rename(columns=rename_map, inplace=True)

            if not df_logs.empty:
                df_logs.rename(columns={'time': '日時', 'level': 'レベル', 'msg': '内容'}, inplace=True)

            # 2. Excelファイルへの書き込み
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 伝票一覧シート
                if df_tx.empty:
                    pd.DataFrame(["データなし"]).to_excel(writer, sheet_name='伝票一覧')
                else:
                    df_tx.to_excel(writer, sheet_name='伝票一覧', index=False)
                
                # 操作ログシート
                if not df_logs.empty:
                    df_logs.to_excel(writer, sheet_name='操作ログ', index=False)

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