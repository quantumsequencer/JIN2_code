from decimal import Decimal
import unittest
from gap_target import target_for_distance, target_command, raw_from_command, OLD_PA_PER_RAW, NEW_RAW_PER_PA
from test_connection import ConnectionTests
from gap_target import model_target
from step_report import StepReport
from unittest.mock import patch


class GapConversionTests(unittest.TestCase):
    def test_054_preserves_physical_current(self):
        pa, raw = target_for_distance('0.54')
        self.assertEqual(pa, Decimal('22.759446322754'))
        self.assertEqual(raw, 0x07E6FAA1)
        self.assertLess(abs(Decimal(raw) / NEW_RAW_PER_PA - pa), 1 / NEW_RAW_PER_PA)
        self.assertNotEqual(raw, 0x05098121)
        self.assertEqual(target_command('0.54').text, 'asz set hg tunnel_current 0x07E6FAA1')

    def test_old_gain_matches_new_workbook_reference_currents(self):
        # SGMO2 HoldGap workbook reference: 0.62 nm = 3.448268 pA; 0.66 nm = 1.342210 pA.
        for old, pa in [(0x00C35F36, '3.448268'), (0x004C0C02, '1.342210')]:
            self.assertLess(abs(Decimal(old) * OLD_PA_PER_RAW - Decimal(pa)), Decimal('0.000001'))

    def test_parse_only_target_commands(self):
        self.assertEqual(raw_from_command('asz set hg tunnel_current 0x07E6FAA1'), 0x07E6FAA1)
        self.assertIsNone(raw_from_command('asz hg start'))


class GapUiTests(ConnectionTests):
    def setUp(self):
        super().setUp()
        self.w.state.reports[10] = StepReport()
        self.w.state.reports[10].baseline_current = {'status': '正常', 'mean_pa': 0.1, 'samples': 10000}

    def test_apply_keeps_ready_but_requires_ack(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.refresh()
        self.assertFalse(w.measure_button.isEnabled())
        w.apply_gap_target()
        w.transport.send.assert_called_once_with(f'asz set hg tunnel_current 0x{model_target(0.6)[1]:08X}')
        self.assertIsNone(w.gap_applied_raw)
        self.ack('Setting change : 0')
        self.assertTrue(w.state.ready)
        self.assertTrue(w.measure_button.isEnabled())
        w.measure()
        self.ack('')
        self.assertTrue(w.state.measurement)
        self.assertFalse(w.gap_apply_button.isEnabled())
        count = w.transport.send.call_count
        w.apply_gap_target()
        self.assertEqual(w.transport.send.call_count, count)

    def test_timed_stop_requires_both_stop_confirmations(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.apply_gap_target()
        self.ack('Setting change : 0')
        w.measure()
        self.assertIsNone(w.measure_deadline)
        self.ack('')
        with patch('gateway_window.time.monotonic', return_value=w.measure_deadline + 1):
            w.check_measure_time()
        w.transport.send.assert_called_with('mcbj stop')
        self.assertTrue(w.timed_finish)
        self.ack('')
        w.engine.feed('Log', 'HoldGap canceled.')
        w.transport.send.assert_called_with('sv_info_sender stop')
        self.assertTrue(w.timed_finish)
        with patch('gateway_window.QTimer.singleShot'):
            self.ack('Stop complete. result:0')
        self.assertFalse(w.timed_finish)
        self.assertFalse(w.state.ready)
        self.assertIn('計測完了', w.problem)

    def test_model_and_missing_baseline(self):
        tunnel, raw = model_target('0.60')
        self.assertAlmostEqual(float(tunnel), 8.307871188, places=7)
        self.assertLess(abs(Decimal(raw) / NEW_RAW_PER_PA - tunnel), 1 / NEW_RAW_PER_PA)
        for d in ('0', '0.001', '10'):
            with self.assertRaises(ValueError):
                model_target(d)
        self.w.state.configured = True
        self.w.state.completed = 11
        self.w.state.reports.clear()
        self.w.apply_gap_target()
        self.w.measure()
        self.w.transport.send.assert_not_called()

    def test_negative_baseline_does_not_change_sent_current(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.state.reports[10].baseline_current['mean_pa'] = -18.960622
        w.gap_choice.setValue(0.610)
        w.refresh()
        self.assertTrue(w.gap_apply_button.isEnabled())
        w.apply_gap_target()
        current, raw = model_target('0.610')
        self.assertAlmostEqual(float(current), 6.606826293, places=7)
        w.transport.send.assert_called_once_with(f'asz set hg tunnel_current 0x{raw:08X}')
        self.ack('Setting change : 0')
        self.assertTrue(w.measure_button.isEnabled())

    def test_failed_apply_never_enables_measurement(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.apply_gap_target()
        self.ack('Setting change : -1')
        self.assertIsNone(w.gap_applied_raw)
        self.assertTrue(w.state.ready)
        self.assertFalse(w.measure_button.isEnabled())


if __name__ == '__main__':
    unittest.main()
