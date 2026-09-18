"""Signed-current tolerance and continuous out-of-range watchdog."""
import math


class HoldMonitor:
    def __init__(self, tolerance=20.0, timeout=30.0):
        self.tolerance, self.timeout = tolerance, timeout
        self.out_since = None

    def update(self, now, median, target):
        if not math.isfinite(median) or not math.isfinite(target):
            self.out_since = None
            return None, None, False
        delta = median - target
        inside = abs(delta) <= self.tolerance
        if inside:
            self.out_since = None
        elif self.out_since is None:
            self.out_since = now
        return delta, inside, self.out_since is not None and now - self.out_since >= self.timeout
