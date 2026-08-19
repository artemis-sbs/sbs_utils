"""`await gui()` reached off the console's main GUI task (LM issue #714).

A GUI handler runs on whatever task BUILT the widget, which is very often not
the GUI task. When such a handler paints a screen and awaits, the console has
to follow it. Historically it did not: gui() printed a warning and handed back
a promise the page never adopted, so the handler hung silently and forever.

Both flag states are pinned here.

  TestOffGuiTaskToday   promote_await_gui = False -- characterization.
  TestPromotion         promote_await_gui = True  -- the fix.

The rule the promotion has to obey, and the reason it is a JUMP and not a
handover: the GUI task's in-flight GuiPromise must NEVER resolve. Resolving it
runs whatever follows the GUI task's own `await gui()`, which is a screen the
scripter never asked to leave.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import logging
import unittest

from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.core_nodes.on_change import OnChangeRuntimeNode
from sbs_utils.agent import Agent

from sbs_utils.procedural.gui.gui import await_gui_sites_clear

from test_gui_message_dead_builder import _Base, HITS, CID


class _Promo(_Base):
    """Everything the #707 fix ships with, plus the promotion under test."""

    PROMOTE = True

    def setUp(self):
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        self._promote = MastAsyncTask.promote_await_gui
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True
        MastAsyncTask.promote_await_gui = self.PROMOTE
        # The warn-once-per-site set is module level and outlives a test.
        await_gui_sites_clear()

    def _restore_flags(self):
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop
        MastAsyncTask.promote_await_gui = self._promote


# --- fixtures ---------------------------------------------------------------
# Every one builds a "Press" button whose handler ends up on a second screen
# showing "Second". `probe_hit("after")` marks the code AFTER the GUI task's own
# `await gui()` -- it must never run.

# Row 1: on_press=<label> -> jump -> await gui()   (the market_action shape)
ROW1_ON_PRESS_JUMP = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    await gui()
    probe_hit("after")
    ->END

== act ==
    probe_hit("acted")
    jump second

== second ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END
"""

# Row 2: `on gui_message(w):` block -> jump -> await gui()
ROW2_BLOCK_JUMP = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("acted")
        jump second
    await gui()
    probe_hit("after")
    ->END

== second ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END
"""

# Row 3: the handler paints IN ITS OWN LABEL and awaits -- no jump.
# This is what discriminates mechanic E (hand over the exact command) from
# mechanic A (re-run the label from the top): "acted" must appear ONCE.
ROW3_PAINT_IN_PLACE = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    await gui()
    probe_hit("after")
    ->END

== act ==
    probe_hit("acted")
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END
"""

# Row 4: a handler that only ACTS must not touch the GUI task.
ROW4_ACT_ONLY = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    await gui()
    probe_hit("after")
    ->END

== act ==
    probe_hit("acted")
    ->END
"""

# Row 8: an explicit gui_task_jump BEFORE the await wins; promotion no-ops.
ROW8_EXPLICIT_WINS = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    await gui()
    probe_hit("after")
    ->END

== act ==
    probe_hit("acted")
    gui_task_jump("third")
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END

== third ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Third")
    await gui()
    ->END
"""


# Row 5: two screens that bounce into each other, so the button is always
# there and the press can be repeated indefinitely.
ROW5_PING_PONG = """
jump ping

== ping ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="to_pong", is_sub_task=True)
    await gui()
    probe_hit("after")
    ->END

== to_pong ==
    probe_hit("acted")
    jump pong

== pong ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="to_ping", is_sub_task=True)
    await gui()
    probe_hit("after")
    ->END

== to_ping ==
    probe_hit("acted")
    jump ping
"""

# Row 6: a panel that repaints itself off `await gui(timeout=...)`. One press
# must not freeze it -- the user-visible face of a task parked with nothing to
# resume it.
ROW6_SELF_TICKING = """
jump panel

== panel ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    await gui(timeout=delay_sim(seconds=1))
    probe_hit("tick")
    jump panel

