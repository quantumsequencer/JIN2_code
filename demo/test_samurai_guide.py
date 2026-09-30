import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from types import SimpleNamespace
import unittest

from workflow import Workflow, STEPS
from samurai_guide import guidance, SamuraiGuide, POSES


class GuideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def window(self, **kwargs):
        values = dict(state=Workflow(configured=True), live=False, problem='', operation=None,
                      engine=None, host_recent=True)
        values.update(kwargs)
        return SimpleNamespace(**values)

    def test_all_steps_and_measurement_have_guidance(self):
        w = self.window()
        for index in range(len(STEPS)):
            w.state.active = index
            mood, lines = guidance(w)
            self.assertNotEqual(mood, 'ready')
            self.assertTrue(lines)
        w.state.active = None
        w.state.completed = 11
        self.assertEqual(guidance(w)[0], 'ready')
        w.state.measurement = True
        self.assertEqual(guidance(w)[0], 'measure')

    def test_alert_and_pending_response_override_completion(self):
        w = self.window(live=True)
        w.state.completed = 11
        w.problem = 'failure'
        self.assertEqual(guidance(w)[0], 'attention')
        w.problem = ''
        for operation in ('stop', 'finalize', 'piezo_cleanup', 'quality_cleanup', 'timed_cleanup'):
            w.operation = operation
            self.assertEqual(guidance(w)[0], 'attention')
        w.operation = 'baseline'
        self.assertEqual(guidance(w)[0], 'focus')
        w.operation = None
        w.state.measurement = True
        w.host_recent = False
        self.assertEqual(guidance(w)[0], 'attention')

    def test_variations_do_not_advance_workflow(self):
        w = self.window()
        w.state.active = 5
        w.state.completed = 5
        guide = SamuraiGuide()
        guide.sync(w, now=100)
        first = guide.portrait.pose, guide.portrait.variant
        guide.sync(w, now=109)
        self.assertNotEqual(first, (guide.portrait.pose, guide.portrait.variant))
        guide.sync(w, now=10000)
        self.assertEqual((w.state.active, w.state.completed), (5, 5))
        self.assertEqual(len(guide.steps), 11)
        self.assertEqual(guide.steps[4].accessibleDescription(), '完了')
        self.assertEqual(guide.steps[5].accessibleDescription(), '進行中')
        self.assertEqual(guide.steps[6].accessibleDescription(), '待機')
        self.assertFalse(guide.portrait.atlas.isNull())
        self.assertTrue(guide.portrait.atlas.hasAlphaChannel())
        w.problem = 'failure'
        guide.sync(w, now=10001)
        self.assertEqual(guide.portrait.pose, 5)
        self.assertEqual(guide.portrait.mood, 'attention')
        guide.close()

    def test_same_gesture_has_random_variants_without_immediate_repeats(self):
        guide = SamuraiGuide()
        guide._random.seed(1234)
        w = self.window(problem='failure')
        seen = set()
        previous = None
        for tick in range(30):
            guide.sync(w, now=100+tick*8)
            image = guide.portrait.pose, guide.portrait.variant
            self.assertIn(image[0], POSES['attention'])
            self.assertNotEqual(image, previous)
            guide.sync(w, now=100+tick*8+.1)
            self.assertEqual(image, (guide.portrait.pose, guide.portrait.variant))
            seen.add(image[1])
            previous = image
        self.assertEqual(seen, {0, 1, 2})
        for atlas in guide.portrait.atlases:
            self.assertFalse(atlas.isNull())
            self.assertTrue(atlas.hasAlphaChannel())
        guide.close()

    def test_portrait_does_not_move_between_image_changes(self):
        guide = SamuraiGuide()
        w = self.window()
        w.state.active = 5
        guide.show()
        guide.sync(w, now=100)
        self.app.processEvents()
        first = guide.portrait.grab().toImage()
        guide.sync(w, now=103)
        self.app.processEvents()
        self.assertEqual(first, guide.portrait.grab().toImage())
        guide.close()


if __name__ == '__main__':
    unittest.main()
