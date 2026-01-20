import sqlite3
import os
import sys
import json

# appパッケージを読み込めるようにパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import DB_PATH, DATA_DIR

# マスタデータのJSONパス
MASTER_DATA_PATH = os.path.join(DATA_DIR, 'master_data.json')

def load_master_data():
    """JSONファイルからマスタデータを読み込む"""
    if not os.path.exists(MASTER_DATA_PATH):
        print(f"Warning: {MASTER_DATA_PATH} not found. Skipping data insertion.")
        return None
    
    try:
        with open(MASTER_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return None

def create_tables():
    """テーブル作成とJSONからの初期データ投入"""
    
    # dataフォルダがなければ作る
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- テーブル定義 (変更なし) ---

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

    # 6. 操作ログ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operation_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level TEXT,
        message TEXT
    )
    """)

    # 7. ユーザー（レジ担当者）マスタ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        user_code TEXT UNIQUE,
        role TEXT DEFAULT 'staff',
        is_active INTEGER DEFAULT 1
    )
    """)

    # 8. 割引ルール (親)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discount_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        required_qty INTEGER NOT NULL,
        discount_amount INTEGER NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    # 9. 割引対象商品 (子: 中間テーブル)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discount_targets (
        rule_id INTEGER,
        product_id INTEGER,
        FOREIGN KEY(rule_id) REFERENCES discount_rules(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    # --- データ投入処理 ---
    
    # 既存データがあるかチェック（二重登録防止のため、productsテーブルが空のときのみ実行）
    cursor.execute("SELECT count(*) FROM products")
    if cursor.fetchone()[0] == 0:
        data = load_master_data()
        
        if data:
            print("Inserting initial data from JSON...")

            # 1. Products
            products_data = []
            for p in data.get("products", []):
                products_data.append((
                    p["name"], p["price"], p["category"], p["color"], 
                    p["display_order"], int(p.get("is_active", True)), p.get("note", "")
                ))
            cursor.executemany("""
                INSERT INTO products (name, price, category, color, display_order, is_active, note) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, products_data)

            # 2. Payment Methods
            payments_data = []
            for pm in data.get("payment_methods", []):
                payments_data.append((
                    pm["name"], int(pm["is_cash"]), int(pm.get("is_active", True))
                ))
            cursor.executemany("INSERT INTO payment_methods (name, is_cash, is_active) VALUES (?, ?, ?)", payments_data)

            # 3. Customer Presets
            presets_data = []
            for cp in data.get("customer_presets", []):
                # 属性は辞書からJSON文字列へ変換して保存
                attr_str = json.dumps(cp["attributes"], ensure_ascii=False)
                presets_data.append((
                    cp["label"], attr_str, cp["color"], cp["display_order"]
                ))
            cursor.executemany("INSERT INTO customer_presets (label, attributes, color, display_order) VALUES (?, ?, ?, ?)", presets_data)

            # 4. Users
            users_data = []
            for u in data.get("users", []):
                users_data.append((
                    u["name"],
                    u["user_code"],
                    u.get("role", "staff"), # roleがなければ staff にする
                    int(u.get("is_active", True))
                ))
            
            cursor.executemany("""
                INSERT INTO users (name, user_code, role, is_active) 
                VALUES (?, ?, ?, ?)
            """, users_data)

            # 5. Initial Expenses
            for exp in data.get("initial_expenses", []):
                cursor.execute("INSERT INTO expenses (title, amount) VALUES (?, ?)", (exp["title"], exp["amount"]))

            # 6. Discount Rules & Targets (Complex Logic)
            for rule in data.get("discount_rules", []):
                # ルール親の挿入
                cursor.execute("""
                    INSERT INTO discount_rules (name, required_qty, discount_amount) 
                    VALUES (?, ?, ?)
                """, (rule["name"], rule["required_qty"], rule["discount_amount"]))
                
                new_rule_id = cursor.lastrowid
                target_names = rule.get("target_product_names", [])

                if target_names:
                    # 名前からIDを引いて紐付け (一度に解決するIN句を使用)
                    placeholders = ','.join('?' * len(target_names))
                    cursor.execute(f"SELECT id FROM products WHERE name IN ({placeholders})", target_names)
                    product_ids = [row[0] for row in cursor.fetchall()]
                    
                    target_data = [(new_rule_id, pid) for pid in product_ids]
                    cursor.executemany("INSERT INTO discount_targets (rule_id, product_id) VALUES (?, ?)", target_data)

            conn.commit()
            print("Data insertion completed.")
        else:
            print("No data inserted (JSON missing or invalid).")
    
    conn.close()
    print(f"Database initialized at: {DB_PATH}")

if __name__ == "__main__":
    create_tables()