import unittest
from hold_monitor import HoldMonitor
from test_connection import ConnectionTests
from unittest.mock import patch


class HoldTests(unittest.TestCase):
    def test_signed_difference_boundaries_and_reset(self):
        m = HoldMonitor()
        self.assertEqual(m.update(0, -10, -30), (20, True, False))
        self.assertEqual(m.update(1, -9, -30), (21, False, False))
        self.assertFalse(m.update(30.9, -9, -30)[2])
        self.assertTrue(m.update(31, -9, -30)[2])
        self.assertTrue(m.update(32, -30, -30)[1])
        self.assertFalse(m.update(33, 0, -30)[2])
        self.assertIsNone(m.update(34, float('nan'), -30)[1])


class ResetTests(ConnectionTests):
    def test_hold_plot_has_wider_range_and_all_judgment_lines(self):
        w = self.w
        y_range = w.hold_plot.viewRange()[1]
        self.assertAlmostEqual(y_range[0], -30, places=6)
        self.assertAlmostEqual(y_range[1], 30, places=6)
        lines = sorted(item.value() for item in w.hold_plot.items() if hasattr(item, 'value'))
        self.assertEqual(lines, [-20, -10, 0, 10, 20])

    def test_hold_quality_shows_both_ranges_and_plot_follows_latest_time(self):
        import numpy as np
        w = self.w
        w.state.measurement = True
        w.operation = 'measure'
        w.hold_started = 10
        w.hold_target = 100
        w.hold_frames.append(np.array([108.0]))
        w.state.reports[10] = type('Report', (), {
            'baseline_current': {'mean_pa': 100.0}
        })()
        with patch('gateway_window.time.monotonic', return_value=80):
            w.last_host = 80
            w.check_hold_quality()
        self.assertIn('±20 pA：IN', w.hold_lamp.text())
        self.assertIn('±10 pA：IN', w.hold_tight_lamp.text())
        x_range = w.hold_plot.viewRange()[0]
        self.assertAlmostEqual(x_range[0], 10, places=6)
        self.assertAlmostEqual(x_range[1], 70, places=6)

    def test_quality_stop_cancels_recipe_and_stops_sampling(self):
        import numpy as np
        from step_report import StepReport
        from protocol import WORKERS
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.state.reports[10] = StepReport()
        w.state.reports[10].baseline_current = {'status': '正常', 'mean_pa': -20, 'samples': 10000}
        w.gap_applied_raw = 1000000
        w.recipe_pending = [(0.6, 1)]
        w.auto_measure = True
        w.start_job('measure', [WORKERS['hg']])
        self.ack('')
        w.hold_frames.append(np.array([100.0]))
        with patch('gateway_window.time.monotonic', return_value=100):
            w.last_host = 100
            w.check_hold_quality()
        with patch('gateway_window.time.monotonic', return_value=130):
            w.last_host = 130
            w.check_hold_quality()
        w.transport.send.assert_called_with('mcbj stop')
        self.assertFalse(w.recipe_pending)
        self.ack('')
        w.engine.feed('Log', 'HoldGap canceled.')
        w.transport.send.assert_called_with('sv_info_sender stop')
        self.ack('Stop complete. result:0')
        self.assertIn('停止確認済み', w.problem)

    def test_reset_waits_for_finalize_and_clears_display(self):
        w = self.w
        w.state.configured = True
        w.recipe_pending = [(0.6, 1)]
        w.recipe_started_at = 100
        w.measure_progress.setValue(500)
        w.reset()
        self.assertEqual(w.operation, 'finalize')
        self.assertTrue(w.reset_pending)
        w.operation = 'finalize'
        w.command_result('success', '')
        self.assertFalse(w.reset_pending)
        self.assertFalse(w.recipe_pending)
        self.assertIsNone(w.recipe_started_at)
        self.assertEqual(w.measure_progress.value(), 0)
        self.assertIsNone(w.hold_target)


if __name__ == '__main__': unittest.main()
