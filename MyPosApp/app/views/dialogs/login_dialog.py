from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QGridLayout
from PySide6.QtCore import Qt
from app.repositories.user_repo import UserRepository

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("担当者選択")
        self.resize(400, 300)
        self.selected_user_name = "ゲスト"
        
        # 基本スタイル（有効なボタン用）
        self.active_style = """
            QPushButton { 
                background-color: #0288d1; color: white; 
                font-size: 18px; font-weight: bold; 
                border-radius: 8px; padding: 15px;
            }
            QPushButton:hover { background-color: #039be5; }
        """
        
        # 無効なボタン用のスタイル（グレーアウト）
        self.inactive_style = """
            QPushButton { 
                background-color: #424242; color: #757575; 
                font-size: 18px; font-weight: bold; 
                border-radius: 8px; padding: 15px;
                border: 1px solid #616161;
            }
        """

        # スタイル (少しリッチに)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLabel {{ font-size: 16px; font-weight: bold; }}
            {self.active_style}
        """)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("レジ担当者を選択してください:"))
        layout.addSpacing(10)

        repo = UserRepository()
        users = repo.fetch_all_users()

        grid = QGridLayout()
        for i, user in enumerate(users):
            # user_repo.py でキーを統一したので user_code を使用
            code = user.user_code
            is_active = user.is_active
            
            label_text = f"{user.name}\n({code})"
            if not is_active:
                label_text += "(無効)"

            btn = QPushButton(label_text)
            
            if is_active:
                # 有効な場合: クリックイベントを設定
                btn.clicked.connect(lambda _, n=user.name: self._on_user_selected(n))
                # スタイルはデフォルト（active_style）が適用される
            else:
                # 無効な場合: ボタンを無効化し、グレーアウト用スタイルを適用
                btn.setEnabled(False)
                btn.setStyleSheet(self.inactive_style)
            
            grid.addWidget(btn, i // 2, i % 2)
        
        layout.addLayout(grid)
        layout.addStretch()

    def _on_user_selected(self, name):
        self.selected_user_name = name
        self.accept()