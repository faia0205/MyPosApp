from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from dataclasses import asdict # ★追加

from app.repositories.discount_repo import DiscountRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.discount_edit_dialog import DiscountEditDialog
from app.models.discount import DiscountRule # ★追加

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
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: #222; color: white; gridline-color: #444; }
            QHeaderView::section { background-color: #333; color: white; border: 1px solid #444; padding: 4px; }
            QTableWidget::item:selected { background-color: #0d47a1; }
        """)
        layout.addWidget(self.table)

    def load_data(self):
        rules = self.repo.fetch_all_rules() # オブジェクトのリストが返る
        self.table.setRowCount(len(rules))
        self.rules = rules
        
        for i, r in enumerate(rules):
            # ★修正: 辞書キー['key']ではなく属性.keyにアクセス
            is_active = r.is_active
            
            base_col = "white" if is_active else "#757575"
            
            def mk(txt, color=None):
                it = QTableWidgetItem(str(txt))
                it.setForeground(QColor(color if color and is_active else base_col))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            self.table.setItem(i, 0, mk(r.id))
            self.table.setItem(i, 1, mk(r.name))
            
            unit = "円引" if r.discount_type == 'fixed' else "%OFF"
            val_text = f"{r.discount_value}{unit}"
            self.table.setItem(i, 2, mk(val_text, "#ffeb3b"))
            
            atype = r.apply_type
            target_val = r.target_value
            
            target_text = ""
            target_color = "white"

            if atype == 'cart':
                target_text = "■ カート全体"
                target_color = "#81d4fa"
            elif atype == 'category':
                target_text = f"【カテゴリ】 {target_val}"
                target_color = "#ffcc80"
            elif atype == 'item':
                target_text = f"【 商  品 】 {target_val}"
                target_color = "#a5d6a7"
            elif atype == 'bundle':
                target_text = "★ セット・バンドル"
                target_color = "#e1bee7"
                if "select" in target_val: target_text += " (まとめ買い)"
                else: target_text += " (組合せ)"
                
            self.table.setItem(i, 3, mk(target_text, target_color))
            self.table.setItem(i, 4, mk("有効" if is_active else "無効"))

    def _add(self):
        dlg = DiscountEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data() # ダイアログからは辞書が返る
            
            # ★修正: オブジェクトを作成してRepositoryに渡す
            new_rule = DiscountRule(
                id=None,
                name=d['name'],
                discount_type=d['discount_type'],
                discount_value=d['discount_value'],
                apply_type=d['apply_type'],
                target_value=d['target_value'],
                is_auto=d['is_auto'],
                is_active=d['is_active']
            )
            
            if self.repo.add(new_rule):
                self.log_repo.add_log("info", f"割引ルール追加: {d['name']}")
                self.load_data()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0: return
        target_obj = self.rules[row]
        
        # ★修正: ダイアログは辞書を期待しているので変換して渡す
        target_dict = asdict(target_obj)
        
        dlg = DiscountEditDialog(data=target_dict, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            
            # ★修正: 更新用オブジェクト作成
            updated_rule = DiscountRule(
                id=target_obj.id,
                name=d['name'],
                discount_type=d['discount_type'],
                discount_value=d['discount_value'],
                apply_type=d['apply_type'],
                target_value=d['target_value'],
                is_auto=d['is_auto'],
                is_active=d['is_active']
            )
            
            if self.repo.update(updated_rule):
                self.log_repo.add_log("info", f"割引ルール更新: {d['name']}")
                self.load_data()