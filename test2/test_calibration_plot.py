import unittest

from calibration_plot import CalibrationPlotData, gap_sensitivity_from_slope


class CalibrationPlotDataTests(unittest.TestCase):
    def test_gap_sensitivity_is_calculated_from_absolute_slope(self):
        sensitivity = gap_sensitivity_from_slope(-0.000290338)
        self.assertAlmostEqual(sensitivity, 56.7, delta=0.2)
        self.assertAlmostEqual(
            gap_sensitivity_from_slope(0.000290338), sensitivity)

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

    def test_blocks_track_direction_and_directional_pass(self):
        data = CalibrationPlotData(block_size=1)
        for piezo in (10, 20, 30, 20, 10, 20):
            data.feed(piezo, [1])
        self.assertEqual(list(data.block_direction), [0, 1, 1, -1, -1, 1])
        self.assertEqual(list(data.block_pass), [1, 1, 1, 2, 2, 3])

    def test_clear_resets_directional_pass(self):
        data = CalibrationPlotData(block_size=1)
        for piezo in (10, 20, 10):
            data.feed(piezo, [1])
        data.clear()
        data.feed(50, [1])
        self.assertEqual(list(data.block_direction), [0])
        self.assertEqual(list(data.block_pass), [1])

    def test_initial_lower_limit_approach_is_not_recorded(self):
        data = CalibrationPlotData(block_size=1, wait_for_first_reversal=True)
        for piezo in (10, 20, 30):
            data.feed(piezo, [100])
        self.assertEqual(list(data.raw_piezo), [])
        data.feed(20, [10])  # first reversal starts the calibration sweep
        data.feed(10, [1])
        self.assertEqual(list(data.raw_piezo), [20.0, 10.0])
        self.assertEqual(list(data.raw_log_current), [1.0, 0.0])

    def test_clear_waits_for_first_reversal_again(self):
        data = CalibrationPlotData(block_size=1, wait_for_first_reversal=True)
        for piezo in (10, 20, 10):
            data.feed(piezo, [1])
        self.assertEqual(list(data.raw_piezo), [10.0])
        data.clear()
        for piezo in (30, 40):
            data.feed(piezo, [1])
        self.assertEqual(list(data.raw_piezo), [])

    def test_linear_fit_uses_all_raw_points(self):
        data = CalibrationPlotData()
        data.feed(10, [1, 10])
        data.feed(20, [100, 1000])
        slope, intercept = data.linear_fit()
        self.assertAlmostEqual(slope, 0.2)
        self.assertAlmostEqual(intercept, -1.5)

    def test_linear_fit_requires_two_distinct_piezo_values(self):
        data = CalibrationPlotData()
        self.assertIsNone(data.linear_fit())
        data.feed(10, [1, 10])
        self.assertIsNone(data.linear_fit())

    def test_linear_fit_uses_within_pass_slope(self):
        data = CalibrationPlotData(block_size=1)
        # Both passes have slope -1 but very different vertical positions.
        for piezo, log_current in ((0, 1), (1, 0), (2, -1),
                                   (1, 9), (0, 10)):
            data.feed(piezo, [10.0 ** log_current])
        slope, _ = data.linear_fit()
        self.assertAlmostEqual(slope, -1.0)

    def test_linear_fit_excludes_repeated_upper_limit(self):
        data = CalibrationPlotData(block_size=3)
        data.feed(0, [1000, 990, 1010] * 3)  # noisy upper-limit hold
        data.feed(1, [10])
        data.feed(2, [1])
        slope, intercept = data.linear_fit()
        self.assertAlmostEqual(slope, -1.0)
        self.assertAlmostEqual(intercept, 2.0)
        x, y, excluded = data.fit_points()
        self.assertEqual(list(x), [1.0, 2.0])
        self.assertEqual(list(y), [1.0, 0.0])
        self.assertEqual(excluded, 9)

    def test_single_maximum_is_not_treated_as_saturation(self):
        data = CalibrationPlotData(block_size=3)
        data.feed(0, [1000, 1000, 1000])
        data.feed(1, [10, 10, 10])
        data.feed(2, [1, 1, 1])
        self.assertEqual(data.fit_points()[2], 0)
        slope, _ = data.linear_fit()
        self.assertAlmostEqual(slope, -1.5)


if __name__ == '__main__':
    unittest.main()
