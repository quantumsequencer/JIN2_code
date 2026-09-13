"""Offline split of Gateway data by firmware log intervals. Originals are read only."""
import csv
import json
import re
from pathlib import Path
from contextlib import ExitStack
from bisect import bisect_right

WORKERS = {
    'FirstCut': ('FirstCut.cpp', 'First Cut start!', r'First Cut (?:finish|canceld)!'),
    'Targeting': ('Targeting.cpp', 'Start.', r'Targeting (?:finished|canceled)\.'),
    'MotorTraining': ('ActuatorTraining.cpp', 'Actuator Training(Motor) start!', r'Actuator Training\(Motor\) (?:end|canceld)!'),
    'PiezoTraining': ('ActuatorTraining.cpp', 'Actuator Training(Piezo) start!', r'Actuator Training\(Piezo\) (?:end|canceld)!'),
    'AutoCut': ('AutoCut.cpp', 'Start.', r'\bEnd\.'),
    'Calibration': ('Calibration.cpp', 'Calibration start!', r'Calibration (?:end|canceld)!'),
    'ExpandGap': ('ExpandGap.cpp', 'ExpandGap start.', r'ExpandGap (?:finished|canceled)\.'),
    'HoldGap': ('HoldGap.cpp', 'HoldGap start.', r'HoldGap (?:finished|canceled)\.'),
}


def intervals(log):
    records, active, previous = [], {}, None
    for line in log.splitlines():
        m = re.search(r'\[(\d+\.\d+)\]\[([^]]+)\]\s*(.*)', line)
        if not m: continue
        t, source, message = float(m[1]), m[2], m[3]
        if previous is not None and t < previous - 1:
            raise ValueError('装置時刻の巻き戻りがあります。セッションを分けて解析してください。')
        previous = t
        for name, (file, start, end) in WORKERS.items():
            if not source.startswith(file + ':'): continue
            if message.startswith(start):
                if name in active:
                    active.pop(name)['status'] = '終了ログ欠落'
                record = dict(step=name, start=t, end=None, status='終了ログ欠落', events=[])
                records.append(record); active[name] = record
            if name in active and re.search(end, message):
                record = active.pop(name)
                record['end'] = t
                record['status'] = '中断' if re.search('cancel', message, re.I) else '完了'
        for record in records:
            if record['start'] <= t and (record['end'] is None or t <= record['end']):
                record['events'].append([t, line])
    return records


def signed(raw):
    return raw - 2**32 if raw >= 2**31 else raw


def export(source, destination):
    source, destination = Path(source), Path(destination)
    log = (source / 'log_port_rx.log').read_text(encoding='utf-8-sig')
    records = intervals(log)
    if not records: raise ValueError('対象工程の開始ログがありません。')
    destination.mkdir(parents=True, exist_ok=False)
    (destination / 'source_log.txt').write_text(log, encoding='utf-8')
    for name in ('debug_port_tx.log', 'debug_port_rx.log'):
        if (source / name).exists():
            (destination / name).write_bytes((source / name).read_bytes())
    with ExitStack() as stack:
        for n, r in enumerate(records, 1):
            folder = destination / f'{n:03d}_{r["step"]}'
            folder.mkdir(); r['folder'] = str(folder)
            r['positions'] = r['samples'] = r['gap_count'] = 0
            r['last_serial'] = None
            for key, header in [('position', ['device_time_s', 'serial', 'motor_um', 'piezo_nm', 'current_raw', 'bias_V']),
                                ('current', ['device_time_s', 'current_raw', 'current', 'unit', 'serial']),
                                ('events', ['device_time_s', 'log'])]:
                f = stack.enter_context((folder / (key + '.csv')).open('w', encoding='utf-8-sig', newline=''))
                r[key + '_writer'] = csv.writer(f); r[key + '_writer'].writerow(header)
            r['events_writer'].writerows(r['events'])
        completed = sorted((r for r in records if r['end'] is not None), key=lambda r: r['start'])
        starts = [r['start'] for r in completed]
        for left, right in zip(completed, completed[1:]):
            if left['end'] > right['start']:
                raise ValueError('工程区間が重複しています。ログを確認してください。')
        def match(t):
            i = bisect_right(starts, t) - 1
            return [completed[i]] if i >= 0 and t < completed[i]['end'] else []
        for file in sorted(source.glob('hw_data_*.csv')):
            with file.open(encoding='utf-8-sig', newline='') as f:
                for row in csv.reader(f):
                    try: t, serial = float(row[0]), int(row[1])
                    except (ValueError, IndexError): continue
                    for r in match(t):
                        r['position_writer'].writerow([t, serial, float(row[5]) / 10, row[6], row[4], row[3]])
                        r['positions'] += 1
        def flush(header, values):
            if header is None: return
            t, serial, kind, bias = float(header[0]), int(header[1]), int(header[2]), float(header[3])
            rate = {1: 10000, 2: 10000, 3: 50000, 4: 100000}.get(kind)
            if not rate: return
            expected = rate // 100
            if len(values) != expected:
                for r in match(t): r['gap_count'] += 1
                return
            divisor, unit = (42781900.799999997, 'uA') if kind == 1 else (5825183.6129280003, 'pA')
            if bias != 0.1: divisor, unit = 1, 'RAW'
            touched = set()
            for i, raw in enumerate(values):
                stamp = t - .01 + i / rate
                for r in match(stamp):
                    r['current_writer'].writerow([f'{stamp:.8f}', raw, raw / divisor, unit, serial])
                    r['samples'] += 1; touched.add(r['folder'])
            for r in records:
                if r['folder'] in touched:
                    if r['last_serial'] is not None and serial != r['last_serial'] + 1: r['gap_count'] += 1
                    r['last_serial'] = serial
        for file in sorted(source.glob('data_*/*')):
            if file.suffix != '.txt': continue
            header, values = None, []
            with file.open(encoding='utf-8-sig') as f:
                for line in f:
                    if line.startswith('#'):
                        flush(header, values); header = line[1:].strip().split(','); values = []
                    elif line.strip() and header is not None:
                        values.append(signed(int(line.strip(), 16)))
                flush(header, values)
        for r in records:
            metadata = {k: v for k, v in r.items() if not k.endswith('_writer') and k not in ('events', 'folder', 'last_serial')}
            metadata.update(source=str(source.resolve()), boundary='装置ログ時刻 [start,end)。サンプル時刻はフレーム終端から推定。',
                            settings='セッション全体のdebug_port_tx.logを参照。距離・時間は自動推定しません。',
                            warnings=['終了ログ欠落区間は抽出しません。', '欠損を補間しません。', '元ファイル書込終了後に実行してください。'])
            folder = Path(r['folder'])
            (folder / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            (folder / 'report.txt').write_text(f'{r["step"]}\n結果：{r["status"]}\n開始：{r["start"]} 秒\n終了：{r["end"]} 秒\n電流サンプル：{r["samples"]}\n位置行数：{r["positions"]}\nフレーム欠落・不整合検出：{r["gap_count"]}', encoding='utf-8')
    return records


if __name__ == '__main__':
    import sys
    try:
        result = export(sys.argv[1], sys.argv[2])
        print(f'Exported {len(result)} intervals', flush=True)
    except Exception as error:
        print(str(error), file=sys.stderr); sys.exit(1)
