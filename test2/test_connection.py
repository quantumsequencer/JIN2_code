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
        recipe_patch = patch('measurement_recipe.load_last_used', return_value=[])
        recipe_patch.start()
        self.addCleanup(recipe_patch.stop)
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

    def test_settings_busy_stops_surviving_hold_gap_then_retries_once(self):
        w = self.w
        w.setting_path = Path('settings.txt')
        w.setting_text = 'mcbj set fc up_limit 10000'
        w.apply_settings()

        self.ack('Setting change : -3')
        self.assertEqual(w.operation, 'settings_recovery')
        self.assertEqual(w.transport.send.call_args.args[0], 'mcbj stop')

        self.ack('')
        self.assertEqual(w.transport.send.call_args.args[0], 'mcbj stop')
        w.engine.feed('Log', 'HoldGap canceled.')
        self.assertEqual(w.transport.send.call_args.args[0], 'mcbj set fc up_limit 10000')

        self.ack('Setting change : 0')
        self.assertTrue(w.state.configured)
        self.assertIsNone(w.operation)
        self.assertEqual(
            [call.args[0] for call in w.transport.send.call_args_list],
            ['mcbj set fc up_limit 10000', 'mcbj stop',
             'mcbj set fc up_limit 10000'])

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

    def test_autoload_default_settings_file(self):
        w = self.w
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / 'test2' / 'setting parameter'
            base.mkdir(parents=True)
            old = base / 'setting_parameter.txt'
            latest = base / 'latest.txt'
            old.write_text('mcbj set fc up_limit 10000', encoding='utf-8')
            latest.write_text('mcbj set fc up_limit 20000', encoding='utf-8')
            os.utime(old, (10, 10))
            os.utime(latest, (20, 20))
            w.state.configured = True
            with patch('gateway_window.ROOT', root / 'test2'):
                w.autoload_default_settings()
        self.assertEqual(w.setting_path.name, 'setting_parameter.txt')
        self.assertIn('10000', w.setting_text)
        self.assertFalse(w.state.configured)
        self.assertIn('未適用', w.file_label.text())
        w.transport.send.assert_not_called()

    def test_settings_dialog_preselects_default_file(self):
        with patch('gateway_window.QFileDialog.getOpenFileName', return_value=('', '')) as dialog:
            self.w.select_settings()
        from gateway_window import ROOT
        self.assertEqual(Path(dialog.call_args.args[2]),
                         ROOT / 'setting parameter' / 'setting_parameter.txt')

    def test_selected_settings_are_restored_without_applying(self):
        with TemporaryDirectory() as tmp, patch('gateway_window.ROOT', Path(tmp)):
            path = Path(tmp) / '前回の設定.txt'
            path.write_text('mcbj set fc up_limit 20000', encoding='utf-8')
            with patch('gateway_window.QFileDialog.getOpenFileName', return_value=(str(path), '')):
                self.w.select_settings()
            self.w.setting_path = None
            self.w.setting_text = ''
            self.w.state.configured = True
            self.w.autoload_default_settings()
            self.assertEqual(self.w.setting_path, path)
            self.assertIn('20000', self.w.setting_text)
            self.assertFalse(self.w.state.configured)
            self.assertIn('未適用', self.w.file_label.text())
            self.w.transport.send.assert_not_called()

    def test_missing_previous_file_requires_selection(self):
        with TemporaryDirectory() as tmp, patch('gateway_window.ROOT', Path(tmp)):
            (Path(tmp) / '.last_settings_path').write_text(
                str(Path(tmp) / 'missing.txt'), encoding='utf-8')
            self.w.autoload_default_settings()
            self.assertIsNone(self.w.setting_path)
            self.assertEqual(self.w.setting_text, '')
            self.assertIn('選択してください', self.w.file_label.text())
            self.w.transport.send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
