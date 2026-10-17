"""`seed=` on the engine's command line seeds the mission.

The headless runner seeds from its own `--seed`; on the engine nothing applied `seed=`,
so `sbs run ... seed=7` produced different faces, names and spawns on every launch, and
a still re-shot for a course no longer matched the marks placed on the last one.

Driven through StoryPage.start_story as the server - the path the engine takes - with the
draw made by the story's own top-level code, so the seed must land before that runs.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (settle node import order)
from cosmos_dev.mock import sbs
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.execution import get_shared_variable
from sbs_utils.procedural.command_line import command_line_scope_reset

STORY = """
shared seed_draw = random.random()
"""


class SeedPage(StoryPage):
    story = None


class TestCommandLineSeed(unittest.TestCase):
    def setUp(self):
        self._argv = list(sbs._command_line)

    def tearDown(self):
        sbs._command_line[:] = self._argv
        command_line_scope_reset()
        Gui.clients = {}
        SeedPage.story = None
        FrameContext.mast = None
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None

    def _draw(self, *args):
        sbs._command_line[:] = ["Artemis3-x64-release.exe", *args]
        command_line_scope_reset()
        Gui.clients = {}
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        errors = story.compile(STORY, "seedtest", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        SeedPage.story = story
        page = SeedPage()
        page.start_story(0)
        return get_shared_variable("seed_draw")

    def test_same_seed_same_draw(self):
        first = self._draw("seed=7")
        self.assertIsNotNone(first)
        self.assertEqual(first, self._draw("seed=7"))

    def test_different_seeds_differ(self):
        self.assertNotEqual(self._draw("seed=7"), self._draw("seed=8"))

    def test_no_seed_is_not_pinned(self):
        # Without the argument the mission's randomness is left alone.
        self.assertNotEqual(self._draw(), self._draw())


if __name__ == "__main__":
    unittest.main()
