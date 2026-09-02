"""A status provider may ask what the other apps are reporting.

Reported from the Gamma with a Q playtest as `"status provider for 'status' raised"`
being printed over and over.

It was not a broken provider. LegendaryMissions' Status tile counts the apps with
something to say, so its provider calls `status_rows()` - and `status_rows` computes a
badge for EVERY app, the asking one included. That is a cycle: measured at **332 nested
provider calls for a single badge**, unwound only when Python's own recursion limit
tripped. `gui_app_badge` caught the RecursionError, logged its one unactionable line, and
returned None - after which the outer call completed and produced the RIGHT badge. So the
board looked correct and the log filled up, several lines a second, forever.

Two things are pinned here: the cycle is answered rather than re-entered, and a provider
that genuinely fails is reported once, naming the exception.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.gui import epadd
from sbs_utils.procedural.gui.epadd import gui_app_register, gui_app_badge, gui_app_list
from sbs_utils.procedural.gui.status_gui import status_rows

ENGI = 7


class _Sim:
    time_tick_counter = 0


class _BadgeBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(ENGI, "test"))
        FrameContext.page = None
        FrameContext.task = None
        clear_shared()
        GuiAppDecoratorLabel.clear()
        epadd._BADGE_REPORTED.clear()
        epadd._BADGE_RUNNING.clear()
        GuiClient(0)
        GuiClient(ENGI)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        GuiAppDecoratorLabel.clear()
        epadd._BADGE_REPORTED.clear()
        epadd._BADGE_RUNNING.clear()

    def app(self, tab, **kw):
        GuiAppDecoratorLabel(tab)
        gui_app_register(tab, **kw)

    def one(self, tab):
        return next(a for a in gui_app_list("engineering") if a["tab"] == tab)

    def _reporting_board(self):
        """LM's Status tile, in shape: it counts the apps with something to say, which
        means asking every app - itself included - for its badge."""
        calls = {"n": 0}

        def provider():
            calls["n"] += 1
            n = len([r for r in status_rows() if r.get("tab") != "status"])
            return f"{n} reporting" if n else ""

        self.app("status", title="Status", status=provider)
        self.app("messages", title="Messages", status=lambda: "2 unread")
        self.app("quest", title="Quests")
        return calls


class BadgeReentryTests(_BadgeBase):
    def test_a_self_referential_provider_runs_exactly_once(self):
        calls = self._reporting_board()
        gui_app_badge(self.one("status"))
        self.assertEqual(calls["n"], 1,
                         "the provider must not be re-entered while it is running")

    def test_and_it_still_produces_the_right_badge(self):
        """The guard must not buy quiet by breaking the count. `messages` is the one
        other app with something to say, so the board reports 1."""
        self._reporting_board()
        self.assertEqual(gui_app_badge(self.one("status")), "1 reporting")

    def test_the_app_is_left_out_of_the_rows_IT_asks_for(self):
        """Asked for its own badge mid-flight, an app has no answer yet - so it is
        absent from the rows its own provider sees, which is what LM's `!= "status"`
        filter was reaching for anyway.

        Observed from INSIDE the provider on purpose: at the top level `status` has a
        badge like any other app and belongs in the board.
        """
        seen = {}

        def provider():
            seen["tabs"] = [r["tab"] for r in status_rows()]
            return "counted"

        self.app("status", title="Status", status=provider)
        self.app("messages", title="Messages", status=lambda: "2 unread")
        gui_app_badge(self.one("status"))
        self.assertEqual(seen["tabs"], ["messages"])

    def test_at_the_top_level_the_board_still_holds_every_app(self):
        """The guard is scoped to the call, not to the app."""
        self._reporting_board()
        self.assertEqual(sorted(r["tab"] for r in status_rows("engineering")),
                         ["messages", "status"])

    def test_repeated_computations_do_not_repeat_the_provider(self):
        calls = self._reporting_board()
        for _ in range(5):
            gui_app_badge(self.one("status"))
        self.assertEqual(calls["n"], 5, "one call per badge, not 332")


class BadgeFailureReportingTests(_BadgeBase):
    def _boom(self, exc=ValueError("no cargo bay")):
        def provider():
            raise exc
        self.app("cargo", title="Cargo", status=provider)

    def test_a_failing_provider_still_costs_only_its_own_badge(self):
        self._boom()
        self.assertIsNone(gui_app_badge(self.one("cargo")))

    def test_it_is_reported_once_not_every_tick(self):
        """The provider is called per tile per build AND by the badge ticker, so an
        unguarded log is several identical lines a second for the rest of the mission -
        which is how this was reported."""
        self._boom()
        logged = []
        import sbs_utils.procedural.execution as execution
        orig = execution.log
        execution.log = lambda msg, *a, **k: logged.append(msg)
        try:
            for _ in range(10):
                gui_app_badge(self.one("cargo"))
        finally:
            execution.log = orig
        self.assertEqual(len(logged), 1, "reported once, as the docstring promises")

    def test_the_report_names_the_exception(self):
        """Without this it is the same unactionable line forever - which is exactly
        why the real cause went unlooked-at."""
        self._boom()
        logged = []
        import sbs_utils.procedural.execution as execution
        orig = execution.log
        execution.log = lambda msg, *a, **k: logged.append(msg)
        try:
            gui_app_badge(self.one("cargo"))
        finally:
            execution.log = orig
        self.assertIn("ValueError", logged[0])
        self.assertIn("no cargo bay", logged[0])

    def test_the_guard_is_released_even_when_the_provider_raises(self):
        """A provider that throws must not poison its own tab for the rest of the
        mission - the release is in a `finally` for this reason."""
        self._boom()
        gui_app_badge(self.one("cargo"))
        self.assertNotIn("cargo", epadd._BADGE_RUNNING)


if __name__ == "__main__":
    unittest.main()
