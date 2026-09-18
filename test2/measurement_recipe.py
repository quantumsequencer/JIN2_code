"""Distance/time CSV recipes. Validation precedes execution."""
import csv
import math
import re
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QFileDialog, QMessageBox, QLabel, QLineEdit)
from gap_target import model_target
RECIPE_ROOT = Path(__file__).resolve().parent / 'recipe'


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
