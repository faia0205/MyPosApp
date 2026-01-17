import sqlite3
import os

# データベースファイル名
DB_NAME = "pos_system.db"

def create_tables():
    """テーブルを作成する関数"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. 商品マスタ (色情報を追加)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        category TEXT, -- 'Food', 'Drink', 'Discount' など
        color TEXT DEFAULT '#f0f0f0',
        display_order INTEGER DEFAULT 0, -- 表示順序用
        is_active INTEGER DEFAULT 1,
        note TEXT
    )
    """)

    # 2. 決済方法マスタ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        is_cash INTEGER DEFAULT 0, -- 1なら現金（釣銭計算対象）
        is_active INTEGER DEFAULT 1
    )
    """)

    # 3. 客層プリセットマスタ
    # ボタンの表示名と、分析用の属性を分けて管理します
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        attributes TEXT,
        color TEXT DEFAULT '#b0bec5', -- 客層ボタンの色
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

    # --- トランザクション系 ---
    
    # 5. 取引ヘッダー
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount INTEGER NOT NULL,
        status TEXT DEFAULT 'completed' -- completed, voided
    )
    """)

    # 6. 取引詳細（商品）
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

    # 7. 取引決済（支払い方法）
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER,
        payment_method TEXT,
        amount INTEGER,
        FOREIGN KEY(transaction_id) REFERENCES transactions(id)
    )
    """)

    # --- 初期データの投入（テスト用完全版） ---
    
    # 商品データ
    # id, name, price, category, color, display_order, is_active, note
    products = [
        # --- フード (オレンジ系: #ffcc80) ---
        ("焼きそば", 500, "フード", "#ffcc80", 1, 1, "大盛り対応可"),
        ("たこ焼き", 500, "フード", "#ffcc80", 2, 1, ""),
        ("唐揚げ", 400, "フード", "#ffcc80", 3, 1, ""),
        ("フランクフルト", 300, "フード", "#ffcc80", 4, 1, ""),
        
        # --- ドリンク (水色系: #80d8ff) ---
        ("生ビール", 600, "ドリンク", "#80d8ff", 1, 1, "年齢確認必須"),
        ("ハイボール", 500, "ドリンク", "#80d8ff", 2, 1, "年齢確認必須"),
        ("ウーロン茶", 150, "ドリンク", "#80d8ff", 3, 1, ""),
        ("コーラ", 150, "ドリンク", "#80d8ff", 4, 1, ""),
        
        # --- その他・割引 (赤/ピンク系: #ff8a80) ---
        ("袋", 10, "その他", "#ffffff", 1, 1, ""),
        ("セット割引", -50, "割引", "#ff8a80", 99, 1, ""), # 表示順を後ろに
        ("ポイント割引", -100, "割引", "#ff8a80", 100, 1, "")
    ]
    cursor.executemany("""
        INSERT INTO products (name, price, category, color, display_order, is_active, note) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, products)

    # 決済方法
    payments = [("現金", 1), ("PayPay", 0), ("クレジット", 0)]
    cursor.executemany("INSERT INTO payment_methods (name, is_cash) VALUES (?, ?)", payments)

    # 客層プリセット (色を追加: 男性=青系, 女性=赤系, グループ=緑系)
    customer_data = [
        ("男1", '{"sex": "male", "count": 1}', "#bbdefb", 1),
        ("女1", '{"sex": "female", "count": 1}', "#f8bbd0", 2),
        ("男複数", '{"sex": "male", "count": "many"}', "#90caf9", 3),
        ("女複数", '{"sex": "female", "count": "many"}', "#f48fb1", 4),
        ("家族連れ", '{"type": "family"}', "#a5d6a7", 5),
        ("男女G", '{"type": "group"}', "#a5d6a7", 6)
    ]
    cursor.executemany("INSERT INTO customer_presets (label, attributes, color, display_order) VALUES (?, ?, ?, ?)", customer_data)
    
    # 経費初期データ
    cursor.execute("INSERT INTO expenses (title, amount) VALUES (?, ?)", ("材料費一式", 15000))

    conn.commit()
    conn.close()
    print(f"データベース {DB_NAME} を作成し、初期データを投入しました。")

if __name__ == "__main__":
    # 既存のDBがあれば削除して作り直す（開発初期のみ）
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    
    create_tables()