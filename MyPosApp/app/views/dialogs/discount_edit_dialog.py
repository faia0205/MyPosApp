from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QSpinBox, QComboBox, QCheckBox, QDialogButtonBox, QRadioButton, QButtonGroup, QWidget)
from app.utils.style import StyleGenerator
from app.repositories.product_repo import ProductRepository

class DiscountEditDialog(QDialog):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("割引ルール編集" if data else "新規割引ルール作成")
        self.resize(400, 500)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit, QComboBox, QSpinBox {{ 
                padding: 8px; color: black; background-color: white; border-radius: 4px;
            }}
            QLabel {{ font-weight: bold; margin-top: 10px; color: #ccc; }}
            QRadioButton {{ color: white; padding: 5px; }}
            {StyleGenerator.get_checkbox_style()}
            {StyleGenerator.get_spinbox_style()}
        """)
        
        self.data = data
        self.prod_repo = ProductRepository()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 1. ルール名
        layout.addWidget(QLabel("割引名称 (レシートに表示されます):"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例: ランチ値引, 従業員割引")
        layout.addWidget(self.name_edit)

        # 2. 割引種別 (円 or %)
        layout.addWidget(QLabel("割引計算:"))
        type_layout = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        
        self.rb_fixed = QRadioButton("値引 (円)")
        self.rb_fixed.setChecked(True)
        self.type_group.addButton(self.rb_fixed)
        type_layout.addWidget(self.rb_fixed)
        
        self.rb_percent = QRadioButton("割引 (%)")
        self.type_group.addButton(self.rb_percent)
        type_layout.addWidget(self.rb_percent)
        layout.addLayout(type_layout)

        # 値
        layout.addWidget(QLabel("値 (円 または %):"))
        self.value_spin = QSpinBox()
        self.value_spin.setRange(1, 999999)
        self.value_spin.setValue(100)
        layout.addWidget(self.value_spin)

        # 3. 適用対象
        layout.addWidget(QLabel("適用対象:"))
        self.apply_combo = QComboBox()
        self.apply_combo.addItems(["カート全体", "特定カテゴリ", "特定商品"])
        self.apply_combo.currentIndexChanged.connect(self._on_apply_type_changed)
        layout.addWidget(self.apply_combo)

        # 対象詳細
        self.target_label = QLabel("対象を選択:")
        layout.addWidget(self.target_label)
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        layout.addWidget(self.target_combo)

        # 4. オプション
        self.auto_chk = QCheckBox("条件を満たしたら自動適用 (未実装)")
        self.auto_chk.setEnabled(False) # 今回は手動のみのため
        layout.addWidget(self.auto_chk)
        
        self.active_chk = QCheckBox("有効")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        # 初期化処理
        self._load_targets()
        if self.data:
            self._load_data()
        else:
            self._on_apply_type_changed(0) # デフォルト状態

        # ボタン
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_targets(self):
        """商品やカテゴリのリストを読み込む"""
        self.products = self.prod_repo.fetch_active_products()
        self.categories = sorted(list(set(p.category for p in self.products if p.category)))

    def _on_apply_type_changed(self, index):
        """対象タイプによってコンボボックスの中身を変える"""
        self.target_combo.clear()
        self.target_combo.setEnabled(True)
        
        if index == 0: # カート全体
            self.target_label.setText("対象: 全体")
            self.target_combo.setEnabled(False)
        elif index == 1: # カテゴリ
            self.target_label.setText("対象カテゴリ:")
            self.target_combo.addItems(self.categories)
        elif index == 2: # 商品
            self.target_label.setText("対象商品:")
            for p in self.products:
                self.target_combo.addItem(p.name, p.id)

    def _load_data(self):
        """編集時のデータ反映"""
        self.name_edit.setText(self.data['name'])
        
        if self.data['discount_type'] == 'percent':
            self.rb_percent.setChecked(True)
        else:
            self.rb_fixed.setChecked(True)
            
        self.value_spin.setValue(self.data['discount_value'])
        
        atype = self.data['apply_type']
        if atype == 'cart': self.apply_combo.setCurrentIndex(0)
        elif atype == 'category': self.apply_combo.setCurrentIndex(1)
        elif atype == 'item': self.apply_combo.setCurrentIndex(2)
        
        # ターゲットの復元
        self._on_apply_type_changed(self.apply_combo.currentIndex())
        if self.data['target_value']:
            idx = self.target_combo.findText(self.data['target_value'])
            if idx >= 0: self.target_combo.setCurrentIndex(idx)
            else: self.target_combo.setCurrentText(self.data['target_value'])

        self.active_chk.setChecked(bool(self.data['is_active']))

    def get_data(self):
        d_type = 'percent' if self.rb_percent.isChecked() else 'fixed'
        
        # 適用タイプ
        idx = self.apply_combo.currentIndex()
        if idx == 0: a_type = 'cart'
        elif idx == 1: a_type = 'category'
        else: a_type = 'item'
        
        # ターゲット値
        target = ""
        if a_type != 'cart':
            target = self.target_combo.currentText()
            
        return {
            "name": self.name_edit.text(),
            "discount_type": d_type,
            "discount_value": self.value_spin.value(),
            "apply_type": a_type,
            "target_value": target,
            "is_auto": self.auto_chk.isChecked(),
            "is_active": self.active_chk.isChecked()
        }