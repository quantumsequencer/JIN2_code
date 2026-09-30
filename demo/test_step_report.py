import unittest
from unittest.mock import patch
from workflow import Workflow
from step_report import StepReport
from worker_progress import WorkerProgress


class StepReportTests(unittest.TestCase):
    def test_calibration_metrics_and_last_slope_are_reported(self):
        r = StepReport()
        r.calibration_gap_sensitivity_pm_per_um = 56.7
        r.calibration_slope_log10_a_per_nm = -0.000290338
        r.feed('[Calibration.cpp:320] Cal amplitude=-1.5, Last Slope(pm/nm)=0.0921153419')
        self.assertAlmostEqual(r.calibration_last_slope_pm_per_um, 92.1153419)
        text = r.describe()
        self.assertIn('Gap Sensitivity 56.7 pm/µm / 傾き -0.000290338 log10(A)/nm', text)
        self.assertIn('Last Slope 92.1153419 pm/µm', text)

    def test_training_endpoints_axes_stale_and_duplicates(self):
        for axis in ('Motor', 'Piezo'):
            r = StepReport()
            up = '[ActuatorTraining.cpp:249] Up OK[0].'
            down = '[ActuatorTraining.cpp:278] Down OK[0].'
            r.feed(up, {'motor': 1, 'piezo': 2}, 0.01)
            self.assertFalse(r.training_positions)
            r.feed(f'Actuator Training({axis}) start!')
            r.feed(up, {'motor': 10, 'piezo': 1000}, 0.01)
            r.feed(up, {'motor': 99, 'piezo': 9999}, 0.01)
            r.feed(down, {'motor': 7, 'piezo': -2000}, 0.02)
            expected = {'Up': 10, 'Down': 7} if axis == 'Motor' else {'Up': 1000, 'Down': -2000}
            self.assertEqual(r.training_positions[0], expected)
            self.assertIn('-3 | 3' if axis == 'Motor' else '-3000 | 3000', r.describe())
            r.feed(up.replace('[0]', '[1]'), {'motor': 4, 'piezo': 5}, 0.6)
            self.assertIsNone(r.training_positions[1]['Up'])
            self.assertIn('取得できず', r.describe())
            r.finish('完了')
            r.feed(down.replace('[0]', '[1]'), {'motor': 4, 'piezo': 5}, 0.01)
            self.assertNotIn('Down', r.training_positions[1])

    def test_completion_freezes_time_and_positions(self):
        w = Workflow(configured=True)
        self.assertTrue(w.begin(0))
        r = w.reports[0]
        r.sample({'motor': 123.4, 'piezo': 100})
        r.sample({'motor': 3.4, 'piezo': 200})
        with patch('step_report.time.monotonic', return_value=r.started + 65):
            w.finish()
        self.assertEqual(r.elapsed, 65)
        self.assertIn('00:01:05', r.describe())
        self.assertIn('-120', r.describe())
        r.sample({'motor': 1000, 'piezo': 1000})
        self.assertEqual(r.last_position['motor'], 3.4)
        w.reset()
        self.assertEqual(r.status, '完了')
        self.assertIs(w.reports[0], r)
        w.begin(0)
        self.assertIsNot(w.reports[0], r)
        w.stop()
        self.assertIsNotNone(w.reports[0].elapsed)
        self.assertNotEqual(w.reports[0].status, '完了')

    def test_first_cut_logs_and_start_gate(self):
        p = WorkerProgress(4)
        r = StepReport()
        line = '[FirstCut.cpp:272] FC find[1]: cur = 589634, th = 3654970, move = 765.0[um]'
        p.feed(line)
        self.assertFalse(p.fc_seen)
        p.feed('[FirstCut.cpp:239] First Cut start!')
        for index in (1, 1, 2, 3):
            event = line.replace('find[1]', f'find[{index}]')
            p.feed(event)
            r.feed(event)
        self.assertIn('切断検出 3/3回', p.describe())
        self.assertIn('完了通知待ち', p.describe())
        self.assertEqual(r.fc_moves, {1: 765.0, 2: 765.0, 3: 765.0})
        self.assertIn('3回目：765', r.describe())
        self.assertIsNone(r.elapsed)


if __name__ == '__main__':
    unittest.main()
