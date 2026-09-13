from unittest.mock import patch
from test_connection import ConnectionTests


class RecoveryTests(ConnectionTests):
    def test_failed_shutdown_close_choices_with_connection_alive(self):
        from unittest.mock import Mock
        w = self.w
        w.touched = True
        for choice in ('cancel', 'retry', 'close'):
            with self.subTest(choice=choice):
                w.shutdown_error = 'sv_info_sender stop: Stop error : -3'
                w.operation = None
                w.allow_close = False
                event = Mock()
                retry, close, cancel = Mock(), Mock(), Mock()
                with patch('gateway_window.QMessageBox') as box, patch.object(w, 'retry_finalize') as finalize:
                    dialog = box.return_value
                    dialog.addButton.side_effect = [retry, close, cancel]
                    dialog.clickedButton.return_value = {'retry': retry, 'close': close, 'cancel': cancel}[choice]
                    w.closeEvent(event)
                    dialog.setDefaultButton.assert_called_once_with(cancel)
                    dialog.setEscapeButton.assert_called_once_with(cancel)
                if choice == 'close':
                    event.accept.assert_called_once()
                    w.transport.close.assert_called_once()
                    finalize.assert_not_called()
                else:
                    event.ignore.assert_called_once()
                    w.transport.close.assert_not_called()
                    self.assertEqual(finalize.call_count, int(choice == 'retry'))
                w.transport.send.assert_not_called()

    def test_negative_motor_cancel_prevents_zero_move(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.w
        w.state.configured = True
        w.state.completed = 1
        w.telemetry.latest['motor'] = -200
        with patch('gateway_window.QMessageBox.warning', return_value=QMessageBox.StandardButton.Cancel) as warning:
            w.run_step(1, batch=True)
        warning.assert_called_once()
        self.assertEqual(warning.call_args.args[-1], QMessageBox.StandardButton.Cancel)
        w.transport.send.assert_not_called()
        self.assertIsNone(w.state.active)
        self.assertEqual(w.state.completed, 1)
        self.assertFalse(w.state.batch)

    def test_negative_motor_explicit_confirmation_allows_zero_move(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.w
        w.state.configured = True
        w.state.completed = 1
        w.telemetry.latest['motor'] = -200
        with patch('gateway_window.QMessageBox.warning', return_value=QMessageBox.StandardButton.Yes):
            w.run_step(1)
        w.transport.send.assert_called_once_with('mw_ac go0')

    def test_manual_zero_move_checks_negative_and_unknown_position(self):
        from PySide6.QtWidgets import QMessageBox
        w = self.w
        for motor, last_host in ((-1, w.last_host), (None, w.last_host), (1, 0)):
            w.telemetry.latest['motor'] = motor
            w.last_host = last_host
            with patch('gateway_window.QMessageBox.warning', return_value=QMessageBox.StandardButton.Cancel) as warning:
                w.manual('Go0 Point')
            warning.assert_called_once()
        w.transport.send.assert_not_called()

    def test_nonnegative_motor_zero_move_without_warning(self):
        w = self.w
        w.state.configured = True
        for motor in (0, 200):
            w.state.completed = 1
            w.telemetry.latest['motor'] = motor
            with patch('gateway_window.QMessageBox.warning') as warning:
                w.run_step(1)
            warning.assert_not_called()
            w.transport.send.assert_called_with('mw_ac go0')
            self.ack('Actuator Control for set 0point complete.')

    def test_shutdown_busy_retry_then_disconnect_without_sampling_restart(self):
        w = self.w
        w.touched = True
        transport = w.transport
        w.toggle_connection()
        self.ack('')
        self.ack('BIAS set complete.')
        self.ack('EP set complete.')
        self.ack('Stop error : -3')
        self.assertEqual(w.operation, 'finalize')
        transport.close.assert_not_called()
        with patch.object(w.engine, 'clock', return_value=w.engine.retry_at):
            w.engine.tick()
        with patch('gateway_window.QTimer.singleShot', side_effect=lambda delay, fn: fn()):
            self.ack('Stop complete. result:0')
        transport.close.assert_called_once()
        self.assertNotIn('sv_info_sender start 0', [c.args[0] for c in transport.send.call_args_list])

    def test_shutdown_persistent_busy_keeps_connection_and_reports_partial_completion(self):
        w = self.w
        w.touched = True
        w.toggle_connection()
        self.ack('')
        self.ack('BIAS set complete.')
        self.ack('EP set complete.')
        for _ in range(4):
            self.ack('Stop error : -3')
            if w.engine.retry_at is not None:
                with patch.object(w.engine, 'clock', return_value=w.engine.retry_at):
                    w.engine.tick()
        w.transport.close.assert_not_called()
        self.assertIsNone(w.operation)
        self.assertIn('Bias解除', w.alarm_status.text())
        self.assertIn('未完了', w.alarm_status.text())
        self.assertTrue(w.connect_button.isEnabled())

    def test_close_during_cleanup_waits_then_finalizes(self):
        from unittest.mock import Mock
        from protocol import SAMPLE_STOP
        w = self.w
        w.start_job('piezo_cleanup', [SAMPLE_STOP])
        w.closeEvent(Mock())
        self.assertEqual(w.operation, 'piezo_cleanup')
        with patch('gateway_window.QTimer.singleShot', side_effect=lambda delay, fn: fn()):
            self.ack('Stop complete. result:0')
        self.assertEqual(w.operation, 'finalize')
        w.transport.send.assert_called_with('mcbj stop')

    def test_faulted_disconnect_retries_cleanup_without_closing_transport(self):
        w = self.w
        w.touched = True
        w.engine.fail('timeout')
        w.toggle_connection()
        w.transport.send.assert_called_with('mcbj stop')
        w.transport.close.assert_not_called()
        self.assertEqual(w.operation, 'finalize')
        w.engine.fail('retry timeout')
        self.assertFalse(w.closing)
        self.assertFalse(w.disconnecting)
        w.transport.close.assert_not_called()

    def test_selected_entry_never_sends_zero_or_first_cut(self):
        w = self.w
        w.state.configured = True
        w.start_at.setCurrentIndex(2)
        w.start_selected_setup()
        self.ack('Stop complete. result:0')
        self.ack('Start complete. result:0')
        self.ack('BIAS set complete.')
        self.assertEqual(w.operation, 'setup_entry_host')
        w.telemetry.latest = {'piezo': 0, 'motor': 0, 'unit': 'µA'}
        w.check_conduction_guard(w.telemetry.latest)
        sent = [c.args[0] for c in w.transport.send.call_args_list]
        self.assertEqual(sent[-1], 'mcbj targeting start')
        self.assertNotIn('mw_ac go0', sent)
        self.assertNotIn('mcbj fc start', sent)
        self.assertEqual(w.state.active, 5)

    def test_bias_entry_starts_at_bias(self):
        w = self.w
        w.state.configured = True
        w.start_at.setCurrentIndex(1)
        w.start_selected_setup()
        self.assertEqual(w.state.completed, 3)
        self.assertNotIn('mw_ac go0', [c.args[0] for c in w.transport.send.call_args_list])
