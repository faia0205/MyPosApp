import sqlite3
import os
import sys

# appパッケージを読み込めるようにパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import DB_PATH, DATA_DIR

def create_tables():
    """テーブル作成と初期データ投入"""
    
    # dataフォルダがなければ作る
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 商品マスタ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        category TEXT,
        color TEXT DEFAULT '#f0f0f0',
        display_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        note TEXT
    )
    """)

    # 2. 決済方法マスタ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        is_cash INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 3. 客層プリセット
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        attributes TEXT,
        color TEXT DEFAULT '#b0bec5',
        display_order INTEGER,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 4. 経費テーブル
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        amount INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 5. トランザクション系
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount INTEGER NOT NULL,
        customer_label TEXT, 
        status TEXT DEFAULT 'completed'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        product_name TEXT,
        unit_price INTEGER,
        quantity INTEGER,
        subtotal INTEGER,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        payment_method TEXT,
        amount INTEGER,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    )
    """)

    # 6. 操作ログ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level TEXT,   -- info, warning, error
        message TEXT
    )
    """)

    # --- データ投入 (存在しない場合のみ) ---
    cursor.execute("SELECT count(*) FROM products")
    if cursor.fetchone()[0] == 0:
        print("Inserting initial data...")
        
        # 商品
        products = [
            # --- フード (オレンジ系: #ffcc80) ---
            ("焼きそば", 500, "フード", "#ffcc80", 1, "大盛り対応可"),
            ("たこ焼き", 500, "フード", "#ffcc80", 2, ""),
            ("唐揚げ", 400, "フード", "#ffcc80", 3, ""),
            ("フランクフルト", 300, "フード", "#ffcc80", 4, ""),

            # --- ドリンク (水色系: #80d8ff) ---
            ("生ビール", 600, "ドリンク", "#80d8ff", 1, "年齢確認必須"),
            ("ハイボール", 500, "ドリンク", "#80d8ff", 2, "年齢確認必須"),
            ("ウーロン茶", 150, "ドリンク", "#80d8ff", 3, ""),
            ("コーラ", 150, "ドリンク", "#80d8ff", 4, ""),

            # --- その他・割引 (赤/ピンク系: #ff8a80) ---
            ("袋", 10, "その他", "#ffffff", 1, ""),
            ("セット割引", -50, "割引", "#ff8a80", 99, ""), # 表示順を後ろに
            ("ポイント割引", -100, "割引", "#ff8a80", 100, "")
        ]
        cursor.executemany("INSERT INTO products (name, price, category, color, display_order, note) VALUES (?, ?, ?, ?, ?, ?)", products)

        # 決済方法
        payments = [("現金", 1), ("PayPay", 0), ("クレジット", 0)]
        cursor.executemany("INSERT INTO payment_methods (name, is_cash) VALUES (?, ?)", payments)

        # 客層
        customers = [
            ("男1", '{"sex": "male", "count": 1}', "#bbdefb", 1),
            ("女1", '{"sex": "female", "count": 1}', "#f8bbd0", 2),
            ("男複数", '{"sex": "male", "count": "many"}', "#90caf9", 3),
            ("女複数", '{"sex": "female", "count": "many"}', "#f48fb1", 4),
            ("家族連れ", '{"type": "family"}', "#a5d6a7", 5),
            ("男女グループ", '{"type": "group"}', "#a5d6a7", 6)
        ]
        cursor.executemany("INSERT INTO customer_presets (label, attributes, color, display_order) VALUES (?, ?, ?, ?)", customers)

        # 経費
        cursor.execute("INSERT INTO expenses (title, amount) VALUES (?, ?)", ("準備金", 15000))
        
        conn.commit()
    
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

if __name__ == "__main__":
    create_tables()


    