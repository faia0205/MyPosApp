from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QPushButton, QHeaderView, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from app.repositories.customer_repo import CustomerRepository
from app.repositories.log_repo import LogRepository
from app.views.dialogs.customer_edit_dialog import CustomerEditDialog
from app.models.customer import Customer
from dataclasses import asdict

class CustomerSettingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.repo = CustomerRepository()
        self.log_repo = LogRepository()
        self._init_ui()
        self.load_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- ボタン ---
        btn_lay = QHBoxLayout()
        add_btn = QPushButton("＋ 追加")
        add_btn.setStyleSheet("background-color: #0277bd; color: white; font-weight: bold; padding: 5px 15px;")
        add_btn.clicked.connect(self._add)
        btn_lay.addWidget(add_btn)
        
        edit_btn = QPushButton("編集")
        edit_btn.setStyleSheet("padding: 5px 15px;")
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

        # --- テーブル ---
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "ラベル", "属性 (詳細)", "状態"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._edit)
        
        self.table.setStyleSheet("""
            QTableWidget { background-color: #222; gridline-color: #444; color: white; }
            QHeaderView::section { background-color: #333; color: white; border: 1px solid #444; padding: 4px; }
            QTableWidget::item:selected { background-color: #0d47a1; }
        """)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("※ IDの順序でメイン画面に表示されます"))

    def load_data(self):
        self.customers = self.repo.fetch_all()
        self.table.setRowCount(len(self.customers))
        for i, c in enumerate(self.customers):
            is_active = c.is_active
            
            text_col = "white" if is_active else "#757575"
            bg_col = None if is_active else "#2b2b2b"

            def mk_item(txt):
                it = QTableWidgetItem(str(txt))
                it.setForeground(QColor(text_col))
                if bg_col:
                    it.setBackground(QColor(bg_col))
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                return it

            # ID
            self.table.setItem(i, 0, mk_item(c.id))
            
            # ラベル
            label_item = mk_item(c.label)
            if is_active:
                label_item.setBackground(QColor(c.color))
                label_item.setForeground(QColor("black"))
            self.table.setItem(i, 1, label_item)

            # 属性
            attrs = c.attributes
            if attrs:
                attr_str = ", ".join([f"{k}: {v}" for k, v in attrs.items()])
            else:
                attr_str = "-"
            self.table.setItem(i, 2, mk_item(attr_str))
            
            # 状態
            status = "有効" if is_active else "無効"
            self.table.setItem(i, 3, mk_item(status))

    def _add(self):
        # Dialog用に辞書リストを作成
        presets_as_dicts = []
        for c in self.customers:
            d = asdict(c)
            d['attributes'] = c.attributes
            presets_as_dicts.append(d)

        dlg = CustomerEditDialog(all_presets=presets_as_dicts, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            new_customer = Customer(
                id=None,
                label=d['label'],
                attributes_json="", # set_attributesで設定
                color=d['color'],
                is_active=d['is_active']
            )
            new_customer.set_attributes(d['attributes'])

            if self.repo.add(new_customer):
                self.log_repo.add_log("info", f"客層追加: {d['label']}")
                self.load_data()

    def _edit(self):
        row = self.table.currentRow()
        if row < 0:
            return
        target = self.customers[row]

        # Dialog用に辞書変換
        target_dict = asdict(target)
        target_dict['attributes'] = target.attributes
        
        presets_as_dicts = []
        for c in self.customers:
            pd = asdict(c)
            pd['attributes'] = c.attributes
            presets_as_dicts.append(pd)

        dlg = CustomerEditDialog(data=target_dict, all_presets=presets_as_dicts, parent=self)
        if dlg.exec():
            d = dlg.get_data()
            updated_customer = Customer(
                id=target.id,
                label=d['label'],
                attributes_json="",
                color=d['color'],
                display_order=target.display_order,
                is_active=d['is_active']
            )
            updated_customer.set_attributes(d['attributes'])

            if self.repo.update(updated_customer):
                self.log_repo.add_log("info", f"客層変更: {target.label}")
                self.load_data()

    def _move(self, direction):
        row = self.table.currentRow()
        if row < 0:
            return
        new_row = row + direction
        if new_row < 0 or new_row >= len(self.customers):
            return
        
        a, b = self.customers[row], self.customers[new_row]
        order_map = {a.id: b.display_order, b.id: a.display_order}
        
        if self.repo.update_display_order(order_map):
            self.load_data()
            self.table.selectRow(new_row)