import unittest
from unittest.mock import patch
from measurement_recipe import validate
from test_connection import ConnectionTests


class RecipeTests(ConnectionTests):
    def setUp(self):
        super().setUp()
        mock = patch('recipe_timing.record')
        mock.start()
        self.addCleanup(mock.stop)

    def test_three_conditions_complete_automatically(self):
        from test_baseline_current import frame
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.recipe = [(0.60, 1), (0.61, 2), (0.62, 3)]
        callbacks = []
        def drain():
            while callbacks: callbacks.pop(0)()
        with patch('gateway_window.QTimer.singleShot', side_effect=lambda delay, fn: callbacks.append(fn)), patch('gateway_window.QMessageBox.information') as notify:
            w.start_recipe()
            self.ack('Stop complete. result:0')
            for i in range(3):
                self.ack('Start complete. result:0'); drain()
                w.transport.send.assert_called_with('asz eg start')
                self.ack('')
                w.engine.feed('Log', 'ExpandGap finished.')
                self.assertEqual(w.operation, 'baseline')
                for serial in range(1, 101): w.baseline_current.feed(frame(serial))
                w.state.reports[10].baseline_current = dict(w.baseline_current.result)
                w.operation = None
                w.finish_live_step(); drain()
                self.assertEqual(w.operation, 'gap_target')
                self.ack('Setting change : 0'); drain()
                w.transport.send.assert_called_with('asz hg start')
                self.ack('')
                with patch('gateway_window.time.monotonic', return_value=w.measure_deadline + 1): w.check_measure_time()
                self.ack('')
                w.engine.feed('Log', 'HoldGap canceled.')
                self.ack('Stop complete. result:0'); drain()
                self.assertEqual(w.recipe_number, min(i + 2, 3))
            notify.assert_called_once()
            self.assertFalse(w.recipe_pending)

    def test_first_condition_reuses_completed_expand_gap(self):
        from step_report import StepReport
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.state.reports[10] = StepReport()
        w.state.reports[10].baseline_current = {'status': '正常', 'mean_pa': 1.23456, 'samples': 10000}
        w.recipe = [(0.61, 2)]
        w.start_recipe()
        self.assertEqual(w.operation, 'gap_target')
        self.assertNotIn('asz eg start', [call.args[0] for call in w.transport.send.call_args_list])
        self.assertIn('Expand Mean：1.235 pA', w.hold_values.text())

    def test_batch_enters_registered_recipe_after_calibration(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.state.batch = True
        w.recipe = [(0.61, 2), (0.62, 3)]
        w.continue_batch()
        self.assertEqual(w.operation, 'resume_sampling')
        self.assertEqual(w.recipe_number, 1)
        self.assertEqual(w.recipe_pending, [(0.62, 3)])
        self.assertEqual(w.gap_choice.value(), 0.61)
        self.assertEqual(w.measure_minutes.value(), 2)

    def test_stopped_batch_does_not_start_registered_recipe(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.recipe = [(0.61, 2)]
        w.state.batch = False
        w.continue_batch()
        w.transport.send.assert_not_called()

    def test_batch_without_recipe_continues_preparation(self):
        w = self.w
        w.state.batch = True
        w.state.completed = 10
        with patch.object(w, 'run_step') as run:
            w.continue_batch()
        run.assert_called_once_with(10, batch=True)

    def test_recipe_scroll_targets_start_button(self):
        w = self.w
        with patch('gateway_window.QTimer.singleShot', side_effect=lambda delay, fn: fn()):
            with patch.object(w.measurement_scroll, 'ensureWidgetVisible') as ensure:
                w.scroll_recipe_controls()
        ensure.assert_called_once_with(w.recipe_start, 0, 60)

    def test_recipe_target_preview_and_button_order(self):
        from measurement_recipe import RecipeDialog
        from PySide6.QtWidgets import QPushButton, QDialog, QTableWidget
        from gap_target import model_target
        dialog = RecipeDialog([(0.61, 2)], self.w)
        buttons = [dialog.layout().itemAt(i).widget() for i in range(dialog.layout().count())]
        self.assertEqual(next(b.text() for b in buttons if isinstance(b, QPushButton)), 'CSV読込')
        with patch.object(QDialog, 'exec'):
            dialog.show_targets()
        preview = dialog.findChild(QDialog)
        table = preview.findChild(QTableWidget)
        self.assertEqual(table.item(0, 2).text(), f'{model_target(0.61)[0]:.6f}')
        self.w.transport.send.assert_not_called()
        dialog.close()

    def test_running_sampling_is_stopped_before_restart(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.resume_measurement()
        w.transport.send.assert_called_once_with('sv_info_sender stop')
        self.ack('Stop complete. result:0')
        self.assertTrue(w.host_paused)
        w.transport.send.assert_called_with('sv_info_sender start 10')
        with patch('gateway_window.QTimer.singleShot') as callback:
            self.ack('Start complete. result:0')
        callback.call_args.args[1]()
        w.transport.send.assert_called_with('asz eg start')

    def test_restart_stop_failure_aborts_recipe(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.recipe_pending = [(0.6, 1)]
        w.resume_measurement()
        self.ack('Stop error : -1')
        w.transport.send.assert_called_once_with('sv_info_sender stop')
        self.assertFalse(w.auto_measure)
        self.assertFalse(w.recipe_pending)
    def test_validation(self):
        self.assertEqual(validate([['0.6', '1'], ['0.61', '2']]), [(0.6, 1), (0.61, 2)])
        for rows in ([], [('nan', 1)], [(0.6, 0)], [(0.6001, 1)], [(0.001, 1)]):
            with self.assertRaises(ValueError): validate(rows)

    def test_restart_sampling_then_expand(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.host_paused = True
        w.resume_measurement()
        self.assertTrue(w.auto_measure)
        w.transport.send.assert_called_with('sv_info_sender start 10')
        with patch('gateway_window.QTimer.singleShot') as callback:
            self.ack('Start complete. result:0')
        self.assertFalse(w.host_paused)
        callback.call_args.args[1]()
        w.transport.send.assert_called_with('asz eg start')
        self.assertEqual(w.state.active, 10)

    def test_manual_stop_cancels_recipe(self):
        w = self.w
        w.recipe_pending = [(0.6, 1)]
        w.auto_measure = True
        w.stop()
        self.assertFalse(w.auto_measure)
        self.assertFalse(w.recipe_pending)

    def test_cleanup_keeps_calibration_and_pauses_host_watchdog(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.operation = 'timed_cleanup'
        with patch('gateway_window.QTimer.singleShot'):
            w.command_result('success', '')
        self.assertEqual(w.state.completed, 10)
        self.assertTrue(w.host_paused)
        self.assertTrue(w.resume_button.isEnabled())


if __name__ == '__main__': unittest.main()
