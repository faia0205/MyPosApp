import os

# プロジェクトのルートディレクトリ (appフォルダの親)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# データフォルダとDBパスの設定
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_NAME = "pos_system.db"
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# アプリ設定
APP_TITLE = "Modular POS System"
WINDOW_SIZE = (1280, 800)

# 必要なフォルダがなければ作成
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)