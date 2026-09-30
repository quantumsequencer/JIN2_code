import unittest
from worker_progress import WorkerProgress


class ProgressTests(unittest.TestCase):
    def test_pairs_duplicates_and_start_gate(self):
        p = WorkerProgress(5)
        up = '[ActuatorTraining.cpp:249] Up   OK[0]. th:0x01'
        down = '[ActuatorTraining.cpp:278] Down OK[0]. th:0x02'
        p.feed(up)
        self.assertFalse(p.seen)
        p.feed('Actuator Training(Piezo) start!')
        p.feed(up)
        self.assertFalse(p.seen)
        p.feed('Actuator Training(Motor) start!\n' + up)
        self.assertIn('往復確認 0回', p.describe())
        p.feed(down + '\n' + down)
        self.assertIn('往復確認 1回', p.describe())
        p.feed('[Calibration.cpp:303] Up OK[1].')
        self.assertEqual(len(p.seen), 2)

    def test_calibration_ten_is_not_completion(self):
        p = WorkerProgress(9)
        p.feed('Calibration start!')
        for i in range(10):
            p.feed(f'[Calibration.cpp:266] Down OK[{i}].\n'
                   f'[Calibration.cpp:303] Up OK[{i}].\n'
                   f'[Calibration.cpp:313] Cal Result[{i}], Up pos=9200')
        self.assertIn('往復確認 10回', p.describe())
        self.assertIn('装置の完了通知待ち', p.describe())
        self.assertEqual(len(p.seen), 20)


if __name__ == '__main__':
    unittest.main()
