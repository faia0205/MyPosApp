from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                               QComboBox, QCheckBox, QDialogButtonBox, QPushButton, 
                               QColorDialog, QListWidget, QMessageBox)
from PySide6.QtGui import QColor
from app.utils.style import StyleGenerator

class CustomerEditDialog(QDialog):
    """客層プリセット編集ダイアログ (属性リスト管理対応版)"""
    def __init__(self, data=None, all_presets=None, parent=None):
        """
        all_presets: 既存の全客層データのリスト（候補生成用）
        """
        super().__init__(parent)
        self.setWindowTitle("客層プリセット編集" if data else "新規客層追加")
        self.resize(450, 600) # 少し縦長に
        
        # 共通スタイル適用
        self.setStyleSheet(f"""
            QDialog {{ background-color: #333; color: white; }}
            QLineEdit, QComboBox {{ 
                padding: 8px; color: black; background-color: white; 
                border-radius: 4px; font-size: 14px;
            }}
            QLabel {{ font-weight: bold; margin-top: 5px; color: #ccc; }}
            QListWidget {{
                background-color: #424242; color: white; border: 1px solid #555;
            }}
            QPushButton {{
                padding: 8px; font-weight: bold; border-radius: 4px;
            }}
            {StyleGenerator.get_checkbox_style()}
        """)
        
        self.data = data
        # 候補辞書の作成: { "sex": {"male", "female"}, "count": {"1", "2"} }
        self.candidates = self._build_candidates(all_presets or [])
        
        self.selected_color = "#90caf9"
        
        # 現在編集中の属性データ {key: value}
        self.current_attributes = {}
        if self.data and isinstance(self.data.get('attributes'), dict):
            self.current_attributes = self.data['attributes'].copy()

        self._init_ui()

    def _build_candidates(self, presets):
        """全データから属性の候補を抽出する"""
        candidates = {}
        for p in presets:
            attrs = p.get('attributes', {})
            if not isinstance(attrs, dict):
                continue
            
            for k, v in attrs.items():
                if k not in candidates:
                    candidates[k] = set()
                candidates[k].add(str(v))
        return candidates

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 基本情報
        layout.addWidget(QLabel("ボタン表示名:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # 2. 属性リスト表示エリア
        layout.addWidget(QLabel("設定済み属性一覧:"))
        self.attr_list_widget = QListWidget()
        self.attr_list_widget.setFixedHeight(100)
        self.attr_list_widget.itemClicked.connect(self._on_list_item_clicked)
        layout.addWidget(self.attr_list_widget)

        # 3. 属性編集エリア
        edit_frame = QVBoxLayout()
        edit_frame.setContentsMargins(10, 10, 10, 10)
        
        # タイプ (Key)
        edit_frame.addWidget(QLabel("属性タイプ (例: sex, age):"))
        self.attr_key_combo = QComboBox()
        self.attr_key_combo.setEditable(True)
        self.attr_key_combo.addItems(sorted(list(self.candidates.keys())))
        self.attr_key_combo.setCurrentText("")
        self.attr_key_combo.currentTextChanged.connect(self._on_key_changed)
        edit_frame.addWidget(self.attr_key_combo)
        
        # 値 (Value)
        edit_frame.addWidget(QLabel("値 (例: male, 20s):"))
        self.attr_val_combo = QComboBox()
        self.attr_val_combo.setEditable(True)
        edit_frame.addWidget(self.attr_val_combo)
        
        # 追加・削除ボタン
        btn_lay = QHBoxLayout()
        btn_add = QPushButton("リストに反映 (追加/更新)")
        btn_add.setStyleSheet("background-color: #0277bd; color: white;")
        btn_add.clicked.connect(self._add_attribute_to_list)
        
        btn_del = QPushButton("リストから削除")
        btn_del.setStyleSheet("background-color: #c62828; color: white;")
        btn_del.clicked.connect(self._remove_attribute_from_list)
        
        btn_lay.addWidget(btn_add)
        btn_lay.addWidget(btn_del)
        edit_frame.addLayout(btn_lay)
        
        layout.addLayout(edit_frame)

        # 4. 色設定
        layout.addWidget(QLabel("ボタン色:"))
        h_lay = QHBoxLayout()
        self.color_preview = QLabel(" SAMPLE ")
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white; padding: 10px; font-weight: bold; border-radius: 4px;")
        self.color_preview.setFixedSize(120, 40)
        
        btn_col = QPushButton("色を選択")
        btn_col.setStyleSheet("background-color: #607d8b; color: white;")
        btn_col.clicked.connect(self._pick_color)
        
        h_lay.addWidget(self.color_preview)
        h_lay.addWidget(btn_col)
        h_lay.addStretch()
        layout.addLayout(h_lay)

        # 5. 有効無効
        self.active_chk = QCheckBox("有効にする (メイン画面に表示)")
        self.active_chk.setChecked(True)
        layout.addWidget(self.active_chk)

        # 初期値反映
        if self.data:
            self.name_edit.setText(self.data['label'])
            self.selected_color = self.data['color']
            self._update_color()
            self.active_chk.setChecked(bool(self.data.get('is_active', True)))
        
        # リスト描画
        self._refresh_attr_list()

        # ダイアログボタン
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _refresh_attr_list(self):
        """current_attributesの内容でリストを更新"""
        self.attr_list_widget.clear()
        for k, v in self.current_attributes.items():
            self.attr_list_widget.addItem(f"{k}: {v}")

    def _on_key_changed(self, key):
        """キー変更時に候補を更新"""
        self.attr_val_combo.clear()
        
        if key in self.candidates:
            self.attr_val_combo.addItems(sorted(list(self.candidates[key])))
        self.attr_val_combo.setCurrentText("")

    def _on_list_item_clicked(self, item):
        """リスト選択時に編集エリアに値をセット"""
        text = item.text() # "key: value"
        if ": " in text:
            k, v = text.split(": ", 1)
            self.attr_key_combo.setCurrentText(k)
            self.attr_val_combo.setCurrentText(v)

    def _add_attribute_to_list(self):
        """編集エリアの内容をリスト(辞書)に反映"""
        key = self.attr_key_combo.currentText().strip()
        val = self.attr_val_combo.currentText().strip()
        
        if not key:
            QMessageBox.warning(self, "入力エラー", "属性タイプを入力してください")
            return
        if not val:
            QMessageBox.warning(self, "入力エラー", "値を入力してください (空の場合は保存されません)")
            return
            
        # 数値変換トライ
        try:
            val = int(val)
        except Exception:
            pass
        
        self.current_attributes[key] = val
        self._refresh_attr_list()
        
        # 入力欄クリア（連続入力しやすくするため）
        self.attr_key_combo.setCurrentText("")
        self.attr_val_combo.setCurrentText("")

    def _remove_attribute_from_list(self):
        """選択中の属性を削除"""
        row = self.attr_list_widget.currentRow()
        if row < 0:
            return
        
        item_text = self.attr_list_widget.item(row).text()
        key = item_text.split(": ")[0]
        
        if key in self.current_attributes:
            del self.current_attributes[key]
            self._refresh_attr_list()

    def _pick_color(self):
        c = QColorDialog.getColor(self.selected_color, self, "色を選択")
        if c.isValid():
            self.selected_color = c.name()
            self._update_color()

    def _update_color(self):
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; color: black; border: 1px solid white; padding: 10px; font-weight: bold; border-radius: 4px;")

    def get_data(self):
        return {
            "label": self.name_edit.text(),
            "attributes": self.current_attributes, # 編集済みの辞書を返す
            "color": self.selected_color,
            "is_active": self.active_chk.isChecked()
        }