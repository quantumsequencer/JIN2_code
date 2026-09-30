"""One second (100 consecutive 10 ms frames) of post-completion current."""
import time
import numpy as np


class BaselineCurrent:
    def __init__(self, last_serial=None):
        self.started = time.monotonic()
        self.previous = last_serial
        self.frames = self.count = 0
        self.total = 0.0
        self.kind = None
        self.done = False
        self.result = {'status': '取得中', 'mean_pa': None, 'samples': 0}

    def fail(self, reason):
        if not self.done:
            self.done = True
            self.result.update(status='取得失敗：' + reason, samples=self.count)

    def feed(self, frame):
        if self.done:
            return
        if self.previous is not None and frame['serial'] != self.previous + 1:
            self.fail('電流データの欠落・重複・装置時刻の変化')
            return
        if frame['unit'] != 'pA' or frame['kind'] not in (2, 3, 4):
            self.fail('pAに換算できない測定条件')
            return
        if self.kind is not None and self.kind != frame['kind']:
            self.fail('取得中にサンプルレートが変化')
            return
        values = frame['values']
        if len(values) != frame['rate'] // 100 or not np.all(np.isfinite(values)):
            self.fail('電流サンプルが不正')
            return
        self.kind = frame['kind']
        self.previous = frame['serial']
        self.total += float(np.sum(values, dtype=np.float64))
        self.count += len(values)
        self.frames += 1
        if self.frames == 100:
            self.done = True
            self.result.update(status='正常', mean_pa=self.total / self.count, samples=self.count)

    def tick(self):
        if time.monotonic() - self.started > 3:
            self.fail('1秒分のデータを取得できずタイムアウト')
