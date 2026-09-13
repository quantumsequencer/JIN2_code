import unittest
from unittest.mock import patch
from piezo_guard import range_problem
from protocol import WORKERS
from test_connection import ConnectionTests


class RangeTests(unittest.TestCase):
    def test_limits_and_endpoints(self):
        for position in (-100, 0, 100):
            self.assertEqual(range_problem('-100', '100', position), '')
        for position in (-101, 101, float('nan'), float('inf')):
            self.assertIn('レンジ外', range_problem('-100', '100', position))

    def test_missing_or_invalid_configuration(self):
        for lower, upper in [('', ''), ('nan', '10'), ('0', 'inf'), ('1', '1'), ('2', '1')]:
            self.assertTrue(range_problem(lower, upper, 0))
        self.assertIn('未取得', range_problem('-100', '100'))


class PiezoStopTests(ConnectionTests):
    def test_no_start_without_limits_or_position(self):
        self.w.piezo_lower.clear()
        self.assertFalse(self.w.start_job('measure', [WORKERS['hg']]))
        self.w.piezo_lower.setText('-10000')
        self.w.telemetry.latest = None
        self.assertFalse(self.w.start_job('measure', [WORKERS['hg']]))
        self.w.transport.send.assert_not_called()

    def test_each_worker_stops_and_cancels_following_commands(self):
        w = self.w
        for name, index in [('fc', 4), ('target', 5), ('mt', 5), ('pt', 6), ('ac', 7), ('cal', 9), ('eg', 10), ('hg', None)]:
            with self.subTest(worker=name):
                w.operation = None
                w.host_paused = False
                w.telemetry.latest = {'piezo': 0}
                w.state.active = index
                w.state.batch = True
                w.auto_measure = True
                w.recipe_pending = [(0.6, 1)]
                operation = 'measure' if name == 'hg' else 'step'
                # Avoid measurement setup callback; test real command/stop handling.
                with patch.object(w.engine, 'accepted'):
                    self.assertTrue(w.start_job(operation, [WORKERS[name], WORKERS['pt']]))
                    self.ack('')
                w.telemetry.latest = {'piezo': 30001}
                w.check_piezo_range()
                w.transport.send.assert_called_with('mcbj stop')
                self.assertFalse(w.state.batch)
                self.assertFalse(w.auto_measure)
                self.assertFalse(w.recipe_pending)
                count = w.transport.send.call_count
                w.check_piezo_range()
                self.assertEqual(w.transport.send.call_count, count)
                self.ack('')
                self.assertEqual(w.operation, 'stop')
                canceled = {'fc': 'First Cut canceld!', 'target': 'Targeting canceled.',
                            'mt': 'Actuator Training(Motor) canceld!', 'pt': 'Actuator Training(Piezo) canceld!',
                            'ac': 'End. Canceled.', 'cal': 'Calibration canceld!',
                            'eg': 'ExpandGap canceled.', 'hg': 'HoldGap canceled.'}[name]
                w.engine.feed('Log', canceled)
                w.transport.send.assert_called_with('sv_info_sender stop')
                self.ack('Stop complete. result:0')
                self.assertIsNone(w.operation)
                self.assertIn('停止確認済み', w.problem)

    def test_stop_waits_for_start_prompt(self):
        w = self.w
        w.start_job('measure', [WORKERS['hg']])
        w.telemetry.latest = {'piezo': -10001}
        w.check_piezo_range()
        w.transport.send.assert_called_once_with('asz hg start')
        self.ack('')
        w.transport.send.assert_called_with('mcbj stop')

    def test_stop_timeout_remains_uncertain(self):
        w = self.w
        w.start_job('measure', [WORKERS['hg']])
        w.telemetry.latest = {'piezo': 30001}
        w.check_piezo_range()
        self.ack('')
        with patch.object(w.engine, 'clock', return_value=w.engine.deadline + 1):
            w.engine.tick()
        self.assertTrue(w.engine.faulted)
        self.assertIn('状態未確認', w.problem)

    def test_stale_host_blocks_start(self):
        self.w.last_host = 0
        self.assertFalse(self.w.start_job('measure', [WORKERS['hg']]))
        self.w.transport.send.assert_not_called()

    def test_resumption_waits_for_host(self):
        w = self.w
        w.operation = 'await_piezo_host'
        w.auto_measure = True
        w.last_host = 0
        with patch.object(w, 'run_step') as run:
            w.expand_after_host()
            run.assert_not_called()
            import time
            w.last_host = time.monotonic()
            w.expand_after_host()
            run.assert_called_once_with(10)

    def test_report_keeps_range_reason(self):
        from step_report import StepReport
        w = self.w
        w.state.active = 6
        w.state.reports[6] = StepReport()
        with patch('report_view.save_report'):
            w.start_job('step', [WORKERS['pt']])
            self.ack('')
            w.telemetry.latest = {'piezo': 30001}
            w.check_piezo_range()
            self.ack('')
            w.engine.feed('Log', 'Actuator Training(Piezo) canceld!')
            self.assertIn('Piezoレンジ外', w.state.reports[6].status)


if __name__ == '__main__':
    unittest.main()
