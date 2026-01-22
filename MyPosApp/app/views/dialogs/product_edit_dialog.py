from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QSpinBox, QCheckBox, QComboBox, 
                               QDialogButtonBox, QPushButton, QColorDialog)
from PySide6.QtCore import Qt
from app.models.product import Product
from app.utils.style import StyleGenerator

class ProductEditDialog(QDialog):
    """商品の追加・編集用ダイアログ"""
    def __init__(self, product: Product = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("商品編集" if product else "新規商品追加")
        self.resize(400, 500)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit, QSpinBox, QComboBox {{ 
                padding: 8px; color: black; background-color: white; 
                border-radius: 4px;
            }}
            QLabel {{ font-weight: bold; margin-top: 5px; }}
            {StyleGenerator.get_checkbox_style()} /* 共通チェックボックス */
        """)

        self.product = product
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 名前
        layout.addWidget(QLabel("商品名:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # 価格
        layout.addWidget(QLabel("価格 (¥):"))
        self.price_spin = QSpinBox()
        self.price_spin.setRange(-9999, 99999) # 割引(-50円)なども許容
        self.price_spin.setSingleStep(10)
        layout.addWidget(self.price_spin)

        # カテゴリ (手入力 + 履歴的な候補があればいいが、一旦固定リスト+編集可で)
        layout.addWidget(QLabel("カテゴリ:"))
        self.cat_combo = QComboBox()
        self.cat_combo.setEditable(True)
        self.cat_combo.addItems(["フード", "ドリンク", "その他", "割引"])
        layout.addWidget(self.cat_combo)

        # 色選択
        layout.addWidget(QLabel("表示色:"))
        self.color_layout = QHBoxLayout()
        self.color_preview = QLabel("　SAMPLE　")
        self.color_preview.setStyleSheet("border: 1px solid white; padding: 5px;")
        self.color_btn = QPushButton("色を選択")
        self.color_btn.clicked.connect(self._pick_color)
        self.selected_color = "#ffcc80" # Default
        
        self.color_layout.addWidget(self.color_preview)
        self.color_layout.addWidget(self.color_btn)
        layout.addLayout(self.color_layout)

        # メモ
        layout.addWidget(QLabel("メモ (オプション):"))
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText("例: 大盛り対応可")
        layout.addWidget(self.note_edit)

        # 有効/無効
        self.active_chk = QCheckBox("販売中 (有効)")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        # --- 初期値セット ---
        if self.product:
            self.name_edit.setText(self.product.name)
            self.price_spin.setValue(self.product.price)
            self.cat_combo.setCurrentText(self.product.category)
            self.selected_color = self.product.color
            self.note_edit.setText(self.product.note)
            self.active_chk.setChecked(self.product.is_active)
        
        self._update_color_preview()

        # ボタン
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _pick_color(self):
        c = QColorDialog.getColor(self.selected_color, self, "色を選択")
        if c.isValid():
            self.selected_color = c.name()
            self._update_color_preview()

    def _update_color_preview(self):
        # 背景色によって文字色を見やすくする簡易ロジック
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white; padding: 5px;")

    def get_data(self):
        """入力データを返す"""
        return {
            "name": self.name_edit.text().strip(),
            "price": self.price_spin.value(),
            "category": self.cat_combo.currentText().strip(),
            "color": self.selected_color,
            "note": self.note_edit.text().strip(),
            "is_active": self.active_chk.isChecked()
        }
    
    def set_category_list(self, categories: list):
        """カテゴリのコンボボックスに候補を設定"""
        current = self.cat_combo.currentText()
        self.cat_combo.clear()
        self.cat_combo.addItems(categories)
        
        # もしリストになければ（新規入力など）、追加しておく
        if current and current not in categories:
            self.cat_combo.addItem(current)
            
        self.cat_combo.setCurrentText(current)