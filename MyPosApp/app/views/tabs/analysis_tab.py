import datetime
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QDateEdit, QFrame, QGridLayout, QMessageBox, QFileDialog 
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor, QFont

# Enum定義
from app.services.analytics.enums import AnalysisAxis, AnalysisMetric
# Exporter
from app.services.excel_exporter import ExcelReportExporter

class AnalysisTab(QWidget):
    def __init__(self, service):
        super().__init__()
        self.service = service
        
        # Excel出力用クラスの初期化 (生データ取得用にserviceを渡す)
        self.exporter = ExcelReportExporter(self.service)
        
        # 直近の集計結果を保持する変数
        self.last_dataframe = None
        self.last_sheet_name = ""

        self._init_ui()
        
        # 初期期間設定
        start_dt, end_dt = self.service.get_initial_date_range()
        self.date_start.setDate(QDate(start_dt.year, start_dt.month, start_dt.day))
        self.date_end.setDate(QDate(end_dt.year, end_dt.month, end_dt.day))

        # 初期ロード (商品 × 時間)
        self._set_initial_selection()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # --- コントロールエリア ---
        control_frame = QFrame()
        control_frame.setStyleSheet("background-color: #333; border-radius: 8px;")
        
        # グリッドレイアウトで整理
        grid = QGridLayout(control_frame)
        grid.setSpacing(10)
        
        # 1. 期間
        grid.addWidget(QLabel("期間:"), 0, 0)
        date_box = QHBoxLayout()
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        
        date_box.addWidget(self.date_start)
        date_box.addWidget(QLabel("～"))
        date_box.addWidget(self.date_end)
        grid.addLayout(date_box, 0, 1, 1, 3) # 横に結合

        # 2. 縦軸 (Row) - 2段構成
        grid.addWidget(QLabel("縦軸 (行):"), 1, 0)
        
        self.row_cat_combo = QComboBox() # 大分類
        self.row_det_combo = QComboBox() # 小分類
        
        grid.addWidget(self.row_cat_combo, 1, 1)
        grid.addWidget(self.row_det_combo, 1, 2)

        # 3. 横軸 (Col) - 2段構成
        grid.addWidget(QLabel("横軸 (列):"), 2, 0)
        
        self.col_cat_combo = QComboBox() # 大分類
        self.col_det_combo = QComboBox() # 小分類
        
        grid.addWidget(self.col_cat_combo, 2, 1)
        grid.addWidget(self.col_det_combo, 2, 2)

        # 4. 集計値
        grid.addWidget(QLabel("集計値:"), 3, 0)
        self.combo_metric = QComboBox()
        self._populate_metric_combo(self.combo_metric)
        grid.addWidget(self.combo_metric, 3, 1, 1, 2)

        # 5. アクションボタン (実行 & Excel出力)
        btn_layout = QHBoxLayout()
        
        self.btn_run = QPushButton("集計実行")
        self.btn_run.setFixedHeight(40)
        self.btn_run.setStyleSheet("""
            QPushButton { 
                background-color: #00897b; color: white; font-weight: bold; border-radius: 5px; 
            }
            QPushButton:hover { background-color: #009688; }
        """)
        self.btn_run.clicked.connect(self.run_analysis)
        
        self.btn_export = QPushButton("Excel出力")
        self.btn_export.setFixedHeight(40)
        self.btn_export.setStyleSheet("""
            QPushButton { 
                background-color: #00695c; color: white; font-weight: bold; border-radius: 5px; 
            }
            QPushButton:hover { background-color: #00796b; }
            QPushButton:disabled { background-color: #555; color: #aaa; }
        """)
        self.btn_export.clicked.connect(self.export_excel)
        self.btn_export.setEnabled(False) # 初期状態は無効
        
        btn_layout.addWidget(self.btn_run, 2)    # 比率 2
        btn_layout.addWidget(self.btn_export, 1) # 比率 1
        
        grid.addLayout(btn_layout, 4, 0, 1, 3) # 全幅

        layout.addWidget(control_frame)

        # --- 結果エリア ---
        self.lbl_status = QLabel("条件を指定して実行してください")
        self.lbl_status.setStyleSheet("color: #bbb; margin: 5px;")
        layout.addWidget(self.lbl_status)

        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget { background-color: #2b2b2b; gridline-color: #555; color: white; }
            QHeaderView::section { background-color: #444; color: white; border: 1px solid #555; padding: 4px; }
            QTableWidget::item:selected { background-color: #0d47a1; color: white; }
        """)
        layout.addWidget(self.table)

        # --- イベント接続 ---
        self.row_cat_combo.currentIndexChanged.connect(lambda: self._update_detail_combo(self.row_cat_combo, self.row_det_combo))
        self.col_cat_combo.currentIndexChanged.connect(lambda: self._update_detail_combo(self.col_cat_combo, self.col_det_combo))

        # 大分類の初期値をセット
        categories = self.service.get_axis_categories()
        self.row_cat_combo.addItems(categories)
        self.col_cat_combo.addItems(categories)

    def _update_detail_combo(self, cat_combo: QComboBox, det_combo: QComboBox):
        """大分類に合わせて小分類を更新"""
        current_cat = cat_combo.currentText()
        det_combo.clear()
        
        items = self.service.get_axis_details(current_cat)
        
        for label, value in items:
            det_combo.addItem(label, userData=value)

    def _set_initial_selection(self):
        """初期値: 縦=商品(商品名), 横=時間(時間帯)"""
        self.row_cat_combo.setCurrentText("商品")
        self._update_detail_combo(self.row_cat_combo, self.row_det_combo)
        self.row_det_combo.setCurrentText("商品名")
        
        self.col_cat_combo.setCurrentText("時間")
        self._update_detail_combo(self.col_cat_combo, self.col_det_combo)
        self.col_det_combo.setCurrentText("時間帯別")

    def run_analysis(self):
        """集計実行"""
        row_key = self.row_det_combo.currentData()
        col_key = self.col_det_combo.currentData()
        metric_key = self.combo_metric.currentData()
        
        if not row_key or not col_key:
            self.lbl_status.setText("軸が正しく選択されていません")
            return

        s_date = self.date_start.date().toString("yyyy-MM-dd")
        e_date = self.date_end.date().toString("yyyy-MM-dd")

        result = self.service.analyze_dynamic(
            row_axis_key=row_key,
            col_axis_key=col_key,
            metric_key=metric_key,
            start_date=s_date,
            end_date=e_date
        )

        if "error" in result:
            self.lbl_status.setText(f"エラー: {result['error']}")
            return

        df = result.get("df")
        max_val = result.get("max_val", 0)
        min_val = result.get("min_val", 0)

        # 結果を保存 (Excel出力用)
        self.last_dataframe = df
        
        # シート名を生成 (例: "商品名_時間帯別")
        # ファイル名に使えない文字を簡易的に除去
        r_txt = self.row_det_combo.currentText()
        c_txt = self.col_det_combo.currentText()
        safe_r = r_txt.replace(":", "").replace("/", "").replace("\\", "")
        safe_c = c_txt.replace(":", "").replace("/", "").replace("\\", "")
        self.last_sheet_name = f"{safe_r}_{safe_c}"

        # ボタン有効化
        self.btn_export.setEnabled(not df.empty)

        # テーブル描画
        self._render_table(df, max_val, min_val)
        
        mode_text = ""
        if result.get("mode") == "basket":
            mode_text = " (バスケット分析)"
        
        self.lbl_status.setText(f"集計結果: {self.row_cat_combo.currentText()}-{r_txt} × {self.col_cat_combo.currentText()}-{c_txt}{mode_text}")
    
    def export_excel(self):
        """Excel出力処理 (新規・追記・生データ選択機能付き)"""
        if self.last_dataframe is None or self.last_dataframe.empty:
            return

        # 1. 保存先ダイアログ
        # デフォルトファイル名: 売上分析_YYYYMMDD_HHMMSS.xlsx
        default_name = f"売上分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Excelファイルを保存", default_name, "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return

        # 2. 出力モードの確認 (カスタムダイアログ)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("出力オプション")
        
        exists = os.path.exists(file_path)
        
        if exists:
            msg_box.setText("選択されたファイルは既に存在します。\n分析結果シートを追加（または上書き）します。")
            msg_box.setInformativeText("出力内容を選択してください。")
            btn_only = msg_box.addButton("この分析シートのみ追加", QMessageBox.ActionRole)
            btn_full = msg_box.addButton("全データ(伝票一覧等)も含めて更新", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("キャンセル", QMessageBox.RejectRole)
        else:
            msg_box.setText("新しいファイルを作成します。")
            msg_box.setInformativeText("出力内容を選択してください。")
            btn_only = msg_box.addButton("分析シートのみ作成", QMessageBox.ActionRole)
            btn_full = msg_box.addButton("全データ(伝票一覧等)も添付", QMessageBox.ActionRole)
            btn_cancel = msg_box.addButton("キャンセル", QMessageBox.RejectRole)
            
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_cancel:
            return
            
        include_raw = (msg_box.clickedButton() == btn_full)

        # 3. 実行
        ok, msg = self.exporter.export_analysis_result(
            df=self.last_dataframe,
            sheet_name=self.last_sheet_name,
            file_path=file_path,
            include_raw_data=include_raw
        )
        
        if ok:
            QMessageBox.information(self, "完了", f"{msg}\nパス: {file_path}")
        else:
            QMessageBox.critical(self, "エラー", f"出力中にエラーが発生しました:\n{msg}")

    def _populate_metric_combo(self, combo: QComboBox):
        combo.clear()
        items = [
            (AnalysisMetric.SALES, "売上金額 (円)"),
            (AnalysisMetric.QUANTITY, "販売数 (個)"),
            (AnalysisMetric.TX_COUNT, "客数/伝票数 (件)"),
        ]
        for enum_val, label in items:
            combo.addItem(label, userData=enum_val.value)

    def _render_table(self, df, max_val, min_val):
        """DataFrameをQTableWidgetに描画 + ヒートマップ処理"""
        self.table.clear()
        
        if df.empty:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.lbl_status.setText("該当データがありません")
            return

        self.table.setRowCount(len(df.index))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])
        self.table.setVerticalHeaderLabels([str(i) for i in df.index])

        for r in range(len(df.index)):
            for c in range(len(df.columns)):
                val = df.iloc[r, c]
                
                try:
                    text_val = f"{int(val):,}"
                except:
                    text_val = str(val)

                item = QTableWidgetItem(text_val)
                item.setTextAlignment(Qt.AlignCenter)
                
                bg_color = QColor("#2b2b2b")
                text_color = QColor("white")

                if val == 0:
                    text_color = QColor("#666")
                elif max_val > 0:
                    # ヒートマップ処理
                    ratio = (val - min_val) / (max_val - min_val) if max_val > min_val else 0
                    if val == max_val: ratio = 1.0
                    
                    bg_color = self._get_heatmap_color(ratio)
                    text_color = self._get_contrasting_text_color(bg_color)
                
                item.setBackground(bg_color)
                item.setForeground(text_color)
                
                self.table.setItem(r, c, item)
    
    def _get_contrasting_text_color(self, bg_color: QColor) -> QColor:
        brightness = (bg_color.red() * 0.299 + 
                      bg_color.green() * 0.587 + 
                      bg_color.blue() * 0.114)
        return QColor("black") if brightness > 140 else QColor("white")

    def _get_heatmap_color(self, ratio: float) -> QColor:
        if ratio <= 0.05:
            return QColor("#2b2b2b")
            
        r = int(43 + (230 - 43) * ratio)
        g = int(43 + (81 - 43) * ratio)
        b = int(43 + (0 - 43) * ratio)
        
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        
        return QColor(r, g, b)
    
    def update_data(self):
        """AdminWindowからの統一呼び出し用 (動的分析なので何もしない)"""
        pass