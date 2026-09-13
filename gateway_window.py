"""Gateway-connected UI. No automatic connection, command replay or demo waveforms."""
import queue
import time
from collections import deque
from pathlib import Path
import pyqtgraph as pg
from hold_monitor import HoldMonitor
from piezo_guard import range_problem
from conduction_guard import ConductionGuard
import numpy as np
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QFileDialog, QMessageBox, QComboBox, QDoubleSpinBox, QProgressBar, QLineEdit, QWidget
from main import MainWindow, ROOT, button, group, QSizePolicy
from workflow import STEPS
from gateway import Gateway
from command_engine import CommandEngine
from telemetry import Telemetry
from worker_progress import WorkerProgress
from baseline_current import BaselineCurrent
from gateway_launcher import launch_gateway
from gap_target import model_target, raw_from_command, describe_raw, NEW_RAW_PER_PA
from protocol import (Command, settings_commands, setup_commands, finalize_commands, WORKERS,
                      BIAS0, BIAS1, EP0, GO0, LOW, SAMPLE_STOP, high)


class GatewayWindow(MainWindow):
    def __init__(self):
        self.live = False
        super().__init__()
        self.live = True
        self.shutdown_confirmed = []
        self.start_at = QComboBox()
        self.start_at.addItems(['最初から準備', 'チップ装着済み：Bias印加から', 'First Cutを省略：Targeting → Motor Trainingから'])
        self.start_at_button = button('選択した工程から準備を実行', self.start_selected_setup, 'primary')
        setup_layout = self.batch_button.parentWidget().layout()
        setup_layout.insertWidget(1, self.start_at)
        setup_layout.insertWidget(2, self.start_at_button)
        self.step_timer.stop()
        self.transport = None
        self.engine = None
        self.telemetry = Telemetry()
        self.last_host = 0
        self.conduction_guard = None
        self.target_guard = None
        self.conduction_stop_reason = ''
        self.worker_progress = WorkerProgress()
        self.baseline_current = None
        self.saved_report_ids = set()
        self.report_save_errors = {}
        self.operation = None
        self.touched = False
        self.closing = False
        self.shutdown_error = ''
        self.disconnecting = False
        self.allow_close = False
        self.problem = ''
        self.host_dirty = False
        self.launch_deadline = None
        self.gap_applied_raw = None
        self.measure_deadline = None
        self.timed_finish = False
        self.host_paused = False
        self.host_start_deadline = None
        self.recipe = []
        self.recipe_pending = []
        self.auto_measure = False
        self.recipe_number = 0
        self.recipe_total = 0
        self.recipe_started_at = None
        self.recipe_estimated_seconds = 0
        self.reset_pending = False
        self.quality_stop_reason = ''
        self.piezo_stop_reason = ''
        self.hold_monitor = HoldMonitor()
        self.hold_frames = deque(maxlen=500)
        self.hold_points = deque(maxlen=1200)
        self.hold_check_at = 0
        self.hold_target = None
        gap_layout = self.measurement_box.layout()
        piezo_row = QHBoxLayout()
        piezo_row.addWidget(QLabel('Piezo正常範囲（nm）'))
        self.piezo_lower = QLineEdit('-100000')
        self.piezo_upper = QLineEdit('100000')
        for edit, label in ((self.piezo_lower, '下限：未設定'), (self.piezo_upper, '上限：未設定')):
            edit.setPlaceholderText(label)
            edit.setToolTip('初期値は暫定範囲 −100000 ～ +100000 nm。メーカー仕様または実機で確認した範囲に変更できます。端点は範囲内として扱います。')
            piezo_row.addWidget(edit)
        gap_layout.addLayout(piezo_row)
        gap_row = QHBoxLayout()
        gap_row.addWidget(QLabel('目標Gap Distance'))
        self.gap_choice = QDoubleSpinBox()
        self.gap_choice.setDecimals(3)
        self.gap_choice.setRange(0.001, 10.0)
        self.gap_choice.setSingleStep(0.01)
        self.gap_choice.setValue(0.60)
        self.gap_choice.setSuffix(' nm')
        self.gap_choice.valueChanged.connect(self.gap_selection_changed)
        gap_row.addWidget(self.gap_choice, 1)
        gap_row.addWidget(QLabel('計測時間'))
        self.measure_minutes = QDoubleSpinBox()
        self.measure_minutes.setRange(0.01, 1440)
        self.measure_minutes.setValue(1)
        self.measure_minutes.setSuffix(' min')
        gap_row.addWidget(self.measure_minutes)
        self.gap_controls = QWidget(self.measurement_box)
        self.gap_controls.setLayout(gap_row)
        self.gap_controls.hide()
        self.measure_button.hide()
        self.phase.setWordWrap(True)
        self.gap_target_label = QLabel()
        self.gap_target_label.setWordWrap(True)
        self.gap_applied_label = QLabel('適用値：未確認')
        self.gap_applied_label.setWordWrap(True)
        self.gap_apply_button = button('目標電流だけを適用', self.apply_gap_target, 'primary')
        gap_layout.insertWidget(2, self.gap_target_label)
        gap_layout.insertWidget(3, self.gap_applied_label)
        gap_layout.insertWidget(4, self.gap_apply_button)
        for widget in (self.gap_target_label, self.gap_applied_label, self.gap_apply_button):
            widget.hide()
        self.measure_progress = QProgressBar()
        self.measure_progress.setRange(0, 1000)
        self.measure_progress.setFormat('計測待機')
        self.measure_progress.setStyleSheet('QProgressBar { background: #24180B; color: white; min-height: 26px; } QProgressBar::chunk { background: #B85C00; }')
        gap_layout.insertWidget(5, self.measure_progress)
        self.recipe_progress = QProgressBar()
        self.recipe_progress.setRange(0, 1000)
        self.recipe_progress.setFormat('レシピ全体：待機')
        self.recipe_progress.setStyleSheet('QProgressBar { background: #20112F; color: white; min-height: 26px; } QProgressBar::chunk { background: #7542B5; }')
        gap_layout.insertWidget(6, self.recipe_progress)
        self.recipe_eta = QLabel('終了見込み：レシピ登録後に表示')
        self.recipe_eta.setWordWrap(True)
        self.recipe_eta.setStyleSheet('font-size: 22px; font-weight: 700; color: #FFE08A; padding: 6px;')
        gap_layout.insertWidget(7, self.recipe_eta)
        self.next_action = QLabel('次の工程：①「レシピ作成・読込」→ ②「レシピ実行」')
        self.next_action.setWordWrap(True)
        self.next_action.setStyleSheet('font-size: 18px; font-weight: 700; color: #FFE08A; padding: 8px; border: 2px solid #F5D547; border-radius: 5px; background: #2A230D;')
        self.next_action.hide()
        gap_layout.insertWidget(8, self.next_action)
        recipe_row = QHBoxLayout()
        self.recipe_edit = button('レシピ作成・読込', self.edit_recipe)
        self.recipe_start = button('レシピ実行', self.start_recipe)
        self.resume_button = button('再計測（Expand Gapから）', self.resume_measurement)
        for b in (self.recipe_edit, self.recipe_start, self.resume_button): recipe_row.addWidget(b)
        self.resume_button.hide()
        gap_layout.insertLayout(9, recipe_row)
        hold_panel, hold_layout = group('HOLD GAP / 電流一致判定')
        self.hold_panel = hold_panel
        hardware_index = self.right_layout.indexOf(self.hardware_box)
        self.right_layout.insertWidget(hardware_index + 1, hold_panel, 2)
        self.hold_values = QLabel('Expand Mean：未取得 / Hold Gap判定：待機')
        self.hold_values.setWordWrap(True)
        self.hold_values.setStyleSheet('font-size: 13px; font-weight: 600;')
        self.hold_values.setMinimumHeight(54)
        self.hold_values.setMaximumHeight(84)
        self.hold_values.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        hold_layout.addWidget(self.hold_values)
        self.hold_lamp = QLabel('● 判定なし')
        self.hold_lamp.setFixedHeight(28)
        self.hold_lamp.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.hold_lamp.setStyleSheet('font-size: 22px; color: #8291A5;')
        hold_layout.addWidget(self.hold_lamp)
        self.hold_plot = pg.PlotWidget()
        self.hold_plot.setMinimumHeight(190)
        self.hold_plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.hold_plot.setLabel('left', 'Median − (Mean + 適用値)', units='pA')
        self.hold_plot.setLabel('bottom', 'Hold Gap経過', units='s')
        for bound in (-20, 20):
            self.hold_plot.addItem(pg.InfiniteLine(pos=bound, angle=0, pen=pg.mkPen('#F5D547', width=1.5)))
        for bound in (-10, 10):
            self.hold_plot.addItem(pg.InfiniteLine(pos=bound, angle=0, pen=pg.mkPen('#39D98A', width=1.2, style=Qt.PenStyle.DashLine)))
        self.hold_plot.addItem(pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('#8291A5', width=1)))
        self.hold_plot.setYRange(-30, 30, padding=0)
        self.hold_curve = self.hold_plot.plot(pen='#FF9F43')
        hold_layout.addWidget(self.hold_plot, 1)
        self.setWindowTitle('JIN SAMURAI Control 0.2')
        self.console.clear()
        self.file_label.setText('設定ファイルを選択してください')
        self.apply_button.setText('設定を装置へ適用')
        self.stop_button.setText('工程・測定を停止')
        self.footer.setText('SGMO2 / 0.2.0  •  データ保存はGateway側のOptionsで設定  •  単独の操作Clientとして使用')
        self.banner.setText('「Gatewayを起動して接続」で保存済みのCOM設定を復元します。初回・COM番号変更時はGatewayで設定し、正常終了すると保存されます。')
        launch_row = QHBoxLayout()
        self.launch_button = button('Gatewayを起動して接続', self.launch_and_connect, 'primary')
        launch_row.addWidget(self.launch_button)
        self.saved_ports_label = QLabel('保存済みのポート設定を使用')
        self.saved_ports_label.setWordWrap(True)
        launch_row.addWidget(self.saved_ports_label, 1)
        self.centralWidget().layout().insertLayout(2, launch_row)
        connection = QHBoxLayout()
        connection.addWidget(QLabel('Gateway  127.0.0.1   受信'))
        self.sub_port = QSpinBox()
        self.push_port = QSpinBox()
        for widget, value in ((self.sub_port, 55555), (self.push_port, 55556)):
            widget.setRange(1024, 65535)
            widget.setValue(value)
        connection.addWidget(self.sub_port)
        connection.addWidget(QLabel('送信'))
        connection.addWidget(self.push_port)
        self.connect_button = button('Gatewayに接続', self.toggle_connection, 'primary')
        connection.addWidget(self.connect_button)
        self.rx_label = QLabel('Host：未受信 / Debug・Log：未受信')
        connection.addWidget(self.rx_label, 1)
        self.centralWidget().layout().insertLayout(3, connection)
        self.debug_seen = self.log_seen = False
        self.io_timer = QTimer(self)
        self.io_timer.timeout.connect(self.poll_gateway)
        self.io_timer.start(20)
        self.clear_graphs()
        self.autoload_latest_settings()
        self.refresh()
        self.log('Gateway接続モード。接続操作だけでは装置コマンドを送信しません。')

    @property
    def available(self):
        return bool(self.transport and self.transport.connected and self.engine and
                    not self.engine.faulted)

    @property
    def host_recent(self):
        return bool(self.last_host and time.monotonic() - self.last_host < 2)

    def log(self, text):
        if not self.live:
            return super().log(text)
        self.console.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def refresh(self):
        if not self.live:
            return super().refresh()
        super().refresh()
        from report_view import save_report
        for index in (4, 5, 6, 10):
            report = self.state.reports.get(index)
            if report is None or report.elapsed is None or report.started in self.saved_report_ids or report.started in self.report_save_errors:
                continue
            try:
                path = save_report(index, report)
                self.saved_report_ids.add(report.started)
                self.log(f'{STEPS[index][0]}レポート自動保存：{path.name}')
            except (OSError, ValueError) as error:
                self.report_save_errors[report.started] = str(error)
                self.log(f'レポート自動保存失敗：{error}')
        self.report_history_button.setText('履歴・統計' if not self.report_save_errors else '履歴・統計（保存失敗あり）')
        pending = self.operation is not None or bool(self.engine and self.engine.busy)
        busy = pending or self.state.active is not None or self.state.measurement
        self.start_at.setEnabled(self.available and not busy)
        self.start_at_button.setEnabled(self.available and self.state.configured and not busy)
        self.piezo_lower.setEnabled(not busy)
        self.piezo_upper.setEnabled(not busy)
        self.create_settings_button.setEnabled(not busy)
        available = self.available
        for item in [self.batch_button, self.reset_button, self.measure_button,
                     *self.manual_buttons, *(row[1] for row in self.rows)]:
            item.setEnabled(item.isEnabled() and available and not pending)
        self.select_button.setEnabled(not busy)
        self.preview_button.setEnabled(bool(self.setting_text))
        self.rate.setEnabled(not busy)
        self.apply_button.setEnabled(available and not busy and bool(self.setting_text))
        self.measure_stop.setEnabled(available and self.state.measurement and self.operation != 'stop')
        self.stop_button.setEnabled(available and busy and self.operation not in ('stop', 'finalize'))
        self.chip_button.setEnabled(available and self.state.active == 2)
        self.connect_button.setEnabled(not busy or bool(self.engine and self.engine.faulted))
        if self.operation in ('stop', 'piezo_cleanup', 'quality_cleanup', 'timed_cleanup'):
            self.connect_button.setEnabled(True)
        self.gap_choice.setEnabled(not busy)
        self.measure_minutes.setEnabled(not busy)
        self.reset_button.setEnabled(available and self.state.configured and not self.reset_pending and self.operation != 'finalize')
        if not self.state.measurement:
            r = self.state.reports.get(10)
            b = r.baseline_current if r else None
            if self.state.completed >= 11 and b and b.get('mean_pa') is not None:
                self.hold_values.setText(f'Expand Mean：{b["mean_pa"]:.3f} pA')
        self.distance_meter.setText(f'{self.gap_choice.value():.3f} nm')
        can_restart = available and not busy and self.state.configured and self.state.completed >= 10
        self.resume_button.setEnabled(can_restart)
        self.recipe_edit.setEnabled(not busy and not self.auto_measure)
        self.recipe_start.setEnabled(can_restart and bool(self.recipe))
        choose_recipe = self.state.ready and not busy and not self.recipe
        self.next_action.setVisible(self.state.ready and not self.state.measurement)
        self.recipe_edit.setStyleSheet(
            'font-size: 17px; font-weight: 700; min-height: 38px; border: 2px solid #F5D547; background: #3A300D;'
            if choose_recipe else '')
        self.gap_apply_button.setEnabled(available and self.state.ready and not busy and self.selected_target() is not None)
        self.gap_target_label.setText(self.gap_target_description())
        self.gap_applied_label.setText(describe_raw(self.gap_applied_raw))
        self.measure_button.setEnabled(self.measure_button.isEnabled() and self.gap_matches_selection())
        launching = self.launch_deadline is not None
        self.launch_button.setEnabled(not busy and not launching and not self.touched and
                                      not (self.transport and self.transport.connected))
        self.connect_button.setEnabled(self.connect_button.isEnabled() and not launching)
        self.connect_button.setText(('終了処理して切断' if self.touched else '切断') if self.transport else 'Gatewayに接続')
        self.sub_port.setEnabled(self.transport is None)
        self.push_port.setEnabled(self.transport is None)
        connected = bool(self.transport and self.transport.connected)
        self.connection_badge.setText('GATEWAY  •  ' + ('状態未確認' if self.engine and self.engine.faulted else
                                                      'Host受信中' if connected and self.host_recent else 'Host待ち' if connected else '未接続'))
        if self.problem:
            self.phase.setText(self.problem)
        elif launching:
            self.phase.setText('Gateway起動・接続待ち…')
        elif self.operation == 'settings':
            self.phase.setText('設定コマンドを順番に送信中…')
        elif self.operation == 'conduction':
            self.phase.setText('First Cut前の導通確認 / 3秒待機・1秒中央値9 µA以上で開始')
        elif self.operation == 'baseline':
            self.phase.setText('Expand Gap完了 / 基準電流を取得中（1秒間）…')
        elif self.operation == 'finalize':
            self.phase.setText('終了処理中：停止・Bias/EP 0・測定回路の復帰を確認中…')
        elif self.operation == 'stop':
            self.phase.setText('停止要求中：装置からの応答・終了ログを待っています')
        elif self.operation == 'gap_target':
            self.phase.setText('目標電流の設定応答を確認中…')
        elif self.operation == 'measure' and not self.state.measurement:
            self.phase.setText('Hold Gap開始要求中…')
        elif self.state.measurement:
            remaining = max(0, self.measure_deadline - time.monotonic()) if self.measure_deadline else 0
            self.phase.setText(f'HOLD GAP / 計測中 / 残り {remaining:.1f} 秒')
        elif self.state.active is not None:
            self.phase.setText(STEPS[self.state.active][0] + (' / 装着確認待ち' if self.state.active == 2 else ' / ' + self.worker_progress.describe()))
        elif self.state.ready and not self.gap_matches_selection():
            self.phase.setText('準備完了 / レシピを設定して「レシピ実行」を押してください')
        elif not self.state.configured:
            self.phase.setText('設定ファイルを適用してください。初期化で測定データの送信を開始します。' if available else
                               'Gateway接続後、設定ファイルを装置へ適用してください')

    def launch_and_connect(self):
        if self.operation or self.touched or self.launch_deadline is not None:
            return
        try:
            ports, saved, reused = launch_gateway()
        except (OSError, ValueError) as error:
            self.problem = f'Gateway起動失敗：{error}'
            self.log(self.problem)
            self.refresh()
            return
        if self.transport:
            self.disconnect()
        self.sub_port.setValue(ports[0])
        self.push_port.setValue(ports[1])
        self.saved_ports_label.setText('保存値（現在の接続状態ではありません）：' + saved)
        self.log('起動済みGatewayへ接続します。' if reused else '保存済み設定でGatewayを起動しました。')
        self.launch_deadline = time.monotonic() + 20
        self.toggle_connection()

    def toggle_connection(self):
        if self.transport:
            if self.touched:
                self.disconnecting = True
                if self.operation in ('stop', 'finalize', 'piezo_cleanup', 'quality_cleanup', 'timed_cleanup'):
                    self.log('現在の停止処理の応答確認後に終了処理して切断します。')
                elif self.operation and self.available:
                    self.stop()
                else:
                    self.retry_finalize()
            else:
                self.disconnect()
            return
        self.problem = ''
        self.gap_applied_raw = None
        self.last_host = 0
        self.debug_seen = self.log_seen = False
        self.telemetry = Telemetry()
        self.state.reset()
        self.state.configured = False
        self.touched = False
        self.transport = Gateway(f'tcp://127.0.0.1:{self.sub_port.value()}',
                                 f'tcp://127.0.0.1:{self.push_port.value()}')
        self.engine = CommandEngine(self.send_command, self.command_result, self.command_accepted)
        self.transport.start()
        self.clear_graphs()
        self.log('Gateway接続を開始しました。Hostデータの到着を待っています。')
        self.refresh()

    def disconnect(self):
        self.launch_deadline = None
        self.gap_applied_raw = None
        if self.transport:
            self.transport.close()
        self.transport = self.engine = None
        self.state.reset()
        self.state.configured = False
        self.operation = None
        self.disconnecting = False
        self.last_host = 0
        self.rx_label.setText('切断済み / 設定・準備は再接続後に確認')
        self.clear_graphs()
        self.refresh()

    def clear_graphs(self):
        for curve in (self.current_curve, self.median_curve, self.motor_curve, self.piezo_curve):
            curve.setData([], [])
        for meter in self.meters.values():
            meter.setText('--')
        self.stats.setText('Hostデータ待ち')

    def clear_display_history(self):
        if not self.live:
            return super().clear_display_history()
        self.telemetry.frames.clear()
        self.telemetry.hardware.clear()
        self.host_dirty = False
        for curve in (self.current_curve, self.median_curve, self.motor_curve, self.piezo_curve):
            curve.setData([], [])
        self.stats.setText('表示履歴をクリアしました。次の受信データから表示します。')
        self.reset_plot_scales()

    def send_command(self, text):
        if not self.available:
            raise RuntimeError('Gatewayに接続していないか、装置状態が未確認です。')
        self.touched = True
        self.log('TX  ' + text)
        self.transport.send(text)
        if text == SAMPLE_STOP.text:
            # Host silence is expected once stopping is requested. The command
            # response, not Host silence, determines whether stopping succeeded.
            self.host_paused = True
            self.host_start_deadline = None
        if self.operation == 'finalize':
            labels = {'mcbj stop': '工程停止', BIAS0.text: 'Bias解除', EP0.text: 'EP解除', SAMPLE_STOP.text: 'データ取得停止'}
            self.alarm_status.setText('終了処理中：' + labels.get(text, text) + '\n確認済み：' + ('、'.join(self.shutdown_confirmed) or 'なし') + '\n成功応答を確認するまで接続を保持します。')
            self.alarm_status.setStyleSheet('background: #594510; color: #FFE291; font-size: 18px; font-weight: bold; padding: 10px;')
        if text == WORKERS['target'].text:
            frame = self.telemetry.latest
            self.target_guard = (time.monotonic(), frame.get('motor') if frame else None)
        else:
            self.target_guard = None

    def poll_gateway(self):
        transport = self.transport
        if not transport:
            return
        if self.launch_deadline is not None:
            if transport.connected:
                self.launch_deadline = None
                self.log('Gatewayに接続しました。Hostデータを待っています。')
            elif time.monotonic() > self.launch_deadline:
                self.disconnect()
                self.problem = 'Gatewayに接続できませんでした。Gateway画面の起動エラーとPUB/PULL表示を確認してください。'
                self.log(self.problem)
                self.refresh()
                return
        if transport.overflow.is_set():
            self.engine.fail('受信キューが上限に達しました。装置状態は未確認です。')
            transport.close()
        for payload in transport.drain_host():
            try:
                restarted = self.telemetry.feed(payload)
                if restarted is None:
                    continue
                if self.telemetry.latest is not None:
                    if self.state.measurement:
                        f = self.telemetry.latest
                        if f['unit'] == 'pA' and len(f['values']):
                            self.hold_frames.append(f['values'])
                        else:
                            self.hold_frames.clear()
                            self.hold_monitor = HoldMonitor()
                    self.host_start_deadline = None
                    if self.operation == 'baseline':
                        self.baseline_current.feed(self.telemetry.latest)
                    report = self.state.reports.get(self.state.active)
                    if report is not None:
                        report.sample(self.telemetry.latest)
                    self.last_host = time.monotonic()
                    self.host_dirty = True
                    self.check_piezo_range()
                    self.check_conduction_guard(self.telemetry.latest)
                if restarted and not self.engine.faulted:
                    self.engine.fail('装置時刻が巻き戻りました。再起動・再生リセットを確認し、再接続してください。')
            except ValueError as error:
                self.log(f'Hostデータ不正：{error}')
                if not self.engine.faulted:
                    self.engine.fail('受信データの形式が不正です。接続とファームウェアを確認してください。')
        for _ in range(500):
            try:
                topic, value = transport.events.get_nowait()
            except queue.Empty:
                break
            if topic in ('Debug', 'Log'):
                self.debug_seen |= topic == 'Debug'
                self.log_seen |= topic == 'Log'
                self.log(f'{topic}  {value}')
                report = self.state.reports.get(self.state.active)
                if report is not None:
                    report.feed(f'{topic}  {value}',
                                frame=self.telemetry.latest if topic == 'Log' else None,
                                position_age=time.monotonic() - self.last_host if self.last_host else None)
                if topic == 'Log' and self.operation == 'step':
                    self.worker_progress.feed(value)
                    if report is not None:
                        report.progress = self.worker_progress.describe()
                self.check_conduction_guard()
                self.engine.feed(topic, value)
            elif topic == 'Error' and not self.engine.faulted:
                self.engine.fail(value)
            elif topic == 'Connection':
                self.log('Gatewayソケット：' + ('接続' if value else '接続待ち'))
        if self.host_start_deadline is not None and time.monotonic() > self.host_start_deadline and not self.engine.faulted:
            self.host_start_deadline = None
            self.engine.fail('データ取得再開後にHostデータを受信できません。')
        if self.operation != 'finalize' and not self.host_paused and self.host_start_deadline is None and self.last_host and time.monotonic() - self.last_host > 2 and not self.engine.faulted:
            self.engine.fail('Host受信が2秒以上途絶えました。装置状態は未確認です。再接続してください。')
        self.check_conduction_guard()
        self.engine.tick()
        self.expand_after_host()
        self.check_hold_quality()
        self.check_measure_time()
        if self.operation == 'baseline':
            self.baseline_current.tick()
            if self.baseline_current.done:
                baseline = self.baseline_current.result
                self.state.reports[10].baseline_current = dict(baseline)
                self.operation = None
                if baseline['mean_pa'] is not None:
                    self.log(f'Expand Gap基準電流：{baseline["mean_pa"]:.6f} pA（{baseline["samples"]}サンプル）')
                    self.finish_live_step()
                else:
                    self.auto_measure = False
                    self.recipe_pending = []
                    self.problem = baseline['status'] + '。Expand Gapを再実行してください。'
                    self.state.reports[10].finish(self.problem)
                    self.state.stop()
                    self.log(self.problem)
        age = time.monotonic() - self.last_host if self.last_host else None
        self.rx_label.setText(f"Host：{f'{age:.1f}秒前' if age is not None else '未受信'} / "
                              f"Debug：{'受信あり' if self.debug_seen else '未受信'} / "
                              f"Log：{'受信あり' if self.log_seen else '未受信'}")
        self.refresh()

    def start_job(self, operation, commands):
        if not self.available or self.operation is not None:
            return False
        if any(command in WORKERS.values() for command in commands):
            problem = self.piezo_problem()
            if not problem and (self.host_paused or not self.host_recent):
                problem = 'Piezo監視用のHostデータがありません。データ取得を再開し、位置受信を確認してください。'
            if problem:
                self.auto_measure = False
                self.recipe_pending = []
                self.recipe_started_at = None
                self.state.stop()
                self.problem = problem
                self.log(problem)
                self.refresh()
                return False
            self.piezo_stop_reason = ''
        self.problem = ''
        self.operation = operation
        if not self.engine.start(commands):
            self.operation = None
            return False
        self.refresh()
        return True

    def piezo_problem(self):
        frame = self.telemetry.latest
        return range_problem(self.piezo_lower.text(), self.piezo_upper.text(),
                             frame['piezo'] if frame is not None else None)

    def check_piezo_range(self):
        # Include Targeting, First Cut and Motor Training, which can precede
        # Piezo work. Ignore recovery/zero-point commands and an ongoing stop.
        monitored = (self.operation == 'measure' or self.operation == 'baseline' or
                     self.operation == 'step' and self.state.active in (4, 5, 6, 7, 9, 10))
        if not monitored or not self.available:
            return
        reason = self.piezo_problem()
        if not reason:
            return
        self.piezo_stop_reason = reason
        self.show_stop_alarm(reason + '。停止確認待ち。')
        self.timed_finish = False
        self.quality_stop_reason = ''
        self.log(reason + '。工程・計測の停止を要求します。')
        self.stop()
        self.problem = reason + '。停止確認待ち。'

    def check_conduction_guard(self, frame=None):
        now = time.monotonic()
        reason = ''
        if self.operation == 'setup_entry_host':
            if frame is not None and frame.get('unit') == 'µA':
                self.operation = None
                self.run_step(self.selected_setup_index, batch=True)
            elif now >= self.setup_entry_deadline:
                self.show_stop_alarm('途中開始：Bias印加後の電流データを確認できません。停止確認待ち。')
                self.conduction_stop_reason = '途中開始：Bias印加後の電流データを確認できません'
                self.stop()
            return
        if self.operation == 'conduction' and self.conduction_guard is not None:
            reason = self.conduction_guard.check(now, frame)
            if not reason and self.conduction_guard.ready:
                self.conduction_guard = None
                self.operation = None
                self.log('導通確認成功：1秒中央値が9 µA以上。First Cutを開始します。')
                self.start_job('step', [WORKERS['fc']])
        elif self.target_guard is not None and self.operation == 'step':
            started, origin = self.target_guard
            latest = self.telemetry.latest
            position = latest.get('motor') if latest else None
            if not self.last_host or now - self.last_host >= 1:
                reason = 'Targeting：Hostデータの受信が1秒以上途絶えました'
            elif origin is None or position is None or not np.isfinite(origin) or not np.isfinite(position):
                reason = 'Targeting：有効なモーター位置を取得できません'
            elif abs(position - origin) >= 200:
                reason = 'Targeting：開始位置からの移動量が200 µmに達しました'
            elif now - started >= 15:
                reason = 'Targeting：実行時間が15秒に達しました'
        if reason:
            self.conduction_stop_reason = reason
            self.show_stop_alarm(reason + '。停止確認待ち。')
            self.log(reason)
            self.stop()
            self.problem = reason + '。停止確認待ち。'

    def show_stop_alarm(self, reason):
        self.alarm_status.setText('異常停止・中断\n' + reason)
        self.alarm_status.setStyleSheet('background: #681F2D; color: #FFFFFF; border: 2px solid #FF6378; font-size: 18px; font-weight: bold; padding: 10px;')

    def settings_base_dir(self):
        return ROOT.parent / 'SGMO2_original/JinSettings-0.2.0.09030'

    def read_settings_file(self, path):
        path = Path(path)
        data = path.read_bytes()
        try:
            text = data.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = data.decode('cp932')
        return text, settings_commands(text)

    def use_settings_file(self, path, text, commands, note='未適用'):
        path = Path(path)
        self.setting_path, self.setting_text = path, text
        self.state.reset()
        self.state.configured = False
        self.file_label.setText(f'{path.name} / {len(commands)}コマンド（{note}）')

    def autoload_latest_settings(self):
        base = self.settings_base_dir()
        try:
            candidates = sorted(base.glob('*.txt'), key=lambda path: path.stat().st_mtime, reverse=True)
        except OSError:
            return
        for path in candidates:
            try:
                text, commands = self.read_settings_file(path)
            except (ValueError, UnicodeError, OSError):
                continue
            self.use_settings_file(path, text, commands, '自動選択・未適用')
            self.log(f'直近の設定ファイルを自動選択：{path.name}')
            return

    def select_settings(self):
        path, _ = QFileDialog.getOpenFileName(self, '設定ファイル',
                  str(self.settings_base_dir()), 'Settings (*.txt)')
        if not path:
            return
        try:
            text, commands = self.read_settings_file(path)
        except (ValueError, UnicodeError, OSError) as error:
            QMessageBox.warning(self, '設定ファイル', str(error))
            return
        self.use_settings_file(path, text, commands)
        self.refresh()

    def apply_settings(self):
        if not self.available or not self.setting_text:
            return
        try:
            commands = settings_commands(self.setting_text)
        except ValueError as error:
            self.problem = str(error)
            self.refresh()
            return
        self.state.reset()
        self.state.configured = False
        self.gap_applied_raw = None
        self.file_label.setText(self.setting_path.name + ' / 適用中…')
        self.start_job('settings', commands)

    def rate_changed(self):
        if not self.live:
            return super().rate_changed()
        self.state.reset()
        self.log('Highサンプルレートを変更しました。準備をやり直してください。')
        self.refresh()

    def confirm_zero_move(self):
        frame = self.telemetry.latest
        motor = frame.get('motor') if frame else None
        if motor is not None and np.isfinite(motor) and motor >= 0 and self.host_recent:
            return True
        reason = (f'Motor位置は {motor:.2f} µm（負の値）です。'
                  if motor is not None and np.isfinite(motor) and motor < 0
                  else '現在のMotor位置を確認できません。')
        answer = QMessageBox.warning(
            self, 'ゼロ点移動前の確認',
            reason + '\nMotorが負の位置からゼロ点へ移動すると上昇し、装着済みのチップを破壊するおそれがあります。'
            '\nチップと装置の状態を確認してください。ゼロ点移動を実行しますか？',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        proceed = answer == QMessageBox.StandardButton.Yes
        self.log('ゼロ点移動前の確認：' + reason + (' 実行を選択。' if proceed else ' キャンセル。'))
        return proceed

    def run_step(self, index, batch=False):
        if not self.live:
            return super().run_step(index, batch)
        if not self.available or self.operation:
            return
        if index == 1 and self.state.completed == 1 and self.state.active is None:
            if not self.confirm_zero_move():
                self.state.batch = False
                self.refresh()
                return
        if not self.state.begin(index, batch):
            return
        self.problem = ''
        self.worker_progress = WorkerProgress(index)
        self.conduction_stop_reason = ''
        if index == 10:
            self.baseline_current = None
        self.state.reports[index].setting = self.setting_path.name if self.setting_path else ''
        self.state.reports[index].setting_text = self.setting_text
        self.log(STEPS[index][0] + '：開始')
        if index == 4:
            self.conduction_stop_reason = ''
            self.conduction_guard = ConductionGuard(time.monotonic())
            self.operation = 'conduction'
            self.log('導通確認：3秒待機後、1秒中央値で判定（下限9 µA、低電流3秒で中断）。')
        elif index != 2:
            rate = (10, 50, 100)[self.rate.currentIndex()]
            self.start_job('step', setup_commands(index, rate))
        self.refresh()

    def confirm_chip(self):
        if self.available and self.state.active == 2:
            self.log('チップ装着を確認しました。')
            self.finish_live_step()

    def finish_live_step(self):
        index, batch = self.state.active, self.state.batch
        if index is None:
            return
        if index == 10 and self.baseline_current is None:
            from recipe_timing import record
            try:
                record(time.monotonic() - self.state.reports[10].started)
            except (OSError, ValueError) as error:
                self.log(f'Expand Gap時間履歴の保存失敗：{error}')
            latest = self.telemetry.latest
            self.baseline_current = BaselineCurrent(latest['serial'] if latest else None)
            self.state.reports[10].baseline_current = self.baseline_current.result
            self.operation = 'baseline'
            self.log('Expand Gapの完了通知を確認。基準電流の1秒間取得を開始します。')
            self.refresh()
            return
        self.state.finish()
        self.log(STEPS[index][0] + '：完了')
        self.refresh()
        if index == 10 and self.auto_measure:
            self.log('自動計測：Expand Gap後の目標電流設定へ移行します。')
            QTimer.singleShot(0, self.auto_apply_target)
        elif index == 10:
            self.log('Expand Gap完了：「レシピ実行」で計測を開始できます。')
        if batch and not self.state.ready:
            # Avoid reentering the command engine inside its completion callback.
            QTimer.singleShot(0, self.continue_batch)

    def continue_batch(self):
        if self.state.batch and self.available and not self.operation:
            if self.state.completed == 10 and self.recipe:
                self.start_recipe()
            else:
                self.run_step(self.state.completed, batch=True)

    def measure(self):
        if self.available and not self.operation and self.state.ready and not self.state.measurement and self.gap_matches_selection():
            self.timed_finish = False
            self.problem = ''
            self.start_job('measure', [WORKERS['hg']])

    def check_hold_quality(self):
        now = time.monotonic()
        if not self.state.measurement or self.operation != 'measure' or now - self.hold_check_at < .25:
            return
        self.hold_check_at = now
        if not self.host_recent or not self.hold_frames or self.hold_target is None:
            self.hold_monitor = HoldMonitor()
            self.hold_lamp.setText('● 判定なし：電流データ未確認')
            self.hold_lamp.setStyleSheet('font-size: 22px; color: #8291A5;')
            return
        median = float(np.median(np.concatenate(self.hold_frames)))
        delta, inside, stop = self.hold_monitor.update(now, median, self.hold_target)
        if inside is None:
            self.hold_lamp.setText('● 判定なし：電流データ不正')
            self.hold_lamp.setStyleSheet('font-size: 22px; color: #8291A5;')
            return
        bg = self.state.reports[10].baseline_current['mean_pa']
        self.hold_values.setText(f'Expand Mean：{bg:.3f} pA\nMean＋適用値：{self.hold_target:.3f} pA\nMedian：{median:.3f} pA / 差：{delta:+.3f} pA')
        outside = now - self.hold_monitor.out_since if self.hold_monitor.out_since is not None else 0
        self.hold_lamp.setText('● TRUE：±20 pA以内' if inside else f'● FALSE：範囲外 {outside:.1f} / 30秒')
        self.hold_lamp.setStyleSheet('font-size: 22px; color: ' + ('#39D98A;' if inside else '#FF6378;'))
        self.hold_points.append((now - self.hold_started, delta))
        self.hold_curve.setData([p[0] for p in self.hold_points], [p[1] for p in self.hold_points])
        if stop:
            self.quality_stop_reason = 'Hold Gap判定が±20 pAの範囲外で30秒継続したため停止'
            self.show_stop_alarm(self.quality_stop_reason + '。停止確認待ち。')
            self.stop()
            self.problem = self.quality_stop_reason + '要求中'
            self.log(self.problem)

    def check_measure_time(self):
        if self.recipe_started_at is not None:
            elapsed = time.monotonic() - self.recipe_started_at
            estimate = self.recipe_estimated_seconds
            self.recipe_progress.setValue(min(990, int(1000 * elapsed / max(estimate, 1))))
            self.recipe_progress.setFormat(f'レシピ {self.recipe_number}/{self.recipe_total}・経過 {elapsed / 60:.1f} min（推定進捗）')
            if elapsed > estimate:
                self.recipe_eta.setText('当初の終了見込みを超過しています。装置応答・工程完了を待っています。')
        if self.measure_deadline is not None:
            total = self.measure_minutes.value() * 60
            remaining = max(0, self.measure_deadline - time.monotonic())
            self.measure_progress.setValue(int(1000 * min(1, max(0, 1 - remaining / total))))
            self.measure_progress.setFormat(f'経過 {total - remaining:.0f} / {total:.0f} 秒・残り {remaining:.0f} 秒')
        if self.operation == 'measure' and self.measure_deadline is not None and time.monotonic() >= self.measure_deadline:
            self.timed_finish = True
            self.measure_deadline = None
            self.stop()

    def edit_recipe(self):
        from measurement_recipe import RecipeDialog
        dialog = RecipeDialog(self.recipe, self)
        if dialog.exec():
            self.recipe = dialog.result_rows
            self.recipe_start.setText(f'レシピ実行（{len(self.recipe)}条件）')
            self.update_recipe_estimate()
            self.refresh()
            self.scroll_recipe_controls()

    def scroll_recipe_controls(self):
        scroll = getattr(self, 'measurement_scroll', None)
        if scroll is not None:
            QTimer.singleShot(0, lambda: scroll.ensureWidgetVisible(self.recipe_start, 0, 60))

    def scroll_batch_controls(self):
        scroll = getattr(self, 'setup_scroll', None)
        if scroll is not None:
            QTimer.singleShot(0, lambda: scroll.ensureWidgetVisible(self.batch_button, 0, 60))

    def update_recipe_estimate(self):
        from recipe_timing import median_duration
        from datetime import datetime, timedelta
        median, _ = median_duration()
        self.recipe_estimated_seconds = sum(m * 60 for d, m in self.recipe) + len(self.recipe) * (median + 1)
        end = datetime.now() + timedelta(seconds=self.recipe_estimated_seconds)
        self.recipe_eta.setText(f'終了見込み {end:%Y-%m-%d %H:%M:%S}')

    def start_recipe(self):
        if not self.available or self.operation or not self.state.configured or self.state.completed < 10:
            return
        from measurement_recipe import validate
        try: self.recipe_pending = validate(self.recipe)
        except ValueError as e:
            QMessageBox.warning(self, 'レシピ', str(e)); return
        self.recipe_number = 0
        self.recipe_total = len(self.recipe_pending)
        self.update_recipe_estimate()
        self.recipe_started_at = time.monotonic()
        self.log(f'レシピ開始：全{self.recipe_total}条件')
        self.next_recipe()

    def next_recipe(self):
        if not self.recipe_pending or not self.available or self.operation: return
        d, minutes = self.recipe_pending.pop(0)
        self.recipe_number += 1
        self.log(f'レシピ {self.recipe_number}/{self.recipe_total}：距離 {d:g} nm・時間 {minutes:g} min / 残り{len(self.recipe_pending)}条件')
        self.gap_choice.setValue(d); self.measure_minutes.setValue(minutes)
        if self.recipe_number == 1 and self.selected_target() is not None:
            self.auto_measure = True
            self.problem = ''
            self.gap_applied_raw = None
            self.measure_progress.setValue(0)
            self.measure_progress.setFormat('計測準備：待機中のExpand Gap基準値を使用')
            self.log('レシピ先頭条件：待機中のExpand Gap基準電流を再利用します。')
            self.auto_apply_target()
        else:
            self.resume_measurement()

    def resume_measurement(self):
        if not self.available or self.operation or not self.state.configured or self.state.completed < 10:
            return
        self.auto_measure = True
        self.problem = ''
        self.state.completed = 10
        self.state.batch = False
        self.gap_applied_raw = None
        self.baseline_current = None
        self.measure_progress.setValue(0)
        self.measure_progress.setFormat('再計測準備：Expand Gap待ち')
        commands = [] if self.host_paused else [SAMPLE_STOP]
        commands.append(high((10, 50, 100)[self.rate.currentIndex()]))
        self.start_job('resume_sampling', commands)

    def selected_target(self):
        if not self.state.ready:
            return None
        report = self.state.reports.get(10)
        baseline = report.baseline_current if report else None
        if not baseline or baseline['status'] != '正常':
            return None
        try:
            return model_target(self.gap_choice.value())
        except ValueError:
            return None

    def gap_target_description(self):
        target = self.selected_target()
        if target is None:
            report = self.state.reports.get(10)
            baseline = report.baseline_current if report else None
            if self.state.ready and baseline and baseline['status'] == '正常':
                try:
                    model_target(self.gap_choice.value())
                except ValueError as error:
                    return '目標電流を適用できません：' + str(error)
            return 'Expand Gapの基準電流取得が必要です。'
        tunnel, raw = target
        bg = self.state.reports[10].baseline_current['mean_pa']
        return f'設定するトンネル電流 {tunnel:.6f} pA / 0x{raw:08X}\n参考：Expand Gap Mean {bg:.6f} pA（送信値には加算しません）\n暫定仕様：距離はモデル上の参考値。装置内部の基準加算は未確認です。'

    def gap_matches_selection(self):
        target = self.selected_target()
        return target is not None and self.gap_applied_raw == target[1]

    def gap_selection_changed(self):
        self.refresh()

    def apply_gap_target(self):
        target = self.selected_target()
        if (target is None or not self.available or not self.state.configured or self.operation or
                self.state.measurement or self.state.active is not None):
            return
        self.start_job('gap_target', [Command(f'asz set hg tunnel_current 0x{target[1]:08X}', 'Setting change : 0')])

    def auto_apply_target(self):
        if not self.auto_measure:
            return
        self.apply_gap_target()
        if self.operation != 'gap_target':
            self.problem = '自動計測を開始できません：' + self.gap_target_description()
            self.log(self.problem)
            self.auto_measure = False
            self.recipe_pending = []

    def command_accepted(self, command):
        if self.operation == 'finalize':
            labels = {'mcbj stop': '工程停止応答', BIAS0.text: 'Bias解除', EP0.text: 'EP解除', SAMPLE_STOP.text: 'データ取得停止'}
            self.shutdown_confirmed.append(labels.get(command.text, command.text))
        if command.text == SAMPLE_STOP.text:
            self.host_paused = True
            self.host_start_deadline = None
        if command.text.startswith('sv_info_sender start '):
            self.host_paused = False
            if self.operation == 'resume_sampling':
                self.last_host = 0
                self.host_start_deadline = time.monotonic() + 3
        raw = raw_from_command(command.text)
        if raw is not None:
            self.gap_applied_raw = raw
        if command.text == 'asz hg start' and self.operation == 'measure':
            self.hold_monitor = HoldMonitor()
            self.hold_frames.clear(); self.hold_points.clear(); self.hold_curve.setData([], [])
            self.hold_started = time.monotonic()
            self.quality_stop_reason = ''
            self.hold_target = self.state.reports[10].baseline_current['mean_pa'] + float(self.gap_applied_raw / NEW_RAW_PER_PA)
            from datetime import datetime, timedelta
            if self.recipe_started_at is None:
                end = datetime.now() + timedelta(minutes=self.measure_minutes.value())
                self.recipe_eta.setText(f'計測終了見込み：{end:%Y-%m-%d %H:%M:%S}')
            self.measure_deadline = time.monotonic() + self.measure_minutes.value() * 60
            self.state.measurement = True
            self.log('Hold Gapの開始応答を確認しました。')
            self.refresh()

    def stop(self):
        if not self.available or self.operation in ('stop', 'finalize'):
            return
        self.conduction_guard = None
        self.target_guard = None
        self.measure_deadline = None
        if not self.timed_finish:
            if self.recipe_started_at is not None:
                self.recipe_progress.setFormat('レシピ中断')
                self.recipe_started_at = None
            self.auto_measure = False
            self.recipe_pending = []
        if self.operation == 'baseline':
            self.baseline_current.fail('取得を中断しました')
        self.problem = ''
        self.state.batch = False
        self.operation = 'stop'
        self.engine.stop()
        self.refresh()

    def reset(self):
        if not self.live:
            return super().reset()
        if not self.available: return
        self.reset_pending = True
        self.recipe_pending = []
        self.auto_measure = False
        self.timed_finish = False
        if self.operation in ('stop', 'finalize', 'piezo_cleanup', 'quality_cleanup', 'timed_cleanup'):
            return
        if self.operation or self.state.active is not None or self.state.measurement:
            self.stop()
        else:
            self.finalize()

    def reset_measurement_display(self):
        self.recipe_pending = []
        self.recipe_number = self.recipe_total = 0
        self.recipe_started_at = self.measure_deadline = None
        self.recipe_estimated_seconds = 0
        self.auto_measure = self.timed_finish = False
        self.baseline_current = None
        self.gap_applied_raw = None
        self.quality_stop_reason = ''
        self.piezo_stop_reason = ''
        self.hold_target = None
        self.hold_monitor = HoldMonitor()
        self.hold_frames.clear(); self.hold_points.clear(); self.hold_curve.setData([], [])
        self.hold_lamp.setText('● 判定なし')
        self.hold_lamp.setStyleSheet('font-size: 22px; color: #8291A5;')
        self.hold_values.setText('Expand Mean：未取得 / Hold Gap判定：待機')
        for bar, text in ((self.measure_progress, '計測待機'), (self.recipe_progress, 'レシピ全体：待機')):
            bar.setValue(0); bar.setFormat(text)
        self.recipe_eta.setText('終了見込み：未開始')

    def start_selected_setup(self):
        if not self.available or self.operation or self.state.active is not None or not self.state.configured:
            return
        index = (0, 3, 5)[self.start_at.currentIndex()]
        self.state.reset()
        self.state.reports.clear()
        self.state.completed = index
        self.conduction_stop_reason = self.piezo_stop_reason = self.quality_stop_reason = ''
        self.gap_applied_raw = None
        self.log('開始工程を選択：' + STEPS[index][0] + '。それ以前の工程は省略（実行済みの確認は利用者）。')
        if index:
            self.selected_setup_index = index
            self.start_job('setup_entry', [SAMPLE_STOP, LOW, BIAS1])
        else:
            self.run_step(0, batch=True)

    def retry_finalize(self):
        if not self.transport or not self.transport.connected:
            self.problem = '終了処理を送信できません。Gatewayの接続を確認してください。切断は行っていません。'
            self.show_stop_alarm(self.problem)
            self.closing = self.disconnecting = False
            return
        if self.engine and self.engine.faulted:
            self.log('状態未確認から終了処理を再試行します。全コマンドの応答確認まで接続を保持します。')
            self.engine = CommandEngine(self.send_command, self.command_result, self.command_accepted)
            self.operation = None
        self.shutdown_error = ''
        self.host_paused = True
        self.host_start_deadline = None
        self.finalize()

    def finalize(self):
        if self.available and not self.operation:
            self.shutdown_confirmed = []
            self.auto_measure = False
            self.recipe_pending = []
            self.start_job('finalize', finalize_commands())

    def manual(self, name):
        rate = (10, 50, 100)[self.rate.currentIndex()]
        commands = {'Volt 0': [BIAS0, EP0], 'Go0 Point': [GO0], 'Volt 0.1': [BIAS1],
                    'Low 10K': [SAMPLE_STOP, LOW],
                    'High 測定': [BIAS0, SAMPLE_STOP, high(rate), BIAS1],
                    '測定データ停止': [SAMPLE_STOP]}[name]
        if self.available and not self.operation:
            if name == 'Go0 Point' and not self.confirm_zero_move():
                return
            self.state.reset()
            self.start_job('manual', commands)

    def command_result(self, result, message):
        operation, self.operation = self.operation, None
        closing_requested = self.closing
        if operation == 'baseline' and self.baseline_current is not None:
            self.baseline_current.fail(message or '取得を中断しました')
        if result not in ('success', 'stopped'):
            if operation == 'finalize' or closing_requested:
                self.shutdown_error = message or '終了処理の成功を確認できませんでした。'
                # Keep the UI and connection open after a failed cleanup.
            self.reset_pending = False
            self.hold_lamp.setText('● 判定なし：操作失敗・状態未確認')
            self.hold_lamp.setStyleSheet('font-size: 22px; color: #8291A5;')
            if self.recipe_started_at is not None:
                self.recipe_progress.setFormat('レシピ停止：エラー')
                self.recipe_started_at = None
            self.auto_measure = False
            self.recipe_pending = []
            self.measure_deadline = None
            self.timed_finish = False
            report = self.state.reports.get(self.state.active)
            if report is not None and '装置側でキャンセルされました' in message:
                terminal = ('ExpandGap canceled.', 'HoldGap canceled.', 'canceled.', 'canceld!')
                context = [line for line in report.logs
                           if line.strip() and not line.startswith('Debug  ')
                           and not any(marker in line for marker in terminal)]
                if context:
                    message += '\nキャンセル直前の装置ログ：' + ' / '.join(context[-3:])
                else:
                    message += '\n装置からキャンセル理由の詳細ログは通知されませんでした。'
            if report is not None:
                report.finish('状態未確認：' + message if result == 'uncertain' else '失敗：' + message)
            if result == 'uncertain' or operation == 'gap_target':
                self.gap_applied_raw = None
            self.state.stop()
            if operation == 'settings' or result == 'uncertain':
                self.state.reset()
                self.state.configured = False
                if self.setting_path:
                    self.file_label.setText(self.setting_path.name + ' / 適用状態未確認')
            self.problem = ('状態未確認：' if result == 'uncertain' else '操作失敗：') + message
            if operation == 'finalize':
                self.problem += '\n終了処理の確認済み：' + ('、'.join(self.shutdown_confirmed) or 'なし')
                self.problem += '\n終了処理は未完了です。接続を保持しています。「終了処理して切断」で再試行、「終了」で再試行またはUIのみ終了を選べます。'
            self.show_stop_alarm(self.problem)
            self.log(self.problem)
            self.closing = self.disconnecting = False
        elif operation == 'settings':
            self.state.configured = True
            self.file_label.setText(self.setting_path.name + ' / 適用済み')
            self.log('設定ファイルの全コマンド成功を確認しました。')
            self.scroll_batch_controls()
        elif operation == 'step':
            self.finish_live_step()
        elif operation == 'setup_entry':
            self.operation = 'setup_entry_host'
            self.setup_entry_deadline = time.monotonic() + 3
            self.log('途中開始：Bias印加後の新しい電流データを待っています。')
        elif operation == 'gap_target':
            self.log(describe_raw(self.gap_applied_raw) + ' / 設定成功応答を確認しました。準備工程は保持します。')
            if not self.auto_measure:
                self.scroll_recipe_controls()
            if self.auto_measure: QTimer.singleShot(0, lambda: self.measure() if self.auto_measure else None)
        elif operation == 'resume_sampling':
            if self.auto_measure:
                self.operation = 'await_piezo_host'
                QTimer.singleShot(0, self.expand_after_host)
        elif operation == 'finalize':
            self.alarm_status.setText('正常')
            self.alarm_status.setStyleSheet('background: #123D32; color: #6EF0B1; font-size: 18px; font-weight: bold; padding: 10px;')
            self.shutdown_error = ''
            self.state.reset()
            self.reset_measurement_display()
            self.reset_pending = False
            self.touched = False
            self.log('終了処理が完了しました。')
            if self.closing:
                self.allow_close = True
                QTimer.singleShot(0, self.close)
            elif self.disconnecting:
                QTimer.singleShot(0, self.disconnect)
        elif operation == 'timed_cleanup':
            if self.closing or self.disconnecting or self.reset_pending:
                self.host_paused = True
                self.timed_finish = False
                self.recipe_pending = []
                QTimer.singleShot(0, self.finalize)
                self.refresh()
                return
            self.state.completed = 10
            self.host_paused = True
            self.timed_finish = False
            self.auto_measure = False
            self.measure_progress.setValue(1000)
            self.measure_progress.setFormat('計測完了（停止確認済み）')
            self.problem = '計測完了：指定時間が経過し、Hold Gapとデータ取得の停止を確認しました。'
            self.log(self.problem)
            if self.recipe_pending:
                QTimer.singleShot(0, self.next_recipe)
            else:
                if self.recipe_started_at is not None:
                    self.recipe_progress.setValue(1000)
                    self.recipe_progress.setFormat('レシピ全条件完了')
                    self.recipe_started_at = None
                QTimer.singleShot(0, lambda: QMessageBox.information(self, '計測完了', '計測が完了しました。レシピを設定して再実行できます。'))
        elif operation == 'quality_cleanup':
            self.host_paused = True
            self.state.completed = 10
            self.problem = self.quality_stop_reason + '。Hold Gap・データ取得の停止確認済み。'
            self.log(self.problem)
            if self.closing or self.disconnecting or self.reset_pending:
                QTimer.singleShot(0, self.finalize)
        elif operation == 'piezo_cleanup':
            self.host_paused = True
            self.problem = self.piezo_stop_reason + '。工程・データ取得の停止確認済み。'
            self.log(self.problem)
            if self.closing or self.disconnecting or self.reset_pending:
                QTimer.singleShot(0, self.finalize)
        elif operation in ('stop', 'measure'):
            reason = self.conduction_stop_reason or self.piezo_stop_reason or self.quality_stop_reason
            if reason:
                self.show_stop_alarm(reason + '。工程停止確認済み。原因を確認し、リセットしてください。')
            self.measure_deadline = None
            report = self.state.reports.get(self.state.active)
            if self.conduction_stop_reason:
                if report is not None:
                    report.finish(self.conduction_stop_reason + '。中断・停止確認済み。')
                self.problem = self.conduction_stop_reason + '。中断・停止確認済み。'
            if self.piezo_stop_reason and report is not None:
                report.finish(self.piezo_stop_reason + '。中断・停止確認済み。')
            self.state.stop()
            self.log('工程・測定の終了を確認しました。')
            if self.reset_pending or self.closing or self.disconnecting:
                QTimer.singleShot(0, self.finalize)
            elif operation == 'stop' and self.piezo_stop_reason:
                self.start_job('piezo_cleanup', [SAMPLE_STOP])
            elif operation == 'stop' and self.quality_stop_reason:
                self.start_job('quality_cleanup', [SAMPLE_STOP])
            elif operation == 'stop' and self.timed_finish:
                self.start_job('timed_cleanup', [SAMPLE_STOP])
            else:
                self.timed_finish = False
        self.refresh()

    def expand_after_host(self):
        if self.operation == 'await_piezo_host' and self.available and self.host_recent:
            self.operation = None
            if self.auto_measure:
                self.run_step(10)

    def update_plots(self):
        if not self.live:
            return super().update_plots()
        if not self.host_dirty or not self.telemetry.latest:
            return
        self.host_dirty = False
        frame = self.telemetry.latest
        x, values = self.telemetry.current_plot()
        self.current_plot.setLabel('left', 'Current', units=frame['unit'])
        self.current_plot.getPlotItem().setDownsampling(auto=True, mode='peak')
        self.current_plot.getPlotItem().setClipToView(True)
        self.current_curve.setData(x, values)
        if len(values):
            median = float(np.median(values))
            rms = float(np.sqrt(np.mean(values ** 2)))
            noise = float(np.std(values))
            self.median_curve.setData([x[0], x[-1]], [median, median])
            stats = f'Median {median:.3f} / RMS {rms:.3f} / Noise RMS {noise:.3f} {frame["unit"]}（表示区間）'
        else:
            self.median_curve.setData([], [])
            stats = '電流サンプルなし / HW情報のみ'
        self.stats.setText(f'{frame["rate"] / 1000:g} kHz · Bias {frame["bias"]:.1f} V · {stats}\n'
                           f'フレーム不連続 {self.telemetry.gaps} / 表示キュー欠落 {self.transport.host_dropped}')
        data = np.array(self.telemetry.hardware)
        self.motor_curve.setData(data[:, 0], data[:, 1], connect='finite')
        self.piezo_curve.setData(data[:, 0], data[:, 2], connect='finite')
        self.meters['CURRENT'].setText(f'{frame["current"]:.3f} {frame["unit"]}')
        self.meters['MOTOR'].setText(f'{frame["motor"]:.2f} µm')
        self.meters['PIEZO'].setText(f'{frame["piezo"]:.0f} nm')

    def closeEvent(self, event):
        if not self.live:
            return super().closeEvent(event)
        if self.allow_close or not self.touched:
            self.io_timer.stop()
            self.plot_timer.stop()
            if self.transport:
                self.transport.close()
            event.accept()
            return
        if self.shutdown_error and not self.operation:
            dialog = QMessageBox(self)
            dialog.setWindowTitle('終了処理は未完了です')
            dialog.setIcon(QMessageBox.Icon.Warning)
            dialog.setText(self.shutdown_error + '\n確認済み：' + ('、'.join(self.shutdown_confirmed) or 'なし') +
                           '\nUIのみ終了しても装置・Gatewayの停止は行いません。装置状態はGatewayで確認してください。')
            retry = dialog.addButton('終了処理を再試行', QMessageBox.ButtonRole.AcceptRole)
            ui_close = dialog.addButton('UIのみ終了', QMessageBox.ButtonRole.DestructiveRole)
            cancel = dialog.addButton('キャンセル', QMessageBox.ButtonRole.RejectRole)
            dialog.setDefaultButton(cancel)
            dialog.setEscapeButton(cancel)
            dialog.exec()
            if dialog.clickedButton() == ui_close:
                self.allow_close = True
                self.closeEvent(event)
            else:
                event.ignore()
                if dialog.clickedButton() == retry:
                    self.closing = True
                    self.retry_finalize()
            return
        if self.transport and self.transport.connected and not self.available:
            event.ignore()
            self.closing = True
            self.retry_finalize()
            return
        if self.shutdown_error or not self.available:
            answer = QMessageBox.warning(self, '装置状態は未確認です',
                (self.shutdown_error or '通信できないため終了処理を確認できません。') +
                '\nGatewayで装置状態を確認してください。\nUIだけを閉じますか？（装置・Gatewayの停止は行いません）',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer == QMessageBox.StandardButton.Yes:
                self.allow_close = True
                self.closeEvent(event)
            else:
                event.ignore()
            return
        event.ignore()
        self.closing = True
        if self.operation in ('stop', 'finalize', 'piezo_cleanup', 'quality_cleanup', 'timed_cleanup'):
            self.log('現在の停止処理の応答確認後に終了します。')
            return
        if self.operation or self.state.active is not None or self.state.measurement:
            self.stop()
        else:
            self.finalize()
