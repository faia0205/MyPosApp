from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QCheckBox, QDialogButtonBox, QPushButton, QColorDialog)
import json

class CustomerEditDialog(QDialog):
    """客層編集ダイアログ"""
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("客層プリセット編集" if data else "新規客層追加")
        self.resize(350, 400)
        self.setStyleSheet("background-color: #333; color: white; QLineEdit, QComboBox { padding: 5px; }")
        self.data = data
        self.selected_color = "#90caf9"
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ラベル
        layout.addWidget(QLabel("表示名 (例: 男1, 家族連れ):"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # 属性 (簡易的な選択式)
        layout.addWidget(QLabel("性別・タイプ:"))
        self.sex_combo = QComboBox()
        self.sex_combo.addItems(["male", "female", "family", "group", "unknown"])
        layout.addWidget(self.sex_combo)
        
        layout.addWidget(QLabel("人数:"))
        self.count_combo = QComboBox()
        self.count_combo.addItems(["1", "2", "3", "many"])
        self.count_combo.setEditable(True) # 数字入力も可能に
        layout.addWidget(self.count_combo)

        # 色
        layout.addWidget(QLabel("ボタン色:"))
        h_lay = QHBoxLayout()
        self.color_preview = QLabel(" SAMPLE ")
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white; padding: 5px;")
        btn_col = QPushButton("色選択")
        btn_col.clicked.connect(self._pick_color)
        h_lay.addWidget(self.color_preview)
        h_lay.addWidget(btn_col)
        layout.addLayout(h_lay)

        # 有効無効
        self.active_chk = QCheckBox("有効")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        # 初期値反映
        if self.data:
            self.name_edit.setText(self.data['label'])
            attrs = self.data.get('attributes', {})
            # 属性の復元 (簡易)
            if 'sex' in attrs: self.sex_combo.setCurrentText(attrs['sex'])
            elif 'type' in attrs: self.sex_combo.setCurrentText(attrs['type'])
            
            if 'count' in attrs: self.count_combo.setCurrentText(str(attrs['count']))
            
            self.selected_color = self.data['color']
            self._update_color()
            self.active_chk.setChecked(bool(self.data.get('is_active', True)))

        # ボタン
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _pick_color(self):
        c = QColorDialog.getColor(self.selected_color, self, "色を選択")
        if c.isValid():
            self.selected_color = c.name()
            self._update_color()

    def _update_color(self):
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white;")

    def get_data(self):
        # 属性JSONの構築
        sex_type = self.sex_combo.currentText()
        cnt_str = self.count_combo.currentText()
        try: cnt = int(cnt_str)
        except: cnt = cnt_str # "many" など

        attrs = {}
        if sex_type in ["family", "group"]:
            attrs["type"] = sex_type
        else:
            attrs["sex"] = sex_type
            attrs["count"] = cnt

        return {
            "label": self.name_edit.text(),
            "attributes": attrs,
            "color": self.selected_color,
            "is_active": self.active_chk.isChecked()
        }