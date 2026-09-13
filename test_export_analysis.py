import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
import csv
from export_analysis import export, intervals


class ExportTests(unittest.TestCase):
    def test_split_original_samples_and_positions(self):
        with TemporaryDirectory() as folder:
            src = Path(folder) / 'source'; src.mkdir()
            (src / 'log_port_rx.log').write_text('[1.000][FirstCut.cpp:239] First Cut start!\n[1.020][FirstCut.cpp:294] First Cut finish!\n', encoding='utf-8')
            (src / 'hw_data_1.csv').write_text('Time,Serial,Kind,Bias,Current,Motor,Piezo\n1.010,101,2,0.1,1,1234,500\n')
            data = src / 'data_1_high'; data.mkdir()
            (data / 'data_000000.txt').write_text('#1.010,101,2,0.1,0,1234,500,0,0\n' + '0xFFFFFFFF\n' * 100)
            out = Path(folder) / 'output'
            records = export(src, out)
            self.assertEqual(records[0]['samples'], 100)
            self.assertEqual(records[0]['positions'], 1)
            with (out / '001_FirstCut/current.csv').open(encoding='utf-8-sig') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]['current_raw'], '-1')
            self.assertEqual(rows[0]['unit'], 'pA')
            with self.assertRaises(FileExistsError): export(src, out)

    def test_missing_end_and_restart(self):
        r = intervals('[1.000][HoldGap.cpp:1] HoldGap start.\n')
        self.assertIsNone(r[0]['end'])
        with self.assertRaises(ValueError):
            intervals('[10.000][A.cpp:1] x\n[1.000][A.cpp:1] x')


if __name__ == '__main__': unittest.main()