== act ==
    probe_hit("acted")
    ->END
"""

# Row 6b: the repaint target is ITSELF a self-ticking panel. After promotion
# the GUI task must keep ticking on the NEW screen.
ROW6B_SELF_TICKING_REPAINT = """
jump panel

== panel ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    await gui(timeout=delay_sim(seconds=1))
    probe_hit("tick")
    jump panel

== act ==
    probe_hit("acted")
    jump panel2

== panel2 ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui(timeout=delay_sim(seconds=1))
    probe_hit("tick2")
    jump panel2
"""


# --- scheduled-builder variants --------------------------------------------
# The rows above all build from the GUI task itself. These build from a task
# that paints and then ENDS -- the #707 shape, and the only place the revive
# machinery is load-bearing. Every row must behave the same either way.

SCHED_ON_PRESS_JUMP = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    await task_schedule(builder)
    await gui()
    probe_hit("after")
    ->END

== builder ==
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    ->END

== act ==
    probe_hit("acted")
    jump second

== second ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END
"""

SCHED_BLOCK_JUMP = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    await task_schedule(builder)
    await gui()
    probe_hit("after")
    ->END

== builder ==
    gui_row()
    b = gui_button("Press")
    on gui_message(b):
        probe_hit("acted")
        jump second
    ->END

== second ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END
"""

SCHED_PAINT_IN_PLACE = """
jump first

== first ==
    gui_section("area: 5,5,95,95;")
    await task_schedule(builder)
    await gui()
    probe_hit("after")
    ->END

== builder ==
    gui_row()
    gui_button("Press", on_press="act", is_sub_task=True)
    ->END

== act ==
    probe_hit("acted")
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Second")
    await gui()
    ->END
