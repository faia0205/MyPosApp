import csv
import datetime
from typing import Dict, Set
from app.repositories.transaction_repo import TransactionRepository

class CsvTransactionExporter:
    """全期間の伝票データを動的カラム形式でCSVに出力するクラス"""
    
    def __init__(self, trans_repo: TransactionRepository):
        self.trans_repo = trans_repo
        self.JST = datetime.timezone(datetime.timedelta(hours=9), "JST")
    
    def _to_jst_str(self, utc_str: str) -> str:
        """UTCの文字列をJSTに変換"""
        if not utc_str or utc_str == "None":
            return "None"
        try:
            dt = datetime.datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
            dt_jst = dt.replace(tzinfo=datetime.timezone.utc).astimezone(self.JST)
            return dt_jst.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return utc_str # 変換できない場合は元の文字列を返す

    def export_all_transactions(self, filepath: str) -> None:
        # DBから全データを一括取得（高速化）
        data = self.trans_repo.get_all_export_data()

        # 現金決済のカラム名を取得（お釣り情報を加算するため）※固定カラムとして「お釣り」を追加するため、ここでは現金決済の名前だけ取得すればOK
        cash_payment_name = self.trans_repo.get_cash_payment_name()
        
        tx_map: Dict[int, dict] = {}
        all_payments: Set[str] = set()
        all_products: Set[str] = set()
        all_discounts: Set[str] = set()

        # 1. ヘッダー情報の初期化
        for row in data["headers"]:
            tx_id = row[0]
            tx_map[tx_id] = {
                "id": tx_id,
                "時間": self._to_jst_str(row[1]) if row[1] else "None",
                "合計金額": row[2] if row[2] is not None else 0,
                "お釣り": row[3] if row[3] is not None else 0,
                "客層": row[4] if row[4] else "None",
                "担当": row[5] if row[5] else "None",
                "payments": {},
                "products": {},
                "discounts": {}
            }

        # 2. 決済情報のマッピング
        for row in data["payments"]:
            tx_id, pay_method, amount = row[0], row[1], row[2]
            if tx_id in tx_map:
                all_payments.add(pay_method)

                if pay_method == cash_payment_name:
                    amount += tx_map[tx_id]["お釣り"] # 現金決済はお釣りを加算して預かり金額にする
                tx_map[tx_id]["payments"][pay_method] = amount

        # 3. 商品・割引情報のマッピング (unit_price < 0 を割引と判定)
        for row in data["items"]:
            tx_id, prod_name, unit_price, quantity = row[0], row[1], row[2], row[3]
            if tx_id in tx_map:
                if unit_price < 0:
                    all_discounts.add(prod_name)
                    # 同じ割引が複数ある場合は合算
                    tx_map[tx_id]["discounts"][prod_name] = tx_map[tx_id]["discounts"].get(prod_name, 0) + quantity
                else:
                    all_products.add(prod_name)
                    # 同じ商品が複数ある場合は合算
                    tx_map[tx_id]["products"][prod_name] = tx_map[tx_id]["products"].get(prod_name, 0) + quantity

        # 動的カラムの列順をソートして固定
        payment_headers = sorted(list(all_payments))
        product_headers = sorted(list(all_products))
        discount_headers = sorted(list(all_discounts))

        headers_csv = ["id", "時間", "合計金額"] + payment_headers + ["お釣り"] + product_headers + discount_headers + ["客層", "担当"]

        # 4. CSVへの書き込み
        with open(filepath, mode='w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(headers_csv)

            # ID順に書き出し
            for tx_id in sorted(tx_map.keys()):
                row_data = tx_map[tx_id]
                csv_row = [
                    row_data["id"],
                    row_data["時間"],
                    row_data["合計金額"]
                ]
                
                # 各決済 (該当なしは0)
                for ph in payment_headers:
                    csv_row.append(row_data["payments"].get(ph, 0))
                
                csv_row.append(row_data["お釣り"])
                
                # 各商品 (該当なしは0)
                for prh in product_headers:
                    csv_row.append(row_data["products"].get(prh, 0))
                    
                # 各割引 (該当なしは0)
                for dh in discount_headers:
                    csv_row.append(row_data["discounts"].get(dh, 0))
                    
                # 客層、担当 (該当なしは "None")
                csv_row.extend([row_data["客層"], row_data["担当"]])
                
                writer.writerow(csv_row)