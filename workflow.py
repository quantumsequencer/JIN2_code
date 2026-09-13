"""UI review simulator. No hardware or network access."""
from dataclasses import dataclass, field
from step_report import StepReport

STEPS = [
    ("初期化", "Bias・EPを0に設定し、Low 10 kHz測定を開始"),
    ("ゼロ点へ移動", "Motor・Piezoを基準位置へ移動"),
    ("チップ装着", "チップの装着を確認してから続行"),
    ("Bias印加", "Biasを0.1 Vに設定"),
    ("First Cut", "初回の切断工程"),
    ("Motor Training", "Targeting → Motor Training"),
    ("Piezo Training", "Targeting → Piezo Training"),
    ("Auto Cut", "Targeting → Auto Cut"),
    ("測定回路切り替え", "Bias 0 → 測定停止 → High測定 → Bias 0.1 V"),
    ("Calibration", "測定回路を校正"),
    ("Expand Gap", "ギャップを広げ、測定準備を完了"),
]

@dataclass
class Workflow:
    configured: bool = False
    completed: int = 0
    active: int | None = None
    measurement: bool = False
    batch: bool = False
    reports: dict = field(default_factory=dict)

    @property
    def ready(self):
        return self.configured and self.completed == len(STEPS) and self.active is None

    def begin(self, index, batch=False):
        if not self.configured or self.measurement or self.active is not None:
            return False
        if index != self.completed or not 0 <= index < len(STEPS):
            return False
        self.active, self.batch = index, batch
        self.reports[index] = StepReport()
        return True

    def finish(self):
        if self.active is None:
            return
        self.reports[self.active].finish('完了')
        self.completed = self.active + 1
        self.active = None

    def stop(self):
        if self.active in self.reports:
            self.reports[self.active].finish('中断・停止（装置の停止確認はログ参照）')
        self.active = None
        self.batch = False
        self.measurement = False

    def reset(self):
        self.stop()
        self.completed = 0

    def start_measurement(self):
        if not self.ready or self.measurement:
            return False
        self.measurement = True
        return True
