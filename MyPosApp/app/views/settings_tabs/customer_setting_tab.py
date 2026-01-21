from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.repositories.customer_repo import CustomerRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.customer_edit_dialog import CustomerEditDialog

class CustomerSettingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = CustomerRepository()
        self.log_repo = LogRepository()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        btn_lay = QHBoxLayout()
        add_btn = QPushButton("＋ 追加")
        add_btn.setStyleSheet("background-color: #0277bd; color: white;")
        add_btn.clicked.connect(self._add)
        btn_lay.addWidget(add_btn)
        
        edit_btn = QPushButton("編集")
        edit_btn.clicked.connect(self._edit)
        btn_lay.addWidget(edit_btn)

        up_btn = QPushButton("▲ 上へ")
        up_btn.clicked.connect(lambda: self._move(-1))
        btn_lay.addWidget(up_btn)
        
        down_btn = QPushButton("▼ 下へ")
        down_btn.clicked.connect(lambda: self._move(1))
        btn_lay.addWidget(down_btn)
        
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "ラベル", "属性", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        self.table.setStyleSheet("background-color: #222; color: white; gridline-color: #444;")
        layout.addWidget(self.table)

    def load_data(self):
        self.customers = self.repo.fetch_all_presets()
        self.table.setRowCount(len(self.customers))
        for i, c in enumerate(self.customers):
            is_active = c['is_active']
            col = "white" if is_active else "#757575"
            bg = None if is_active else "#2b2b2b"

            def mk_item(txt):
                it = QTableWidgetItem(str(txt))
                it.setForeground(QColor(col))
                if bg: it.setBackground(QColor(bg))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            self.table.setItem(i, 0, mk_item(c['id']))
            self.table.setItem(i, 1, mk_item(c['label']))
            self.table.setItem(i, 2, mk_item(str(c['attributes'])))
            self.table.setItem(i, 3, mk_item("有効" if is_active else "無効"))
            
            # 色プレビューを背景に設定
            if is_active:
                self.table.item(i, 1).setBackground(QColor(c['color']))
                self.table.item(i, 1).setForeground(QColor("black"))

    def _add(self):
        dlg = CustomerEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.add_preset(d['label'], d['attributes'], d['color'], d['is_active']):
                self.log_repo.add_log("info", f"客層追加: {d['label']}")
                self.load_data()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0: return
        target = self.customers[row]
        dlg = CustomerEditDialog(data=target, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.update_preset(target['id'], d['label'], d['attributes'], d['color'], d['is_active']):
                self.log_repo.add_log("info", f"客層変更: {target['label']}")
                self.load_data()

    def _move(self, direction):
        row = self.table.currentRow()
        if row < 0: return
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.customers): return
        
        a, b = self.customers[row], self.customers[new_row]
        order_map = {a['id']: b['display_order'], b['id']: a['display_order']}
        if self.repo.update_display_order(order_map):
            self.load_data()
            self.table.selectRow(new_row)