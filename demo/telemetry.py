"""Bounded display buffers; the Gateway owns raw data recording."""
from collections import deque
import numpy as np
from protocol import decode_host


class Telemetry:
    def __init__(self):
        self.frames = deque(maxlen=500)  # 5 seconds at 100 frames/s, including 100 kHz
        self.hardware = deque(maxlen=6000)
        self.latest = None
        self.gaps = 0

    def feed(self, payload):
        frame = decode_host(payload)
        if frame is None:
            return None
        previous = self.latest
        restart = bool(previous and frame['serial'] < previous['serial'])
        gap = previous and frame['serial'] != (previous['serial'] + 1) % (2**32)
        if gap:
            self.gaps += 1
        if gap or (previous and (frame['kind'], frame['unit']) != (previous['kind'], previous['unit'])):
            self.frames.clear()
        if restart:
            self.hardware.clear()
        elif gap:
            self.hardware.append((frame['time'], np.nan, np.nan))
        self.latest = frame
        self.frames.append(frame)
        self.hardware.append((frame['time'], frame['motor'], frame['piezo']))
        return restart

    def current_plot(self):
        frames = [f for f in self.frames if len(f['values'])]
        if not frames:
            return np.empty(0), np.empty(0)
        return np.concatenate([f['times'] for f in frames]), np.concatenate([f['values'] for f in frames])
