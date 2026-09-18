"""Live current-versus-Piezo plot used while Calibration is running."""
from collections import deque

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QVBoxLayout


class CalibrationPlotData:
    """Bounded raw log-current points plus consecutive 200-point averages."""

    def __init__(self, block_size=200, max_raw_points=200_000):
        self.block_size = block_size
        self.raw_piezo = deque(maxlen=max_raw_points)
        self.raw_log_current = deque(maxlen=max_raw_points)
        self.block_piezo = deque(maxlen=max_raw_points // block_size)
        self.block_log_current = deque(maxlen=max_raw_points // block_size)
        self._pending_piezo = []
        self._pending_log_current = []

    def clear(self):
        self.raw_piezo.clear()
        self.raw_log_current.clear()
        self.block_piezo.clear()
        self.block_log_current.clear()
        self._pending_piezo.clear()
        self._pending_log_current.clear()

    def feed(self, piezo, currents, unit='A'):
        values = np.asarray(currents, dtype=float)
        valid = np.isfinite(values) & (values != 0)
        scales = {'A': 1.0, 'mA': 1e-3, 'µA': 1e-6, 'uA': 1e-6,
                  'nA': 1e-9, 'pA': 1e-12}
        logs = np.log10(np.abs(values[valid]) * scales.get(unit, 1.0))
        if not len(logs):
            return
        piezos = np.full(len(logs), float(piezo))
        self.raw_piezo.extend(piezos)
        self.raw_log_current.extend(logs)
        self._pending_piezo.extend(piezos)
        self._pending_log_current.extend(logs)
        while len(self._pending_log_current) >= self.block_size:
            px = self._pending_piezo[:self.block_size]
            cy = self._pending_log_current[:self.block_size]
            del self._pending_piezo[:self.block_size]
            del self._pending_log_current[:self.block_size]
            self.block_piezo.append(float(np.mean(px)))
            self.block_log_current.append(float(np.mean(cy)))


class CalibrationPlotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = CalibrationPlotData()
        self.setWindowTitle('Calibration：電流－Piezo リアルタイムグラフ')
        self.resize(900, 620)
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.raw_check = QCheckBox('全データ')
        self.raw_check.setChecked(True)
        self.block_check = QCheckBox('200データポイント平均')
        self.block_check.setChecked(True)
        self.status = QLabel('Calibration待機中')
        controls.addWidget(self.raw_check)
        controls.addWidget(self.block_check)
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
        layout.addWidget(self.plot)
        self.raw_check.toggled.connect(self.refresh)
        self.block_check.toggled.connect(self.refresh)

    def clear(self):
        self.data.clear()
        self.refresh(active=False)

    def feed(self, frame):
        self.data.feed(frame['piezo'], frame.get('values', ()), frame.get('unit', 'A'))

    def refresh(self, checked=False, active=True):
        raw_x = np.asarray(self.data.raw_piezo)
        raw_y = np.asarray(self.data.raw_log_current)
        block_x = np.asarray(self.data.block_piezo)
        block_y = np.asarray(self.data.block_log_current)
        self.raw_curve.setData(raw_x, raw_y) if self.raw_check.isChecked() else self.raw_curve.setData([], [])
        self.block_curve.setData(block_x, block_y) if self.block_check.isChecked() else self.block_curve.setData([], [])
        state = '計測中' if active else 'Calibration待機中'
        self.status.setText(f'{state} / 全点 {len(raw_y):,} / 200点平均 {len(block_y):,}')
