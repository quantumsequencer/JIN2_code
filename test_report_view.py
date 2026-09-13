import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest
from dataclasses import asdict
from PySide6.QtWidgets import QApplication
from step_report import StepReport
from report_view import save_report, load_reports, numeric_rows, ReportDialog, HistoryDialog


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

    def test_statistics_excludes_failure_and_missing(self):
        r = StepReport(fc_moves={1: 10, 2: 20})
        r.finish('完了')
        failed = StepReport(fc_moves={1: 999})
        failed.finish('失敗')
        data = [{'version': 1, 'step': 4, 'report': asdict(x)} for x in (r, failed)]
        with patch('report_view.load_reports', return_value=(data, [])):
            dialog = HistoryDialog()
            self.assertIn('有効値 2点', dialog.summary.text())
            self.assertIn('平均 15', dialog.summary.text())
            dialog.show(); self.app.processEvents(); dialog.close()

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

    def test_hold_gap_panel_is_outside_hardware_panel(self):
        from gateway_window import GatewayWindow
        w = GatewayWindow()
        w.io_timer.stop(); w.plot_timer.stop()
        self.assertIs(w.hold_panel.parentWidget(), w.hardware_box.parentWidget())
        self.assertEqual(w.hardware_graphs.indexOf(w.hold_panel), -1)
        self.assertGreaterEqual(w.hold_plot.minimumHeight(), 190)
        w.allow_close = True; w.close()


if __name__ == '__main__': unittest.main()
