"""Session reports based on elapsed time, received positions and firmware logs."""
from dataclasses import dataclass, field
from datetime import datetime
import time
import re


def duration(seconds):
    seconds = int(seconds)
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'


@dataclass
class StepReport:
    started: float = field(default_factory=time.monotonic)
    started_at: str = field(default_factory=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    elapsed: float | None = None
    ended_at: str = ''
    status: str = '実行中'
    setting: str = ''
    setting_text: str = ''
    first_position: dict = field(default_factory=dict)
    last_position: dict = field(default_factory=dict)
    fc_moves: dict = field(default_factory=dict)
    logs: list = field(default_factory=list)
    progress: str = ''
    baseline_current: dict | None = None
    expand_final_current: dict | None = None
    training_axis: str | None = None
    training_positions: dict = field(default_factory=dict)

    def sample(self, frame):
        if self.elapsed is not None:
            return
        positions = {key: frame[key] for key in ('motor', 'piezo')}
        if not self.first_position:
            self.first_position = positions
        self.last_position = positions

    def feed(self, text, frame=None, position_age=None):
        if self.elapsed is not None:
            return
        self.logs.extend(text.splitlines())
        self.logs = self.logs[-2000:]
        for line in text.splitlines():
            start = re.search(r'Actuator Training\((Motor|Piezo)\) start!', line)
            if start:
                self.training_axis = start[1].lower()
            if not self.training_axis or 'ActuatorTraining.cpp:' not in line:
                continue
            reached = re.search(r'\b(Up|Down)\s+OK\[(\d+)\]', line)
            if reached:
                direction, index = reached[1], int(reached[2])
                if not 0 <= index < 10:
                    continue
                pair = self.training_positions.setdefault(index, {})
                # Preserve the first observation; duplicate logs must not move an endpoint.
                if direction not in pair:
                    valid = frame is not None and position_age is not None and 0 <= position_age <= 0.5
                    pair[direction] = frame[self.training_axis] if valid else None
        for match in re.finditer(r'FC find\[(\d+)\].*?move\s*=\s*([+-]?[\d.]+)\[um\]', text):
            self.fc_moves[int(match[1])] = float(match[2])

    def finish(self, status):
        if self.elapsed is None:
            self.elapsed = time.monotonic() - self.started
            self.ended_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.status = status

    def describe(self):
        lines = [f'結果：{self.status}', f'開始：{self.started_at}',
                 f'終了：{self.ended_at or "—"}',
                 f'所要時間：{duration(self.elapsed if self.elapsed is not None else time.monotonic() - self.started)}',
                 f'設定ファイル：{self.setting or "未記録"}', '',
                 '位置・移動量（装置から受信した位置。実移動距離の保証ではありません）']
        for key, label, unit in [('motor', 'Motor', 'µm'), ('piezo', 'Piezo', 'nm')]:
            if key in self.first_position:
                start, end = self.first_position[key], self.last_position[key]
                lines.append(f'{label}：開始 {start:g} → 終了 {end:g} {unit} ／ 差分 {end - start:+g} {unit}')
            else:
                lines.append(f'{label}：位置データなし')
        lines += ['※開始・終了は工程中に受信した最初・最後の位置。差分は往復の総移動距離ではありません。']
        if self.training_axis:
            unit = 'µm' if self.training_axis == 'motor' else 'nm'
            lines += ['', f'{self.training_axis.title()} Training：各回の到達位置（近似値・{unit}）',
                      'ログ処理時の最新受信位置を使用。受信から0.5秒超・未受信の場合は取得できず。',
                      '回 [n] | Up位置 | Down位置 | 差分（Down − Up） | 振幅（絶対値）']
            for index in range(10):
                pair = self.training_positions.get(index, {})
                up, down = pair.get('Up'), pair.get('Down')
                def endpoint(direction):
                    if direction not in pair:
                        return '到達ログなし'
                    value = pair[direction]
                    return f'{value:g}' if value is not None else '取得できず'
                delta = f'{down - up:+g} | {abs(down - up):g}' if up is not None and down is not None else '— | —'
                lines.append(f'{index + 1}回目 [{index}] | {endpoint("Up")} | {endpoint("Down")} | {delta}')
        if self.baseline_current is not None:
            baseline = self.baseline_current
            mean = baseline['mean_pa']
            lines += ['', 'Expand Gap終了後の基準電流',
                      f'Mean Current：{mean:.6f} pA' if mean is not None else 'Mean Current：未確定',
                      '平均区間：完了通知処理後に受信した1秒間（100フレーム）',
                      f'使用サンプル数：{baseline["samples"]}',
                      '取得状態：' + baseline['status']]
        if self.expand_final_current is not None:
            final = self.expand_final_current
            if final.get('status') == '正常':
                lines += ['', 'Expand Gap 最終電流値',
                          f'測定条件：{final["rate_hz"] / 1000:g} kHz / Bias {final["bias_v"]:.1f} V',
                          f'Median：{final["median_pa"]:.6f} pA',
                          f'RMS：{final["rms_pa"]:.6f} pA',
                          f'Noise RMS：{final["noise_rms_pa"]:.6f} pA',
                          f'使用サンプル数：{final["samples"]}']
            else:
                lines += ['', 'Expand Gap 最終電流値：取得不可',
                          '取得状態：' + final.get('status', '不明')]
        if self.fc_moves:
            lines += ['', 'First Cut：装置ログのMotor移動量（move）']
            lines += [f'{index}回目：{value:g} µm' for index, value in sorted(self.fc_moves.items())]
        if self.progress:
            lines += ['', '最終進捗：' + self.progress]
        lines += ['', '工程中の装置ログ（最新2000行）', *self.logs]
        return '\n'.join(lines)
