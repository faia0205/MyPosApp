from enum import Enum, auto

class AnalysisAxis(Enum):
    """分析軸の定義"""
    NONE = "none"               # 指定なし
    TIME_MONTH = "time_month"   # 月別
    TIME_DOW = "time_dow"       # 曜日別
    TIME_HOUR = "time_hour"     # 時間帯別
    PRODUCT_NAME = "prod_name"  # 商品名
    PRODUCT_CAT = "prod_cat"    # カテゴリ
    CUSTOMER_LBL = "cust_label" # 客層ラベル
    CUSTOMER_SEX = "cust_sex"   # 性別 (属性)
    CUSTOMER_AGE = "cust_age"   # 年代 (属性)
    CASHIER = "cashier"         # 担当者
    PAYMENT = "payment"         # 決済方法

class AnalysisMetric(Enum):
    """集計対象（値）の定義"""
    SALES = "sales"       # 売上金額
    QUANTITY = "qty"      # 販売個数
    TX_COUNT = "tx_count" # 客数（伝票数）