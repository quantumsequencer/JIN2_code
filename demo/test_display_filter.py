import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import numpy as np
from display_filter import lowpass


class FilterTests(unittest.TestCase):
    def test_frequency_response_and_raw_preservation(self):
        t = np.arange(10000) / 1000
        raw = 3 + np.sin(2*np.pi*t) + np.sin(2*np.pi*200*t)
        before = raw.copy()
        filtered = lowpass(t, raw, 10)
        reference = 3 + np.sin(2*np.pi*t)
        self.assertLess(np.std((filtered-reference)[1000:]), 0.08)
        self.assertGreater(np.std((lowpass(t, raw, 300)-reference)[1000:]), 0.4)
        np.testing.assert_array_equal(raw, before)

    def test_constant_empty_and_gap(self):
        np.testing.assert_allclose(lowpass(np.arange(10), np.ones(10)*4, 1), 4)
        self.assertEqual(len(lowpass([], [], 1)), 0)
        np.testing.assert_allclose(lowpass([0, .01, 1, 1.01], [0, 0, 10, 10], 1), [0, 0, 10, 10])
        result = lowpass([0, .01, .02, .03], [1, np.nan, 5, 5], 1)
        np.testing.assert_allclose(result, [1, np.nan, 5, 5])


class DisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def test_both_windows_and_live_data(self):
        from main import MainWindow
        from gateway_window import GatewayWindow
        from test_protocol import frame
        from types import SimpleNamespace
        for window_type in (MainWindow, GatewayWindow):
            with self.subTest(window=window_type.__name__):
                w = window_type()
                try:
                    w.show()
                    self.app.processEvents()
                    self.assertFalse(w.detail_dialog.isVisible())
                    self.assertFalse(w.rows[0][1].isVisible())
                    self.assertTrue(w.stop_button.isVisible())
                    self.assertTrue(w.progress.isVisible())
                    self.assertGreater(w.right_scroll.width(), w.width() * .65)
                    w.detail_button.click()
                    self.app.processEvents()
                    self.assertTrue(w.detail_dialog.isVisible())
                    self.assertTrue(w.rows[0][1].isVisible())
                    self.assertTrue(w.lowpass_cutoff.isVisible())
                    w.detail_dialog.close()
                    self.assertTrue(w.stats.isHidden())
                    self.assertFalse(w.median_curve.isVisible())
                    self.assertIs(w.piezo_plot.linkedView(0), w.motor_plot.plotItem.vb)
                    np.testing.assert_allclose(w.piezo_plot.viewRange()[0], w.motor_plot.viewRange()[0], atol=1e-12)
                    if isinstance(w, GatewayWindow):
                        w.telemetry.feed(frame())
                        raw = w.telemetry.latest['values'].copy()
                        w.transport = SimpleNamespace(host_dropped=0, close=lambda: None)
                        w.host_dirty = True
                        w.update_plots()
                        np.testing.assert_array_equal(raw, w.telemetry.latest['values'])
                    w.lowpass_cutoff.setValue(2)
                    self.assertGreater(len(w.current_curve.getData()[0]), 0)
                    x, raw_values = w._display_raw
                    np.testing.assert_array_equal(w.raw_current_curve.getData()[1], raw_values)
                    np.testing.assert_allclose(w.current_curve.getData()[1], lowpass(x, raw_values, 2))
                    w.lowpass_cutoff.setValue(100)
                    np.testing.assert_array_equal(w.raw_current_curve.getData()[1], raw_values)
                    np.testing.assert_allclose(w.current_curve.getData()[1], lowpass(x, raw_values, 100))
                    w.reset_plot_scales()
                    w.clear_display_history()
                    w.lowpass_cutoff.setValue(5)
                    cleared = w.current_curve.getData()[0]
                    self.assertTrue(cleared is None or len(cleared) == 0)
                    raw_cleared = w.raw_current_curve.getData()[0]
                    self.assertTrue(raw_cleared is None or len(raw_cleared) == 0)
                    w.details_toggle.setChecked(True)
                    self.assertFalse(w.stats.isHidden())
                finally:
                    w.close()

    def test_chip_confirmation_and_active_progress_stay_on_main_screen(self):
        from main import MainWindow
        w = MainWindow()
        try:
            w.show()
            w.state.active = 2
            w.refresh()
            self.app.processEvents()
            self.assertTrue(w.chip_button.isVisible())
            self.assertFalse(w.detail_dialog.isVisible())
            w.state.active = 5
            w.refresh()
            w.plot_timer.timeout.emit()
            self.assertFalse(w.chip_button.isVisible())
            self.assertTrue(w.active_step_progress.isVisible())
            self.assertEqual(w.active_step_progress.maximum(), 10)
            self.assertEqual(w.active_step_progress.value(), w.motor_training_progress.value())
        finally:
            w.close()


if __name__ == '__main__':
    unittest.main()
