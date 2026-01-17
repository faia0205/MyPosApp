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
    def _darken_color(hex_color, factor):
        if not hex_color.startswith('#') or len(hex_color) != 7: return hex_color
        try:
            r, g, b = (int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            r, g, b = (max(0, int(c * (1 - factor))) for c in (r, g, b))
            return f'#{r:02x}{g:02x}{b:02x}'
        except: return hex_color

    @staticmethod
    def _get_text_color(bg_color):
        if not bg_color.startswith('#') or len(bg_color) != 7: return "#000000"
        try:
            r, g, b = (int(bg_color[i:i+2], 16) for i in (1, 3, 5))
            bri = (r * 299 + g * 587 + b * 114) / 1000
            return "#000000" if bri > 128 else "#ffffff"
        except: return "#000000"