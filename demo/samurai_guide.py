"""Read-only exhibition host: illustrations and narration follow real UI state."""
import math
import random
import time
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout
from workflow import STEPS


STEP_LINES = (
    ('基準を整えよう。初期化を進めているぞ。', 'まずは測定の土台づくりだ。'),
    ('基準位置へ移動中。ここが出発点だ。', 'モーターとピエゾの動きに注目してくれ。'),
    ('チップを装着したら、確認ボタンで知らせてくれ。', 'ここは君の出番だ。装着の確認を待っているぞ。'),
    ('Biasを印加して、次の工程に備えるぞ。', '電流の変化は右のグラフで見られるぞ。'),
    ('First Cutを進めているぞ。', '切断工程の進み具合は進捗バーで確認しよう。'),
    ('モーターをトレーニング中だ。', '緑の線がモーター。左の目盛りで読めるぞ。'),
    ('今度はピエゾをトレーニング中だ。', '紫の線がピエゾ。右の目盛りで読めるぞ。'),
    ('Auto Cutを進めているぞ。', '細かな変化を、グラフと一緒に見守ろう。'),
    ('測定回路を切り替えているぞ。', '測定に向けて、回路の準備を進めている。'),
    ('Calibrationで測定回路を校正中だ。', '良い測定のために、ここは丁寧に進めよう。'),
    ('ギャップを広げて、測定の準備を進めるぞ。', 'あと一工程。装置からの完了を待とう。'),
)
SHORT_NAMES = ('初期化', 'ゼロ点', '装着', 'Bias', 'Cut', 'Motor', 'Piezo', 'Auto', '回路', '校正', 'Gap')
POSES = {'welcome': (0, 3), 'focus': (1, 3), 'training': (2, 1, 3),
         'chip': (3,), 'measure': (3, 1), 'ready': (4, 0), 'attention': (5,)}
ATLAS_FILES = ('samurai_host_atlas.png', 'samurai_host_atlas_b.png', 'samurai_host_atlas_c.png')


def guidance(window):
    """Never infer completion from elapsed time, animations, or chart values."""
    s = window.state
    if getattr(window, 'problem', '') or getattr(getattr(window, 'engine', None), 'faulted', False):
        return 'attention', ('確認が必要だ。画面の異常表示を確認してくれ。',)
    operation = getattr(window, 'operation', None)
    if operation in ('stop', 'finalize', 'piezo_cleanup', 'quality_cleanup', 'timed_cleanup'):
        return 'attention', ('停止・終了処理を確認中だ。装置の応答を待とう。',)
    if getattr(window, 'live', False) and not window.host_recent and (s.active is not None or s.measurement):
        return 'attention', ('装置の状態を確認中だ。受信状況を確認してくれ。',)
    if s.active == 2:
        return 'chip', STEP_LINES[2]
    if operation and operation != 'step':
        return 'focus', ('装置の応答を確認しているぞ。進行状況を見守ろう。',)
    if s.measurement:
        return 'measure', ('測定中だ。電流の変化を一緒に見ていこう。',
                           '電流はグレーが元波形、水色がローパス後だ。',
                           '位置グラフは緑がモーター、紫がピエゾだ。')
    if s.active is not None:
        return ('training' if s.active in (4, 5, 6, 7) else 'focus'), STEP_LINES[s.active]
    if s.ready:
        return 'ready', ('11工程の準備が整ったぞ！', '測定の開始は操作パネルから進めてくれ。')
    if s.configured:
        return 'welcome', ('準備の開始を待っているぞ。', '11の工程を、僕と一緒に見ていこう。')
    return 'welcome', ('ようこそ。SAMURAIが測定の進行を案内するぞ。',
                       '右側は電流と位置のグラフ。準備ができたら始めよう。')


