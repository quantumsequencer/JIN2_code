"""Distance/time CSV recipes. Validation precedes execution."""
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QFileDialog, QMessageBox, QLabel, QLineEdit,
    QDoubleSpinBox, QCheckBox)
from gap_target import model_target
RECIPE_ROOT = Path(__file__).resolve().parent / 'recipe'
RECIPE_STATE_PATH = RECIPE_ROOT / 'last_used_recipe.json'


def load_last_used():
    """Load the recipe selected with 'use' in the previous session."""
    try:
        return validate(json.loads(RECIPE_STATE_PATH.read_text(encoding='utf-8'))['rows'])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return []


def save_last_used(rows):
    rows = validate(rows)
    RECIPE_ROOT.mkdir(parents=True, exist_ok=True)
    RECIPE_STATE_PATH.write_text(
        json.dumps({'rows': rows}, ensure_ascii=False, indent=2), encoding='utf-8')


def validate(rows):
    result = []
    for index, row in enumerate(rows, 1):
        if len(row) != 2:
            raise ValueError(f'{index}行目：距離と時間の2列が必要です。')
        d, minutes = map(float, row)
        if not math.isfinite(d) or not 0.001 <= d <= 10 or not math.isfinite(minutes) or not 0.01 <= minutes <= 1440:
            raise ValueError(f'{index}行目：距離0.001〜10 nm、時間0.01〜1440 minで入力してください。')
        if abs(d - round(d, 3)) > 1e-9 or abs(minutes - round(minutes, 2)) > 1e-9:
            raise ValueError(f'{index}行目：距離は小数3桁、時間は小数2桁までです。')
        model_target(d)
        result.append((d, minutes))
    if not result:
        raise ValueError('1行以上入力してください。')
    return result