"""


class TestOffGuiTaskToday(_Promo):
    """Characterization: what happens with the promotion OFF.

    Measured, and NOT what the issue notes assumed. The pixels do follow the
    handler -- widgets are queued onto the PAGE by gui_* calls, whichever task
    makes them -- so the second screen draws. What does not follow is
    OWNERSHIP: the GUI task is still parked in the first label on the first
    promise, and the handler task is stranded in the second label forever,
    leaking in gui_task.sub_tasks.

    That is why this has been so hard to place. It does not look like nothing
    happened; it looks like the screen changed and then the flow died.
    """

    PROMOTE = False

    def test_the_screen_moves_but_the_gui_task_does_not(self):
        self.start(ROW1_ON_PRESS_JUMP)
        gui_task = self.page.gui_task
        self.click()
        self.present(3)
        self.assertIn("acted", HITS, "the handler itself does run")
        self.assertIn("Second", self.visible(), "and its widgets do draw")
        # ...but nothing else moved.
        self.assertEqual(gui_task.active_label, "first",
                         "the GUI task never left the first screen")
        self.assertNotIn("after", HITS)

    def test_the_handler_task_is_stranded_and_leaks(self):
        self.start(ROW1_ON_PRESS_JUMP)
        gui_task = self.page.gui_task
        self.click()
        self.present(3)
        stranded = [t for t in gui_task.sub_tasks if not t.done()]
        self.assertEqual(len(stranded), 1,
                         "the handler hangs on a promise nothing will resolve")
        self.assertEqual(stranded[0].active_label, "second")


class TestPromotion(_Promo):
    """The fix: the console follows the handler."""

    def _assert_moved(self):
        self.assertIn("Second", self.visible(),
                      f"console did not follow the handler; on screen: {self.visible()}")
        self.assertNotIn("after", HITS,
                         "the GUI task's own await gui() must NOT have resolved")

    def test_row1_on_press_label_that_jumps(self):
        self.start(ROW1_ON_PRESS_JUMP)
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1)
        self._assert_moved()

    def test_row2_inline_block_that_jumps(self):
        self.start(ROW2_BLOCK_JUMP)
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1)
        self._assert_moved()

    def test_row3_handler_paints_in_place_runs_once(self):
        self.start(ROW3_PAINT_IN_PLACE)
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1,
                         "the handler's pre-build code must not be re-executed")
        self._assert_moved()

    def test_row4_act_only_leaves_the_console_alone(self):
        self.start(ROW4_ACT_ONLY)
        before = self.visible()
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1)
        self.assertEqual(self.visible(), before, "an act-only handler must not repaint")
        self.assertNotIn("after", HITS)

    def test_row5_repeat_presses_leave_nothing_behind(self):
        self.start(ROW5_PING_PONG)
        gui_task = self.page.gui_task
        before = len(Agent.all)
        for _ in range(10):
            self.click()
            self.present(1)
        self.assertEqual(HITS.count("acted"), 10, "every press must land")
        self.assertNotIn("after", HITS)
        self.assertEqual(len(gui_task.label_stack), 0,
                         "every push must be balanced by a pop")
        self.assertEqual([t for t in gui_task.sub_tasks if not t.done()], [],
                         "no handler may be left stranded")
        # 10 presses must not grow the registry by 10 tasks.
        self.assertLess(len(Agent.all) - before, 3,
                        f"agents grew by {len(Agent.all) - before} over 10 presses")

    def test_row6_a_press_does_not_freeze_a_self_ticking_panel(self):
        self.start(ROW6_SELF_TICKING)
        self.click()
        HITS.clear()
        self.present(4)
        self.assertGreater(HITS.count("tick"), 0,
                           "the panel stopped repainting after a press")

    def test_row6b_the_promoted_screen_keeps_ticking(self):
        self.start(ROW6B_SELF_TICKING_REPAINT)
        self.click()
        self.present(2)
        self.assertIn("Second", self.visible())
        HITS.clear()
        self.present(4)
        self.assertGreater(HITS.count("tick2"), 0,
                           "the screen promotion landed on stopped repainting")
        self.assertEqual(HITS.count("tick"), 0,
                         "the old screen must not still be ticking")

    def test_row7_the_old_promise_is_superseded_never_resolved(self):
        self.start(ROW1_ON_PRESS_JUMP)
        old = self.page.gui_promise
        self.click()
        self.present(2)
        self.assertIsNot(self.page.gui_promise, old, "a new promise must be installed")
        self.assertNotIn("after", HITS)

    def test_row8_an_explicit_gui_task_jump_wins(self):
        self.start(ROW8_EXPLICIT_WINS)
        self.click()
        self.present(3)
        self.assertIn("Third", self.visible(),
                      f"gui_task_jump must win over promotion; on screen: {self.visible()}")
        self.assertNotIn("after", HITS)

    def test_row8_leaves_nothing_stranded_and_says_nothing(self):
        """Declining to promote is not the same as failing to.

        The scripter named the screen they wanted, so the handler is finished
        and must be ended -- not left parked on a promise nothing resolves --
        and this is correct code, so it must not be warned about.
        """
        logs = []

        class _Cap(logging.Handler):
            def emit(self, record):
                logs.append(record.getMessage())

        cap = _Cap()
        log = logging.getLogger("mast.runtime")
        log.addHandler(cap)
        try:
            self.start(ROW8_EXPLICIT_WINS)
            self.click()
            self.present(3)
        finally:
            log.removeHandler(cap)
        gui_task = self.page.gui_task
        self.assertEqual([t for t in gui_task.sub_tasks if not t.done()], [],
                         "the handler must be ended, not stranded")
        self.assertEqual([m for m in logs if "await gui()" in m], [],
                         "correct code must not be warned about")


class TestOffGuiTaskWarning(_Promo):
    """When nothing can be done, say so -- loudly enough to find."""

    PROMOTE = False

    def test_it_reaches_the_mast_runtime_log(self):
        logs = []

        class _Cap(logging.Handler):
            def emit(self, record):
                logs.append(record.getMessage())

        cap = _Cap()
        log = logging.getLogger("mast.runtime")
        log.addHandler(cap)
        try:
            self.start(ROW1_ON_PRESS_JUMP)
            self.click()
            self.present(2)
        finally:
            log.removeHandler(cap)
        hits = [m for m in logs if "await gui()" in m]
        self.assertEqual(len(hits), 1, f"expected exactly one warning, got {logs}")
        self.assertIn("gui_task_jump", hits[0], "it must name the way out")

    def test_it_warns_once_per_site_not_once_per_press(self):
        logs = []

        class _Cap(logging.Handler):
            def emit(self, record):
                logs.append(record.getMessage())

        cap = _Cap()
        log = logging.getLogger("mast.runtime")
        log.addHandler(cap)
        try:
            self.start(ROW5_PING_PONG)
            for _ in range(5):
                self.click()
                self.present(1)
        finally:
            log.removeHandler(cap)
        self.assertLessEqual(len([m for m in logs if "await gui()" in m]), 2,
                             "one warning per SITE, not per press")


class TestPromotionFromScheduledBuilder(_Promo):
    """The same rows, built by a task that ended before the press.

    This is where the #707 revive machinery is load-bearing: without it the
    handler never runs at all, so promotion never gets a chance.
    """

    def _assert_moved(self):
        self.assertIn("Second", self.visible(),
                      f"console did not follow the handler; on screen: {self.visible()}")
        self.assertNotIn("after", HITS,
                         "the GUI task's own await gui() must NOT have resolved")

    def test_on_press_label_that_jumps(self):
        self.start(SCHED_ON_PRESS_JUMP)
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1)
        self._assert_moved()

    def test_inline_block_that_jumps(self):
        self.start(SCHED_BLOCK_JUMP)
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1)
        self._assert_moved()

    def test_handler_paints_in_place_runs_once(self):
        self.start(SCHED_PAINT_IN_PLACE)
        self.click()
        self.present(2)
        self.assertEqual(HITS.count("acted"), 1,
                         "the handler's pre-build code must not be re-executed")
        self._assert_moved()

    def test_nothing_is_stranded_afterwards(self):
        self.start(SCHED_ON_PRESS_JUMP)
        self.click()
        self.present(3)
        gui_task = self.page.gui_task
        self.assertEqual([t for t in gui_task.sub_tasks if not t.done()], [],
                         "no handler or revived builder may be left running")
        self.assertEqual(len(gui_task.label_stack), 0)



# ---------------------------------------------------------------------------
# Phase 2: on_press=<label> runs as a hosted sub-task by default (LM #714)
# ---------------------------------------------------------------------------

MARKET_SHAPE = """
jump market_show

