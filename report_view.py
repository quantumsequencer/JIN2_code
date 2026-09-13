"""Durable per-run reports and exploratory plots of recorded step values."""
import csv
import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, QPlainTextEdit,
    QPushButton, QLabel, QComboBox, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox)

NAMES = {4: 'First Cut', 5: 'Motor Training', 6: 'Piezo Training', 10: 'Expand Gap'}
ROOT = Path(__file__).resolve().parent / 'reports'


def numeric_rows(step, report):
    if step == 10:
        return []
    rows = []
    for i in range(1, 4) if step == 4 else range(10):
        if step == 4:
            value = report['fc_moves'].get(str(i), report['fc_moves'].get(i))
            rows.append([i, None, None, None, value])
        else:
            pair = report['training_positions'].get(str(i), report['training_positions'].get(i, {}))
            up, down = pair.get('Up'), pair.get('Down')
            delta = down - up if up is not None and down is not None else None
            rows.append([i + 1, up, down, delta, abs(delta) if delta is not None else None])
    return rows


def save_report(step, report, root=ROOT):
    root.mkdir(parents=True, exist_ok=True)
    token = report.started_at.replace('-', '').replace(':', '').replace(' ', '_') + f'_{step}_{uuid4().hex[:12]}'
    data = {'version': 1, 'step': step, 'report': asdict(report)}
    base = root / token
    base.with_suffix('.txt').write_text(report.describe(), encoding='utf-8')
    with base.with_suffix('.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['run', 'step', 'started_at', 'status', 'settings', 'elapsed_seconds', 'unit', 'cycle', 'up', 'down', 'down_minus_up', 'move_or_amplitude'])
        for row in numeric_rows(step, data['report']):
            writer.writerow([token, NAMES[step], report.started_at, report.status, report.setting,
                             report.elapsed, 'nm' if step == 6 else 'um', *row])
    temporary = base.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2), encoding='utf-8')
    temporary.replace(base.with_suffix('.json'))
    return base.with_suffix('.json')


