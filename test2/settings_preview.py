"""Searchable settings editor with decimal display and lossless hex values."""
from pathlib import Path
from datetime import datetime
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QPlainTextEdit, QPushButton, QHeaderView,
    QStyledItemDelegate, QFileDialog, QMessageBox,
)


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
    'fb_table': ('電流差上限', '移動量', '速度'),
    'threshold': ('電流しきい値',),
}


class ValueDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 1:
            return super().createEditor(parent, option, index)
        return None


class SettingsPreview(QDialog):
    def __init__(self, text, filename, parent=None, editable=False):
        super().__init__(parent)
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
                      '16進数の値は10進数で表示します。電流は装置の数値（RAW）で、pA換算ではありません。')
        note.setWordWrap(True)
        if editable:
            self.setWindowTitle('新しい設定を作成')
            note.setText('変更する項目の設定値をダブルクリックし、10進数で入力してください。\n'
                         '電流は装置の数値（RAW）で、pAではありません。元が16進数の値は保存時に16進数へ戻します。')
        layout.addWidget(note)
        self.search = QLineEdit()
        self.search.setPlaceholderText('工程・項目名・設定値で検索')
        layout.addWidget(self.search)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        self.tree = QTreeWidget()
        self.tree.setItemDelegate(ValueDelegate(self.tree))
        self.tree.setHeaderLabels(['工程 / 設定項目', '設定値（10進数）', '元の項目名', '行'])
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
        count = 0
        for number, line in enumerate(text.splitlines(), 1):
            parts = line.split()
            if not parts or line.lstrip().startswith('#'):
                continue
            if len(parts) >= 5 and parts[0] in ('mcbj', 'asz') and parts[1] == 'set':
                group, key, values = parts[2], parts[3], parts[4:]
                group_key = (parts[0], group)
                heading = GROUPS.get(group, group)
                name = NAMES.get(key, key)
                if key.endswith('_table') and values:
                    name += f' ［行 {values[0]}］'
                    values = values[1:]
            else:
                group_key, heading = ('other', ''), 'その他 / 原文で確認'
                name, key, values = '未分類の行', '', [line]
            if group_key not in groups:
                groups[group_key] = QTreeWidgetItem(self.tree, [heading])
            labels = FIELDS.get(key, ())
            prefix_size = 5 if key.endswith('_table') else 4
            for offset, value in enumerate(values):
                is_hex = bool(re.fullmatch(r'0[xX][0-9a-fA-F]+', value))
                display = str(int(value, 16)) if is_hex else value
                field = labels[offset] if offset < len(labels) else (
                    f'値 {offset + 1}' if len(values) > 1 else '')
                field_name = f'{name} / {field}' if field else name
                item = QTreeWidgetItem(groups[group_key], [field_name, display, key, str(number)])
                if editable and key:
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    self.edit_rows.append((item, number - 1, prefix_size + offset, value, is_hex))
                for column in range(4):
                    item.setToolTip(column, line + ('\n10進数の装置値（RAW）。pA換算ではありません。' if is_hex else ''))
            count += 1
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

    def edited_text(self):
        lines = self.source_text.splitlines(keepends=True)
        replacements = {}
        for item, number, position, original, is_hex in self.edit_rows:
            value = item.text(1).strip()
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
        base = Path(__file__).resolve().parent
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
