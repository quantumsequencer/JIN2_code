"""Integration check against ONLY the isolated, all-Stub Gateway copy."""
import json
import os
import time
from pathlib import Path

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase
from gateway_window import GatewayWindow

ROOT = Path(__file__).resolve().parent
settings = json.loads((ROOT / '.stub_gateway/settings.json').read_text(encoding='utf-8-sig'))['Values']
assert [settings[key] for key in ('HostPortUnit', 'DebugPortUnit', 'LogPortUnit')] == [
    'StubHostPort0', 'StubDebugPort0', 'StubLogPort0']
config = json.loads((ROOT / '.stub_gateway/config.json').read_text(encoding='utf-8-sig'))
assert (config['PubPort'], config['PullPort']) == (55665, 55666)

app = QApplication([])
for font in ('segoeui.ttf', 'YuGothR.ttc', 'meiryo.ttc'):
    QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + font)
app.setStyle('Fusion')
app.setStyleSheet((ROOT / 'style.qss').read_text(encoding='utf-8'))
w = GatewayWindow()
# Stub generator positions only; these are not real-device travel limits.
w.piezo_lower.setText('0')
w.piezo_upper.setText('40000')
w.show()


def wait_for(predicate, timeout=25):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if w.problem:
            raise AssertionError(w.problem + '\n' + w.console.toPlainText()[-3000:])
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('Timeout\n' + w.console.toPlainText()[-3000:])


try:
    assert not w.apply_button.isEnabled()
    w.sub_port.setValue(55665)
    w.push_port.setValue(55666)
    w.toggle_connection()
    wait_for(lambda: w.available)
    assert w.telemetry.latest['rate'] == 100000
    w.setting_path = next((ROOT.parent / 'SGMO2_original/JinSettings-0.2.0.09030').glob('*_初期値.txt'))
    w.setting_text = w.setting_path.read_text(encoding='utf-8-sig')
    w.apply_settings()
    wait_for(lambda: w.state.configured and not w.operation)
    w.run_batch()
    wait_for(lambda: w.state.active == 2)
    assert w.chip_button.isVisible() and not w.engine.busy
    w.confirm_chip()
    wait_for(lambda: w.state.ready and not w.operation)
    w.apply_gap_target()
    wait_for(lambda: not w.operation)
    assert w.gap_matches_selection() and w.state.ready
    w.measure()
    wait_for(lambda: w.state.measurement)
    w.update_plots()
    app.processEvents()
    assert w.grab().save(str(ROOT / 'gateway-preview.png'))
    w.stop()
    wait_for(lambda: not w.operation and not w.state.measurement)
    assert w.state.ready
    w.reset()
    wait_for(lambda: not w.operation)
    assert w.state.completed == 0 and not w.touched
    # Stop a worker in flight, then retry only the incomplete stage.
    for index in range(4):
        w.run_step(index)
        if index == 2:
            w.confirm_chip()
        wait_for(lambda: not w.operation)
    w.run_step(4)
    wait_for(lambda: w.engine.ack)
    w.stop()
    wait_for(lambda: not w.operation)
    assert w.state.completed == 4
    w.run_step(4)
    wait_for(lambda: not w.operation)
    assert w.state.completed == 5
    # Closing the window runs the complete finalization sequence first.
    w.close()
    wait_for(lambda: w.allow_close)
    (ROOT / 'gateway-check.log').write_text(w.console.toPlainText(), encoding='utf-8')
    print('PASS: actual Gateway Stub, 100 kHz Host, full settings, batch setup, chip pause, '
          'Hold Gap start/stop, reset, worker stop/retry, graceful close.')
finally:
    w.allow_close = True
    w.close()
