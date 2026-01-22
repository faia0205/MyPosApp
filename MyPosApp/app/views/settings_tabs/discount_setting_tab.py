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
        add_btn.setStyleSheet("background-color: #0277bd; color: white;")
        add_btn.clicked.connect(self._add)
        btn_lay.addWidget(add_btn)

        edit_btn = QPushButton("編集")
        edit_btn.clicked.connect(self._edit)
        btn_lay.addWidget(edit_btn)
        
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "内容", "対象", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        self.table.setStyleSheet("background-color: #222; color: white; gridline-color: #444;")
        layout.addWidget(self.table)

    def load_data(self):
        rules = self.repo.fetch_all_rules()
        self.table.setRowCount(len(rules))
        self.rules = rules
        
        for i, r in enumerate(rules):
            is_active = bool(r['is_active'])
            col = "white" if is_active else "#757575"
            
            def mk(txt):
                it = QTableWidgetItem(str(txt))
                it.setForeground(QColor(col))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            self.table.setItem(i, 0, mk(r['id']))
            self.table.setItem(i, 1, mk(r['name']))
            
            # 内容 (例: 100円引, 10%引)
            unit = "円引" if r['discount_type'] == 'fixed' else "%OFF"
            self.table.setItem(i, 2, mk(f"{r['discount_value']}{unit}"))
            
            # 対象
            target = r['apply_type']
            if r['target_value']: target += f" ({r['target_value']})"
            self.table.setItem(i, 3, mk(target))
            
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