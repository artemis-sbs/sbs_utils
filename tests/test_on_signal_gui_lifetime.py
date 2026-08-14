"""How long an `on signal x:` block lives, relative to the GUI build (LM #589).

The GUI system has no gui_begin(). It notices a new build lazily, from the first
TAGGED WIDGET (`add_tag` -> `on_new_gui`), and the teardown there used to drop
every inline signal handler the GUI task owned. But by that point the new build
has already been running for several lines, so an `on signal` written above the
first widget was registered and then purged along with the old build's handlers.
A `gui_section` does not count -- it never reaches add_tag -- which is why the
issue reporter saw the section behave and the text widget not.

Both flag states are exercised throughout: `buffer_inline_signals = False` is
the old wholesale purge and is pinned here so the change stays measured rather
than guessed, exactly as tests/test_gui_message_dead_builder.py does for #707.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast.mastscheduler import MastScheduler, MastAsyncTask
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import (FrameContext, FrameContextOverride, Context,
                               FakeEvent, props_display_text)
from sbs_utils.procedural.signal import signal_emit

CID = 1

# Module-level collector, so these assertions do not depend on `shared` variable
# scoping -- which is not what they are about.
HITS = []


def on_signal_probe(what):
    HITS.append(what)


MastGlobals.import_python_function(on_signal_probe)


class SignalPage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    """Build a real StoryPage from a MAST snippet, present it, emit signals."""

    # Subclasses set this; None means "leave the shipped default alone".
    BUFFER = None

    def setUp(self):
        self._buffer = MastAsyncTask.buffer_inline_signals
        if self.BUFFER is not None:
            MastAsyncTask.buffer_inline_signals = self.BUFFER

    def tearDown(self):
        MastAsyncTask.buffer_inline_signals = self._buffer
        if getattr(self, "_orig_rte", None) is not None:
            MastScheduler.runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        SignalPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        HITS.clear()

    def start(self, code):
        HITS.clear()
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(code, "onsignal", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        SignalPage.story = story
        FrameContext.mast = story
        self.story = story

        self.errors = []
        self._orig_rte = MastScheduler.runtime_error
        MastScheduler.runtime_error = lambda s, message: self.errors.append(message)

        self.page = SignalPage()
        Gui.push(CID, self.page)
        self.present(3)
        return self.page

    def present(self, n=1):
        for _ in range(n):
            # the mock sim exposes time_tick_counter read-only; physics owns the
            # backing field, and nothing runs physics in a unit test.
            sbs.sim._time_tick_counter += 30      # ~1 sim-second per present
            self.page.present(FakeEvent(CID, "gui_present"))

    def emit(self, name="example_signal"):
        """An emit the way a mission makes one -- inside the page context."""
        with FrameContextOverride(None, self.page):
            signal_emit(name)
        self.present(1)
        self.assertEqual(self.errors, [], f"runtime errors: {self.errors}")

    def find_tag(self, text):
        want = text.strip().lower()
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown and shown.strip().lower() == want:
                return tag
        self.fail(f"no widget showing {text!r}; on screen: {self.visible()}")

    def visible(self):
        out = []
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown:
                out.append(shown.strip())
        return out

    def click(self, text):
        """A click the way the engine delivers one: dispatch, then a tick.

        handlerhooks._cosmos_event_handler does Gui.on_message(event) and then
        tick_the_rest(event) in the same breath, so a tick ALWAYS follows.
        """
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message",
                                 sub_tag=self.find_tag(text)))
        self.present(2)

    def inline_infos(self):
        """Every inline (non-jump) registration the GUI task still owns."""
        found = []
        for name, task_map in self.story.signal_observers.items():
            for task, infos in task_map.items():
                if task is not self.page.gui_task:
                    continue
                found += [(name, i) for i in infos if not i.is_jump]
        return found


# --- fixtures ---------------------------------------------------------------

# The issue repro. Blocks 0 and 1 sit above the first tagged widget; the
# gui_section between them is deliberate -- it proves the section is not what
# trips the teardown.
ISSUE_589 = """
on signal example_signal:
    on_signal_probe("block0")

gui_section(style="area:10,10,50,20;")

on signal example_signal:
    on_signal_probe("block1")

gui_text("text A")

on signal example_signal:
    on_signal_probe("block2")

gui_text("text B")

on signal example_signal:
    on_signal_probe("block3")

await gui()
"""

# No GUI is ever built or presented. The handler must still fire -- this is the
# case that forbids deferring registration to present time.
NO_GUI = """
on signal example_signal:
    on_signal_probe("idle")
yield idle
"""

# Switching screens, from LM #579. The first screen handler must die.
TWO_SCREENS = """
on signal example_signal:
    on_signal_probe("first")
gui_section(style="area:10,10,50,20;")
gui_text("first screen")
on gui_message(gui_button("Next")):
    jump second_screen
await gui()

