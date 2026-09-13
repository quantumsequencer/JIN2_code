"""Reference distance presets: preserve SGMO1 target pA, encode for SGMO2 ADC gain.

Sources: SGMO1_original/history/jin_FC上限値変更.txt and
Jin_期待値算出_検算用_Ver0.1.3_電流値_AD値変換.xlsx (C25),
SGMO2 HoldGap settings workbook (C23). This is not a distance measurement.
"""
from decimal import Decimal
import re
from protocol import Command

OLD_PA_PER_RAW = Decimal('0.000000269314')
NEW_RAW_PER_PA = Decimal('5825183.6129280003')
OLD_PRESETS = {'0.54': 0x05098121, '0.56': 0x03248321,
               '0.58': 0x01F5EDE0, '0.60': 0x01392660}


def target_for_distance(distance):
    pa = Decimal(OLD_PRESETS[distance]) * OLD_PA_PER_RAW
    return pa, int(pa * NEW_RAW_PER_PA)  # same truncation as Excel DEC2HEX


def target_command(distance):
    _, raw = target_for_distance(distance)
    return Command(f'asz set hg tunnel_current 0x{raw:08X}', 'Setting change : 0')


def model_target(distance):
    """Provisional command value: tunnel current only, without baseline addition."""
    d = Decimal(str(distance))
    if not d.is_finite() or d <= 0:
        raise ValueError('距離は正の数で入力してください。')
    tunnel = Decimal('7750000') * (-Decimal('22.91') * d).exp()
    raw = int(tunnel * NEW_RAW_PER_PA)
    if not 0 < raw <= 0x7FFFFFFF:
        raise ValueError(f'設定電流 {tunnel:.6f} pAは現在のUIで送信可能な電流値の範囲外です。')
    return tunnel, raw


def raw_from_command(text):
    match = re.fullmatch(r'asz\s+set\s+hg\s+tunnel_current\s+(0[xX][0-9a-fA-F]+|[0-9]+)', text.strip())
    if not match:
        return None
    value = match.group(1)
    return int(value, 16 if value.lower().startswith('0x') else 10)


def describe_raw(raw):
    if raw is None:
        return '適用値：未確認'
    pa = Decimal(raw) / NEW_RAW_PER_PA
    return f'適用値：{pa:.6f} pA（装置への設定成功応答に基づく）'