== market_show ==
    default market_msg = "-"
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text(f"msg {market_msg}")
    gui_button("Press", data={"mkey": "widget", "msell": 1}, on_press="market_action")
    await gui()
    probe_hit("after")
    ->END

--- market_action
    default mkey = ""
    default msell = 0
    probe_hit(f"act:{mkey}:{msell}")
    market_msg = f"Sold {mkey}."
    jump market_show
"""

ACT_ONLY_DATA = """
jump screen

== screen ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", data={"slot": 7}, on_press="act")
    await gui()
    probe_hit("after")
    ->END

== act ==
    default slot = -1
    probe_hit(f"slot:{slot}")
    ->END
"""

PARITY_DICT = """
jump screen

== screen ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", data={"slot": 7}, on_press="act")
    await gui()
    probe_hit("after")
    ->END

--- act
    default slot = -1
    probe_hit(f"slot:{slot}")
    jump screen
"""

PARITY_NONDICT = """
jump screen

== screen ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", data="just-a-string", on_press="act")
    await gui()
    probe_hit("after")
    ->END

--- act
    default data = "-"
    probe_hit(f"data:{data}")
    jump screen
"""

ACT_ONLY_NONDICT = """
jump screen

== screen ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_button("Press", data="just-a-string", on_press="act")
    await gui()
    probe_hit("after")
    ->END

