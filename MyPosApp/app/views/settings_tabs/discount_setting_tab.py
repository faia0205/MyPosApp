from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.discount_edit_dialog import DiscountEditDialog

class DiscountSettingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = DiscountRepository()
        self.log_repo = LogRepository()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        btn_lay = QHBoxLayout()
        add_btn = QPushButton("＋ ルール追加")
        add_btn.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold; padding: 5px 15px;")
        add_btn.clicked.connect(self._add)
        btn_lay.addWidget(add_btn)

        edit_btn = QPushButton("編集")
        edit_btn.setStyleSheet("padding: 5px 15px;")
        edit_btn.clicked.connect(self._edit)
        btn_lay.addWidget(edit_btn)
        
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "内容", "対象", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # 対象も見やすく広げる
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        
        # テーブル全体のスタイル
        self.table.setStyleSheet("""
            QTableWidget { background-color: #222; color: white; gridline-color: #444; }
            QHeaderView::section { background-color: #333; color: white; border: 1px solid #444; padding: 4px; }
            QTableWidget::item:selected { background-color: #0d47a1; }
        """)
        layout.addWidget(self.table)

    def load_data(self):
        rules = self.repo.fetch_all_rules()
        self.table.setRowCount(len(rules))
        self.rules = rules
        
        for i, r in enumerate(rules):
            is_active = bool(r['is_active'])
            
            # 基本色（無効ならグレー）
            base_col = "white" if is_active else "#757575"
            
            def mk(txt, color=None):
                it = QTableWidgetItem(str(txt))
                # 指定がなければ基本色を使う
                it.setForeground(QColor(color if color and is_active else base_col))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            self.table.setItem(i, 0, mk(r['id']))
            self.table.setItem(i, 1, mk(r['name']))
            
            # 内容 (例: 100円引, 10%引)
            unit = "円引" if r['discount_type'] == 'fixed' else "%OFF"
            val_text = f"{r['discount_value']}{unit}"
            # 値引き内容は少し強調（黄色っぽい色）
            self.table.setItem(i, 2, mk(val_text, "#ffeb3b"))
            
            # --- ★改善: 対象の見やすさ向上 ---
            atype = r['apply_type']
            target_val = r['target_value']
            
            target_text = ""
            target_color = "white"

            if atype == 'cart':
                target_text = "■ カート全体"
                target_color = "#81d4fa" # 水色
            elif atype == 'category':
                target_text = f"【カテゴリ】 {target_val}"
                target_color = "#ffcc80" # オレンジ
            elif atype == 'item':
                target_text = f"【 商  品 】 {target_val}"
                target_color = "#a5d6a7" # 薄緑
            elif atype == 'bundle':
                # ★追加: バンドルの中身を少し表示
                target_text = "★ セット・バンドル"
                target_color = "#e1bee7" # 紫系
                # target_val (JSON) を簡易解析して表示しても良い
                if "select" in target_val: target_text += " (まとめ買い)"
                else: target_text += " (組合せ)"
                
            self.table.setItem(i, 3, mk(target_text, target_color))
            # ------------------------------------
            
            self.table.setItem(i, 4, mk("有効" if is_active else "無効"))

    def _add(self):
        dlg = DiscountEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.add_rule(d['name'], d['discount_type'], d['discount_value'], 
                                  d['apply_type'], d['target_value'], d['is_auto']):
                self.log_repo.add_log("info", f"割引ルール追加: {d['name']}")
                self.load_data()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0: return
        target = self.rules[row]
        
        dlg = DiscountEditDialog(data=target, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.update_rule(target['id'], d['name'], d['discount_type'], d['discount_value'], 
                                     d['apply_type'], d['target_value'], d['is_auto'], d['is_active']):
                self.log_repo.add_log("info", f"割引ルール更新: {target['name']}")
                self.load_data()