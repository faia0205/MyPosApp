# style.py

class StyleGenerator:
    """ウィジェットのスタイルシート(QSS)を生成するクラス"""

    def create_button_style(self, base_color: str) -> str:
        if not base_color: base_color = "#e0e0e0"
        
        hover_bg_color = self._darken_color(base_color, 0.1)
        pressed_bg_color = self._darken_color(base_color, 0.2)
        
        text_color = self._get_text_color(base_color)
        hover_text_color = self._get_text_color(hover_bg_color)

        return f"""
            QPushButton {{
                background-color: {base_color};
                color: {text_color};
                border: 1px solid #888;
                border-radius: 8px;
                padding: 5px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_bg_color};
                color: {hover_text_color};
                border: 2px solid #007acc;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg_color};
                border: 2px solid #0056b3;
            }}
            /* ★修正: 選択状態(:checked)でも元の色をベースにする（枠線で強調） */
            QPushButton:checked {{
                background-color: {base_color}; 
                color: {text_color};
                border: 4px solid #ff5722; /* オレンジ色の太枠で選択を強調 */
            }}
            QPushButton:disabled {{
                background-color: #f0f0f0;
                color: #bdbdbd;
                border: 1px solid #e0e0e0;
            }}
        """

    def create_tab_style(self) -> str:
        """★追加: タブのスタイル定義"""
        return """
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab {
                background: #555; 
                color: #fff; /* 未選択は白文字 */
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px; 
            }
            QTabBar::tab:selected {
                background: #fff; 
                color: #000; /* ★修正: 選択中は白背景に黒文字 */
                border-bottom-color: #fff;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #777;
            }
        """

    # ... (_darken_color, _get_text_color は以前と同じなので省略) ...
    def _darken_color(self, hex_color: str, factor: float) -> str:
        if not hex_color.startswith('#') or len(hex_color) != 7: return hex_color
        try:
            r, g, b = (int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            r, g, b = (max(0, int(c * (1 - factor))) for c in (r, g, b))
            return f'#{r:02x}{g:02x}{b:02x}'
        except: return hex_color

    def _get_text_color(self, background_color: str) -> str:
        if not background_color.startswith('#') or len(background_color) != 7: return "#000000"
        try:
            r, g, b = (int(background_color[i:i+2], 16) for i in (1, 3, 5))
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if brightness > 128 else "#ffffff"
        except: return "#000000"