== act ==
    default data = "-"
    probe_hit(f"data:{data}")
    ->END
"""


class _Phase2(_Base):
    """Both #714 flags on: the sub-task default and the promotion it needs."""

    DEFAULT_SUB_TASK = True

    def setUp(self):
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        self._promote = MastAsyncTask.promote_await_gui
        self._dflt = MastAsyncTask.handler_sub_task_default
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True
        MastAsyncTask.promote_await_gui = self.DEFAULT_SUB_TASK
        MastAsyncTask.handler_sub_task_default = self.DEFAULT_SUB_TASK
        await_gui_sites_clear()

    def _restore_flags(self):
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop
        MastAsyncTask.promote_await_gui = self._promote
        MastAsyncTask.handler_sub_task_default = self._dflt

    def handler(self):
        entry = self.page.tag_map[self.find_tag("Press")]
        return entry[1] if isinstance(entry, tuple) else entry


class TestCoupling(_Phase2):
    """The default flip is meaningless -- and dangerous -- without promotion."""

    DEFAULT_SUB_TASK = False

    def test_the_default_does_not_flip_on_its_own(self):
        MastAsyncTask.handler_sub_task_default = True
        MastAsyncTask.promote_await_gui = False
        self.assertFalse(MastAsyncTask.handler_defaults_to_sub_task(),
                         "flipping the default alone would break every repaint handler")

    def test_both_together_flip_it(self):
        MastAsyncTask.handler_sub_task_default = True
        MastAsyncTask.promote_await_gui = True
        self.assertTrue(MastAsyncTask.handler_defaults_to_sub_task())

    def test_legacy_default_still_jumps_the_builder(self):
        self.start(ACT_ONLY_DATA)
        self.assertFalse(self.handler().runs_as_sub_task(),
                         "with the flags off nothing about on_press changes")


class TestSubTaskDefault(_Phase2):

    def test_an_unspecified_on_press_is_now_a_sub_task(self):
        self.start(ACT_ONLY_DATA)
        self.assertTrue(self.handler().runs_as_sub_task())

    def test_explicit_false_still_jumps_the_builder(self):
        self.start(ACT_ONLY_DATA.replace('on_press="act"',
                                         'on_press="act", is_sub_task=False'))
        self.assertFalse(self.handler().runs_as_sub_task(),
                         "an explicit False is honored, deprecated or not")

    def test_a_repaint_handler_still_works(self):
        """The market shape: data + act + `jump <paint>` + `await gui()`."""
        self.start(MARKET_SHAPE)
        self.click()
        self.present(2)
        self.assertIn("act:widget:1", HITS, "data= must reach the handler")
        self.assertNotIn("after", HITS, "the GUI task must not fall past its await")
        self.assertIn("msg Sold widget.", " ".join(self.visible()),
                      f"the repaint must show the handler's state; saw {self.visible()}")

    def test_a_repaint_handler_survives_repeated_presses(self):
        self.start(MARKET_SHAPE)
        for _ in range(8):
            self.click()
            self.present(1)
        self.assertEqual(len([h for h in HITS if h.startswith("act:")]), 8)
        self.assertNotIn("after", HITS)
        gui_task = self.page.gui_task
        self.assertEqual(len(gui_task.label_stack), 0)
        self.assertEqual([t for t in gui_task.sub_tasks if not t.done()], [])

    def test_an_act_only_handler_may_now_end_with_END(self):
        """The exact confusion in #707: how should the handler label end?

        With the legacy `is_sub_task=False`, `->END` ends the GUI TASK, because
        the handler IS that task -- the console dies. As a sub-task it just ends
        the handler, which is what every scripter expected it to mean.
        """
        self.start(ACT_ONLY_DATA)
        self.click()
        self.present(2)
        self.assertIn("slot:7", HITS)
        self.assertFalse(self.page.gui_task.done(),
                         "->END in the handler must not kill the console")
        self.assertIn("Press", self.visible(), "the screen is still up")

    def test_the_legacy_default_kills_the_console_on_END(self):
        """Pinned so the difference is measured, not asserted from memory."""
        MastAsyncTask.handler_sub_task_default = False
        self.start(ACT_ONLY_DATA)
        with self.assertRaises(Exception) as cm:
            self.click()
        self.assertIn("END or Yield the last GUI Task", str(cm.exception))

    def test_an_act_only_handler_ends_cleanly(self):
        self.start(ACT_ONLY_DATA)
        self.click()
        self.present(2)
        self.assertIn("slot:7", HITS)
        self.assertNotIn("after", HITS)
        self.assertEqual([t for t in self.page.gui_task.sub_tasks if not t.done()], [])


