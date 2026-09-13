import unittest
from unittest.mock import patch
from gateway_launcher import launch_gateway


class LauncherTests(unittest.TestCase):
    def test_reuses_existing_gateway(self):
        with patch('gateway_launcher.running_executable', return_value=True), \
             patch('gateway_launcher.subprocess.Popen') as spawn:
            ports, saved, reused = launch_gateway()
            self.assertEqual(ports, (55555, 55556))
            self.assertIn('Host:', saved)
            self.assertTrue(reused)
            spawn.assert_not_called()

    def test_launches_with_gateway_working_directory(self):
        with patch('gateway_launcher.running_executable', return_value=False), \
             patch('gateway_launcher.subprocess.Popen') as spawn:
            _, _, reused = launch_gateway()
            self.assertFalse(reused)
            self.assertEqual(spawn.call_count, 1)
            self.assertTrue(spawn.call_args.kwargs['cwd'].endswith('JinGateway-0.2.0.09030'))

    def test_missing_exe_does_not_launch(self):
        with patch('gateway_launcher.subprocess.Popen') as spawn:
            with self.assertRaises(FileNotFoundError):
                launch_gateway('missing-gateway.exe')
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
