class StyleGenerator:
    """スタイル生成クラス"""

    @staticmethod
    def create_button_style(base_color: str) -> str:
        if not base_color: base_color = "#e0e0e0"
        
        text_col = StyleGenerator._get_text_color(base_color)
        hover_bg = StyleGenerator._darken_color(base_color, 0.1)
        pressed_bg = StyleGenerator._darken_color(base_color, 0.2)

        return f"""
            QPushButton {{
                background-color: {base_color};
                color: {text_col};
                border: 1px solid #999;
                border-radius: 6px;
                padding: 5px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover_bg}; border: 2px solid #007acc; }}
            QPushButton:pressed {{ background-color: {pressed_bg}; }}
            QPushButton:checked {{
                background-color: {base_color};
                border: 4px solid #d32f2f;
                color: {text_col};
            }}
            QPushButton:disabled {{
                background-color: #eee; color: #aaa; border: 1px solid #ddd;
            }}
        """

    @staticmethod
    def create_tab_style() -> str:
        return """
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab {
                background: #666; color: #fff; padding: 8px 16px;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #fff; color: #000; font-weight: bold;
                border-bottom: 2px solid #ff5722;
            }
        """

    @staticmethod
    def _darken_color(hex_color: str, factor: float) -> str:
        if not hex_color.startswith('#') or len(hex_color) != 7: return hex_color
        try:
            r, g, b = (int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            r, g, b = (max(0, int(c * (1 - factor))) for c in (r, g, b))
            return f'#{r:02x}{g:02x}{b:02x}'
        except: return hex_color

    @staticmethod
    def _get_text_color(bg_color: str) -> str:
        if not bg_color.startswith('#') or len(bg_color) != 7: return "#000000"
        try:
            r, g, b = (int(bg_color[i:i+2], 16) for i in (1, 3, 5))
            bri = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if bri > 128 else "#ffffff"
        except: return "#000000"
    
    @staticmethod
    def get_checkbox_style() -> str:
        """
        全設定画面共通: トグルボタン風チェックボックス
        ON: 背景緑・文字白 (全体が緑)
        OFF: 背景暗グレー・文字グレー
        ※ paddingとmarginでクリック領域を広げています
        """
        return """
            QCheckBox {
                spacing: 10px;
                font-size: 14px;
                font-weight: bold;
                color: #bdbdbd; /* OFF時の文字色 */
                
                /* ボタンのような見た目にする */
                background-color: #424242;
                padding: 10px;
                border-radius: 6px;
                border: 1px solid #555;
                margin-top: 5px;
                margin-bottom: 5px;
            }
            
            /* ホバー時の反応 */
            QCheckBox:hover {
                background-color: #505050;
                border-color: #888;
            }

            /* インジケータ(四角い枠)のデザイン */
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid #aaa;
                background-color: #333;
            }
            
            /* --- ONの状態 (全体を緑にする) --- */
            QCheckBox:checked {
                color: #ffffff; 
                background-color: #2e7d32; /* 全体背景を濃い緑に */
                border: 1px solid #69f0ae; /* 枠線を明るい緑に */
            }
            
            QCheckBox:checked:hover {
                background-color: #388e3c; /* ホバー時は少し明るく */
            }

            QCheckBox::indicator:checked {
                background-color: #00e676; 
                border-color: #ffffff;
                /* 標準のチェックマーク画像 */
                image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-yes-16.png);
            }
        """

    @staticmethod
    def get_spinbox_style() -> str:
        """
        QSpinBox, QDoubleSpinBox のスタイル
        ※ 矢印アイコンが崩れないよう、ボタン部分の画像指定は行わず、
           背景色と文字色のみを調整します。
        """
        return """
            QSpinBox, QDoubleSpinBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: white;
                color: black;
                font-size: 14px;
                font-weight: bold;
            }
            /* 選択時の色 */
            QSpinBox::selection, QDoubleSpinBox::selection {
                background-color: #0d47a1;
                color: white;
            }
            /* 矢印ボタンの背景色のみ調整 (形はOS/Qt標準に任せる) */
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                background-color: #e0e0e0;
                width: 20px;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #cfcfcf;
            }
        """