class TestDataParity(_Phase2):
    """data= must mean the same thing down both paths.

    A dict was always unpacked by both (start_sub_task walks `inputs`), but a
    NON-dict was not: the jump path bound it to a variable called `data` while
    the sub-task path handed it to `for k in inputs`, which walks a string one
    character at a time.
    """

    def _run(self, code, sub_task):
        code = code.replace('on_press="act"',
                            f'on_press="act", is_sub_task={sub_task}')
        self.start(code)
        self.click()
        self.present(2)
        return [h for h in HITS if ":" in h]

    def test_a_dict_unpacks_the_same_either_way(self):
        # start() rebuilds the sim and the page, so two runs in one test are
        # independent without touching setUp/tearDown.
        jumped = self._run(PARITY_DICT, False)
        subbed = self._run(PARITY_DICT, True)
        self.assertEqual(jumped, subbed)
        self.assertEqual(jumped, ["slot:7"])

    def test_a_non_dict_binds_to_data_the_same_either_way(self):
        jumped = self._run(PARITY_NONDICT, False)
        subbed = self._run(PARITY_NONDICT, True)
        self.assertEqual(jumped, subbed,
                         "non-dict data used to walk the string in the sub-task path")
        self.assertEqual(jumped, ["data:just-a-string"])


# ---------------------------------------------------------------------------
# Phase 3: `on change` registered by a scheduled builder (LM #713)
# ---------------------------------------------------------------------------

WATCHER_IN_PANEL = """
jump screen

== screen ==
    shared counter = 0
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Main")
    on change counter:
        probe_hit(f"main:{counter}")
    gui_sub_task_schedule(panel)
    await gui()
    ->END

== panel ==
    gui_row()
    gui_text("Panel")
    on change counter:
        probe_hit(f"panel:{counter}")
    ->END
"""

WATCHER_SEES_BUILDER_SCOPE = """
jump screen

== screen ==
    shared counter = 0
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Main")
    gui_sub_task_schedule(panel, {"who": "panel-A"})
    await gui()
    ->END

== panel ==
    gui_row()
    gui_text("Panel")
    on change counter:
        probe_hit(f"{who}:{counter}")
    ->END
"""


class _Watchers(_Base):
    REHOST = True

    def setUp(self):
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        self._promote = MastAsyncTask.promote_await_gui
        self._dflt = MastAsyncTask.handler_sub_task_default
        self._rehost = MastAsyncTask.rehost_gui_watchers
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True
        MastAsyncTask.promote_await_gui = True
        MastAsyncTask.handler_sub_task_default = True
        MastAsyncTask.rehost_gui_watchers = self.REHOST
        await_gui_sites_clear()

    def _restore_flags(self):
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop
        MastAsyncTask.promote_await_gui = self._promote
        MastAsyncTask.handler_sub_task_default = self._dflt
        MastAsyncTask.rehost_gui_watchers = self._rehost

    def bump(self, value):
        Agent.SHARED.set_inventory_value("counter", value)
        self.present(2)


