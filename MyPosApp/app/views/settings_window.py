from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QPushButton, QMessageBox, QLabel, QWidget)
from PySide6.QtCore import Qt
from app.services.master_data_service import MasterDataService

# 作成したタブをインポート
from app.views.settings_tabs.product_setting_tab import ProductSettingTab
# from app.views.settings_tabs.user_setting_tab import UserSettingTab # (未実装の場合コメントアウト)

class SettingsWindow(QDialog):
    """設定管理・マスタ編集ウィンドウ"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("システム設定・マスタ管理")
        self.resize(1000, 700)
        
        # 全体スタイル
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QTabWidget::pane { border: 1px solid #444; top: -1px; }
            QTabBar::tab { background: #333; color: #aaa; padding: 10px 20px; border: 1px solid #444; }
            QTabBar::tab:selected { background: #546e7a; color: white; font-weight: bold; border-bottom: 1px solid #546e7a; }
            QLabel { color: white; }
        """)

        self.master_service = MasterDataService()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- ヘッダー ---
        header = QHBoxLayout()
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("MASTER SETTINGS")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #90caf9;")
        lbl_desc = QLabel("設定はDBに即時保存されます。「JSON出力」でバックアップと初期化用ファイルを作成します。")
        lbl_desc.setStyleSheet("color: #ccc; font-size: 12px;")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_desc)
        
        header.addLayout(title_box)
        header.addStretch()
        
        # アクションボタン
        btn_export = QPushButton("💾 設定を保存してJSON出力")
        btn_export.setFixedSize(220, 50)
        btn_export.setStyleSheet("""
            QPushButton { 
                background-color: #c62828; color: white; font-weight: bold; font-size: 14px; 
                border-radius: 5px; 
            }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        btn_export.clicked.connect(self._export_to_json)
        header.addWidget(btn_export)
        
        layout.addLayout(header)

        # --- タブエリア ---
        self.tabs = QTabWidget()
        
        # 1. 商品管理
        self.tab_product = ProductSettingTab()
        self.tabs.addTab(self.tab_product, "商品管理")

        # 2. ユーザー管理 (まだ実装していない場合、プレースホルダー)
        # self.tab_user = UserSettingTab()
        # self.tabs.addTab(self.tab_user, "ユーザー管理")
        self.tabs.addTab(QWidget(), "ユーザー管理(未)")
        self.tabs.addTab(QWidget(), "その他設定(未)")

        layout.addWidget(self.tabs)

    def _export_to_json(self):
        """DBの内容をJSONに書き出す"""
        msg = "現在のデータベースの設定内容で `master_data.json` を上書きします。\n\nこれにより、次回「初期化」を行った際にもこの設定が復元されます。\n実行しますか？"
        if QMessageBox.question(self, "確認", msg) != QMessageBox.Yes:
            return

        if self.master_service.save_db_to_json():
            QMessageBox.information(self, "完了", "JSONファイルへの出力が完了しました。\nバックアップファイルも作成されました。")
        else:
            QMessageBox.critical(self, "エラー", "出力に失敗しました。ログを確認してください。")