"""A GUI handler that reroutes must not be re-ticked mid-flight (LM issue #634).

`gui_message(widget, label)` runs the handler as a sub-task of the task that
BUILT the widget -- which, for a normal screen, is the page's gui_task. If that
handler calls gui_reroute_server()/gui_reroute_client(), the reroute ticks the
gui_task in the current frame, and MastAsyncTask.tick() finishes by calling
tick_subtasks() -- which walks straight back into the handler that is still
running:

    MessageTrigger.on_message -> sub_task.tick_in_context()
      -> PyTicker.tick()  `for res in gen:`
        -> gui_reroute_client() -> page.gui_task.tick_in_context()
          -> MastAsyncTask.tick() -> tick_subtasks() -> sub_task.tick()
            -> PyTicker.tick()  `for res in gen:`   <-- same live generator

With a pymast label that raises `ValueError: generator already executing` and
the mission dies on screen. With a MAST label it lands in MastTicker's plain
`while` loop instead, which Python is happy to re-enter -- it does not raise
here, but the ticker is re-entered mid-command all the same.

The reporter's workarounds (`await delay_app(0.01)` before the reroute, or
gui_task_jump instead of it) work only because they move the tick out of the
current frame.

Self-contained on purpose: `unittest discover -s tests` imports test modules as
TOP-LEVEL names, so importing a sibling test module as `tests.<name>` would
create a second copy of it, and any MastGlobals registration in that copy would
shadow the first one's. The harness here is deliberately a small twin of the one
in test_gui_message_dead_builder.py rather than an import of it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent, props_display_text
from sbs_utils.mast.label import label
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.execution import END
from sbs_utils.procedural.gui.navigation import gui_reroute_client

CID = 1

# Names are unique to this module so they cannot collide in the flat MastGlobals
# namespace with another test file's probes.
REROUTE_HITS = []


def reroute_probe(what):
    REROUTE_HITS.append(what)


MastGlobals.import_python_function(reroute_probe)


# @label() registers the raw function and hands back a wrapper. That wrapper is
# a plain function -- not str, not Label -- which is exactly why
# MastAsyncTask.jump routes it to the PyTicker rather than the MastTicker.
@label()
def reroute_pymast_handler():
    reroute_probe("pymast")
    gui_reroute_client(CID, "screen_two")
    yield END()


MastGlobals.import_python_function(reroute_pymast_handler)


SCREEN_TWO = """
== screen_two ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("SECOND")
    await gui()
"""

PYMAST_REROUTE = """
gui_section("area: 5,5,95,95;")
gui_row()
b = gui_button("Press")
gui_message(b, label=reroute_pymast_handler)
await gui()
""" + SCREEN_TWO

MAST_REROUTE = """
gui_section("area: 5,5,95,95;")
gui_row()
b = gui_button("Press")
gui_message(b, label=handler)
await gui()

== handler ==
    reroute_probe("mast")
    gui_reroute_client(%d, "screen_two")
    ->END
""" % CID + SCREEN_TWO

TASK_JUMP = """
gui_section("area: 5,5,95,95;")
gui_row()
b = gui_button("Press")
gui_message(b, label=handler)
await gui()

== handler ==
    reroute_probe("mast")
    gui_task_jump("screen_two")
    ->END
""" + SCREEN_TWO


class ReroutePage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    """Build a real StoryPage from a MAST snippet, present it, click by text."""

    def start(self, code):
        REROUTE_HITS.clear()
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

        story = MastStory()
        errors = story.compile(code, "reroute", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        ReroutePage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        # StoryScheduler OVERRIDES `runtime_error`, so patching it on MastScheduler
        # binds a method nothing calls and the assertion below is vacuous. The
        # class-level `on_runtime_error` seam is what the story scheduler actually
        # fires (and is what cosmos_dev's verdict uses).
        MastScheduler.on_runtime_error = self.errors.append

        self.page = ReroutePage()
        Gui.push(CID, self.page)
        self.present(3)
        return self.page

    def tearDown(self):
        # hasattr, NOT "is not None": `on_runtime_error` DEFAULTS to None, so a
        # truthiness guard skips the restore and leaks this test's hook - and the
        # list it appends to - into every test that runs afterwards.
        if hasattr(self, "_orig_rte"):
            MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        ReroutePage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        REROUTE_HITS.clear()

    def present(self, n=1):
        for _ in range(n):
            sbs.sim._time_tick_counter += 30      # ~1 sim-second per present
            self.page.present(FakeEvent(CID, "gui_present"))

    def visible(self):
        out = []
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown:
                out.append(shown.strip())
        return out

    def find_tag(self, text):
        want = text.strip().lower()
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown and shown.strip().lower() == want:
                return tag
        self.fail(f"no widget showing {text!r}; on screen: {self.visible()}")

    def click(self, text="Press"):
        """A click the way the engine delivers one: dispatch, then a tick.

        handlerhooks._cosmos_event_handler does Gui.on_message(event) and then
        tick_the_rest(event) in the same breath, so a tick ALWAYS follows a
        click. Dispatching without it produces states the engine cannot reach.
        """
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message",
                                 sub_tag=self.find_tag(text)))
        self.present(1)


class TestRerouteFromHandler(_Base):
    def test_pymast_handler_reroute_does_not_crash(self):
        # Before the re-entrancy guard this raises ValueError: generator
        # already executing, straight out of the click dispatch.
        self.start(PYMAST_REROUTE)
        self.click()
        self.assertEqual(self.errors, [])
        self.assertIn("SECOND", self.visible())

    def test_pymast_handler_runs_exactly_once(self):
        self.start(PYMAST_REROUTE)
        self.click()
        self.assertEqual(REROUTE_HITS, ["pymast"])

    def test_mast_handler_reroute_still_works(self):
        # The MAST twin never raised -- pin that it still reroutes, once.
        self.start(MAST_REROUTE)
        self.click()
        self.assertEqual(self.errors, [])
        self.assertEqual(REROUTE_HITS, ["mast"])
        self.assertIn("SECOND", self.visible())

    def test_gui_task_jump_still_works(self):
        # The form that already worked -- it must keep working.
        self.start(TASK_JUMP)
        self.click()
        self.assertEqual(self.errors, [])
        self.assertEqual(REROUTE_HITS, ["mast"])
        self.assertIn("SECOND", self.visible())


if __name__ == "__main__":
    unittest.main()
