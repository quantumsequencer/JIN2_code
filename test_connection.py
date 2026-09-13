"""Startup must work before the device begins sending Host samples."""
import os
import time
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from command_engine import CommandEngine
from gateway_window import GatewayWindow


class ConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.w = GatewayWindow()
        self.w.io_timer.stop()
        self.w.plot_timer.stop()
        # Explicit simulated travel range and position; not hardware defaults.
        self.w.piezo_lower.setText('-10000')
        self.w.piezo_upper.setText('30000')
        self.w.telemetry.latest = {'piezo': 0, 'serial': 0}
        self.w.last_host = time.monotonic()
        self.w.transport = SimpleNamespace(connected=True, send=Mock(), close=Mock())
        self.w.engine = CommandEngine(self.w.send_command, self.w.command_result,
                                      self.w.command_accepted)

    def tearDown(self):
        self.w.allow_close = True
        self.w.close()

    def ack(self, text):
        resuming = self.w.operation == 'resume_sampling' and text == 'Start complete. result:0'
        self.w.engine.feed('Debug', text)
        self.w.engine.feed('Debug', '> ')
        if resuming:
            self.w.last_host = time.monotonic()  # Simulate resumed Host reception.

    def test_settings_and_initialization_without_host(self):
        w = self.w
        w.last_host = 0
        w.telemetry.latest = None
        self.assertEqual(w.last_host, 0)
        w.setting_path = Path('settings.txt')
        w.setting_text = 'mcbj set fc up_limit 10000'
        w.refresh()
        self.assertTrue(w.apply_button.isEnabled())
        self.assertIn('Host待ち', w.connection_badge.text())
        w.apply_settings()
        with patch('gateway_window.QTimer.singleShot', side_effect=lambda delay, fn: fn()):
            with patch.object(w.setup_scroll, 'ensureWidgetVisible') as ensure:
                self.ack('Setting change : 0')
        ensure.assert_called_once_with(w.batch_button, 0, 60)
        self.assertTrue(w.state.configured)
        w.run_step(0)
        self.ack('BIAS set complete.')
        self.ack('EP set complete.')
        w.transport.send.assert_called_with('sv_info_sender start 0')
        self.ack('Start complete. result:0')
        self.assertEqual(w.state.completed, 1)
        self.assertFalse(w.host_recent)

    def test_disconnected_or_faulted_still_blocks_commands(self):
        w = self.w
        w.setting_text = 'mcbj set fc up_limit 10000'
        w.transport.connected = False
        w.refresh()
        self.assertFalse(w.apply_button.isEnabled())
        w.transport.connected = True
        w.engine.fail('connection lost')
        w.refresh()
        self.assertFalse(w.apply_button.isEnabled())
        self.assertFalse(w.available)
        w.transport.send.assert_not_called()

    def test_autoload_latest_settings_file(self):
        w = self.w
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'SGMO2_original' / 'JinSettings-0.2.0.09030'
            base.mkdir(parents=True)
            old = base / 'old.txt'
            latest = base / 'latest.txt'
            old.write_text('mcbj set fc up_limit 10000', encoding='utf-8')
            latest.write_text('mcbj set fc up_limit 20000', encoding='utf-8')
            os.utime(old, (10, 10))
            os.utime(latest, (20, 20))
            w.state.configured = True
            with patch('gateway_window.ROOT', root / 'test2'):
                w.autoload_latest_settings()
        self.assertEqual(w.setting_path.name, 'latest.txt')
        self.assertIn('20000', w.setting_text)
        self.assertFalse(w.state.configured)
        self.assertIn('自動選択', w.file_label.text())


if __name__ == '__main__':
    unittest.main()
