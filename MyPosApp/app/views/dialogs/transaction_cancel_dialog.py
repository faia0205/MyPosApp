from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from app.services.analytics_service import AnalyticsService
from app.services.checkout_service import CheckoutService

class TransactionCancelDialog(QDialog):
    def __init__(self, analytics_service: AnalyticsService, checkout_service: CheckoutService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("伝票取消")
        self.resize(800, 500)
        self.analytics_service = analytics_service
        self.checkout_service = checkout_service

        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; }
            QTableWidget { background-color: #333; gridline-color: #555; color: white; }
            QHeaderView::section { background-color: #444; color: white; padding: 4px; border: 1px solid #555; }
            QTableWidget::item:selected { background-color: #d32f2f; }
        """)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["伝票ID", "日時", "客層", "決済方法", "金額", "お釣り"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        
        self.btn_cancel_tx = QPushButton("選択した伝票を取消")
        self.btn_cancel_tx.setFixedSize(200, 40)
        self.btn_cancel_tx.setStyleSheet("background-color: #c62828; color: white; font-weight: bold; border-radius: 4px;")
        self.btn_cancel_tx.clicked.connect(self._on_cancel_clicked)
        btn_layout.addWidget(self.btn_cancel_tx)

        self.btn_close = QPushButton("閉じる")
        self.btn_close.setFixedSize(120, 40)
        self.btn_close.setStyleSheet("background-color: #555; color: white; border-radius: 4px;")
        self.btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _load_data(self):
        self.transactions = self.analytics_service.get_transaction_list()
        self.table.setRowCount(len(self.transactions))
        for row, tx in enumerate(self.transactions):
            self.table.setItem(row, 0, QTableWidgetItem(str(tx['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(str(tx['time'])))
            self.table.setItem(row, 2, QTableWidgetItem(str(tx['customer'])))
            self.table.setItem(row, 3, QTableWidgetItem(str(tx['payment'])))
            self.table.setItem(row, 4, QTableWidgetItem(f"¥{tx['total']:,}"))
            self.table.setItem(row, 5, QTableWidgetItem(f"¥{tx['change']:,}"))

    def _on_cancel_clicked(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "エラー", "取り消す伝票を選択してください。")
            return

        row = selected_rows[0].row()
        tx_id = self.transactions[row]['id']

        msg = f"伝票ID: {tx_id} を本当に取り消しますか？\nこの操作は元に戻せません。"
        if QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if self.checkout_service.cancel_transaction(tx_id):
                QMessageBox.information(self, "成功", f"伝票ID: {tx_id} を取り消しました。")
                self._load_data()
            else:
                QMessageBox.critical(self, "エラー", "伝票の取消に失敗しました。")