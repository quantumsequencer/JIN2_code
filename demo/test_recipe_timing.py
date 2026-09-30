import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from recipe_timing import record, median_duration


class TimingTests(unittest.TestCase):
    def test_persistent_median_and_invalid_file(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(median_duration(root), (30, 0))
            for v in (20, 30, 100): record(v, root)
            (root / 'broken.json').write_text('broken')
            self.assertEqual(median_duration(root), (30, 3))


if __name__ == '__main__': unittest.main()
