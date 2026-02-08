import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

# appパッケージのパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import DB_PATH
from init_db import create_tables # init_dbをインポート

from app.views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if not os.path.exists(DB_PATH):
        print("Database not found. Initializing...")
        create_tables()
    
    # フォント設定
    font = QFont("Yu Gothic UI", 12)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())