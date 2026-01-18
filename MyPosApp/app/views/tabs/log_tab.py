from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, 
                               QTableWidgetItem, QHeaderView)
from PySide6.QtGui import QColor

class LogTab(QWidget):
    def __init__(self, service):
        super().__init__()
        self.service = service
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        self.table_logs = QTableWidget()
        self.table_logs.setColumnCount(3)
        self.table_logs.setHorizontalHeaderLabels(["日時", "レベル", "内容"])
        h = self.table_logs.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        layout.addWidget(self.table_logs)

    def update_data(self):
        logs = self.service.get_logs()
        self.table_logs.setRowCount(len(logs))
        for i, log in enumerate(logs):
            self.table_logs.setItem(i, 0, QTableWidgetItem(str(log['time'])))
            
            lvl = QTableWidgetItem(log['level'])
            if log['level'] == 'error':
                lvl.setForeground(QColor("#ff5252"))
            elif log['level'] == 'warning':
                lvl.setForeground(QColor("#ff9800"))
            else:
                lvl.setForeground(QColor("#4caf50"))
                
            self.table_logs.setItem(i, 1, lvl)
            self.table_logs.setItem(i, 2, QTableWidgetItem(log['msg']))