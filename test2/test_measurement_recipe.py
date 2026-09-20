import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from measurement_recipe import validate, load_last_used, save_last_used
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
            for i in range(3):
                self.ack('Start complete. result:0')
                if i > 0:
                    w.last_host = __import__('time').monotonic()
                drain()
                if i == 0:
                    w.transport.send.assert_called_with('asz eg start')
                    self.ack('')
                    w.engine.feed('Log', 'ExpandGap finished.')
                    self.assertEqual(w.operation, 'baseline')
                    for serial in range(1, 101): w.baseline_current.feed(frame(serial))
                    w.state.reports[10].baseline_current = dict(w.baseline_current.result)
                    w.operation = None
                    w.finish_live_step(); drain()
                else:
                    self.assertEqual(
                        [call.args[0] for call in w.transport.send.call_args_list].count('asz eg start'),
                        1)
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

    def test_start_recipe_clears_previous_stop_alarm(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.recipe = [(0.61, 2)]
        w.show_stop_alarm('Hold Gap判定で停止')

        w.start_recipe()

        self.assertEqual(w.alarm_status.text(), '正常')
        self.assertIn('background: #123D32', w.alarm_status.styleSheet())

    def test_next_condition_reuses_expand_gap_after_sampling_restart(self):
        from step_report import StepReport
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.state.reports[10] = StepReport()
        w.state.reports[10].baseline_current = {'status': '正常', 'mean_pa': 1.23456, 'samples': 10000}
        w.recipe_pending = [(0.62, 3)]
        w.recipe_number = 1
        w.recipe_total = 2
        w.host_paused = True

        w.next_recipe()

        self.assertEqual(w.operation, 'resume_target_sampling')
        w.transport.send.assert_called_with('sv_info_sender start 10')
        self.assertNotIn('asz eg start', [call.args[0] for call in w.transport.send.call_args_list])

    def test_gap_distance_is_shown_only_for_active_recipe_hold_gap(self):
        w = self.w
        w.refresh()
        self.assertEqual(w.distance_meter.text(), '-- nm')

        w.recipe_started_at = 1
        w.recipe_number = 1
        w.gap_choice.setValue(0.61)
        w.operation = 'resume_sampling'
        w.refresh()
        self.assertEqual(w.distance_meter.text(), '-- nm')

        w.operation = 'gap_target'
        w.refresh()
        self.assertEqual(w.distance_meter.text(), '0.610 nm')

        w.gap_choice.setValue(0.62)
        w.refresh()
        self.assertEqual(w.distance_meter.text(), '0.620 nm')

        w.operation = None
        w.refresh()
        self.assertEqual(w.distance_meter.text(), '-- nm')

    def test_batch_stops_for_confirmation_before_expand_gap(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.state.batch = True
        w.recipe = [(0.61, 2), (0.62, 3)]
        with patch.object(w, 'run_step') as run:
            w.continue_batch()
        run.assert_not_called()
        self.assertFalse(w.state.batch)
        self.assertIsNone(w.operation)
        self.assertFalse(w.recipe_pending)
        w.transport.send.assert_not_called()

    def test_stopped_batch_does_not_start_registered_recipe(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10
        w.recipe = [(0.61, 2)]
        w.state.batch = False
        w.continue_batch()
        w.transport.send.assert_not_called()

    def test_batch_without_recipe_also_stops_before_expand_gap(self):
        w = self.w
        w.state.batch = True
        w.state.completed = 10
        with patch.object(w, 'run_step') as run:
            w.continue_batch()
        run.assert_not_called()
        self.assertFalse(w.state.batch)

    def test_restored_recipe_is_draft_until_explicitly_used(self):
        from gateway_window import GatewayWindow
        remembered = [(0.61, 2), (0.62, 3)]
        with patch('measurement_recipe.load_last_used', return_value=remembered):
            window = GatewayWindow()
        window.io_timer.stop()
        window.plot_timer.stop()
        try:
            self.assertEqual(window.remembered_recipe, remembered)
            self.assertEqual(window.recipe, [])
            self.assertFalse(window.recipe_start.isEnabled())
        finally:
            window.allow_close = True
            window.close()

    def test_recipe_scroll_targets_start_button(self):
        w = self.w
        with patch('gateway_window.QTimer.singleShot', side_effect=lambda delay, fn: fn()):
            with patch.object(w.measurement_scroll, 'ensureWidgetVisible') as ensure:
                w.scroll_recipe_controls()
        ensure.assert_called_once_with(w.recipe_start, 0, 60)

    def test_next_recipe_action_is_highlighted_after_calibration(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 10

        w.recipe = []
        w.refresh()
        self.assertIn('background: #F5D547', w.recipe_edit.styleSheet())
        self.assertEqual(w.recipe_start.styleSheet(), '')
        self.assertIn('レシピ作成・読込', w.next_action.text())
        self.assertFalse(w.next_action.isHidden())

        w.recipe = [(0.61, 2)]
        w.refresh()
        self.assertEqual(w.recipe_edit.styleSheet(), '')
        self.assertIn('background: #F5D547', w.recipe_start.styleSheet())
        self.assertIn('レシピ実行', w.next_action.text())
        self.assertFalse(w.next_action.isHidden())

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

    def test_running_recipe_can_append_only_to_pending_tail(self):
        from measurement_recipe import RunningRecipeDialog
        w = self.w
        w.recipe = [(0.60, 1), (0.61, 2)]
        w.recipe_pending = [(0.61, 2)]
        w.recipe_run_rows = list(w.recipe)
        w.recipe_number = 1
        w.recipe_total = 2
        w.recipe_started_at = __import__('time').monotonic()
        w.recipe_estimated_seconds = 180
        dialog = RunningRecipeDialog(w.recipe_run_rows, w.recipe_number, w)
        dialog.distance.setValue(0.62)
        dialog.minutes.setValue(3)
        dialog.add_candidate()
        with patch('measurement_recipe.RunningRecipeDialog', return_value=dialog), \
                patch.object(dialog, 'exec', return_value=True):
            w.edit_recipe()
        self.assertEqual(w.recipe_pending, [(0.61, 2), (0.62, 3)])
        self.assertEqual(w.recipe_run_rows[-1], (0.62, 3))
        self.assertEqual(w.recipe_total, 3)
        self.assertEqual(w.recipe, [(0.60, 1), (0.61, 2)])

    def test_running_recipe_dialog_marks_current_and_waiting_rows(self):
        from measurement_recipe import RunningRecipeDialog
        dialog = RunningRecipeDialog([(0.60, 1), (0.61, 2), (0.62, 3)], 2, self.w)
        self.assertEqual([dialog.table.item(i, 0).text() for i in range(3)],
                         ['完了', '計測中', '実行待ち'])
        dialog.close()

    def test_completed_measurement_restarts_sampling_without_duplicate_stop(self):
        w = self.w
        w.state.configured = True
        w.state.completed = 11
        w.host_paused = True
        w.resume_measurement()
        w.transport.send.assert_called_once_with('sv_info_sender start 10')
        self.assertNotIn('sv_info_sender stop', [c.args[0] for c in w.transport.send.call_args_list])
        with patch('gateway_window.QTimer.singleShot') as callback:
            self.ack('Start complete. result:0')
        callback.call_args.args[1]()
        w.transport.send.assert_called_with('asz eg start')

    def test_validation(self):
        self.assertEqual(validate([['0.6', '1'], ['0.61', '2']]), [(0.6, 1), (0.61, 2)])
        for rows in ([], [('nan', 1)], [(0.6, 0)], [(0.6001, 1)], [(0.001, 1)]):
            with self.assertRaises(ValueError): validate(rows)

    def test_last_used_recipe_is_persisted_and_loaded(self):
        with TemporaryDirectory() as folder:
            state = Path(folder) / 'last_used_recipe.json'
            with patch('measurement_recipe.RECIPE_ROOT', Path(folder)), \
                    patch('measurement_recipe.RECIPE_STATE_PATH', state):
                save_last_used([(0.6, 1), (0.61, 2)])
                self.assertEqual(load_last_used(), [(0.6, 1), (0.61, 2)])
                self.assertEqual(json.loads(state.read_text(encoding='utf-8'))['rows'],
                                 [[0.6, 1], [0.61, 2]])

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
