"""Persistent successful Expand Gap durations, excluding baseline acquisition."""
from pathlib import Path
from datetime import datetime
from uuid import uuid4
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent / 'reports' / 'expand_timing'


def record(seconds, root=ROOT):
    if not math.isfinite(seconds) or seconds < 0: raise ValueError('Invalid duration')
    root.mkdir(parents=True, exist_ok=True)
    (root / (uuid4().hex + '.json')).write_text(json.dumps({'at': datetime.now().isoformat(), 'seconds': seconds}), encoding='utf-8')


def median_duration(root=ROOT):
    values = []
    for p in root.glob('*.json'):
        try:
            v = float(json.loads(p.read_text(encoding='utf-8'))['seconds'])
            if math.isfinite(v) and v >= 0: values.append(v)
        except (OSError, ValueError, KeyError, TypeError): continue
    return (statistics.median(values), len(values)) if values else (30.0, 0)
