import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QButtonGroup, 
                               QPushButton)
from PySide6.QtCore import Qt
from app.services.cart_service import CartService
from app.repositories.customer_repo import CustomerRepository
from app.models.customer import Customer
from app.views.components.custom_buttons import CustomerButton

class CustomerPanel(QWidget):
    """客層選択パネル"""
    def __init__(self, cart_service: CartService, parent=None):
        super().__init__(parent)
        self.cart_service = cart_service
        self.repo = CustomerRepository()
        self._init_ui()
        
        self.cart_service.checkout_completed.connect(self._reset_selection)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.cust_group = QButtonGroup(self)
        self.customer_grid = QGridLayout()
        layout.addLayout(self.customer_grid)
        
        self.refresh_data()

    def refresh_data(self):
        # グリッドのクリア
        while self.customer_grid.count():
            item = self.customer_grid.takeAt(0)
            w = item.widget()
            if w: 
                self.cust_group.removeButton(w)
                w.deleteLater()
        
        # Repoからオブジェクトリストを取得
        all_customers = self.repo.fetch_all() 
        current_selection_valid = False

        for i, c_model in enumerate(all_customers):
            # c_model は既に Customer オブジェクト
            
            btn = CustomerButton(c_model)
            self.cust_group.addButton(btn)
            self.customer_grid.addWidget(btn, i//2, i%2)
            
            if not c_model.is_active:
                btn.setEnabled(False)
                btn.setStyleSheet("background-color: #424242; color: #757575; border: 1px solid #616161; border-radius: 8px; font-weight: bold;")
                btn.setText(f"{c_model.label}\n(無効)")
            else:
                btn.clicked.connect(lambda _, x=c_model: self._on_customer_selected(x))
                
                # 選択状態の復元
                if self.cart_service.selected_customer and self.cart_service.selected_customer.id == c_model.id:
                    btn.setChecked(True)
                    current_selection_valid = True

        # 無効になっていたら選択解除
        if self.cart_service.selected_customer and not current_selection_valid:
            self.cart_service.set_customer(None)
            self._reset_selection()

    def _on_customer_selected(self, customer: Customer):
        self.cart_service.set_customer(customer)

    def _reset_selection(self, *args):
        self.cust_group.setExclusive(False)
        for btn in self.cust_group.buttons():
            btn.setChecked(False)
        self.cust_group.setExclusive(True)