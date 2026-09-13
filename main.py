"""Shared SGMO2 screen and local demo. Default entry point uses GatewayWindow."""
import math
import sys
import time
from collections import deque
from pathlib import Path

if __name__ == '__main__':
    from runtime import ensure_project_python
    ensure_project_python()

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QScrollArea, QSplitter, QComboBox, QPlainTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QDialog, QGridLayout, QSizePolicy,
)
from workflow import Workflow, STEPS
from step_report import duration

ROOT = Path(__file__).resolve().parent


def button(text, callback, kind=""):
    item = QPushButton(text)
    if kind:
        item.setObjectName(kind)
    item.clicked.connect(callback)
    return item


def group(title):
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.setSpacing(8)
    return box, layout


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = Workflow()
        self.setting_path = None
        self.setting_text = ""
        self.high = False
        self.started = time.monotonic()
        self.history = deque(maxlen=120)
        self.rng = np.random.default_rng(7)
        self.setWindowTitle("JIN SAMURAI Control 0.2")
        self.resize(1360, 900)
        self.setMinimumSize(1000, 720)

        base = QWidget()
        self.setCentralWidget(base)
        root = QVBoxLayout(base)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(ROOT / "assets/jin_mark_white.png")).scaled(
            42, 42, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation))
        header.addWidget(logo)
        title = QLabel("JIN SAMURAI Control 0.2")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        demo = self.connection_badge = QLabel("DEMO  •  装置への接続なし")
        demo.setObjectName("badge")
        header.addWidget(demo)
        header.addWidget(button("終了", self.close))
        root.addLayout(header)
        self.alarm_status = QLabel('正常')
        self.alarm_status.setStyleSheet('background: #123D32; color: #6EF0B1; font-size: 18px; font-weight: bold; padding: 10px;')
        self.alarm_status.setWordWrap(True)
        root.addWidget(self.alarm_status)

        banner = self.banner = QLabel("画面レビュー用デモ  /  ボタン操作・工程・波形はシミュレーションです。測定データは保存されません。")
        banner.setWordWrap(True)
        banner.setObjectName("banner")
        root.addWidget(banner)

        split = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(split, 1)
        left = QWidget()
        panel = QVBoxLayout(left)
        panel.setContentsMargins(0, 0, 10, 0)
        panel.setSpacing(12)

        box, layout = group("01  SETTINGS  /  設定")
        self.file_label = QLabel("デモ用設定を使用")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)
        file_row = QHBoxLayout()
        self.select_button = button("設定ファイルを選択", self.select_settings)
        self.preview_button = button("内容確認", self.preview_settings)
        self.report_history_button = button('履歴・統計', self.show_report_history)
        self.analysis_export_button = button('工程別データ出力', self.export_analysis_data)
        self.create_settings_button = button("新しい設定を作成", self.create_settings)
        file_row.addWidget(self.select_button)
        file_row.addWidget(self.preview_button)
        file_row.addWidget(self.report_history_button)
        file_row.addWidget(self.analysis_export_button)
        file_row.addWidget(self.create_settings_button)
        layout.addLayout(file_row)
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("High サンプルレート"))
        self.rate = QComboBox()
        self.rate.addItems(["10 kHz", "50 kHz", "100 kHz"])
        self.rate.currentIndexChanged.connect(self.rate_changed)
        mode_row.addWidget(self.rate)
        layout.addLayout(mode_row)
        self.apply_button = button("設定を適用（デモ）", self.apply_settings, "primary")
        layout.addWidget(self.apply_button)
        panel.addWidget(box)

        box, layout = group("02  SETUP  /  ナノギャップ生成・測定準備")
        actions = QHBoxLayout()
        self.batch_button = button("準備をまとめて実行", self.run_batch, "primary")
        self.reset_button = button("リセット", self.reset)
        actions.addWidget(self.batch_button)
        actions.addWidget(self.reset_button)
        layout.addLayout(actions)
        self.progress = QProgressBar()
        self.progress.setRange(0, len(STEPS))
        self.progress.setFormat("%v / %m 工程完了")
        layout.addWidget(self.progress)
        self.rows = []
        self.report_buttons = []
        self.elapsed_labels = []
        for index, (name, description) in enumerate(STEPS):
            row = QHBoxLayout()
            label = QLabel(f"{index+1:02d}  {name}")
            label.setToolTip(description)
            action = button("実行", lambda checked=False, i=index: self.run_step(i))
            action.setFixedWidth(72)
            action.setStyleSheet("padding: 2px 6px; min-height: 18px;")
            row.addWidget(label, 1)
            row.addWidget(action)
            elapsed = QLabel('')
            elapsed.setMinimumWidth(58)
            report = button('レポート', lambda checked=False, i=index: self.show_step_report(i))
            report.setStyleSheet('padding: 2px 6px; min-height: 18px;')
            row.addWidget(elapsed)
            row.addWidget(report)
            self.elapsed_labels.append(elapsed)
            self.report_buttons.append(report)
            layout.addLayout(row)
            self.rows.append((label, action))
        self.chip_note = QLabel("チップを装着したら、下のボタンで続行してください。")
        self.chip_note.setWordWrap(True)
        self.chip_button = button("チップ装着を確認・続行", self.confirm_chip, "primary")
        panel.addWidget(box)

        box, layout = group("03  MEASUREMENT  /  測定")
        self.phase = QLabel("設定を適用して準備を開始してください")
        self.phase.setWordWrap(True)
        layout.addWidget(self.phase)
        layout.addWidget(self.chip_note)
        layout.addWidget(self.chip_button)
        row = QHBoxLayout()
        self.measure_button = button("Hold Gap 開始", self.measure, "primary")
        self.measure_stop = button("測定停止", self.stop)
        row.addWidget(self.measure_button)
        row.addWidget(self.measure_stop)
        layout.addLayout(row)
        self.stop_button = button("工程・測定を停止（デモ）", self.stop, "danger")
        layout.addWidget(self.stop_button)
        self.measurement_box = box

        self.manual_dialog = QDialog(self)
        self.manual_dialog.setWindowTitle('MANUAL / 個別操作')
        self.manual_dialog.resize(520, 200)
        layout = QVBoxLayout(self.manual_dialog)
        note = QLabel("準備工程は上の実行ボタンから個別に進められます。")
        note.setWordWrap(True)
        layout.addWidget(note)
        grid = QGridLayout()
        self.manual_buttons = []
        for index, name in enumerate(["Volt 0", "Go0 Point", "Volt 0.1",
                                      "Low 10K", "High 測定", "測定データ停止"]):
            item = button(name, lambda checked=False, n=name: self.manual(n))
            self.manual_buttons.append(item)
            grid.addWidget(item, index // 3, index % 3)
        layout.addLayout(grid)
        layout.addWidget(button('閉じる', self.manual_dialog.close))
        panel.addWidget(button('MANUAL / 個別操作を開く', self.show_manual_dialog))
        panel.addStretch()
        scroll = QScrollArea()
        self.setup_scroll = scroll
        self.last_visible_step = None
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(left)
        scroll.setMinimumWidth(370)
        left_shell = QWidget()
        left_layout = QVBoxLayout(left_shell)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.left_sections = QSplitter(Qt.Orientation.Vertical)
        self.left_sections.setChildrenCollapsible(False)
        scroll.setMinimumHeight(280)
        self.left_sections.addWidget(scroll)
        measurement_scroll = QScrollArea()
        self.measurement_scroll = measurement_scroll
        measurement_scroll.setWidgetResizable(True)
        measurement_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        measurement_scroll.setWidget(self.measurement_box)
        measurement_scroll.setMinimumHeight(220)
        self.left_sections.addWidget(measurement_scroll)
        self.left_sections.setSizes([430, 350])
        self.left_sections.setStretchFactor(0, 3)
        self.left_sections.setStretchFactor(1, 2)
        left_layout.addWidget(self.left_sections)
        split.addWidget(left_shell)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.right_layout = right_layout
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(6)
        meters = QHBoxLayout()
        self.meters = {}
        for key in ("CURRENT", "MOTOR", "PIEZO"):
            card, layout = group(key)
            value = QLabel("--")
            value.setObjectName("meter")
            layout.addWidget(value)
            self.meters[key] = value
            meters.addWidget(card)
        right_layout.addLayout(meters)
        distance_card, distance_layout = group('GAP DISTANCE / 指定距離（参考目標）')
        self.distance_meter = QLabel('-- nm')
        self.distance_meter.setObjectName('meter')
        distance_layout.addWidget(self.distance_meter)
        meters.addWidget(distance_card)

        box, layout = group("CURRENT DATA  /  電流波形")
        plot_actions = QHBoxLayout()
        plot_actions.addWidget(button('スケールを戻す', self.reset_plot_scales))
        plot_actions.addWidget(button('表示履歴をクリア', self.clear_display_history))
        plot_actions.addStretch()
        layout.addLayout(plot_actions)
        self.stats = QLabel("デモ波形")
        self.stats.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.stats)
        self.current_plot = self.make_plot("Current", "µA")
        self.current_plot.setMinimumHeight(180)
        self.current_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.current_plot.setMaximumHeight(450)
        self.current_plot.addLegend(offset=(8, 8))
        self.current_curve = self.current_plot.plot(pen=pg.mkPen("#24C8DB", width=1), name="Data")
        self.median_curve = self.current_plot.plot(pen=pg.mkPen("#F5D547", width=1.5), name="Median")
        layout.addWidget(self.current_plot, 1)
        right_layout.addWidget(box, 2)

        box, layout = group("HARDWARE DATA  /  位置トレンド")
        self.hardware_box = box
        box.setMaximumHeight(290)
        graphs = QHBoxLayout()
        self.hardware_graphs = graphs
        self.motor_plot = self.make_plot("Motor", "µm")
        self.piezo_plot = self.make_plot("Piezo", "nm")
        self.motor_curve = self.motor_plot.plot(pen=pg.mkPen("#39D98A", width=1.5))
        self.piezo_curve = self.piezo_plot.plot(pen=pg.mkPen("#B294FF", width=1.5))
        for plot in (self.motor_plot, self.piezo_plot):
            plot.setMinimumHeight(100)
            plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
            graphs.addWidget(plot)
        layout.addLayout(graphs)
        right_layout.addWidget(box, 1)

        box, layout = group("CONSOLE  /  操作履歴")
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumBlockCount(500)
        self.console.setMinimumHeight(45)
        self.console.setMaximumHeight(85)
        self.console.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addWidget(self.console)
        right_layout.addWidget(box, 1)
        right.setMinimumHeight(0)
        right_scroll = QScrollArea()
        self.right_scroll = right_scroll
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right)
        right_scroll.setMinimumWidth(550)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        split.addWidget(right_scroll)
        split.setSizes([435, 865])

        footer = self.footer = QLabel("SGMO2 / 0.2.0    •    デモ表示    •    保存：なし")
        footer.setObjectName("muted")
        root.addWidget(footer)
        self.step_timer = QTimer(self)
        self.step_timer.setSingleShot(True)
        self.step_timer.timeout.connect(self.finish_step)
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(100)
        self.refresh()
        self.update_plots()
        self.log("デモを開始しました。設定を適用すると準備を実行できます。")

    def make_plot(self, name, unit):
        plot = pg.PlotWidget(background="#0E1620")
        plot.showGrid(x=True, y=True, alpha=0.15)
        plot.setLabel("left", name, units=unit)
        plot.setLabel("bottom", "Time", units="s")
        plot.setMenuEnabled(False)
        for axis in ("left", "bottom"):
            plot.getAxis(axis).setTextPen("#8291A5")
            plot.getAxis(axis).setPen("#30445A")
        return plot

    def log(self, text):
        self.console.appendPlainText(f"{time.strftime('%H:%M:%S')}  [DEMO] {text}")

    def refresh(self):
        s = self.state
        if s.active != self.last_visible_step:
            self.last_visible_step = s.active
            if s.active is not None:
                label = self.rows[s.active][0]
                QTimer.singleShot(0, lambda: self.setup_scroll.ensureWidgetVisible(label, 0, 60))
        busy = s.active is not None or s.measurement
        self.progress.setValue(s.completed)
        self.select_button.setEnabled(not busy)
        self.create_settings_button.setEnabled(not busy)
        self.apply_button.setEnabled(not busy)
        self.rate.setEnabled(not busy)
        self.batch_button.setEnabled(s.configured and not busy and not s.ready)
        self.reset_button.setEnabled(s.configured and not busy)
        self.measure_button.setEnabled(s.ready and not busy)
        self.measure_stop.setEnabled(s.measurement)
        self.stop_button.setEnabled(busy)
        for index, (label, action) in enumerate(self.rows):
            report = s.reports.get(index)
            self.elapsed_labels[index].setText(duration(report.elapsed) if report and report.elapsed is not None else '')
            self.report_buttons[index].setEnabled(bool(report and report.elapsed is not None))
            self.report_buttons[index].setToolTip('各工程の最新の実行記録（リセット後も保持、再実行で更新）')
            done = index < s.completed
            active = index == s.active
            label.setText(f"{'✓' if done else f'{index+1:02d}'}  {STEPS[index][0]}")
            label.setStyleSheet(
                "background-color: #FFFFFF; color: #0B1017; font-weight: 700;"
                " padding: 2px 6px; border-radius: 4px;"
                if active else
                f"background-color: #0B1017; color: {'#39D98A' if done else '#AFC0D2'};"
                " font-weight: 400; padding: 2px 6px; border-radius: 4px;"
            )
            action.setStyleSheet(
                "QPushButton { padding: 2px 6px; min-height: 18px; }"
                + ("QPushButton, QPushButton:disabled { background-color: #FFFFFF;"
                   " color: #0B1017; border-color: #FFFFFF; font-weight: 700; }"
                   if active else "")
            )
            action.setText("進行中" if active else "完了" if done else "実行")
            action.setEnabled(s.configured and not busy and index == s.completed)
        self.chip_note.setVisible(s.active == 2)
        self.chip_button.setVisible(s.active == 2)
        for item in self.manual_buttons:
            item.setEnabled(s.configured and not busy)
        if s.measurement:
            text = "HOLD GAP  /  測定中（デモ）"
        elif s.active is not None:
            text = f"{STEPS[s.active][0]}  /  " + ("装着確認待ち" if s.active == 2 else "実行中（デモ）")
        elif s.ready:
            text = "準備完了  /  Hold Gapを開始できます"
        elif s.configured:
            text = f"次の工程：{STEPS[s.completed][0]}"
        else:
            text = "設定を適用して準備を開始してください"
        self.phase.setText(text)

    def select_settings(self):
        base = ROOT.parent / "SGMO2_original/JinSettings-0.2.0.09030"
        path, _ = QFileDialog.getOpenFileName(self, "設定ファイル", str(base), "Settings (*.txt)")
        if not path:
            return
        try:
            data = Path(path).read_bytes()
            try:
                content = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                content = data.decode("cp932")
            commands = [line.strip() for line in content.splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
            if not commands:
                raise ValueError("設定コマンドがありません。")
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, "ファイルを読み込めません", str(error))
            return
        self.reset()
        self.state.configured = False
        self.setting_path, self.setting_text = Path(path), content
        self.file_label.setText(f"{Path(path).name}  /  {len(commands)}行（未適用）")
        self.refresh()

    def preview_settings(self):
        from settings_preview import SettingsPreview
        dialog = SettingsPreview(self.setting_text,
                                 self.setting_path.name if self.setting_path else '', self)
        dialog.exec()

    def show_step_report(self, index):
        report = self.state.reports.get(index)
        if report is None:
            return
        from report_view import ReportDialog
        ReportDialog(index, report, self).exec()

    def show_report_history(self):
        from report_view import HistoryDialog
        if getattr(self, 'report_save_errors', None):
            QMessageBox.warning(self, 'レポート保存失敗', '\n'.join(self.report_save_errors.values()) + '\n保存を再試行します。')
            self.report_save_errors.clear()
            self.refresh()
        HistoryDialog(self).exec()

    def export_analysis_data(self):
        from PySide6.QtCore import QProcess
        from datetime import datetime
        source = QFileDialog.getExistingDirectory(self, '記録終了済みのGateway log_日時フォルダを選択', str(ROOT.parent))
        if not source:
            return
        if not (Path(source) / 'log_port_rx.log').is_file():
            QMessageBox.warning(self, '保存フォルダ', 'log_port_rx.logがあるフォルダを選択してください。')
            return
        output = ROOT / 'analysis' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        self.analysis_process = QProcess(self)
        self.analysis_process.setProgram(sys.executable)
        self.analysis_process.setArguments([str(ROOT / 'export_analysis.py'), source, str(output)])
        self.analysis_export_button.setEnabled(False)
        self.analysis_export_button.setText('工程別データ出力中…')
        def finished(code, status):
            self.analysis_export_button.setEnabled(True)
            self.analysis_export_button.setText('工程別データ出力')
            if code == 0:
                QMessageBox.information(self, '工程別データ出力完了', str(output))
            else:
                error = bytes(self.analysis_process.readAllStandardError()).decode('utf-8', errors='replace')
                QMessageBox.warning(self, '出力失敗', error + '\n途中の出力は解析に使用しないでください。')
        self.analysis_process.finished.connect(finished)
        self.analysis_process.errorOccurred.connect(lambda error: finished(-1, None) if error == QProcess.FailedToStart else None)
        self.analysis_process.start()

    def create_settings(self):
        from settings_preview import SettingsPreview
        text, path = self.setting_text, self.setting_path
        if not text:
            path = ROOT.parent / 'SGMO2_original/JinSettings-0.2.0.09030/jin_setting_change_初期値.txt'
            try:
                data = path.read_bytes()
                try:
                    text = data.decode('utf-8-sig')
                except UnicodeDecodeError:
                    text = data.decode('cp932')
            except (OSError, UnicodeError) as error:
                QMessageBox.warning(self, '設定ファイル', f'元になる設定ファイルを選択してください。\n{error}')
                return
        dialog = SettingsPreview(text, path.name if path else 'settings.txt', self, editable=True)
        dialog.exec()
        if dialog.saved_path is not None:
            self.setting_path, self.setting_text = dialog.saved_path, dialog.saved_text
            self.state.reset()
            self.state.configured = False
            self.file_label.setText(f'{self.setting_path.name} / 未適用')
            self.log(f'新しい設定を保存・選択：{self.setting_path.name}')
            self.refresh()

    def apply_settings(self):
        self.reset()
        self.state.configured = True
        name = self.setting_path.name if self.setting_path else "デモ用設定"
        self.file_label.setText(name + "  /  デモ適用済み")
        self.log(f"設定適用をシミュレーション：{name}（送信なし）")
        self.refresh()

    def rate_changed(self):
        if self.state.configured:
            self.reset()
            self.log(f"High設定を{self.rate.currentText()}へ変更。準備工程をリセットしました。")

    def run_batch(self):
        self.run_step(self.state.completed, batch=True)

    def run_step(self, index, batch=False):
        if not self.state.begin(index, batch):
            return
        self.state.reports[index].setting = 'デモ / ' + (self.setting_path.name if self.setting_path else 'デモ用設定')
        self.log(f"{STEPS[index][0]}：{STEPS[index][1]}")
        self.refresh()
        if index != 2:
            self.step_timer.start(800)

    def confirm_chip(self):
        if self.state.active == 2:
            self.log("チップ装着確認を受け付けました（デモ）。")
            self.finish_step()

    def finish_step(self):
        index = self.state.active
        if index is None:
            return
        batch = self.state.batch
        if index == 8:
            self.high = True
        self.state.finish()
        self.log(f"{STEPS[index][0]} 完了（デモ）")
        self.refresh()
        if batch and not self.state.ready:
            self.run_step(self.state.completed, batch=True)

    def measure(self):
        if self.state.start_measurement():
            self.log("Hold Gap開始（デモ）。")
            self.refresh()

    def stop(self):
        self.step_timer.stop()
        self.state.stop()
        self.log("工程・測定を停止しました（デモ）。未完了工程から再実行できます。")
        self.refresh()

    def reset(self):
        self.step_timer.stop()
        self.state.reset()
        self.high = False
        self.log("準備工程をリセットしました（デモ）。")
        self.refresh()

    def show_manual_dialog(self):
        self.refresh()
        self.manual_dialog.show()
        self.manual_dialog.raise_()
        self.manual_dialog.activateWindow()

    def manual(self, name):
        self.reset()
        if name == "High 測定":
            self.high = True
        self.log(f"個別操作：{name}（送信なし）。準備状態をリセットしました。")

    def reset_plot_scales(self):
        for plot in (self.current_plot, self.motor_plot, self.piezo_plot):
            plot.autoRange()
            plot.enableAutoRange(x=True, y=True)

    def clear_display_history(self):
        self.history.clear()
        self.display_start = time.monotonic() - self.started
        for curve in (self.current_curve, self.median_curve, self.motor_curve, self.piezo_curve):
            curve.setData([], [])
        self.stats.setText('表示履歴をクリアしました。次のデータを待っています。')
        self.reset_plot_scales()

    def update_plots(self):
        now = time.monotonic() - self.started
        x = np.linspace(max(getattr(self, 'display_start', 0), now - 5), max(now, 0.001), 1500)
        center = 24.0 if self.high else 1.2
        y = center + center * (0.035 * np.sin(x * 8) + self.rng.normal(0, 0.01, len(x)))
        median = float(np.median(y))
        rms = float(np.sqrt(np.mean(y ** 2)))
        noise = float(np.sqrt(np.mean((y - np.mean(y)) ** 2)))
        unit = "pA" if self.high else "µA"
        self.current_plot.setLabel("left", "Current", units=unit)
        self.current_curve.setData(x, y)
        self.median_curve.setData([x[0], x[-1]], [median, median])
        self.stats.setText(f"DEMO  ·  {'High ' + self.rate.currentText() if self.high else 'Low 10 kHz'}"
                           f"    Median {median:.3f}  /  RMS {rms:.3f}  /  Noise RMS {noise:.3f} {unit}")
        motor = 671.4 + 0.03 * math.sin(now / 2)
        piezo = 20000 + 80 * math.sin(now / 3)
        self.history.append((now, motor, piezo))
        data = np.array(self.history)
        self.motor_curve.setData(data[:, 0], data[:, 1])
        self.piezo_curve.setData(data[:, 0], data[:, 2])
        self.meters["CURRENT"].setText(f"{y[-1]:.3f} {unit}")
        self.meters["MOTOR"].setText(f"{motor:.2f} µm")
        self.meters["PIEZO"].setText(f"{piezo:.0f} nm")

    def closeEvent(self, event):
        self.step_timer.stop()
        self.plot_timer.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet((ROOT / "style.qss").read_text(encoding="utf-8"))
    if '--demo' in sys.argv:
        window = MainWindow()
    else:
        from gateway_window import GatewayWindow
        window = GatewayWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
