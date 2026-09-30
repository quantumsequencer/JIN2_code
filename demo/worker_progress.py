"""Display-only progress from firmware logs; never completes a command."""
import re
import time


class WorkerProgress:
    def __init__(self, step=None):
        self.step = step
        self.started = time.monotonic()
        self.worker_started = False
        self.seen = set()
        self.latest = None
        self.updated = None
        self.fc_seen = set()

    def feed(self, text):
        names = {4: 'First Cut', 5: 'Actuator Training(Motor)', 6: 'Actuator Training(Piezo)',
                 9: 'Calibration'}
        name = names.get(self.step)
        if not name:
            return
        source = 'FirstCut.cpp' if self.step == 4 else 'Calibration.cpp' if self.step == 9 else 'ActuatorTraining.cpp'
        for line in text.splitlines():
            if name + ' start!' in line:
                self.worker_started = True
            if not self.worker_started or source not in line:
                continue
            if self.step == 4:
                match = re.search(r'FC find\[([1-3])\]', line)
                if match:
                    self.fc_seen.add(int(match[1]))
                    self.updated = time.monotonic()
                continue
            match = re.search(r'\b(Up|Down)\s+OK\[(\d+)\]', line)
            if match:
                direction, index = match[1], int(match[2])
                if (index, direction) not in self.seen:
                    self.seen.add((index, direction))
                    self.latest = (index, direction)
                    self.updated = time.monotonic()

    def describe(self):
        elapsed = int(time.monotonic() - self.started)
        clock = f'経過 {elapsed // 60}:{elapsed % 60:02d}'
        if self.step not in (4, 5, 6, 9):
            return '完了待ち / ' + clock
        if not self.worker_started:
            return '開始ログ待ち（前処理を含む） / ' + clock
        if self.step == 4:
            return f'切断検出 {len(self.fc_seen)}/3回 / ' + clock + ' / 装置の完了通知待ち'
        count = sum((i, 'Down') in self.seen for i, d in self.seen if d == 'Up')
        status = f'往復確認 {count}回（参考：10回）'
        if self.latest:
            index, direction = self.latest
            status += f' / {index + 1}回目 {direction}到達'
            status += f' / 更新 {int(time.monotonic() - self.updated)}秒前'
        else:
            status += ' / 到達ログ待ち'
        return status + ' / ' + clock + ' / 装置の完了通知待ち'
