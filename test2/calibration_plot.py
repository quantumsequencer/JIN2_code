"""Live current-versus-Piezo plot used while Calibration is running."""
from collections import deque
from math import log

import numpy as np
import pyqtgraph as pg
from tunneling_model import WORK_FUNCTION_EV, barrier_decay_per_nm
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)


DIRECTION_COLORS = {-1: '#4DB6FF', 0: '#AAB4C0', 1: '#FF6B8A'}
PASS_COLORS = (
    '#F5D547', '#4DB6FF', '#FF6B8A', '#71D99E', '#B58CFF',
    '#FF9F43', '#56D6D0', '#E879F9',
)

AU_WORK_FUNCTION_EV = WORK_FUNCTION_EV
REFERENCE_GAP_SENSITIVITY_PM_PER_UM = 40.0


def gap_sensitivity_from_slope(slope_log10_current_per_nm):
    """Convert a calibration slope to modeled gap sensitivity in pm/um."""
    beta_per_nm = barrier_decay_per_nm()
    return abs(float(slope_log10_current_per_nm)) * log(10) / beta_per_nm * 1e6


class CalibrationPlotData:
    """Bounded raw log-current points plus consecutive 200-point averages."""

    def __init__(self, block_size=200, max_raw_points=200_000,
                 wait_for_first_reversal=False):
        self.block_size = block_size
        self.wait_for_first_reversal = wait_for_first_reversal
        self.raw_piezo = deque(maxlen=max_raw_points)
        self.raw_log_current = deque(maxlen=max_raw_points)
        self.block_piezo = deque(maxlen=max_raw_points // block_size)
        self.block_log_current = deque(maxlen=max_raw_points // block_size)
        self.block_direction = deque(maxlen=max_raw_points // block_size)
        self.block_pass = deque(maxlen=max_raw_points // block_size)
        self._pending_piezo = []
        self._pending_log_current = []
        self._pending_direction = []
        self._pending_pass = []
        self._last_piezo = None
        self._direction = 0
        self._pass_number = 1
        self._measurement_started = not wait_for_first_reversal

    def clear(self):
        self.raw_piezo.clear()
        self.raw_log_current.clear()
        self.block_piezo.clear()
        self.block_log_current.clear()
        self.block_direction.clear()
        self.block_pass.clear()
        self._pending_piezo.clear()
        self._pending_log_current.clear()
        self._pending_direction.clear()
        self._pending_pass.clear()
        self._last_piezo = None
        self._direction = 0
        self._pass_number = 1
        self._measurement_started = not self.wait_for_first_reversal

    def feed(self, piezo, currents, unit='A'):
        piezo = float(piezo)
        reversed_direction = False
        if self._last_piezo is not None:
            delta = piezo - self._last_piezo
            new_direction = 1 if delta > 0 else -1 if delta < 0 else self._direction
            if self._direction and new_direction and new_direction != self._direction:
                self._pass_number += 1
                reversed_direction = True
            if new_direction:
                self._direction = new_direction
        self._last_piezo = piezo
        if reversed_direction:
            self._measurement_started = True
        if not self._measurement_started:
            return
        values = np.asarray(currents, dtype=float)
        valid = np.isfinite(values) & (values != 0)
        scales = {'A': 1.0, 'mA': 1e-3, 'µA': 1e-6, 'uA': 1e-6,
                  'nA': 1e-9, 'pA': 1e-12}
        logs = np.log10(np.abs(values[valid]) * scales.get(unit, 1.0))
        if not len(logs):
            return
        piezos = np.full(len(logs), piezo)
        self.raw_piezo.extend(piezos)
        self.raw_log_current.extend(logs)
        self._pending_piezo.extend(piezos)
        self._pending_log_current.extend(logs)
        self._pending_direction.extend([self._direction] * len(logs))
        self._pending_pass.extend([self._pass_number] * len(logs))
        while len(self._pending_log_current) >= self.block_size:
            px = self._pending_piezo[:self.block_size]
            cy = self._pending_log_current[:self.block_size]
            directions = self._pending_direction[:self.block_size]
            passes = self._pending_pass[:self.block_size]
            del self._pending_piezo[:self.block_size]
            del self._pending_log_current[:self.block_size]
            del self._pending_direction[:self.block_size]
            del self._pending_pass[:self.block_size]
            self.block_piezo.append(float(np.mean(px)))
            self.block_log_current.append(float(np.mean(cy)))
            self.block_direction.append(max(set(directions), key=directions.count))
            self.block_pass.append(max(set(passes), key=passes.count))

    def linear_fit(self):
        """Return the common within-pass slope, centered over all scan points.

        Separate scans can have different vertical offsets.  Removing each
        pass mean before calculating the slope prevents those offsets from
        flattening the fitted line.
        """
        block_x = np.asarray(self.block_piezo, dtype=float)
        block_y = np.asarray(self.block_log_current, dtype=float)
        passes = np.asarray(self.block_pass, dtype=int)
        if len(block_x) >= 2:
            usable = np.ones(len(block_x), dtype=bool)
            if len(block_y) >= 3:
                saturated = block_y >= np.max(block_y) - 0.005
                if np.count_nonzero(saturated) >= 3:
                    usable &= ~saturated

            centered_x = []
            centered_y = []
            for pass_number in np.unique(passes[usable]):
                in_pass = usable & (passes == pass_number)
                px = block_x[in_pass]
                py = block_y[in_pass]
                if len(px) >= 2 and np.ptp(px) > 0:
                    centered_x.extend(px - np.mean(px))
                    centered_y.extend(py - np.mean(py))
            if centered_x:
                cx = np.asarray(centered_x)
                cy = np.asarray(centered_y)
                denominator = float(np.dot(cx, cx))
                if denominator:
                    slope = float(np.dot(cx, cy) / denominator)
                    intercept = float(np.mean(block_y[usable])
                                      - slope * np.mean(block_x[usable]))
                    return slope, intercept

        # Keep a useful fit while fewer than one complete 200-point block is
        # available at the beginning of measurement.
        x, y, _ = self.fit_points()
        if len(x) < 2 or np.ptp(x) == 0:
            return None
        slope, intercept = np.polyfit(x, y, 1)
        return float(slope), float(intercept)

    def fit_points(self):
        """Return fit input and the number of upper-limit points removed.

        Calibration holds near its current ceiling rather than returning one
        bit-identical raw value. Detect that horizontal band from consecutive
        block averages, then remove all raw samples belonging to those blocks.
        """
        x = np.asarray(self.raw_piezo, dtype=float)
        y = np.asarray(self.raw_log_current, dtype=float)
        block_y = np.asarray(self.block_log_current, dtype=float)
        if not len(y) or len(block_y) < 3:
            return x, y, 0

        # 0.005 decade is about 1.2 % in current: wide enough for measurement
        # noise, but much narrower than the changing-current part of a scan.
        saturated_blocks = block_y >= np.max(block_y) - 0.005
        if np.count_nonzero(saturated_blocks) < 3:
            return x, y, 0

        completed_points = len(block_y) * self.block_size
        # raw_* may also contain the not-yet-averaged tail.
        completed_points = min(completed_points, len(y))
        block_count = completed_points // self.block_size
        saturated_blocks = saturated_blocks[-block_count:]
        saturated = np.repeat(saturated_blocks, self.block_size)
        usable = np.ones(len(y), dtype=bool)
        usable[:len(saturated)] = ~saturated
        excluded = int(np.count_nonzero(saturated))
        return x[usable], y[usable], excluded


class CalibrationPlotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # The first one-way motion only brings current to the lower limit; the
        # calibration sweep starts when Piezo first reverses direction.
        self.data = CalibrationPlotData(wait_for_first_reversal=True)
        self.color_mode = 0
        self.data_is_active = False
        self.setWindowTitle('Calibration：電流－Piezo リアルタイムグラフ')
        self.resize(900, 620)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.raw_check = QCheckBox('全データ')
        self.raw_check.setChecked(False)
        self.block_check = QCheckBox('200データポイント平均')
        self.block_check.setChecked(True)
        self.color_button = QPushButton()
        self._update_color_button()
        self.status = QLabel('Calibration待機中')
        controls.addWidget(self.raw_check)
        controls.addWidget(self.block_check)
        controls.addWidget(self.color_button)
        controls.addStretch()
        controls.addWidget(self.status)
        layout.addLayout(controls)
        self.plot = pg.PlotWidget(background='#0E1620')
        self.plot.showGrid(x=True, y=True, alpha=0.15)
        self.plot.setLabel('bottom', 'Piezo', units='nm')
        self.plot.setLabel('left', 'log10(|Current [A]|)')
        self.plot.addLegend(offset=(8, 8))
        self.plot.getPlotItem().setDownsampling(auto=True, mode='peak')
        self.plot.getPlotItem().setClipToView(True)
        self.raw_curve = self.plot.plot(pen=pg.mkPen('#24C8DB', width=1), name='全データ')
        self.block_curve = self.plot.plot(
            pen=None, symbol='o', symbolSize=6,
            symbolBrush='#F5D547', symbolPen=None, name='200点平均')
        self.fit_curve = self.plot.plot(
            pen=pg.mkPen('#FF8C42', width=2), name='走査内共通傾き')
        layout.addWidget(self.plot)
        self.raw_check.toggled.connect(self.refresh)
        self.block_check.toggled.connect(self.refresh)
        self.color_button.clicked.connect(self.cycle_color_mode)

    def _update_color_button(self):
        labels = ('色分け: 単色', '色分け: 方向別', '色分け: 走査回別')
        self.color_button.setText(labels[self.color_mode])

    def cycle_color_mode(self):
        self.color_mode = (self.color_mode + 1) % 3
        self._update_color_button()
        self.refresh(active=self.data_is_active)

    def _block_brushes(self):
        if self.color_mode == 1:
            return [pg.mkBrush(DIRECTION_COLORS[d]) for d in self.data.block_direction]
        if self.color_mode == 2:
            return [pg.mkBrush(PASS_COLORS[(n - 1) % len(PASS_COLORS)])
                    for n in self.data.block_pass]
        return pg.mkBrush(PASS_COLORS[0])

    def clear(self):
        self.data.clear()
        self.refresh(active=False)

    def feed(self, frame):
        self.data.feed(frame['piezo'], frame.get('values', ()), frame.get('unit', 'A'))

    def calibration_metrics(self):
        """Return the latest fitted slope and its modeled gap sensitivity."""
        fit = self.data.linear_fit()
        if fit is None:
            return None
        slope, _ = fit
        return slope, gap_sensitivity_from_slope(slope)

    def refresh(self, checked=False, active=True):
        self.data_is_active = active
        raw_x = np.asarray(self.data.raw_piezo)
        raw_y = np.asarray(self.data.raw_log_current)
        block_x = np.asarray(self.data.block_piezo)
        block_y = np.asarray(self.data.block_log_current)
        self.raw_curve.setData(raw_x, raw_y) if self.raw_check.isChecked() else self.raw_curve.setData([], [])
        if self.block_check.isChecked():
            self.block_curve.setData(block_x, block_y, symbolBrush=self._block_brushes())
        else:
            self.block_curve.setData([], [])
        fit_x_data, _, excluded = self.data.fit_points()
        fit = self.data.linear_fit()
        if fit is None:
            self.fit_curve.setData([], [])
            metric_text = 'Gap Sensitivity --- / 傾き ---'
        else:
            slope, intercept = fit
            fit_x = np.array([np.min(fit_x_data), np.max(fit_x_data)])
            self.fit_curve.setData(fit_x, slope * fit_x + intercept)
            gap_sensitivity = gap_sensitivity_from_slope(slope)
            relative = gap_sensitivity / REFERENCE_GAP_SENSITIVITY_PM_PER_UM
            metric_text = (
                f'Gap Sensitivity {gap_sensitivity:.1f} pm/µm / '
                f'基準 {REFERENCE_GAP_SENSITIVITY_PM_PER_UM:.1f} pm/µm / '
                f'相対 {relative:.2f} x / '
                f'傾き {slope:.6g} log10(A)/nm'
            )
        state = '計測中' if active else 'Calibration待機中'
        color_notes = (
            '',
            ' / 近づく=桃・遠ざかる=青',
            f' / 走査 {max(self.data.block_pass, default=0)}回',
        )
        self.status.setText(
            f'{state} / 全点 {len(raw_y):,} / 200点平均 {len(block_y):,} / '
            f'上限除外 {excluded:,} / {metric_text}{color_notes[self.color_mode]}')
