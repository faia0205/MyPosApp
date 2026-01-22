from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.payment_edit_dialog import PaymentEditDialog

class PaymentSettingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = TransactionRepository()
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
        
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "現金扱い", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        self.table.setStyleSheet("background-color: #222; color: white; gridline-color: #444;")
        layout.addWidget(self.table)

    def load_data(self):
        self.methods = self.repo.fetch_all_payment_methods()
        self.table.setRowCount(len(self.methods))
        for i, m in enumerate(self.methods):
            active = bool(m['is_active'])
            col = "white" if active else "#757575"
            
            def mk(txt):
                it = QTableWidgetItem(str(txt))
                it.setForeground(QColor(col))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            self.table.setItem(i, 0, mk(m['id']))
            self.table.setItem(i, 1, mk(m['name']))
            self.table.setItem(i, 2, mk("Yes" if m['is_cash'] else "No"))
            self.table.setItem(i, 3, mk("有効" if active else "無効"))

    def _add(self):
        dlg = PaymentEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.add_payment_method(d['name'], d['is_cash']):
                self.log_repo.add_log("info", f"支払方法追加: {d['name']}")
                self.load_data()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.methods[row]
        dlg = PaymentEditDialog(data=target, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.update_payment_method(target['id'], d['name'], d['is_cash'], d['is_active']):
                self.log_repo.add_log("info", f"支払方法更新: {target['name']}")
                self.load_data()