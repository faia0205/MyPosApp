from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QCheckBox, QDialogButtonBox, QPushButton, QColorDialog)
from PySide6.QtGui import QColor
from app.utils.style import StyleGenerator

class CustomerEditDialog(QDialog):
    """客層プリセット編集ダイアログ"""
    def __init__(self, data=None, all_presets=None, parent=None):
        """
        all_presets: 既存の全客層データのリスト（候補生成用）
        """
        super().__init__(parent)
        self.setWindowTitle("客層プリセット編集" if data else "新規客層追加")
        self.resize(400, 500)
        
        # 共通スタイル適用
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit, QComboBox {{ 
                padding: 8px; color: black; background-color: white; 
                border-radius: 4px; font-size: 14px;
            }}
            QLabel {{ font-weight: bold; margin-top: 10px; color: #ccc; }}
            {StyleGenerator.get_checkbox_style()}
        """)
        
        self.data = data
        # 候補辞書の作成: { "sex": {"male", "female"}, "count": {"1", "2"} }
        self.candidates = self._build_candidates(all_presets or [])
        
        self.selected_color = "#90caf9"
        self._init_ui()

    def _build_candidates(self, presets):
        """全データから属性の候補を抽出する"""
        candidates = {}
        for p in presets:
            attrs = p.get('attributes', {})
            if not isinstance(attrs, dict): continue
            
            for k, v in attrs.items():
                if k not in candidates: candidates[k] = set()
                candidates[k].add(str(v))
        return candidates

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # ラベル
        layout.addWidget(QLabel("ボタン表示名 (例: 男1, 家族):"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # --- 属性設定エリア ---
        layout.addWidget(QLabel("属性の設定:"))
        
        # 属性タイプ (Key)
        layout.addWidget(QLabel("タイプ (例: sex, age):"))
        self.attr_key_combo = QComboBox()
        self.attr_key_combo.setEditable(True)
        # 候補にあるキーを追加
        keys = sorted(list(self.candidates.keys()))
        self.attr_key_combo.addItems(keys)
        self.attr_key_combo.setCurrentText("") # 初期は空
        # キーが変わったら値を更新
        self.attr_key_combo.currentTextChanged.connect(self._on_key_changed)
        layout.addWidget(self.attr_key_combo)
        
        # 属性値 (Value)
        layout.addWidget(QLabel("値 (例: male, 20s):"))
        self.attr_val_combo = QComboBox()
        self.attr_val_combo.setEditable(True)
        layout.addWidget(self.attr_val_combo)
        
        layout.addWidget(QLabel("※ 値を空欄にすると属性は保存されません。"))

        # 色
        layout.addWidget(QLabel("ボタン色:"))
        h_lay = QHBoxLayout()
        self.color_preview = QLabel(" SAMPLE ")
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white; padding: 10px; font-weight: bold; border-radius: 4px;")
        self.color_preview.setFixedSize(120, 40)
        
        btn_col = QPushButton("色を選択")
        btn_col.setStyleSheet("background-color: #607d8b; color: white; padding: 10px; border-radius: 4px; font-weight: bold;")
        btn_col.clicked.connect(self._pick_color)
        
        h_lay.addWidget(self.color_preview)
        h_lay.addWidget(btn_col)
        h_lay.addStretch()
        layout.addLayout(h_lay)

        # 有効無効 (共通スタイル適用済み)
        self.active_chk = QCheckBox("有効 (メイン画面に表示)")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        # 初期値反映
        if self.data:
            self.name_edit.setText(self.data['label'])
            attrs = self.data.get('attributes', {})
            
            # 属性の復元 (最初の1つを表示)
            if attrs:
                key = list(attrs.keys())[0]
                val = str(attrs[key])
                self.attr_key_combo.setCurrentText(key)
                # キーセット後に手動で値をセット
                self.attr_val_combo.setCurrentText(val)
            
            self.selected_color = self.data['color']
            self._update_color()
            self.active_chk.setChecked(bool(self.data.get('is_active', True)))

        # ボタン
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_key_changed(self, key):
        """キーが変更されたら、値の候補を更新する"""
        current_val = self.attr_val_combo.currentText()
        self.attr_val_combo.clear()
        
        if key in self.candidates:
            # 候補があれば追加
            vals = sorted(list(self.candidates[key]))
            self.attr_val_combo.addItems(vals)
        
        # もし以前の値が候補になくても、手入力中かもしれないので維持を試みる
        # (ただし候補切り替えの邪魔にならない範囲で)
        # 今回はシンプルに「候補にあればセット、なければ空」にするが、
        # ユーザビリティ的には「キーを変えたら値はクリア」が自然
        self.attr_val_combo.setCurrentText("")

    def _pick_color(self):
        c = QColorDialog.getColor(self.selected_color, self, "色を選択")
        if c.isValid():
            self.selected_color = c.name()
            self._update_color()

    def _update_color(self):
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white; padding: 10px; font-weight: bold; border-radius: 4px;")

    def get_data(self):
        key = self.attr_key_combo.currentText().strip()
        val_str = self.attr_val_combo.currentText().strip()
        
        # 数字なら数値に変換
        try: val = int(val_str)
        except: val = val_str

        # ★修正: 値が空なら保存しない
        attrs = {}
        if key and val_str: # val_strが空文字でないこと
            attrs[key] = val

        return {
            "label": self.name_edit.text(),
            "attributes": attrs,
            "color": self.selected_color,
            "is_active": self.active_chk.isChecked()
        }