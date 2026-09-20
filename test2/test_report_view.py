import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from dataclasses import asdict
from PySide6.QtWidgets import QApplication
from step_report import StepReport
from report_view import save_report, load_reports, numeric_rows, histogram_peaks, ReportDialog, HistoryDialog


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_persistence_and_missing_values(self):
        r = StepReport(setting='sample.txt', training_axis='piezo')
        r.training_positions = {0: {'Up': 100, 'Down': -50}, 1: {'Up': None, 'Down': 50}}
        r.finish('完了')
        with TemporaryDirectory() as folder:
            root = Path(folder)
            save_report(6, r, root)
            save_report(6, r, root)
            records, errors = load_reports(root)
            self.assertEqual(len(records), 2)
            self.assertFalse(errors)
            rows = numeric_rows(6, records[0]['report'])
            self.assertEqual(rows[0], [1, 100, -50, -150, 150])
            self.assertIsNone(rows[1][4])
            self.assertEqual(len(list(root.glob('*.csv'))), 2)
            (root / 'bad.json').write_text('broken')
            self.assertEqual(len(load_reports(root)[1]), 1)
        dialog = ReportDialog(6, r)
        dialog.show(); self.app.processEvents(); dialog.close()

    def test_calibration_report_is_persisted(self):
        r = StepReport(
            calibration_slope_log10_a_per_nm=-0.000290338,
            calibration_gap_sensitivity_pm_per_um=56.7,
            calibration_last_slope_pm_per_um=92.1153419,
        )
        r.finish('完了')
        with TemporaryDirectory() as folder:
            path = save_report(9, r, Path(folder))
            records, errors = load_reports(Path(folder))
            self.assertTrue(path.exists())
            self.assertFalse(errors)
            self.assertEqual(records[0]['step'], 9)
            self.assertEqual(numeric_rows(9, records[0]['report']), [])

    def test_calibration_metrics_are_available_in_history(self):
        reports = []
        for gap, last_slope in ((82.9, 92.1153419), (80.0, 90.0)):
            r = StepReport(
                calibration_gap_sensitivity_pm_per_um=gap,
                calibration_last_slope_pm_per_um=last_slope,
            )
            r.finish('完了')
            reports.append({'version': 1, 'step': 9, 'report': asdict(r)})
        with patch('report_view.load_reports', return_value=(reports, [])):
            dialog = HistoryDialog()
            dialog.step.setCurrentIndex(dialog.step.findData(9))
            self.assertEqual(dialog.metric_choice.currentText(), 'Gap Sensitivity')
            self.assertEqual([dialog.metric_choice.itemText(i) for i in range(dialog.metric_choice.count())],
                             ['Gap Sensitivity', 'Last Slope', '所要時間（秒）'])
            self.assertIn('平均 81.45', dialog.summary.text())
            dialog.metric_choice.setCurrentIndex(1)
            self.assertEqual(dialog.metric_choice.currentText(), 'Last Slope')
            self.assertIn('pm/µm', dialog.summary.text())
            dialog.close()

    def test_history_metrics_are_limited_to_values_recorded_by_each_step(self):
        expected = {
            4: ['各回のmove / 振幅', '所要時間（秒）'],
            5: ['各回のmove / 振幅', '所要時間（秒）'],
            6: ['各回のmove / 振幅', '所要時間（秒）'],
            9: ['Gap Sensitivity', 'Last Slope', '所要時間（秒）'],
            10: ['Expand Gap 最終 Median', 'Expand Gap 最終 RMS',
                 'Expand Gap 最終 Noise RMS', '所要時間（秒）'],
        }
        with patch('report_view.load_reports', return_value=([], [])):
            dialog = HistoryDialog()
            for step, labels in expected.items():
                dialog.step.setCurrentIndex(dialog.step.findData(step))
                self.assertEqual(
                    [dialog.metric_choice.itemText(i) for i in range(dialog.metric_choice.count())],
                    labels,
                )
            dialog.close()

    def test_statistics_excludes_failure_and_missing(self):
        r = StepReport(fc_moves={1: 10, 2: 10, 3: 20})
        r.finish('完了')
        failed = StepReport(fc_moves={1: 999})
        failed.finish('失敗')
        data = [{'version': 1, 'step': 4, 'report': asdict(x)} for x in (r, failed)]
        with patch('report_view.load_reports', return_value=(data, [])):
            dialog = HistoryDialog()
            self.assertIn('有効値 3点', dialog.summary.text())
            self.assertIn('中央値 10', dialog.summary.text())
            self.assertIn('ヒストグラムのピーク値 11.67 µm（階級 10–13.33、2点）', dialog.summary.text())
            self.assertEqual(len(dialog.histogram.listDataItems()), 1)
            dialog.show(); self.app.processEvents(); dialog.close()

    def test_histogram_peaks_returns_bin_center_range_and_count(self):
        counts, edges, peaks = histogram_peaks([10, 10, 20])
        self.assertEqual(counts.tolist(), [2, 0, 1])
        self.assertEqual(len(edges), 4)
        center, low, high, count = peaks[0]
        self.assertAlmostEqual(center, 35 / 3)
        self.assertAlmostEqual(low, 10)
        self.assertAlmostEqual(high, 40 / 3)
        self.assertEqual(count, 2)

    def test_expand_gap_final_current_history_statistics(self):
        reports = []
        for median, rms, noise in ((1.0, 2.0, 0.2), (3.0, 4.0, 0.4)):
            r = StepReport(expand_final_current={
                'status': '正常', 'rate_hz': 10000, 'bias_v': 0.1,
                'median_pa': median, 'rms_pa': rms, 'noise_rms_pa': noise, 'samples': 100,
            })
            r.finish('完了')
            reports.append({'version': 1, 'step': 10, 'report': asdict(r)})
        with patch('report_view.load_reports', return_value=(reports, [])):
            dialog = HistoryDialog()
            dialog.step.setCurrentIndex(dialog.step.findData(10))
            self.assertEqual(dialog.metric_choice.currentText(), 'Expand Gap 最終 Median')
            self.assertEqual([dialog.metric_choice.itemText(i) for i in range(dialog.metric_choice.count())],
                             ['Expand Gap 最終 Median', 'Expand Gap 最終 RMS',
                              'Expand Gap 最終 Noise RMS', '所要時間（秒）'])
            self.assertIn('中央値 2', dialog.summary.text())
            self.assertIn('pA', dialog.summary.text())
            dialog.metric_choice.setCurrentIndex(2)
            self.assertIn('平均 0.3', dialog.summary.text())
            dialog.close()

    def test_gateway_saves_completed_report_once(self):
        from gateway_window import GatewayWindow
        w = GatewayWindow()
        w.io_timer.stop(); w.plot_timer.stop()
        w.state.configured = True
        w.state.completed = 4
        w.state.begin(4)
        w.state.reports[4].fc_moves = {1: 10}
        w.state.finish()
        with patch('report_view.save_report', return_value=Path('saved.json')) as save:
            w.refresh(); w.refresh()
            save.assert_called_once()
        w.allow_close = True; w.close()

    def test_expand_gap_report_is_persisted(self):
        from gateway_window import GatewayWindow
        w = GatewayWindow()
        w.io_timer.stop(); w.plot_timer.stop()
        w.state.configured = True
        w.state.completed = 10
        w.state.begin(10)
        w.state.reports[10].feed('Log  ExpandGap canceled.')
        w.state.reports[10].finish('失敗')
        with patch('report_view.save_report', return_value=Path('saved.json')) as save:
            w.refresh(); w.refresh()
            save.assert_called_once_with(10, w.state.reports[10])
        w.allow_close = True; w.close()

    def test_expand_gap_completion_captures_final_10khz_current(self):
        from gateway_window import GatewayWindow
        import numpy as np
        w = GatewayWindow()
        w.io_timer.stop(); w.plot_timer.stop()
        w.state.configured = True
        w.state.completed = 10
        w.state.begin(10)
        values = np.array([1.0, 2.0, 3.0])
        w.telemetry.latest = {
            'serial': 7, 'rate': 10000, 'bias': 0.1, 'unit': 'pA', 'values': values,
        }
        with patch('recipe_timing.record'):
            w.finish_live_step()
        final = w.state.reports[10].expand_final_current
        self.assertEqual(final['median_pa'], 2.0)
        self.assertAlmostEqual(final['rms_pa'], np.sqrt(14 / 3))
        self.assertAlmostEqual(final['noise_rms_pa'], np.sqrt(2 / 3))
        self.assertEqual(final['samples'], 3)
        self.assertEqual(w.operation, 'baseline')
        w.allow_close = True; w.close()

    def test_hold_gap_panel_is_outside_hardware_panel(self):
        from gateway_window import GatewayWindow
        w = GatewayWindow()
        w.io_timer.stop(); w.plot_timer.stop()
        self.assertIs(w.hold_panel.parentWidget(), w.hardware_box.parentWidget())
        self.assertEqual(w.hardware_graphs.indexOf(w.hold_panel), -1)
        self.assertGreaterEqual(w.hold_plot.minimumHeight(), 190)
        w.allow_close = True; w.close()


if __name__ == '__main__': unittest.main()