class RecipeDialog(QDialog):
    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.setWindowTitle('計測レシピ')
        self.resize(520, 500)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('先頭条件は待機中のExpand Gap基準値を使い、目標電流設定→Hold Gapを実行します。\n2条件目以降はExpand Gapから実行します。'))
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['距離 (nm)', '時間 (min)'])
        layout.addWidget(self.table)
        self.suffix = QLineEdit()
        self.suffix.setPlaceholderText('保存名の任意文字（日時は自動付与）')
        layout.addWidget(self.suffix)
        for row in rows or [(0.6, 1)]: self.add(row)
        for text, callback in [('CSV読込', self.load),
                               ('目標電流を表示', self.show_targets),
                               ('行追加', lambda: self.add((0.6, 1))),
                               ('選択行削除', lambda: self.table.removeRow(self.table.currentRow())),
                               ('CSV保存', self.save), ('このレシピを使用', self.use), ('閉じる', self.reject)]:
            b = QPushButton(text); b.clicked.connect(callback); layout.addWidget(b)

    def show_targets(self):
        try:
            rows = self.rows()
        except ValueError as error:
            QMessageBox.warning(self, '入力を確認', str(error))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('レシピの目標電流')
        dialog.resize(620, 400)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels(['距離 (nm)', '時間 (min)', '目標電流 (pA)', '送信値'])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        for index, (distance, minutes) in enumerate(rows):
            current, raw = model_target(distance)
            for column, value in enumerate((f'{distance:.3f}', f'{minutes:.2f}', f'{current:.6f}', f'0x{raw:08X}')):
                table.setItem(index, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        note = QLabel('各条件のExpand Gap・基準電流取得後に自動適用します。\n距離は暫定モデル上の参考値です。Expand Meanは送信値に加算しません。')
        note.setWordWrap(True)
        layout.addWidget(note)
        close = QPushButton('閉じる')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def add(self, row):
        n = self.table.rowCount(); self.table.insertRow(n)
        for i, v in enumerate(row): self.table.setItem(n, i, QTableWidgetItem(str(v)))

    def rows(self):
        return validate([[self.table.item(i, j).text() if self.table.item(i, j) else '' for j in range(2)] for i in range(self.table.rowCount())])

    def use(self):
        try: self.result_rows = self.rows()
        except ValueError as e:
            QMessageBox.warning(self, '入力を確認', str(e)); return
        try: save_last_used(self.result_rows)
        except OSError as e:
            QMessageBox.warning(self, '保存失敗', str(e)); return
        self.accept()

    def load(self):
        path, _ = QFileDialog.getOpenFileName(self, 'レシピ読込', str(RECIPE_ROOT), 'CSV (*.csv)')
        if not path: return
        try:
            with Path(path).open(encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                if next(reader, None) != ['distance_nm', 'duration_min']: raise ValueError('ヘッダーが不正です。')
                rows = validate(list(reader))
            self.table.setRowCount(0)
            for row in rows: self.add(row)
        except (OSError, ValueError) as e: QMessageBox.warning(self, '読込失敗', str(e))

    def save(self):
        try: rows = self.rows()
        except ValueError as e:
            QMessageBox.warning(self, '入力を確認', str(e)); return
        try:
            suffix = self.suffix.text().strip()
            if re.search(r'[<>:"/\\|?*\x00-\x1f]', suffix):
                raise ValueError('保存名に使用できない文字が含まれています。')
            RECIPE_ROOT.mkdir(parents=True, exist_ok=True)
            path = RECIPE_ROOT / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + ('_' + suffix if suffix else '') + '.csv')
            with path.open('x', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f); writer.writerow(['distance_nm', 'duration_min']); writer.writerows(rows)
            QMessageBox.information(self, '保存完了', str(path))
        except (OSError, ValueError) as e: QMessageBox.warning(self, '保存失敗', str(e))


class RunningRecipeDialog(QDialog):
    """Read-only view of a running recipe with safe tail-only additions."""
    def __init__(self, rows, current_number, parent=None):
        super().__init__(parent)
        self.setWindowTitle('実行中レシピの確認・追加')
        self.resize(620, 480)
        self.result_rows = []
        layout = QVBoxLayout(self)
        note = QLabel('実行済み・計測中・実行待ちの条件は変更できません。新しい条件は末尾にだけ追加できます。')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['状態', '距離 (nm)', '時間 (min)'])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)
        for index, row in enumerate(rows, 1):
            status = '完了' if index < current_number else ('計測中' if index == current_number else '実行待ち')
            self._add_table_row(status, row)

        add_row = QHBoxLayout()
        self.distance = QDoubleSpinBox()
        self.distance.setDecimals(3)
        self.distance.setRange(0.001, 10.0)
        self.distance.setValue(0.6)
        self.distance.setSuffix(' nm')
        self.minutes = QDoubleSpinBox()
        self.minutes.setDecimals(2)
        self.minutes.setRange(0.01, 1440.0)
        self.minutes.setValue(1.0)
        self.minutes.setSuffix(' min')
        add = QPushButton('追加候補へ')
        add.clicked.connect(self.add_candidate)
        for widget in (QLabel('末尾に追加'), self.distance, self.minutes, add):
            add_row.addWidget(widget)
        layout.addLayout(add_row)
        self.persist = QCheckBox('保存レシピにも追加する')
        layout.addWidget(self.persist)
        apply_button = QPushButton('追加を反映')
        apply_button.clicked.connect(self.apply_additions)
        layout.addWidget(apply_button)
        close = QPushButton('閉じる')
        close.clicked.connect(self.reject)
        layout.addWidget(close)

    def _add_table_row(self, status, row):
        index = self.table.rowCount()
        self.table.insertRow(index)
        values = (status, f'{row[0]:.3f}', f'{row[1]:g}')
        for column, value in enumerate(values):
            self.table.setItem(index, column, QTableWidgetItem(value))

    def add_candidate(self):
        row = validate([(self.distance.value(), self.minutes.value())])[0]
        self.result_rows.append(row)
        self._add_table_row('追加候補', row)
        self.table.scrollToBottom()

    def apply_additions(self):
        if not self.result_rows:
            QMessageBox.information(self, 'レシピ', '追加する条件がありません。')
            return
        self.accept()
