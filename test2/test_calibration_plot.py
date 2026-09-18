import unittest

from calibration_plot import CalibrationPlotData


class CalibrationPlotDataTests(unittest.TestCase):
    def test_log_absolute_current_and_200_point_average(self):
        data = CalibrationPlotData()
        data.feed(1234, [1.0] * 100 + [-10.0] * 100)
        self.assertEqual(len(data.raw_log_current), 200)
        self.assertEqual(len(data.block_log_current), 1)
        self.assertAlmostEqual(data.block_piezo[0], 1234)
        self.assertAlmostEqual(data.block_log_current[0], 0.5)

    def test_zero_and_non_finite_values_are_ignored(self):
        data = CalibrationPlotData(block_size=2)
        data.feed(10, [0, float('nan'), float('inf'), 0.1, -100])
        self.assertEqual(list(data.raw_log_current), [-1.0, 2.0])
        self.assertAlmostEqual(data.block_log_current[0], 0.5)

    def test_units_are_normalized_to_amperes(self):
        data = CalibrationPlotData()
        data.feed(10, [1], unit='µA')
        data.feed(10, [1], unit='pA')
        self.assertEqual(list(data.raw_log_current), [-6.0, -12.0])

    def test_clear_removes_raw_block_and_partial_data(self):
        data = CalibrationPlotData(block_size=2)
        data.feed(10, [1])
        data.clear()
        data.feed(20, [100, 100])
        self.assertEqual(list(data.block_piezo), [20.0])


if __name__ == '__main__':
    unittest.main()
