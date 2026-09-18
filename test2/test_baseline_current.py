import unittest
from unittest.mock import patch
import numpy as np
from baseline_current import BaselineCurrent


def frame(serial, kind=2, value=-12.5):
    rate = {2: 10000, 3: 50000, 4: 100000}[kind]
    return dict(serial=serial, kind=kind, unit='pA', rate=rate,
                values=np.full(rate // 100, value))


class BaselineTests(unittest.TestCase):
    def test_signed_mean_full_second_all_rates(self):
        for kind in (2, 3, 4):
            collector = BaselineCurrent(100)
            for serial in range(101, 201):
                collector.feed(frame(serial, kind, -10 if serial < 151 else 20))
                self.assertEqual(collector.done, serial == 200)
            self.assertEqual(collector.result['mean_pa'], 5)
            self.assertEqual(collector.count, frame(1, kind)['rate'])

    def test_invalid_data_never_produces_mean(self):
        for mode in ('gap', 'unit', 'rate', 'nan'):
            c = BaselineCurrent(10)
            c.feed(frame(11))
            bad = frame(13 if mode == 'gap' else 12, 3 if mode == 'rate' else 2)
            if mode == 'unit': bad['unit'] = 'RAW'
            if mode == 'nan': bad['values'][0] = np.nan
            c.feed(bad)
            self.assertTrue(c.done)
            self.assertIsNone(c.result['mean_pa'])

    def test_timeout(self):
        c = BaselineCurrent()
        with patch('baseline_current.time.monotonic', return_value=c.started + 4):
            c.tick()
        self.assertTrue(c.done)
        self.assertIsNone(c.result['mean_pa'])


if __name__ == '__main__':
    unittest.main()
