class StyleGenerator:
    """ウィジェットのスタイルシート(QSS)を生成するクラス"""

    def create_button_style(self, base_color: str) -> str:
        if not base_color: base_color = "#e0e0e0"
        
        # 色の計算
        hover_bg = self._darken_color(base_color, 0.1)
        pressed_bg = self._darken_color(base_color, 0.2)
        text_col = self._get_text_color(base_color)

        # ★修正ポイント: 
        # checked状態でも background-color を強制的に指定し、枠線を目立たせる
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
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 2px solid #007acc;
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
            }}
            QPushButton:checked {{
                background-color: {base_color}; /* 色を維持 */
                border: 4px solid #d32f2f;      /* 赤系の太枠で選択を強調 */
                color: {text_col};
            }}
            QPushButton:disabled {{
                background-color: #eee;
                color: #aaa;
                border: 1px solid #ddd;
            }}
        """

    def create_tab_style(self) -> str:
        return """
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab {
                background: #666; color: #fff; padding: 8px 16px;
                border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #fff; color: #000; font-weight: bold;
                border-bottom: 2px solid #ff5722; /* 選択中のタブの下線 */
            }
        """

    def _darken_color(self, hex_color, factor):
        if not hex_color.startswith('#') or len(hex_color) != 7: return hex_color
        try:
            r, g, b = (int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            r, g, b = (max(0, int(c * (1 - factor))) for c in (r, g, b))
            return f'#{r:02x}{g:02x}{b:02x}'
        except: return hex_color

    def _get_text_color(self, bg_color):
        if not bg_color.startswith('#') or len(bg_color) != 7: return "#000000"
        try:
            r, g, b = (int(bg_color[i:i+2], 16) for i in (1, 3, 5))
            bri = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if bri > 128 else "#ffffff"
        except: return "#000000"