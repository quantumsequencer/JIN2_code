"""User-confirmed position limits; no assumed manufacturer travel range."""
import math


def range_problem(lower, upper, position=None):
    try:
        low, high = float(lower), float(upper)
    except (TypeError, ValueError):
        return 'Piezo正常範囲の下限・上限（nm）を設定してください。'
    if not math.isfinite(low) or not math.isfinite(high) or low >= high:
        return 'Piezo正常範囲は有限値で、下限 < 上限にしてください。'
    if position is None:
        return 'Piezo位置が未取得です。Hostデータを確認してください。'
    if not math.isfinite(position) or not low <= position <= high:
        return f'Piezoレンジ外：{position:g} nm（正常範囲 {low:g} ～ {high:g} nm）'
    return ''
