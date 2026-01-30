from typing import List, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QLabel, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class BaseSettingTab(QWidget):
    """
    設定画面タブの基底クラス
    共通のレイアウト（ボタン群 + テーブル）とヘルパーメソッドを提供する。
    """
    def __init__(self, title: str = ""):
        super().__init__()
        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(10, 10, 10, 10)
        
        # タイトルや説明文（任意）
        if title:
            self.layout_main.addWidget(QLabel(title))

        self._setup_buttons()
        self._setup_table()
        
    def _setup_buttons(self):
        """上部の操作ボタンエリア構築"""
        self.layout_btns = QHBoxLayout()
        
        # 追加ボタン
        self.btn_add = QPushButton("＋ 新規追加")
        self.btn_add.setFixedSize(120, 40)
        self.btn_add.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold;")
        self.btn_add.clicked.connect(self.on_add)
        self.layout_btns.addWidget(self.btn_add)

        # 編集ボタン
        self.btn_edit = QPushButton("編集")
        self.btn_edit.clicked.connect(self.on_edit_selected)
        self.layout_btns.addWidget(self.btn_edit)

        # 拡張用プレースホルダ（継承先でボタンを追加したい場合に使用）
        self.layout_btns.addStretch()

        # 削除ボタン
        self.btn_delete = QPushButton("削除/無効化")
        self.btn_delete.setStyleSheet("background-color: #c62828; color: white;")
        self.btn_delete.clicked.connect(self.on_delete_selected)
        self.layout_btns.addWidget(self.btn_delete)

        self.layout_main.addLayout(self.layout_btns)

    def _setup_table(self):
        """テーブルの初期設定"""
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #222; gridline-color: #444; color: white; }
            QHeaderView::section { background-color: #333; color: white; border: 1px solid #444; }
            QTableWidget::item:selected { background-color: #0d47a1; }
        """)
        # ダブルクリックで編集
        self.table.doubleClicked.connect(self.on_edit_selected)
        
        self.layout_main.addWidget(self.table)

    def set_columns(self, columns: List[str]):
        """カラムヘッダーを設定"""
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch) # 2列目を伸縮

    def create_item(self, text: str, text_color: str = "white", bg_color: str = None, align: int = None) -> QTableWidgetItem:
        """テーブルアイテム作成ヘルパー"""
        item = QTableWidgetItem(str(text))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled) # 編集不可
        item.setForeground(QColor(text_color))
        if bg_color:
            item.setBackground(QColor(bg_color))
        if align:
            item.setTextAlignment(align)
        return item

    def get_selected_row_data(self, data_list: list):
        """選択行に対応するデータリストの要素を取得"""
        row = self.table.currentRow()
        if row < 0 or row >= len(data_list):
            return None
        return data_list[row]

    # --- 継承先で実装すべきメソッド ---
    def load_data(self):
        raise NotImplementedError

    def on_add(self):
        pass

    def on_edit_selected(self):
        pass

    def on_delete_selected(self):
        pass