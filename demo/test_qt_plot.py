"""Check Qt selection in fresh processes, without other tests masking it."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


class QtBindingTests(unittest.TestCase):
    def test_each_plot_entry_uses_pyside6(self):
        for module in ('main', 'gateway_window', 'calibration_plot', 'report_view'):
            with self.subTest(module=module):
                env = dict(os.environ, QT_QPA_PLATFORM='offscreen',
                           PYQTGRAPH_QT_LIB='PyQt6')
                code = f'''
import importlib
module = importlib.import_module({module!r})
from PySide6.QtWidgets import QApplication, QSizePolicy, QWidget
assert module.pg.Qt.QT_LIB == 'PySide6'
app = QApplication([])
plot = module.pg.PlotWidget()
assert isinstance(plot, QWidget)
plot.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
plot.close()
from gateway_window import GatewayWindow
window = GatewayWindow()
window.close()
'''
                result = subprocess.run(
                    [sys.executable, '-B', '-c', code],
                    cwd=Path(__file__).resolve().parent, env=env,
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
