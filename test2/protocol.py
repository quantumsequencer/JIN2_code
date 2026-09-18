"""SGMO2 0.2.0 protocol, from the supplied developer guide and client source."""
from dataclasses import dataclass
import re
import struct
import numpy as np


@dataclass(frozen=True)
class Command:
    text: str
    success: str | None = None
    done: str | None = None
    canceled: str | None = None
    timeout: float | None = 600.0


BIAS0 = Command('dd_ep bias 0', 'BIAS set complete.')
BIAS1 = Command('dd_ep bias 1', 'BIAS set complete.')
EP0 = Command('dd_ep ep 0', 'EP set complete.')
GO0 = Command('mw_ac go0', 'Actuator Control for set 0point complete.')
LOW = Command('sv_info_sender start 0', 'Start complete. result:0')
SAMPLE_STOP = Command('sv_info_sender stop', 'Stop complete. result:0')
STOP = Command('mcbj stop')
WORKERS = {
    'fc': Command('mcbj fc start', done=r'First Cut finish!$', canceled=r'First Cut canceld!$'),
    'target': Command('mcbj targeting start', done=r'Targeting finished\.$', canceled=r'Targeting canceled\.$'),
    'mt': Command('mcbj mt start', done=r'Actuator Training\(Motor\) end!$', canceled=r'Actuator Training\(Motor\) canceld!$'),
    'pt': Command('mcbj pt start', done=r'Actuator Training\(Piezo\) end!$', canceled=r'Actuator Training\(Piezo\) canceld!$'),
    'ac': Command('mcbj ac start', done=r'End\.$', canceled=r'End\. Canceled\.$'),
    'cal': Command('mcbj cal start', done=r'Calibration end!$', canceled=r'Calibration canceld!$'),
    'eg': Command('asz eg start', done=r'ExpandGap finished\.$', canceled=r'ExpandGap canceled\.$'),
    'hg': Command('asz hg start', done=r'HoldGap finished\.$', canceled=r'HoldGap canceled\.$', timeout=None),
}


def high(rate):
    return Command('sv_info_sender start ' + {10: '10', 50: '2', 100: '1'}[rate], 'Start complete. result:0')


def setup_commands(index, rate):
    return [
        [BIAS0, EP0, LOW], [GO0], [], [BIAS1], [WORKERS['fc']],
        [WORKERS['target'], WORKERS['mt']], [WORKERS['target'], WORKERS['pt']],
        [WORKERS['target'], WORKERS['ac']], [BIAS0, SAMPLE_STOP, high(rate), BIAS1],
        [WORKERS['cal']], [WORKERS['eg']],
    ][index]


def finalize_commands():
    return [STOP, BIAS0, EP0, SAMPLE_STOP]


def settings_commands(text):
    result = []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if not re.fullmatch(r'(?:mcbj|asz) set [A-Za-z0-9_+ .-]+', line):
            raise ValueError(f'{number}行目：設定ファイルは mcbj set / asz set のみ使用できます。')
        result.append(Command(line, 'Setting change : 0'))
    if not result:
        raise ValueError('設定コマンドがありません。')
    return result


def decode_host(payload):
    if len(payload) < 24:
        raise ValueError('Host frame shorter than 24 bytes')
    serial, kind = struct.unpack_from('<IH', payload)
    if kind not in range(5):
        return None  # diagnostics/reserved frames are not measurements
    count = (0, 100, 100, 500, 1000)[kind]
    if len(payload) != 24 + count * 4:
        raise ValueError(f'Host frame length mismatch: type={kind}, length={len(payload)}')
    bias, ep_plus, ep_minus = payload[8] / 10, *struct.unpack_from('bb', payload, 10)
    current, motor, piezo = struct.unpack_from('<iii', payload, 12)
    # Conversion is only specified for Bias 0.1 V and a known measuring circuit.
    unit, divisor = ('RAW', 1.0)
    if payload[8] == 1 and kind:
        unit, divisor = ('µA', 42781900.799999997) if kind == 1 else ('pA', 5825183.6129280003)
    values = np.frombuffer(payload, dtype='<i4', offset=24).astype(np.float64) / divisor
    rate = (0, 10000, 10000, 50000, 100000)[kind]
    end = serial * .01
    times = end - .01 + np.arange(count) / rate if count else np.empty(0)
    return dict(serial=serial, kind=kind, time=end, bias=bias, ep_plus=ep_plus / 10,
                ep_minus=ep_minus / 10, current=current / divisor, motor=motor / 10,
                piezo=piezo, values=values, times=times, unit=unit, rate=rate)
