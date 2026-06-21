import os
import sys
# PyInstallerで実行されているかどうかの判定
if getattr(sys, 'frozen', False):
    # exe化されている場合：exeファイルがあるフォルダをベースにする
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
    # ご提示のコードの階層構造（appフォルダの親など）に合わせる場合：
    BASE_DIR = EXE_DIR
else:
    # 通常のPython実行の場合：元のロジック
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