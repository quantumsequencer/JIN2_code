"""Display-only first-order low-pass; raw telemetry is never modified."""
import numpy as np
from scipy.signal import lfilter


def lowpass(times, values, cutoff_hz):
    """Filter the displayed window, restarting at gaps and invalid samples."""
    times = np.asarray(times, dtype=float)
    values = np.asarray(values, dtype=float)
    result = values.copy()
    if len(values) < 2:
        return result
    if not np.isfinite(cutoff_hz) or cutoff_hz <= 0:
        raise ValueError('Cutoff must be positive and finite')
    intervals = np.diff(times)
    positive = intervals[np.isfinite(intervals) & (intervals > 0)]
    if not len(positive):
        return result
    dt = float(np.median(positive))
    valid = np.isfinite(values) & np.isfinite(times)
    boundaries = np.flatnonzero(
        (~valid[1:]) | (~valid[:-1]) | (intervals <= 0)
        | (intervals > dt * 1.5) | (~np.isfinite(intervals))) + 1
    pole = np.exp(-2 * np.pi * cutoff_hz * dt)
    for start, end in zip(np.r_[0, boundaries], np.r_[boundaries, len(values)]):
        if not valid[start]:
            continue
        result[start:end], _ = lfilter(
            [1 - pole], [1, -pole], values[start:end],
            zi=[pole * values[start]])
    return result