def load_reports(root=ROOT):
    records, errors = [], []
    for path in sorted(root.glob('*.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if data['version'] != 1 or data['step'] not in NAMES:
                raise ValueError('未対応の形式')
            report = data['report']
            for key in ('status', 'setting', 'started_at', 'elapsed', 'fc_moves', 'training_positions'):
                report[key]
            numeric_rows(data['step'], report)
            records.append(data)
        except (ValueError, KeyError, TypeError, OSError) as error:
            errors.append(f'{path.name}: {error}')
    return records, errors


class ReportDialog(QDialog):
    def __init__(self, step, report, parent=None):
        super().__init__(parent)
        self.setWindowTitle(NAMES.get(step, '工程') + ' / レポート')
        self.resize(950, 720)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        text = QPlainTextEdit()
        text.setReadOnly(True)
        text.setPlainText(report.describe())
        if step in (4, 5, 6):
            page = QWidget()
            pl = QVBoxLayout(page)
            unit = 'nm' if step == 6 else 'µm'
            pl.addWidget(QLabel('First Cutはログのmove値、Trainingは到達ログ処理時の近似位置です。欠損は空欄。'))
            rows = numeric_rows(step, asdict(report))
            plot = pg.PlotWidget()
            plot.setLabel('bottom', '回')
            plot.setLabel('left', '移動量 / 位置', units=unit)
            plot.addLegend()
            for col, name, color in ([(4, 'Motor move', '#24C8DB')] if step == 4 else
                                     [(1, 'Up', '#24C8DB'), (2, 'Down', '#F5D547'), (4, '振幅', '#39D98A')]):
                plot.plot([r[0] for r in rows], [r[col] if r[col] is not None else np.nan for r in rows],
                          pen=color, symbol='o', name=name, connect='finite')
            pl.addWidget(plot)
            table = QTableWidget(len(rows), 5)
            table.setHorizontalHeaderLabels(['回', f'Up ({unit})', f'Down ({unit})', f'差分 ({unit})', f'move / 振幅 ({unit})'])
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem('' if value is None else f'{value:g}'))
            table.setEditTriggers(QTableWidget.NoEditTriggers)
            table.horizontalHeader().setStretchLastSection(True)
            pl.addWidget(table)
            tabs.addTab(page, 'グラフ・数値')
        tabs.addTab(text, '詳細・ログ')
        export = QPushButton('レポートをテキスト保存')
        def save_text():
            path, _ = QFileDialog.getSaveFileName(self, 'レポートを保存', 'report.txt', 'Text (*.txt)')
            if path:
                try:
                    Path(path).write_text(report.describe(), encoding='utf-8')
                except OSError as error:
                    QMessageBox.warning(self, '保存失敗', str(error))
        export.clicked.connect(save_text)
        layout.addWidget(export)
        close = QPushButton('閉じる')
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('工程レポート履歴・統計')
        self.resize(1000, 720)
        layout = QVBoxLayout(self)
        self.records, errors = load_reports()
        self.step = QComboBox()
        for key, value in NAMES.items(): self.step.addItem(value, key)
        self.setting = QComboBox()
        self.setting.addItem('すべての設定（混在）', None)
        for name in sorted({r['report']['setting'] for r in self.records}): self.setting.addItem(name, name)
        self.metric_choice = QComboBox()
        self.metric_choice.addItems(['各回のmove / 振幅', '所要時間（秒）'])
        for widget in (self.step, self.setting, self.metric_choice): layout.addWidget(widget)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.plot = pg.PlotWidget()
        layout.addWidget(self.plot)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        layout.addWidget(QLabel(f'正常完了した実行のみを統計対象にします。欠損を0として扱いません。読込失敗 {len(errors)}件'))
        if errors:
            detail = QPlainTextEdit('\n'.join(errors)); detail.setReadOnly(True); layout.addWidget(detail)
        for widget in (self.step, self.setting, self.metric_choice): widget.currentIndexChanged.connect(self.refresh)
        self.table.cellDoubleClicked.connect(self.open_record)
        close = QPushButton('閉じる'); close.clicked.connect(self.accept); layout.addWidget(close)
        self.refresh()

    def refresh(self):
        self.selected = [r for r in self.records if r['step'] == self.step.currentData()
                         and (self.setting.currentData() is None or r['report']['setting'] == self.setting.currentData())]
        self.plot.clear()
        values = []
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(['開始日時（ダブルクリックで詳細）', '結果', '設定', '所要秒'])
        self.table.setRowCount(len(self.selected))
        for i, record in enumerate(self.selected):
            r = record['report']
            for j, value in enumerate((r['started_at'], r['status'], r['setting'], r['elapsed'])):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))
            if r['status'] != '完了': continue
            if self.metric_choice.currentIndex() == 1:
                self.plot.plot([i + 1], [r['elapsed']], symbol='o', pen=None)
                values.append(r['elapsed'])
            else:
                rows = numeric_rows(record['step'], r)
                ys = [row[4] if row[4] is not None else np.nan for row in rows]
                self.plot.plot([row[0] for row in rows], ys, pen=pg.intColor(i), symbol='o', connect='finite')
                values.extend(v for v in ys if np.isfinite(v))
        unit = 's' if self.metric_choice.currentIndex() else 'nm' if self.step.currentData() == 6 else 'µm'
        self.plot.setLabel('left', '所要時間' if self.metric_choice.currentIndex() else 'move / 振幅', units=unit)
        self.plot.setLabel('bottom', '履歴順' if self.metric_choice.currentIndex() else '回')
        if values:
            a = np.array(values)
            sd = f'{a.std(ddof=1):.4g}' if len(a) > 1 else '—'
            self.summary.setText(f'履歴 {len(self.selected)}件 / 有効値 {len(a)}点 / 平均 {a.mean():.4g} / 中央値 {np.median(a):.4g} / 標本SD {sd} / 最小 {a.min():.4g} / 最大 {a.max():.4g} {unit}\n各回の統計は全実行の有効な回をまとめた記述統計です。')
        else:
            self.summary.setText('統計対象の有効データがありません。')
        self.table.resizeColumnsToContents()

    def open_record(self, row, column):
        from step_report import StepReport
        record = self.selected[row]
        data = dict(record['report'])
        data['fc_moves'] = {int(k): v for k, v in data['fc_moves'].items()}
        data['training_positions'] = {int(k): v for k, v in data['training_positions'].items()}
        ReportDialog(record['step'], StepReport(**data), self).exec()
