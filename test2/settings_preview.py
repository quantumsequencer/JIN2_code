"""Searchable settings editor with decimal display and lossless hex values."""
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QPlainTextEdit, QPushButton, QHeaderView,
    QStyledItemDelegate, QFileDialog, QMessageBox, QWidget,
)


CURRENT_RAW_PER_PA = 5825183.6129280003
CURRENT_RAW_PER_PA_DECIMAL = Decimal('5825183.6129280003')
CURRENT_RAW_PER_UA_DECIMAL = Decimal('42781900.799999997')


def current_unit_for(command, group, key, offset):
    """Return the physical unit for current-valued setting arguments."""
    if command == 'mcbj':
        if key == 'threshold' and offset == 0:
            return 'µA'
        if key in ('ROUGH', 'SMOOTH', 'limit') and offset in (0, 1):
            return 'µA'
        if key in ('up_table', 'down_table') and offset == 0:
            return 'µA'
    if command == 'asz':
        if group == 'eg' and key == 'stable_current_range' and offset == 0:
            return 'pA'
        if group == 'hg' and key in ('tunnel_current', 'fb_table') and offset == 0:
            return 'pA'
    return None


def current_divisor(unit):
    return CURRENT_RAW_PER_PA_DECIMAL if unit == 'pA' else CURRENT_RAW_PER_UA_DECIMAL


def format_current(value):
    """Format a physical current with at most three significant digits."""
    text = format(Decimal(value), '.3g')
    if 'e' in text.lower():
        mantissa, exponent = re.split(r'([eE].*)', text, maxsplit=1)[:2]
        return mantissa.rstrip('0').rstrip('.') + exponent
    return text.rstrip('0').rstrip('.') if '.' in text else text


GROUPS = {
    'fc': 'First Cut / 初期切断', 'mt': 'Motor Training / モータートレーニング',
    'pt': 'Piezo Training / ピエゾトレーニング', 'targeting': 'Targeting / 位置調整',
    'ac': 'Auto Cut / 自動切断', 'cal': 'Calibration / 校正',
    'eg': 'Expand Gap / ギャップ拡張', 'hg': 'Hold Gap / ギャップ保持',
}
NAMES = {
    'up_limit': '上昇上限', 'last_down_distance': '最終下降距離',
    'threshold': 'しきい値', 'speed_table': '速度テーブル',
    'ROUGH': 'トレーニング設定（ROUGH）', 'SMOOTH': 'トレーニング設定（SMOOTH）',
    'up_table': '上昇テーブル', 'down_table': '下降テーブル',
    'timeout': 'タイムアウト', 'limit': '範囲設定', 'speed': '速度',
    'delta': '変化量', 'stable_current_range': '電流の安定判定範囲',
    'stable_current_count': '電流の安定判定回数',
    'tunnel_current': '目標トンネル電流', 'fb_table': 'フィードバックテーブル',
}

# Argument order from the supplied ZeroMQClient.py command methods.
FIELDS = {
    'ROUGH': ('電流下限', '電流上限', 'モーター速度'),
    'SMOOTH': ('電流下限', '電流上限', 'ピエゾ速度'),
    'limit': ('電流下限', '電流上限'),
    'speed_table': ('上昇速度', '下降速度'),
    'up_table': ('電流上限', '移動量', '速度'),
    'down_table': ('電流上限', '移動量', '速度'),
    'fb_table': ('電流差上限', '移動量', '動作時間'),
    'threshold': ('電流しきい値',),
}


class ValueDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, editable_column=1):
        super().__init__(parent)
        self.editable_column = editable_column

    def createEditor(self, parent, option, index):
        if index.column() == self.editable_column:
            return super().createEditor(parent, option, index)
        return None


