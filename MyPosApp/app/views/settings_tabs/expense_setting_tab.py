from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from app.repositories.transaction_repo import TransactionRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.expense_edit_dialog import ExpenseEditDialog

class ExpenseSettingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = TransactionRepository()
        self.log_repo = LogRepository()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        btn_lay = QHBoxLayout()
        add_btn = QPushButton("＋ 経費登録")
        add_btn.setStyleSheet("background-color: #0277bd; color: white;")
        add_btn.clicked.connect(self._add)
        btn_lay.addWidget(add_btn)

        # 「編集」ボタンを追加
        edit_btn = QPushButton("編集")
        edit_btn.clicked.connect(self._edit)
        btn_lay.addWidget(edit_btn)
        
        del_btn = QPushButton("削除")
        del_btn.setStyleSheet("background-color: #c62828; color: white;")
        del_btn.clicked.connect(self._delete)
        btn_lay.addWidget(del_btn)
        
        btn_lay.addStretch()
        layout.addLayout(btn_lay)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "日時", "項目名", "金額"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setStyleSheet("background-color: #222; color: white; gridline-color: #444;")
        
        # ★追加: ダブルクリックで編集画面を開く
        self.table.doubleClicked.connect(self._edit)
        
        layout.addWidget(self.table)

    def load_data(self):
        expenses = self.repo.fetch_expense_list()
        self.table.setRowCount(len(expenses))
        self.expenses = expenses
        for i, ex in enumerate(expenses):
            # 日時変換は簡易的に
            ts = ex['timestamp']
            
            def mk(txt):
                it = QTableWidgetItem(str(txt))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            self.table.setItem(i, 0, mk(ex['id']))
            self.table.setItem(i, 1, mk(ts))
            self.table.setItem(i, 2, mk(ex['title']))
            self.table.setItem(i, 3, mk(f"¥{ex['amount']:,}"))

    def _add(self):
        dlg = ExpenseEditDialog(parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.add_expense(d['title'], d['amount']):
                self.log_repo.add_log("info", f"経費登録: {d['title']} ¥{d['amount']}")
                self.load_data()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.expenses[row]
        
        dlg = ExpenseEditDialog(data=target, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            if self.repo.update_expense(target['id'], d['title'], d['amount'], d['timestamp']):
                self.log_repo.add_log("info", f"経費編集: {target['title']} -> {d['title']}")
                self.load_data()

    def _delete(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.expenses[row]
        
        if QMessageBox.question(self, "確認", f"「{target['title']}」を削除しますか？\n(取り消せません)") == QMessageBox.Yes:
            if self.repo.delete_expense(target['id']):
                self.log_repo.add_log("warning", f"経費削除: {target['title']}")
                self.load_data()