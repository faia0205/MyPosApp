import sys
import os
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont

# appパッケージのパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.config import DB_PATH
from init_db import create_tables
from app.utils.logger import setup_logger

logger = setup_logger()

def global_exception_handler(exc_type, exc_value, exc_traceback):
    """未捕捉の例外をキャッチするグローバルハンドラ"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # スタックトレースをフォーマットしてテキストログに出力
    err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical(f"Uncaught exception:\n{err_msg}")

    # UIへの強制ポップアップ通知
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("重大なエラー")
    msg_box.setText("予期せぬエラーが発生しました。アプリを終了します。")
    msg_box.setDetailedText(err_msg)
    msg_box.exec()

    sys.exit(1)

# グローバル例外ハンドラを登録
sys.excepthook = global_exception_handler

from app.views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    if not os.path.exists(DB_PATH):
        logger.info("Database not found. Initializing...")
        create_tables()
    
    # フォント設定
    font = QFont("Yu Gothic UI", 12)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())