class SettingsPreview(QDialog):
    def __init__(self, text, filename, parent=None, editable=False):
        super().__init__(parent)
        self.editable = editable
        self.source_text = text
        self.filename = filename
        self.saved_path = None
        self.saved_text = None
        self.edit_rows = []
        self.setWindowTitle('設定内容の確認')
        self.resize(1000, 680)
        layout = QVBoxLayout(self)
        title = QLabel(filename or 'デモ用設定')
        title.setTextFormat(Qt.PlainText)
        title.setWordWrap(True)
        layout.addWidget(title)
        note = QLabel('選択したファイルの内容です（装置の現在値ではありません）。\n'
                      '電流設定は回路に応じてµAまたはpA、その他の16進数値は10進数で表示します。')
        note.setWordWrap(True)
        if editable:
            self.setWindowTitle('設定内容の確認・編集')
            note.setText('変更する項目の設定値をダブルクリックして入力してください。\n'
                         '電流設定は表示されたµAまたはpAで入力し、保存時に装置値（RAW）へ変換します。')
        layout.addWidget(note)
        self.search = QLineEdit()
        self.search.setPlaceholderText('工程・項目名・設定値で検索')
        layout.addWidget(self.search)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.tree = QTreeWidget()
        self.tree.setItemDelegate(ValueDelegate(self.tree))
        self.tree.setHeaderLabels(['工程 / 設定項目', '設定値（µA・pA / その他は10進数）', '元の項目名', '行'])
        self.tree.setColumnWidth(0, 330)
        self.tree.setColumnWidth(1, 310)
        self.tree.setColumnWidth(2, 180)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet('QTreeWidget { background: #0E1620; alternate-background-color: #182331; }'
                                'QTreeWidget::item { padding: 6px; }'
                                'QTreeWidget::item:selected { background: #FFFFFF; color: #0B1017; }')
        tabs.addTab(self.tree, '項目一覧')
        raw = QPlainTextEdit()
        raw.setReadOnly(True)
        raw.setPlainText(text or 'デモ用設定です。実際の設定ファイルを選ぶと内容を確認できます。')
        tabs.addTab(raw, '元テキスト')
        groups = {}
        self.hold_target_item = None
        self.hold_fb_rows = {}
        count = 0
        for number, line in enumerate(text.splitlines(), 1):
            parts = line.split()
            if not parts or line.lstrip().startswith('#'):
                continue
            if len(parts) >= 5 and parts[0] in ('mcbj', 'asz') and parts[1] == 'set':
                command = parts[0]
                group, key, values = parts[2], parts[3], parts[4:]
                group_key = (parts[0], group)
                heading = GROUPS.get(group, group)
                name = NAMES.get(key, key)
                table_index = None
                if key.endswith('_table') and values:
                    table_index = values[0]
                    name += f' ［行 {table_index}］'
                    values = values[1:]
            else:
                command = None
                group_key, heading = ('other', ''), 'その他 / 原文で確認'
                name, key, values = '未分類の行', '', [line]
            if group_key not in groups:
                groups[group_key] = QTreeWidgetItem(self.tree, [heading])
            labels = FIELDS.get(key, ())
            prefix_size = 5 if key.endswith('_table') else 4
            for offset, value in enumerate(values):
                is_hex = bool(re.fullmatch(r'0[xX][0-9a-fA-F]+', value))
                current_unit = current_unit_for(command, group, key, offset) if is_hex else None
                current_max = bool(current_unit and key in ('up_table', 'down_table', 'fb_table') and
                                   int(value, 16) in (0x7FFFFFFF, 0xFFFFFFFF))
                if current_max:
                    display = 'MAX'
                elif current_unit:
                    display = format_current(Decimal(int(value, 16)) / current_divisor(current_unit))
                else:
                    display = str(int(value, 16)) if is_hex else value
                field = labels[offset] if offset < len(labels) else (
                    f'値 {offset + 1}' if len(values) > 1 else '')
                if current_unit:
                    field += f'（{current_unit}）'
                field_name = f'{name} / {field}' if field else name
                item = QTreeWidgetItem(groups[group_key], [field_name, display, key, str(number)])
                item.setData(1, Qt.UserRole, ('current_max:' if current_max else 'current:') + current_unit
                             if current_unit else 'raw')
                item.setData(1, Qt.UserRole + 1, display)
                if group == 'hg' and key == 'tunnel_current' and offset == 0:
                    self.hold_target_item = item
                if group == 'hg' and key == 'fb_table' and table_index is not None:
                    self.hold_fb_rows.setdefault(table_index, []).append(item)
                if editable and key and not current_max:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                if editable and key:
                    self.edit_rows.append((item, number - 1, prefix_size + offset, value, is_hex))
                for column in range(4):
                    note = f'\n{current_unit}で入力し、保存時に装置値（RAW）へ変換します。' if current_unit else (
                        '\n10進数の装置値（RAW）。pA換算ではありません。' if is_hex else '')
                    item.setToolTip(column, line + note)
            count += 1
        self.hold_detail = QTreeWidget()
        self.hold_detail.setItemDelegate(ValueDelegate(self.hold_detail, editable_column=2))
        self.hold_detail.setHeaderLabels([
            '段', '電流偏差の範囲', '上限', '移動量', '動作時間', '計算上の速度'
        ])
        self.hold_detail.setAlternatingRowColors(True)
        self.hold_detail.setStyleSheet(self.tree.styleSheet())
        detail_page = QWidget()
        detail_layout = QVBoxLayout(detail_page)
        self.hold_target_label = QLabel()
        self.hold_target_label.setWordWrap(True)
        detail_layout.addWidget(self.hold_target_label)
        self.hold_target_edit = None
        if editable and self.hold_target_item is not None:
            self.hold_target_edit = QLineEdit()
            self.hold_target_edit.setPlaceholderText('目標トンネル電流を pA で入力')
            self.hold_target_edit.editingFinished.connect(self.apply_hold_target_pa)
            detail_layout.addWidget(self.hold_target_edit)
        detail_layout.addWidget(QLabel(
            '電流差上限は 1 pA = 5,825,183.612928 RAW で換算。'
            '計算上の速度 = 移動量 ÷ 動作時間です。'
        ))
        detail_layout.addWidget(self.hold_detail)
        self._refreshing_hold_detail = False
        self.hold_detail.itemChanged.connect(self.apply_hold_upper_pa)
        tabs.insertTab(1, detail_page, 'Hold Gap換算')
        self.refresh_hold_detail()
        self.tree.itemChanged.connect(self.refresh_hold_detail)
        self.tree.expandAll()
        self.summary = QLabel(f'{len(groups)} 分類 / {count} 項目 ・ 読み取り専用')
        if editable:
            self.summary.setText(f'{len(groups)} 分類 / {count} 項目 ・ 設定値を編集可能')
        layout.addWidget(self.summary)
        self.search.textChanged.connect(self.filter_items)
        if editable:
            layout.addWidget(QLabel('ファイル名に付ける文字（任意）'))
            self.filename_suffix = QLineEdit()
            self.filename_suffix.setPlaceholderText('例：試料A_調整後（空欄なら日時のみ）')
            layout.addWidget(self.filename_suffix)
            layout.addWidget(QLabel('保存名：YYYYMMDD_HHMMSS_入力文字.txt（保存時の日時）'))
            save = QPushButton('別名で保存して使用')
            save.clicked.connect(self.save_settings)
            layout.addWidget(save)
        close = QPushButton('閉じる')
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    @staticmethod
    def _pa_text(value):
        return format_current(value) + ' pA'

    def refresh_hold_detail(self, *_):
        if self._refreshing_hold_detail:
            return
        self._refreshing_hold_detail = True
        self.hold_detail.clear()
        if self.hold_target_item is None and not self.hold_fb_rows:
            self.hold_target_label.setText('Hold Gap設定はありません。')
            self._refreshing_hold_detail = False
            return
        if self.hold_target_item is not None:
            try:
                target = float(self.hold_target_item.text(1))
                self.hold_target_label.setText(f'目標トンネル電流：{format_current(target)} pA')
                if self.hold_target_edit is not None and not self.hold_target_edit.hasFocus():
                    self.hold_target_edit.setText(format_current(target))
            except ValueError:
                self.hold_target_label.setText('目標トンネル電流：入力値を確認してください。')
        previous = 0.0
        def order(value):
            try:
                return int(value)
            except ValueError:
                return value
        for index in sorted(self.hold_fb_rows, key=order):
            items = self.hold_fb_rows[index]
            if len(items) < 3:
                continue
            try:
                upper_text_value = items[0].text(1)
                distance = float(items[1].text(1))
                duration = float(items[2].text(1))
            except ValueError:
                QTreeWidgetItem(self.hold_detail, [index, '入力値を確認してください。'])
                continue
            if upper_text_value == 'MAX':
                upper_text = 'MAX'
                range_text = f'{self._pa_text(previous)}超'
            else:
                try:
                    upper = float(upper_text_value)
                except ValueError:
                    QTreeWidgetItem(self.hold_detail, [index, '入力値を確認してください。'])
                    continue
                upper_text = self._pa_text(upper)
                range_text = (f'0 ～ {upper_text}' if previous == 0 else
                              f'{self._pa_text(previous)}超 ～ {upper_text}')
                previous = upper
            speed = '―' if duration == 0 else f'{distance / duration * 1000:.3f}'.rstrip('0').rstrip('.') + ' nm/s'
            detail_item = QTreeWidgetItem(self.hold_detail, [
                index, range_text, upper_text, f'{distance:g} nm', f'{duration:g} ms', speed
            ])
            detail_item.setData(0, Qt.UserRole, index)
            if self.editable and upper_text_value != 'MAX':
                detail_item.setFlags(detail_item.flags() | Qt.ItemIsEditable)
        for column in range(6):
            self.hold_detail.resizeColumnToContents(column)
        self._refreshing_hold_detail = False

    @staticmethod
    def raw_from_pa(text):
        return SettingsPreview.raw_from_current(text, 'pA')

    @staticmethod
    def raw_from_current(text, unit):
        try:
            current = Decimal(text.strip())
        except InvalidOperation as error:
            raise ValueError(f'{unit}は0以上の数値で入力してください。') from error
        if not current.is_finite() or current < 0:
            raise ValueError(f'{unit}は0以上の数値で入力してください。')
        raw = int((current * current_divisor(unit)).to_integral_value(rounding=ROUND_HALF_UP))
        if raw > 0xFFFFFFFE:
            raise ValueError(f'{unit}が装置で設定できる範囲を超えています。')
        return raw

    def apply_hold_target_pa(self):
        if self.hold_target_edit is None:
            return
        try:
            raw = self.raw_from_pa(self.hold_target_edit.text())
            if raw == 0:
                raise ValueError('目標トンネル電流は0より大きい値を入力してください。')
        except ValueError as error:
            QMessageBox.warning(self, '設定値を確認してください', str(error))
            self.refresh_hold_detail()
            return
        actual_pa = Decimal(raw) / CURRENT_RAW_PER_PA_DECIMAL
        self.hold_target_item.setText(1, format_current(actual_pa))

    def apply_hold_upper_pa(self, item, column):
        if self._refreshing_hold_detail or column != 2:
            return
        index = item.data(0, Qt.UserRole)
        rows = self.hold_fb_rows.get(str(index))
        if not rows or item.text(2) == 'MAX':
            return
        text = item.text(2).removesuffix('pA').strip()
        try:
            raw = self.raw_from_pa(text)
        except ValueError as error:
            QMessageBox.warning(self, '設定値を確認してください', str(error))
            self.refresh_hold_detail()
            return
        actual_pa = Decimal(raw) / CURRENT_RAW_PER_PA_DECIMAL
        rows[0].setText(1, format_current(actual_pa))

    def edited_text(self):
        previous = -1
        for index in sorted(self.hold_fb_rows, key=lambda value: int(value)):
            text = self.hold_fb_rows[index][0].text(1)
            if text == 'MAX':
                continue
            upper = self.raw_from_pa(text)
            if upper <= previous:
                raise ValueError('Hold Gapの電流差上限は、行番号順に大きくなるよう設定してください。')
            previous = upper
        lines = self.source_text.splitlines(keepends=True)
        replacements = {}
        for item, number, position, original, is_hex in self.edit_rows:
            value = item.text(1).strip()
            value_kind = item.data(1, Qt.UserRole)
            if value_kind.startswith('current_max:'):
                continue
            elif value_kind.startswith('current:'):
                unit = value_kind.split(':', 1)[1]
                if value == item.data(1, Qt.UserRole + 1):
                    continue
                decimal = self.raw_from_current(value, unit)
                if item is self.hold_target_item and decimal == 0:
                    raise ValueError('目標トンネル電流は0より大きい値を入力してください。')
                value = original if decimal == int(original, 16) else f'0x{decimal:0{len(original) - 2}X}'
                if value != original:
                    replacements.setdefault(number, {})[position] = value
                continue
            pattern = r'[0-9]+' if is_hex else r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)'
            if not re.fullmatch(pattern, value):
                raise ValueError(f'{number + 1}行目・{item.text(0)}：10進数' +
                                 ('の非負整数' if is_hex else '') + 'を1つ入力してください。')
            if is_hex:
                decimal = int(value)
                if decimal > 0xFFFFFFFF:
                    raise ValueError(f'{number + 1}行目・{item.text(0)}：4294967295以下で入力してください。')
                value = original if decimal == int(original, 16) else f'0x{decimal:0{len(original) - 2}X}'
            if value != original:
                replacements.setdefault(number, {})[position] = value
        for number, changes in replacements.items():
            tokens = list(re.finditer(r'\S+', lines[number]))
            for position, value in sorted(changes.items(), reverse=True):
                token = tokens[position]
                lines[number] = lines[number][:token.start()] + value + lines[number][token.end():]
        result = ''.join(lines)
        from protocol import settings_commands
        settings_commands(result)
        return result

    def save_settings(self):
        try:
            text = self.edited_text()
            suffix = self.filename_suffix.text().strip()
            if re.search(r'[<>:"/\\|?*\x00-\x1f]', suffix):
                raise ValueError('ファイル名には次の文字は使えません： < > : " / \\ | ? *')
        except ValueError as error:
            QMessageBox.warning(self, '設定値を確認してください', str(error))
            return
        base = Path(__file__).resolve().parent / 'setting parameter'
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        suggested = base / (stamp + ('_' + suffix if suffix else '') + '.txt')
        path, _ = QFileDialog.getSaveFileName(self, '新しい設定を保存', str(suggested), 'Settings (*.txt)')
        if not path:
            return
        target = Path(path)
        if not target.suffix:
            target = target.with_suffix('.txt')
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            # New files only: the source and existing settings cannot be overwritten.
            with target.open('x', encoding='utf-8', newline='\n') as output:
                output.write(text)
        except OSError as error:
            QMessageBox.warning(self, '保存できません', f'新しいファイル名で保存してください。\n{error}')
            return
        self.saved_path, self.saved_text = target, text
        self.accept()

    def filter_items(self, text):
        query = text.strip().casefold()
        for index in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(index)
            visible = False
            for row in range(group.childCount()):
                item = group.child(row)
                haystack = group.text(0) + ' ' + ' '.join(item.text(c) for c in range(4))
                match = query in haystack.casefold()
                item.setHidden(not match)
                visible |= match
            group.setHidden(not visible)
            if query:
                group.setExpanded(True)
