from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QGridLayout
from PySide6.QtCore import Qt
from app.repositories.user_repo import UserRepository

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("担当者選択")
        self.resize(400, 300)
        self.selected_user_name = "ゲスト"
        
        # スタイル (少しリッチに)
        self.setStyleSheet("""
            QDialog { background-color: #333; color: white; }
            QPushButton { 
                background-color: #0288d1; color: white; 
                font-size: 18px; font-weight: bold; 
                border-radius: 8px; padding: 15px;
            }
            QPushButton:hover { background-color: #039be5; }
            QLabel { font-size: 16px; font-weight: bold; }
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("レジ担当者を選択してください:"))
        layout.addSpacing(10)

        repo = UserRepository()
        users = repo.fetch_active_users()

        grid = QGridLayout()
        for i, user in enumerate(users):
            btn = QPushButton(f"{user['name']}\n({user['code']})")
            btn.clicked.connect(lambda _, n=user['name']: self._on_user_selected(n))
            grid.addWidget(btn, i // 2, i % 2)
        
        layout.addLayout(grid)
        layout.addStretch()

    def _on_user_selected(self, name):
        self.selected_user_name = name
        self.accept()