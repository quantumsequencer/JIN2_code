"""Close ONLY our isolated Stub Gateway while a command is pending."""
import json
import os
from pathlib import Path
import subprocess
import time

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from gateway_window import GatewayWindow

root = Path(__file__).resolve().parent
settings = json.loads((root / '.stub_gateway/settings.json').read_text(encoding='utf-8-sig'))['Values']
assert all(settings[k] == v for k, v in [('HostPortUnit', 'StubHostPort0'),
                                        ('DebugPortUnit', 'StubDebugPort0'), ('LogPortUnit', 'StubLogPort0')])
app = QApplication([])
w = GatewayWindow()
# Stub generator positions only; these are not real-device travel limits.
w.piezo_lower.setText('0')
w.piezo_upper.setText('40000')
w.sub_port.setValue(55665)
w.push_port.setValue(55666)


def pump(predicate, timeout=10):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError(w.console.toPlainText()[-2000:])


try:
    w.toggle_connection()
    pump(lambda: w.available)
    # Exercise disconnection during an indefinite Hold Gap operation in Stub only.
    w.state.configured = True
    w.state.completed = 11
    w.gap_choice.setCurrentIndex(0)
    w.measure()
    pump(lambda: w.state.measurement)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                    str(root / 'stop_stub_check.ps1')], check=True, timeout=15)
    pump(lambda: w.engine.faulted)
    assert not w.state.configured and not w.available
    assert not w.measure_button.isEnabled() and not w.batch_button.isEnabled()
    assert w.operation is None and not w.engine.busy
    assert w.transport.halt.is_set()
    assert not w.engine.start([])
    print('PASS: disconnect during Hold Gap latches unknown state, disables commands, '
          'clears pending work, prevents automatic reconnect/replay; isolated Gateway stopped.')
finally:
    w.allow_close = True
    w.close()