== second_screen ==
    on signal example_signal:
        on_signal_probe("second")
    gui_section(style="area:10,10,50,20;")
    gui_text("second screen")
    on gui_message(gui_button("Back")):
        jump main
    await gui()
"""

# A jump registration is NOT gui-transient: it survives every new GUI, and only
# ends when its task does. This is the same is_jump=True path a //signal route
# uses -- the route form is not spelled here because the compiler appends its
# injected signal_register to the END of main, which this fixture never reaches
# (it parks in await gui() first). That the route compiles to is_jump=True is
# covered by tests/test_signal_route_registration.py.
WITH_JUMP_REGISTRATION = """
signal_register("example_signal", jumped)
on signal example_signal:
    on_signal_probe("inline")
gui_text("screen one")
on gui_message(gui_button("Next")):
    jump screen_two
await gui()

== screen_two ==
    gui_text("screen two")
    await gui()

== jumped ==
    on_signal_probe("jump")
    ->END
"""

# A build that adds NO tagged widget, so on_new_gui never fires for the build
# that follows it. gui_section alone does not reach add_tag.
SECTION_ONLY = """
on signal example_signal:
    on_signal_probe("sectiononly")
gui_section(style="area:10,10,50,20;")
await gui()
"""


class TestIssue589Fixed(_Base):
    """With the buffering on -- the behavior the issue asks for."""
    BUFFER = True

    def test_every_block_runs_wherever_it_sits(self):
        self.start(ISSUE_589)
        self.emit()
        self.assertEqual(sorted(HITS),
                         ["block0", "block1", "block2", "block3"])

    def test_it_keeps_working_on_a_second_emit(self):
        self.start(ISSUE_589)
        self.emit()
        HITS.clear()
        self.emit()
        self.assertEqual(sorted(HITS),
                         ["block0", "block1", "block2", "block3"])

    def test_a_handler_with_no_gui_at_all_still_fires(self):
        """The regression guard: registration is eager, never deferred."""
        self.start(NO_GUI)
        self.emit()
        self.assertEqual(HITS, ["idle"])

    def test_the_old_screens_handler_dies_and_the_new_one_lives(self):
        self.start(TWO_SCREENS)
        self.click("Next")
        self.emit()
        self.assertEqual(HITS, ["second"])

    def test_switching_back_and_forth_leaves_one_handler(self):
        self.start(TWO_SCREENS)
        for _ in range(5):
            self.click("Next")
            self.click("Back")
        self.assertEqual(len(self.inline_infos()), 1,
                         f"handlers accumulated: {self.inline_infos()}")
        self.emit()
        self.assertEqual(HITS, ["first"])

    def test_a_jump_registration_survives_a_new_gui(self):
        self.start(WITH_JUMP_REGISTRATION)
        self.click("Next")
        self.emit()
        self.assertEqual(HITS, ["jump"])

    def test_a_build_with_no_tagged_widget_still_hands_off(self):
        """on_new_gui never fired for it, so swap_inline_signals does the purge."""
        self.start(SECTION_ONLY)
        self.emit()
        self.assertEqual(HITS, ["sectiononly"])
        # Re-enter the same screen: the old registration must be replaced, not
        # joined, or the block would run twice per emit.
        HITS.clear()
        self.page.gui_task.jump("main")
        self.present(3)
        self.emit()
        self.assertEqual(HITS, ["sectiononly"])
        self.assertEqual(len(self.inline_infos()), 1)


class TestIssue589Characterization(_Base):
    """With the buffering off -- the defect, pinned.

    These assertions describe the behavior the fix replaces. They are expected to
    disagree with TestIssue589Fixed; that disagreement is the point.
    """
    BUFFER = False

    def test_blocks_above_the_first_widget_are_lost(self):
        self.start(ISSUE_589)
        self.emit()
        self.assertEqual(sorted(HITS), ["block2", "block3"],
                         "pre-fix: the first tagged widget purges blocks 0 and 1")

    def test_a_handler_with_no_gui_at_all_still_fires(self):
        """Unchanged by the fix -- it worked before and must keep working."""
        self.start(NO_GUI)
        self.emit()
        self.assertEqual(HITS, ["idle"])

    def test_switching_screens_loses_both_handlers(self):
        """Pre-fix, switching screens left NO handler at all.

        The old screen dying is correct and intended. The new screen dying with
        it is the defect: its `on signal` sits above its first widget, so the
        teardown that came for its predecessor took it too. This is the shape the
        #579 reporter hit and could not work around.
        """
        self.start(TWO_SCREENS)
        self.click("Next")
        self.emit()
        self.assertEqual(HITS, [])

    def test_a_jump_registration_survives_a_new_gui(self):
        self.start(WITH_JUMP_REGISTRATION)
        self.click("Next")
        self.emit()
        self.assertEqual(HITS, ["jump"])


if __name__ == "__main__":
    unittest.main()
