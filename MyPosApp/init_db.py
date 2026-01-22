import sqlite3
import os
import sys
import json

# appパッケージを読み込めるようにパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import DB_PATH, DATA_DIR

MASTER_DATA_PATH = os.path.join(DATA_DIR, 'master_data.json')

def load_master_data():
    if not os.path.exists(MASTER_DATA_PATH):
        print(f"Warning: {MASTER_DATA_PATH} not found.")
        return None
    try:
        with open(MASTER_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def create_tables():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1-7. 他のテーブル (変更なし) ---
    # 商品マスタ
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
    # 決済方法
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        is_cash INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )
    """)
    # 客層
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
    # 経費
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        amount INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # トランザクション
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount INTEGER NOT NULL,
        change INTEGER DEFAULT 0,
        customer_label TEXT,
        cashier_name TEXT,
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
    # ログ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level TEXT,
        message TEXT
    )
    """)
    # ユーザー
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        user_code TEXT UNIQUE,
        role TEXT DEFAULT 'staff',
        is_active INTEGER DEFAULT 1
    )
    """)

    # --- 8. 割引ルール (★スキーマ変更) ---
    # 開発中はテーブル作り直し推奨
    cursor.execute("DROP TABLE IF EXISTS discount_targets") # 旧テーブル削除
    cursor.execute("DROP TABLE IF EXISTS discount_rules")   # 旧テーブル削除

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discount_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        discount_type TEXT NOT NULL DEFAULT 'fixed',
        discount_value INTEGER NOT NULL,
        apply_type TEXT NOT NULL DEFAULT 'cart',
        target_value TEXT,
        is_auto INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )
    """)

    # --- データ投入 ---
    cursor.execute("SELECT count(*) FROM products")
    if cursor.fetchone()[0] == 0:
        data = load_master_data()
        if data:
            print("Inserting initial data...")

            # Products
            p_data = [(p["name"], p["price"], p["category"], p["color"], p["display_order"], int(p.get("is_active", 1)), p.get("note", "")) for p in data.get("products", [])]
            cursor.executemany("INSERT INTO products (name, price, category, color, display_order, is_active, note) VALUES (?, ?, ?, ?, ?, ?, ?)", p_data)

            # Payments
            pay_data = [(pm["name"], int(pm["is_cash"]), int(pm.get("is_active", 1))) for pm in data.get("payment_methods", [])]
            cursor.executemany("INSERT INTO payment_methods (name, is_cash, is_active) VALUES (?, ?, ?)", pay_data)

            # Customer Presets
            presets_data = []
            for cp in data.get("customer_presets", []):
                # 属性は辞書からJSON文字列へ変換して保存
                attr_str = json.dumps(cp["attributes"], ensure_ascii=False)
                # ★修正: is_active を取得 (デフォルトは True/1)
                is_active = int(cp.get("is_active", 1))
                
                presets_data.append((
                    cp["label"], attr_str, cp["color"], cp["display_order"], is_active
                ))
            
            # ★修正: INSERT文に is_active を追加
            cursor.executemany("""
                INSERT INTO customer_presets (label, attributes, color, display_order, is_active) 
                VALUES (?, ?, ?, ?, ?)
            """, presets_data)

            # Users
            u_data = [(u["name"], u["user_code"], u.get("role", "staff"), int(u.get("is_active", 1))) for u in data.get("users", [])]
            cursor.executemany("INSERT INTO users (name, user_code, role, is_active) VALUES (?, ?, ?, ?)", u_data)

            # Expenses
            for exp in data.get("initial_expenses", []):
                cursor.execute("INSERT INTO expenses (title, amount) VALUES (?, ?)", (exp["title"], exp["amount"]))

            # ★ Discount Rules (新)
            d_rules = []
            for r in data.get("discount_rules", []):
                d_rules.append((
                    r["name"], 
                    r.get("discount_type", "fixed"), 
                    r.get("discount_value", 0),
                    r.get("apply_type", "cart"),
                    r.get("target_value", None),
                    int(r.get("is_auto", 0)),
                    int(r.get("is_active", 1))
                ))
            
            cursor.executemany("""
                INSERT INTO discount_rules (name, discount_type, discount_value, apply_type, target_value, is_auto, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, d_rules)

            conn.commit()
            print("Data insertion completed.")
        else:
            print("No data inserted (JSON missing or invalid).")
    
    conn.close()
    print("Database initialized.")

if __name__ == "__main__":
    create_tables()