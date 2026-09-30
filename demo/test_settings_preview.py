import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest
from pathlib import Path
from unittest.mock import patch
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
        self.assertEqual(lower.text(1), '0.1')
        self.assertEqual(upper.text(1), '8')
        self.assertEqual(dialog.edited_text(), source)
        speed.setText(1, '1500')
        self.assertEqual(dialog.edited_text(), source.replace('500\r', '1500\r'))
        lower.setText(1, '0.2')
        self.assertIn('SMOOTH 0x00828F5C 0x14666666 1500', dialog.edited_text())

    def test_all_current_setting_types_show_physical_units_in_both_modes(self):
        source = ('mcbj set fc threshold 0x004147AE\n'
                  'mcbj set mt ROUGH 0x004147AE 0x14666666 80\n'
                  'mcbj set targeting up_table 0 0x15641390 13 250\n'
                  'mcbj set targeting down_table 1 0x7FFFFFFF 1 20\n'
                  'mcbj set ac threshold 0x001C7163\n'
                  'mcbj set cal limit 0x115C432C 0x45710CB2\n'
                  'asz set eg stable_current_range 0x010AA7DE\n'
                  'asz set hg tunnel_current 0x00C35F36\n')
        for editable in (False, True):
            dialog = SettingsPreview(source, 'base.txt', editable=editable)
            items = [dialog.tree.topLevelItem(group).child(row)
                     for group in range(dialog.tree.topLevelItemCount())
                     for row in range(dialog.tree.topLevelItem(group).childCount())]
            current_items = [item for item in items if '（µA）' in item.text(0) or '（pA）' in item.text(0)]
            self.assertEqual(len(current_items), 10)
            self.assertEqual(sum('（µA）' in item.text(0) for item in current_items), 8)
            self.assertEqual(sum('（pA）' in item.text(0) for item in current_items), 2)
            self.assertTrue(any(item.text(1) == 'MAX' for item in current_items))

    def test_table_index_and_integer_boundaries(self):
        source = 'asz set hg fb_table 4 0xFFFFFFFF 500 450\n'
        dialog = SettingsPreview(source, 'base.txt', editable=True)
        current = dialog.edit_rows[0][0]
        self.assertEqual(current.text(1), 'MAX')
        self.assertEqual(dialog.edited_text(), source)
        dialog.edit_rows[1][0].setText(1, '600')
        self.assertEqual(dialog.edited_text(), source.replace('500', '600'))
        for invalid in ('-1', 'NaN', 'Infinity', '100 / 200'):
            with self.assertRaises(ValueError):
                dialog.raw_from_pa(invalid)

    def test_hold_gap_conversion_table_and_live_edit(self):
        source = ('asz set hg tunnel_current 0x00C35F36\n'
                  'asz set hg fb_table 0 0x0010FF55 0 0\n'
                  'asz set hg fb_table 1 0x0058E29F 2 1000\n'
                  'asz set hg fb_table 4 0xFFFFFFFF 88 300\n')
        dialog = SettingsPreview(source, 'base.txt', editable=True)
        self.assertIn('2.2 pA', dialog.hold_target_label.text())
        self.assertEqual(dialog.hold_detail.topLevelItemCount(), 3)
        first = dialog.hold_detail.topLevelItem(0)
        second = dialog.hold_detail.topLevelItem(1)
        last = dialog.hold_detail.topLevelItem(2)
        self.assertEqual([first.text(i) for i in range(6)],
                         ['0', '0 ～ 0.191 pA', '0.191 pA', '0 nm', '0 ms', '―'])
        self.assertEqual(second.text(1), '0.191 pA超 ～ 1 pA')
        self.assertEqual(second.text(5), '2 nm/s')
        self.assertEqual(last.text(1), '1 pA超')
        self.assertEqual(last.text(2), 'MAX')
        dialog.hold_fb_rows['1'][2].setText(1, '500')
        self.assertEqual(dialog.hold_detail.topLevelItem(1).text(5), '4 nm/s')

    def test_hold_gap_pa_edit_rounds_to_nearest_raw(self):
        source = ('asz set hg tunnel_current 0x00C35F36\n'
                  'asz set hg fb_table 0 0x0010FF55 0 0\n'
                  'asz set hg fb_table 1 0x0058E29F 2 1000\n'
                  'asz set hg fb_table 4 0xFFFFFFFF 88 300\n')
        dialog = SettingsPreview(source, 'base.txt', editable=True)

        dialog.hold_target_edit.setText('2.5')
        dialog.apply_hold_target_pa()
        self.assertEqual(dialog.hold_target_item.text(1), '2.5')

        upper = dialog.hold_detail.topLevelItem(1)
        upper.setText(2, '1.5')
        self.assertEqual(dialog.hold_fb_rows['1'][0].text(1), '1.5')
        self.assertIn('tunnel_current 0x00DE368F', dialog.edited_text())
        self.assertIn('fb_table 1 0x008553EF 2 1000', dialog.edited_text())

    def test_hold_gap_pa_upper_limits_must_increase(self):
        source = ('asz set hg fb_table 0 0x0010FF55 0 0\n'
                  'asz set hg fb_table 1 0x0058E29F 2 1000\n'
                  'asz set hg fb_table 4 0xFFFFFFFF 88 300\n')
        dialog = SettingsPreview(source, 'base.txt', editable=True)
        dialog.hold_fb_rows['1'][0].setText(1, '0.01')
        with self.assertRaisesRegex(ValueError, '行番号順'):
            dialog.edited_text()

    def test_read_only_confirmation_also_shows_hold_gap_in_pa(self):
        source = ('asz set hg tunnel_current 0x00C35F36\n'
                  'asz set hg fb_table 0 0x0010FF55 0 0\n'
                  'asz set hg fb_table 1 0x0058E29F 2 1000\n'
                  'asz set hg fb_table 4 0xFFFFFFFF 88 300\n')
        dialog = SettingsPreview(source, 'base.txt', editable=False)

        self.assertEqual(dialog.hold_target_item.text(1), '2.2')
        self.assertIn('（pA）', dialog.hold_target_item.text(0))
        self.assertEqual(dialog.hold_fb_rows['0'][0].text(1), '0.191')
        self.assertEqual(dialog.hold_fb_rows['1'][0].text(1), '1')
        self.assertEqual(dialog.hold_fb_rows['4'][0].text(1), 'MAX')

    def test_save_dialog_starts_in_setting_parameter_directory(self):
        dialog = SettingsPreview('asz set hg threshold 100\n', 'base.txt', editable=True)
        with patch('settings_preview.QFileDialog.getSaveFileName', return_value=('', '')) as save_dialog:
            dialog.save_settings()

        suggested = Path(save_dialog.call_args.args[2])
        expected = Path(__file__).resolve().parent / 'setting parameter'
        self.assertEqual(suggested.parent, expected)
        self.assertRegex(suggested.name, r'^\d{8}_\d{6}\.txt$')


if __name__ == '__main__':
    unittest.main()
