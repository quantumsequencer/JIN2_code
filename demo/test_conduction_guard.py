import unittest
from unittest.mock import patch
from conduction_guard import ConductionGuard
from test_connection import ConnectionTests
from protocol import WORKERS


class ConductionTests(unittest.TestCase):
    def run_current(self, current):
        guard = ConductionGuard(0)
        reason = ''
        for tick in range(1, 61):
            reason = guard.check(tick / 10, {'unit': 'µA', 'values': [current]})
            if reason or guard.ready:
                break
        return guard, reason, tick / 10

    def test_low_current_stops_after_settling_and_three_windows(self):
        guard, reason, elapsed = self.run_current(0.013)
        self.assertIn('導通異常', reason)
        self.assertEqual(elapsed, 6)
        self.assertFalse(guard.ready)

    def test_threshold_passes_only_after_full_window(self):
        guard, reason, elapsed = self.run_current(9)
        self.assertTrue(guard.ready)
        self.assertEqual(elapsed, 4)
        self.assertFalse(reason)

    def test_missing_and_invalid_data(self):
        self.assertIn('途絶', ConductionGuard(0).check(1))
        for unit, values in [('RAW', [9]), ('µA', []), ('µA', [float('nan')])]:
            guard = ConductionGuard(0)
            guard.last_received = 2.9
            self.assertTrue(guard.check(3, {'unit': unit, 'values': values}))


class GuardIntegrationTests(ConnectionTests):
    def test_first_cut_waits_for_conduction(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 4
        with patch('gateway_window.time.monotonic', return_value=100):
            w.run_step(4)
        w.transport.send.assert_not_called()
        for tick in range(1, 41):
            with patch('gateway_window.time.monotonic', return_value=100 + tick / 10):
                w.last_host = 100 + tick / 10
                w.check_conduction_guard({'unit': 'µA', 'values': [10]})
        w.transport.send.assert_called_with('mcbj fc start')

    def test_target_limits_cancel_next_worker(self):
        import time
        for limit in ('time', 'distance', 'missing'):
            w = self.w
            w.operation = None
            w.telemetry.latest = {'piezo': 0, 'motor': 0}
            w.last_host = time.monotonic()
            w.start_job('step', [WORKERS['target'], WORKERS['mt']])
            self.ack('')
            if limit == 'time':
                w.target_guard = (time.monotonic() - 15, 0)
            elif limit == 'distance':
                w.telemetry.latest['motor'] = -200
            else:
                w.last_host = time.monotonic() - 1
            w.check_conduction_guard()
            w.transport.send.assert_called_with('mcbj stop')
            self.ack('')
            w.engine.feed('Log', 'Targeting canceled.')
            self.assertNotIn('mcbj mt start', [c.args[0] for c in w.transport.send.call_args_list])
            self.assertIn('停止確認済み', w.problem)


if __name__ == '__main__':
    unittest.main()
