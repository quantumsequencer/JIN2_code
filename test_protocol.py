import struct
import unittest
import numpy as np
from protocol import decode_host, settings_commands, WORKERS, BIAS0, BIAS1, Command
from command_engine import CommandEngine
from telemetry import Telemetry


def frame(kind=1, serial=100, bias=1, value=42781901):
    count = (0, 100, 100, 500, 1000)[kind]
    return struct.pack('<IHHBBbbiii', serial, kind, 0, bias, 0, 2, -2,
                       value, 1234, 5678) + struct.pack('<i', value) * count


class ProtocolTests(unittest.TestCase):
    def test_rates_units_signed_and_lengths(self):
        for kind, count, rate in [(0, 0, 0), (1, 100, 10000), (2, 100, 10000),
                                  (3, 500, 50000), (4, 1000, 100000)]:
            f = decode_host(frame(kind))
            self.assertEqual((len(f['values']), f['rate']), (count, rate))
            self.assertAlmostEqual(f['motor'], 123.4)
            self.assertEqual(f['ep_minus'], -.2)
        self.assertAlmostEqual(decode_host(frame())['current'], 1.0, places=6)
        self.assertAlmostEqual(decode_host(frame(2, value=-5825184))['current'], -1, places=6)
        self.assertEqual(decode_host(frame(1, bias=0))['unit'], 'RAW')
        self.assertEqual(decode_host(frame(0))['unit'], 'RAW')
        with self.assertRaises(ValueError):
            decode_host(frame(4)[:-4])
        self.assertIsNone(decode_host(struct.pack('<IH', 0, 65535) + bytes(18)))

    def test_settings_preflight(self):
        self.assertEqual(len(settings_commands('# comment\n\nmcbj set fc threshold 0x004147AE')), 1)
        for text in ['', 'mcbj fc start', 'mcbj set fc 1; dd_ep bias 1']:
            with self.assertRaises(ValueError):
                settings_commands(text)

    def test_display_gaps_modes_and_restart(self):
        t = Telemetry()
        t.feed(frame(serial=100))
        t.feed(frame(serial=102))
        self.assertEqual(t.gaps, 1)
        self.assertEqual(len(t.frames), 1)
        self.assertTrue(np.isnan(t.hardware[-2][1]))
        t.feed(frame(kind=2, serial=103))
        self.assertEqual(len(t.frames), 1)
        self.assertTrue(t.feed(frame(serial=1)))
        self.assertEqual(len(t.hardware), 1)
        self.assertIsNone(t.feed(struct.pack('<IH', 2, 65535) + bytes(18)))
        self.assertEqual(t.latest['serial'], 1)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.sent, self.results, self.accepted = [], [], []
        self.now = 0
        self.e = CommandEngine(self.sent.append, lambda *args: self.results.append(args),
                               self.accepted.append, clock=lambda: self.now)

    def ack(self, *lines):
        for line in (*lines, '> '):
            self.e.feed('Debug', line)

    def test_waits_prompt_and_exact_success(self):
        self.e.start([BIAS0, BIAS1])
        self.e.feed('Debug', 'BIAS set complete.')
        self.assertEqual(len(self.sent), 1)
        self.e.feed('Debug', '> ')
        self.assertEqual(len(self.sent), 2)
        self.ack('BIAS set complete.')
        self.assertEqual(self.results[-1][0], 'success')
        self.e.start([Command('setting', 'Setting change : 0')])
        self.ack('Setting change : 01')
        self.assertEqual(self.results[-1][0], 'failure')

    def test_worker_log_before_or_after_prompt(self):
        for early in (True, False):
            self.e.start([WORKERS['target']])
            if early:
                self.e.feed('Log', '12:00 Targeting finished.')
            self.ack()
            if not early:
                self.assertTrue(self.e.busy)
                self.e.feed('Log', '12:00 Targeting finished.')
            self.assertFalse(self.e.busy)
            self.assertEqual(self.results[-1][0], 'success')

    def test_cancel_is_not_success(self):
        self.e.start([WORKERS['ac'], BIAS1])
        self.ack()
        self.e.feed('Log', 'End. Canceled.')
        self.assertEqual(self.results[-1][0], 'failure')
        self.assertEqual(len(self.sent), 1)

    def test_stop_waits_original_prompt_and_worker_terminal(self):
        self.e.start([WORKERS['fc'], BIAS1])
        self.e.stop()
        self.assertEqual(self.sent, ['mcbj fc start'])
        self.ack()
        self.assertEqual(self.sent, ['mcbj fc start', 'mcbj stop'])
        self.ack()
        self.assertTrue(self.e.busy)
        self.e.feed('Log', 'First Cut canceld!')
        self.assertEqual(self.results[-1][0], 'stopped')

    def test_stop_terminal_can_precede_stop_ack(self):
        self.e.start([WORKERS['hg']])
        self.ack()
        self.now = 100000
        self.e.tick()
        self.assertTrue(self.e.busy)  # Hold Gap has no duration limit after ack
        self.e.stop()
        self.e.feed('Log', 'HoldGap finished.')
        self.assertTrue(self.e.busy)
        self.ack()
        self.assertEqual(self.results[-1][0], 'stopped')

    def test_timeout_latches_no_replay(self):
        self.e.start([BIAS0, BIAS1])
        self.now = 121
        self.e.tick()
        self.assertEqual(self.results[-1][0], 'uncertain')
        self.assertFalse(self.e.start([BIAS1]))
        self.ack('BIAS set complete.')
        self.assertEqual(len(self.sent), 1)

    def test_sampling_busy_retries_only_after_prompt_and_delay(self):
        from protocol import SAMPLE_STOP
        self.e.start([SAMPLE_STOP, BIAS0])
        self.e.feed('Debug', 'Stop error : -3')
        self.e.tick()
        self.assertEqual(len(self.sent), 1)
        self.ack('')
        self.now = .49
        self.e.tick()
        self.assertEqual(len(self.sent), 1)
        self.now = .5
        self.e.tick()
        self.assertEqual(self.sent, [SAMPLE_STOP.text] * 2)
        self.ack('Stop complete. result:0')
        self.assertEqual(self.sent[-1], BIAS0.text)

    def test_sampling_busy_is_not_success_and_retry_is_bounded(self):
        from protocol import SAMPLE_STOP
        self.e.start([SAMPLE_STOP, BIAS1])
        for _ in range(4):
            self.ack('Stop error : -3')
            self.now += .5
            self.e.tick()
        self.assertEqual(self.sent, [SAMPLE_STOP.text] * 4)
        self.assertEqual(self.results[-1][0], 'failure')
        self.assertFalse(self.accepted)


if __name__ == '__main__':
    unittest.main()
