import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest
from PySide6.QtWidgets import QApplication
from settings_preview import SettingsPreview


class SettingsPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_decimal_fields_and_preserved_text(self):
        source = '# note\r\nmcbj set pt SMOOTH 0x004147AE 0x14666666 500\r\n'
        dialog = SettingsPreview(source, 'base.txt', editable=True)
        lower, upper, speed = [row[0] for row in dialog.edit_rows]
        self.assertIn('電流下限', lower.text(0))
        self.assertIn('電流上限', upper.text(0))
        self.assertIn('ピエゾ速度', speed.text(0))
        self.assertEqual(lower.text(1), str(0x004147AE))
        self.assertEqual(upper.text(1), str(0x14666666))
        self.assertEqual(dialog.edited_text(), source)
        speed.setText(1, '1500')
        self.assertEqual(dialog.edited_text(), source.replace('500\r', '1500\r'))
        lower.setText(1, '100')
        self.assertIn('SMOOTH 0x00000064 0x14666666 1500', dialog.edited_text())

    def test_table_index_and_integer_boundaries(self):
        source = 'asz set hg fb_table 4 0xFFFFFFFF 500 450\n'
        dialog = SettingsPreview(source, 'base.txt', editable=True)
        current = dialog.edit_rows[0][0]
        self.assertEqual(current.text(1), '4294967295')
        self.assertEqual(dialog.edited_text(), source)
        dialog.edit_rows[1][0].setText(1, '600')
        self.assertEqual(dialog.edited_text(), source.replace('500', '600'))
        for invalid in ('4294967296', '-1', '1.5', '0xFF', '100 / 200'):
            current.setText(1, invalid)
            with self.assertRaises(ValueError):
                dialog.edited_text()


if __name__ == '__main__':
    unittest.main()