class SamuraiPortrait(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.setMaximumHeight(275)
        self.setAccessibleName('SAMURAI 進行役')
        self.atlases = tuple(QPixmap(str(Path(__file__).parent / 'assets' / name)) for name in ATLAS_FILES)
        self.variant = 0
        self.pose = 0
        self.mood = 'welcome'
        self.elapsed = 0.0

    @property
    def atlas(self):
        return self.atlases[self.variant]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        color = QColor('#E69C58' if self.mood == 'attention' else '#24C8DB')
        p.setPen(QPen(color, 1))
        p.drawEllipse(QRectF(self.width()*.18, self.height()-18, self.width()*.64, 10))
        if self.atlas.isNull():
            return
        cw, ch = self.atlas.width() / 3, self.atlas.height() / 2
        # Frame the upper body closely so facial expressions read at booth distance.
        portrait_height = ch * .72
        source = QRectF((self.pose % 3)*cw, (self.pose // 3)*ch, cw, portrait_height)
        size = min((self.width()-12)*portrait_height/cw, self.height()-12)
        # The image remains stationary; variety comes only from prepared artwork.
        p.translate(self.width()/2, self.height()/2)
        width = size*cw/portrait_height
        p.drawPixmap(QRectF(-width/2, -size/2, width, size), self.atlas, source)
        if self.mood == 'ready' and self.elapsed < 3:
            p.setPen(QPen(QColor('#FFE08A'), 2))
            for n in range(6):
                angle = n * math.pi / 3 + self.elapsed*.4
                x, y = math.cos(angle)*size*.43, math.sin(angle)*size*.40
                p.drawLine(int(x-3), int(y), int(x+3), int(y))
                p.drawLine(int(x), int(y-3), int(x), int(y+3))


class SamuraiGuide(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        heading = QLabel('SAMURAI  /  進行ガイド')
        heading.setStyleSheet('font-size: 16px; font-weight: bold; color: #E8EEF5;')
        layout.addWidget(heading)
        self.portrait = SamuraiPortrait()
        layout.addWidget(self.portrait)
        self.speech = QLabel()
        self.speech.setWordWrap(True)
        self.speech.setMinimumHeight(60)
        self.speech.setStyleSheet('background: #142633; border: 1px solid #285468; border-radius: 10px; padding: 8px; font-size: 14px;')
        layout.addWidget(self.speech)
        grid = QGridLayout()
        grid.setSpacing(3)
        self.steps = []
        for index, (name, description) in enumerate(STEPS):
            label = QLabel(f'{index+1:02d}\n{SHORT_NAMES[index]}')
            label.setAlignment(Qt.AlignCenter)
            label.setToolTip(f'{index+1:02d} {name}：{description}')
            label.setAccessibleName(f'工程{index+1} {name}')
            grid.addWidget(label, index//6, index%6)
            self.steps.append(label)
        layout.addLayout(grid)
        self._key = None
        self._since = time.monotonic()
        self._step_key = None
        self._image_key = None
        self._random = random.Random()

    def sync(self, window, now=None):
        now = time.monotonic() if now is None else now
        mood, lines = guidance(window)
        key = (mood, window.state.active, lines)
        if key != self._key:
            self._key, self._since = key, now
        elapsed = max(0, now-self._since)
        # Slow variations during a long operation; text does not change every tick.
        beat = int(elapsed // 8)
        self.speech.setText(lines[beat % len(lines)])
        image_key = (key, beat)
        if image_key != self._image_key:
            candidates = [(pose, variant) for pose in POSES[mood]
                          for variant in range(len(self.portrait.atlases))]
            previous = (self.portrait.pose, self.portrait.variant)
            if self._image_key is not None and previous in candidates:
                candidates.remove(previous)
            self.portrait.pose, self.portrait.variant = self._random.choice(candidates)
            self._image_key = image_key
        self.portrait.mood = mood
        self.portrait.elapsed = elapsed
        self.portrait.update()
        step_key = (window.state.active, window.state.completed, mood)
        if step_key != self._step_key:
            self._step_key = step_key
            for index, label in enumerate(self.steps):
                active = index == window.state.active
                done = index < window.state.completed and not active
                color = '#FFE08A' if active and mood == 'attention' else '#24C8DB' if active else '#39D98A' if done else '#60748B'
                label.setText(f'{"✓" if done else f"{index+1:02d}"}\n{SHORT_NAMES[index]}')
                label.setStyleSheet(f'color: {color}; border: 1px solid {color}; border-radius: 4px; padding: 2px; font-size: 10px; background: #101923;')
                label.setAccessibleDescription('進行中' if active else '完了' if done else '待機')
