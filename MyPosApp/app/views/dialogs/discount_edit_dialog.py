from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QSpinBox, QComboBox, QCheckBox, QDialogButtonBox, 
                               QRadioButton, QButtonGroup, QWidget, QListWidget, QPushButton, QMessageBox)
import json
from app.utils.style import StyleGenerator
from app.services.product_service import ProductService
from app.logic.strategies.bundle_strategy import BundleDiscountStrategy

class DiscountEditDialog(QDialog):
    # コンストラクタの引数を ProductService に変更
    def __init__(self, product_service: ProductService, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("割引ルール編集")
        self.resize(500, 600)
        
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit, QComboBox, QSpinBox {{
                padding: 8px; color: black; background-color: white; border-radius: 4px;
            }}
            QLabel {{ font-weight: bold; margin-top: 10px; color: #ccc; }}
            QRadioButton {{ color: white; padding: 5px; }}
            QListWidget {{ background-color: #444; color: white; border: 1px solid #555; }}
            {StyleGenerator.get_checkbox_style()}
            {StyleGenerator.get_spinbox_style()}
        """)

        self.data = data
        self.product_service = product_service  # Serviceを保持

        self.bundle_conditions = []
        self.bundle_targets = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 基本設定
        layout.addWidget(QLabel("割引名称:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例: フード3個で割引")
        layout.addWidget(self.name_edit)

        # 2. 割引タイプ
        h_lay = QHBoxLayout()
        self.type_group = QButtonGroup(self)
        self.rb_fixed = QRadioButton("値引 (円)")
        self.rb_fixed.setChecked(True)
        self.type_group.addButton(self.rb_fixed)
        h_lay.addWidget(self.rb_fixed)
        self.rb_percent = QRadioButton("割引 (%)")
        self.type_group.addButton(self.rb_percent)
        h_lay.addWidget(self.rb_percent)
        
        self.value_spin = QSpinBox()
        self.value_spin.setRange(1, 999999)
        self.value_spin.setValue(100)
        h_lay.addWidget(QLabel("値:"))
        h_lay.addWidget(self.value_spin)
        layout.addLayout(h_lay)

        # 3. 適用対象タイプ
        layout.addWidget(QLabel("適用ロジック:"))
        self.apply_combo = QComboBox()
        self.apply_combo.addItems(["カート全体", "特定カテゴリ", "特定商品", "★ セット・まとめ買い (Bundle)"])
        self.apply_combo.currentIndexChanged.connect(self._on_apply_type_changed)
        layout.addWidget(self.apply_combo)

        # --- A. 通常設定エリア ---
        self.normal_widget = QWidget()
        normal_lay = QVBoxLayout(self.normal_widget)
        normal_lay.setContentsMargins(0,0,0,0)
        self.target_label = QLabel("対象を選択:")
        normal_lay.addWidget(self.target_label)
        self.target_combo = QComboBox()
        self.target_combo.setEditable(True)
        normal_lay.addWidget(self.target_combo)
        layout.addWidget(self.normal_widget)

        # --- B. バンドル設定エリア ---
        self.bundle_widget = QWidget()
        self.bundle_widget.setVisible(False)
        bundle_lay = QVBoxLayout(self.bundle_widget)
        bundle_lay.setContentsMargins(0,0,0,0)
        
        bundle_lay.addWidget(QLabel("セットのパターン:"))
        self.bundle_mode_combo = QComboBox()
        self.bundle_mode_combo.addItems(["選択式 (A,BからN個)", "組み合わせ (Aを1個とBを1個)"])
        self.bundle_mode_combo.currentIndexChanged.connect(self._on_bundle_mode_changed)
        bundle_lay.addWidget(self.bundle_mode_combo)
        
        # B-1. 選択式 (Select)
        self.select_widget = QWidget()
        select_lay = QVBoxLayout(self.select_widget)
        select_lay.setContentsMargins(0,0,0,0)
        select_lay.addWidget(QLabel("対象商品・カテゴリを追加:"))
        
        sl_h = QHBoxLayout()
        self.select_target_combo = QComboBox() # 候補
        sl_h.addWidget(self.select_target_combo)
        btn_add_sel = QPushButton("追加")
        btn_add_sel.clicked.connect(self._add_select_target)
        sl_h.addWidget(btn_add_sel)
        select_lay.addLayout(sl_h)
        
        self.select_list_widget = QListWidget()
        self.select_list_widget.setFixedHeight(80)
        select_lay.addWidget(self.select_list_widget)
        
        select_lay.addWidget(QLabel("必要な合計個数:"))
        self.select_qty_spin = QSpinBox()
        self.select_qty_spin.setRange(2, 999)
        select_lay.addWidget(self.select_qty_spin)
        bundle_lay.addWidget(self.select_widget)

        # B-2. 組み合わせ (Combo)
        self.combo_widget = QWidget()
        self.combo_widget.setVisible(False)
        combo_lay = QVBoxLayout(self.combo_widget)
        combo_lay.setContentsMargins(0,0,0,0)
        combo_lay.addWidget(QLabel("条件を追加 (例: フード 1個):"))
        
        cm_h = QHBoxLayout()
        self.combo_target_combo = QComboBox()
        cm_h.addWidget(self.combo_target_combo)
        self.combo_qty_spin = QSpinBox()
        self.combo_qty_spin.setRange(1, 99)
        cm_h.addWidget(QLabel("個"))
        cm_h.addWidget(self.combo_qty_spin)
        btn_add_cm = QPushButton("追加")
        btn_add_cm.clicked.connect(self._add_combo_condition)
        cm_h.addWidget(btn_add_cm)
        combo_lay.addLayout(cm_h)

        self.combo_list_widget = QListWidget()
        self.combo_list_widget.setFixedHeight(80)
        combo_lay.addWidget(self.combo_list_widget)
        bundle_lay.addWidget(self.combo_widget)

        layout.addWidget(self.bundle_widget)

        # 4. オプション (有効/無効のみ)
        # ★修正: 自動適用のチェックボックスを削除し、常に自動扱いとする
        
        self.active_chk = QCheckBox("有効にする")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        layout.addStretch()

        # データ読み込み
        self._load_master_data()
        if self.data:
            self._load_data()
        else:
            self._on_apply_type_changed(0)

        # ダイアログボタン
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_master_data(self):
        self.products = self.product_service.get_active_products()
        self.categories = sorted(list(set(p.category for p in self.products if p.category)))
        
        candidates = []
        for c in self.categories: candidates.append(f"[カテゴリ] {c}")
        for p in self.products: candidates.append(f"{p.name}")
        
        self.select_target_combo.addItems(candidates)
        self.combo_target_combo.addItems(candidates)

    def _on_apply_type_changed(self, index):
        if index == 3:
            self.normal_widget.setVisible(False)
            self.bundle_widget.setVisible(True)
        else:
            self.normal_widget.setVisible(True)
            self.bundle_widget.setVisible(False)
            
        self.target_combo.clear()
        self.target_combo.setEnabled(True)
        if index == 0:
            self.target_label.setText("対象: 全体")
            self.target_combo.setEnabled(False)
        elif index == 1:
            self.target_label.setText("対象カテゴリ:")
            self.target_combo.addItems(self.categories)
        elif index == 2:
            self.target_label.setText("対象商品:")
            for p in self.products: self.target_combo.addItem(p.name)

    def _on_bundle_mode_changed(self, index):
        if index == 0:
            self.select_widget.setVisible(True)
            self.combo_widget.setVisible(False)
        else:
            self.select_widget.setVisible(False)
            self.combo_widget.setVisible(True)

    def _add_select_target(self):
        txt = self.select_target_combo.currentText()
        if txt not in self.bundle_targets:
            self.bundle_targets.append(txt)
            self.select_list_widget.addItem(txt)

    def _add_combo_condition(self):
        txt = self.combo_target_combo.currentText()
        qty = self.combo_qty_spin.value()
        
        target_type = 'item'
        target_val = txt
        if txt.startswith("[カテゴリ] "):
            target_type = 'category'
            target_val = txt.replace("[カテゴリ] ", "")
            
        cond = {'target': target_val, 'type': target_type, 'qty': qty}
        self.bundle_conditions.append(cond)
        self.combo_list_widget.addItem(f"{txt} x {qty}個")

    def _load_data(self):
        self.name_edit.setText(self.data['name'])
        if self.data['discount_type'] == 'percent': self.rb_percent.setChecked(True)
        else: self.rb_fixed.setChecked(True)
        
        self.value_spin.setValue(self.data['discount_value'])
        self.active_chk.setChecked(bool(self.data['is_active']))
        
        atype = self.data['apply_type']
        target_val = self.data['target_value']
        
        if atype == 'bundle':
            self.apply_combo.setCurrentIndex(3)
            try:
                b_data = json.loads(target_val)
                mode = b_data.get('mode', 'select')
                if mode == 'select':
                    self.bundle_mode_combo.setCurrentIndex(0)
                    self.select_qty_spin.setValue(b_data.get('qty', 2))
                    for t in b_data.get('targets', []):
                        # 表示用にプレフィックス復元を試みる簡易ロジック
                        disp = t
                        if t in self.categories: disp = f"[カテゴリ] {t}"
                        self.bundle_targets.append(disp)
                        self.select_list_widget.addItem(disp)
                else:
                    self.bundle_mode_combo.setCurrentIndex(1)
                    for c in b_data.get('conditions', []):
                        self.bundle_conditions.append(c)
                        prefix = "[カテゴリ] " if c['type'] == 'category' else ""
                        self.combo_list_widget.addItem(f"{prefix}{c['target']} x {c['qty']}個")
            except:
                pass
        else:
            idx = 0
            if atype == 'category': idx = 1
            elif atype == 'item': idx = 2
            self.apply_combo.setCurrentIndex(idx)
            self._on_apply_type_changed(idx)
            self.target_combo.setCurrentText(target_val or "")

    def get_data(self):
        d_type = 'percent' if self.rb_percent.isChecked() else 'fixed'
        idx = self.apply_combo.currentIndex()
        
        a_type = 'cart'
        target_value = ""

        if idx == 0:
            a_type = 'cart'
        elif idx == 1:
            a_type = 'category'
            target_value = self.target_combo.currentText()
        elif idx == 2:
            a_type = 'item'
            target_value = self.target_combo.currentText()
        elif idx == 3:
            a_type = 'bundle'
            mode_idx = self.bundle_mode_combo.currentIndex()
            
            # ★ BundleDiscountStrategy の静的メソッドを使用してJSONを生成 (SRP対応)
            if mode_idx == 0:
                target_value = BundleDiscountStrategy.create_target_json(
                    mode='select',
                    targets=self.bundle_targets, # UI上の生の文字列を渡す
                    qty=self.select_qty_spin.value()
                )
            else:
                target_value = BundleDiscountStrategy.create_target_json(
                    mode='combo',
                    conditions=self.bundle_conditions
                )

        return {
            "name": self.name_edit.text(),
            "discount_type": d_type,
            "discount_value": self.value_spin.value(),
            "apply_type": a_type,
            "target_value": target_value,
            "is_auto": True,
            "is_active": self.active_chk.isChecked()
        }