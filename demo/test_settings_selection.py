import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main


class SettingsSelectionTests(unittest.TestCase):
    def test_read_settings_accepts_utf8_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'settings.txt'
            path.write_text('# comment\n\nmcbj set pt speed 100\n', encoding='utf-8-sig')

            content, commands = main.read_settings(path)

            self.assertIn('mcbj set pt speed 100', content)
            self.assertEqual(commands, ['mcbj set pt speed 100'])

    def test_default_settings_file_is_setting_parameter(self):
        self.assertEqual(main.DEFAULT_SETTINGS_PATH,
                         main.SETTINGS_DIR / 'setting_parameter.txt')

    def test_file_dialog_opens_settings_directory(self):
        window = object()
        with patch.object(main.QFileDialog, 'getOpenFileName', return_value=('', '')) as dialog:
            main.MainWindow.select_settings(window)

        self.assertEqual(dialog.call_args.args[2], str(main.DEFAULT_SETTINGS_PATH))


if __name__ == '__main__':
    unittest.main()
