"""First Cut preflight; times are monotonic seconds, current is µA."""
import numpy as np


class ConductionGuard:
    def __init__(self, now):
        self.started = self.last_received = now
        self.window_start = now + 3
        self.samples = []
        self.low_seconds = 0
        self.ready = False

    def check(self, now, frame=None):
        if now - self.last_received >= 1:
            return '導通確認：電流データの受信が1秒以上途絶えました'
        if frame is None:
            return ''
        self.last_received = now
        if now < self.started + 3:
            return ''
        values = frame.get('values', [])
        if frame.get('unit') != 'µA' or not len(values) or not np.all(np.isfinite(values)):
            return '導通確認：有効なµA単位の電流データを取得できません'
        self.samples.extend(values)
        if now - self.window_start < 1:
            return ''
        median = float(np.median(self.samples))
        self.samples.clear()
        self.window_start = now
        if median >= 9:
            self.ready = True
        else:
            self.low_seconds += 1
            if self.low_seconds >= 3:
                return '導通異常：電流が9 µA未満で3秒継続。チップの破損・装着・配線を確認してください'
        return ''