class TestWatcherToday(_Watchers):
    """Characterization: #713 as reported."""

    REHOST = False

    def test_a_panel_watcher_never_fires(self):
        self.start(WATCHER_IN_PANEL)
        self.bump(1)
        self.assertIn("main:1", HITS, "the GUI task's own watcher works")
        self.assertNotIn("panel:1", HITS,
                         "TODAY: the panel builder ended, taking its watcher with it")

    def test_and_the_builder_is_already_gone(self):
        self.start(WATCHER_IN_PANEL)
        self.assertEqual([s for s in self.page.gui_task.sub_tasks if not s.done()], [],
                         "tick_subtasks disposed it; run_on_change can no longer reach it")


class TestWatcherRehosted(_Watchers):
    """The fix: a watcher belongs to the BUILD, like every other handler."""

    def test_a_panel_watcher_fires(self):
        self.start(WATCHER_IN_PANEL)
        self.bump(1)
        self.assertIn("main:1", HITS)
        self.assertIn("panel:1", HITS, "#713")

    def test_it_keeps_firing(self):
        self.start(WATCHER_IN_PANEL)
        for n in range(1, 5):
            self.bump(n)
        self.assertEqual([h for h in HITS if h.startswith("panel:")],
                         [f"panel:{n}" for n in range(1, 5)])

    def test_the_block_runs_in_the_builders_scope(self):
        """`who` is the sub-task's own variable, not the GUI task's."""
        self.start(WATCHER_SEES_BUILDER_SCOPE)
        self.bump(1)
        self.assertIn("panel-A:1", HITS)

    def test_the_watcher_is_hosted_on_the_gui_task(self):
        self.start(WATCHER_IN_PANEL)
        gui_task = self.page.gui_task
        self.assertEqual(len(gui_task.on_change_items), 2,
                         "both the GUI task's own and the panel's")

    def test_repeated_fires_leave_the_task_balanced(self):
        self.start(WATCHER_IN_PANEL)
        for n in range(1, 7):
            self.bump(n)
        builders = [s for s in self.page.gui_task.sub_tasks if not s.done()]
        self.assertEqual(builders, [], "a revived builder must end again each time")
        self.assertEqual(len(self.page.gui_task.label_stack), 0)

    def test_the_gui_tasks_own_watcher_is_untouched(self):
        self.start(WATCHER_IN_PANEL)
        self.bump(1)
        self.assertEqual([h for h in HITS if h.startswith("main:")], ["main:1"],
                         "exactly once -- re-hosting must not double-register")


# The one shape in the whole LM/OU corpus that matches #713 --
# gamemaster_comms/gamemaster_ship_data.mast:90 -- ends its builder with
# `yield idle` rather than ->END, which keeps the task alive and is why it works
# today. Re-hosting must not double-fire it.
WATCHER_BUILDER_STAYS_ALIVE = """
jump screen

== screen ==
    shared counter = 0
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Main")
    gui_sub_task_schedule(panel)
    await gui()
    ->END

== panel ==
    gui_row()
    gui_text("Panel")
    on change counter:
        probe_hit(f"panel:{counter}")
    yield idle
"""


class TestWatcherLiveBuilder(_Watchers):
    """`yield idle` keeps the builder alive -- the existing workaround."""

    def test_it_fires_exactly_once_per_change(self):
        self.start(WATCHER_BUILDER_STAYS_ALIVE)
        for n in range(1, 4):
            self.bump(n)
        self.assertEqual([h for h in HITS if h.startswith("panel:")],
                         ["panel:1", "panel:2", "panel:3"],
                         "re-hosting must not register the watcher twice")

    def test_the_builder_is_still_alive(self):
        self.start(WATCHER_BUILDER_STAYS_ALIVE)
        alive = [s for s in self.page.gui_task.sub_tasks if not s.done()]
        self.assertEqual(len(alive), 1, "yield idle parks it, it does not end it")


class TestWatcherLiveBuilderToday(TestWatcherLiveBuilder):
    """...and it must keep working with the flag OFF, since it does today."""
    REHOST = False


if __name__ == "__main__":
    unittest.main()
