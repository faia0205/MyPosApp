import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

# appパッケージのパスを通す
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.views.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # フォント設定
    font = QFont("Yu Gothic UI", 12)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())