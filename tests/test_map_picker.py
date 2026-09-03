"""`@map` selection without LegendaryMissions: the `if` filter and `map_start`.

Both halves of map selection used to live in LM, so a mission loading only sbs_utils could
neither list its maps nor start one. These cover the library side of closing that.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.procedural import maps as maps_mod
from sbs_utils.procedural.maps import maps_get_list, map_start


class FakeMap:
    """Stands in for a MapCardLabel. `shown` mimics CardLabelBase.test(task)."""

    def __init__(self, path, shown=True, raises=False):
        self.path = path
        self.display_name = path.title()
        self.desc = ""
        self._shown = shown
        self._raises = raises

    def test(self, task):
        if self._raises:
            raise ValueError("condition blew up")
        return self._shown


class FakePage:
    # gui_task matters: FrameContext.task is a PROPERTY that falls back to page.gui_task
    # when no task is set explicitly, so the "no task" case needs this to exist and be None.
    gui_task = None

    def __init__(self, labels):
        self.story = type("S", (), {"labels": labels})()


def _install(maps, task="a-task"):
    """Point FrameContext at a story holding these maps."""
    FrameContext.page = FakePage({"map/" + m.path: m for m in maps})
    FrameContext.task = task


class TestConditionalMapsAreHidden(unittest.TestCase):
    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None

    def test_false_condition_is_hidden(self):
        _install([FakeMap("alpha"), FakeMap("beta", shown=False)])
        self.assertEqual([m.path for m in maps_get_list()], ["alpha"])

    def test_true_condition_is_kept(self):
        _install([FakeMap("alpha"), FakeMap("beta", shown=True)])
        self.assertEqual([m.path for m in maps_get_list()], ["alpha", "beta"])

    def test_include_hidden_returns_everything(self):
        """game_code_decode resolves a map BY PATH; a saved code must keep working even
        when the map's condition happens to be false right now."""
        _install([FakeMap("alpha"), FakeMap("beta", shown=False)])
        self.assertEqual([m.path for m in maps_get_list(include_hidden=True)],
                         ["alpha", "beta"])

    def test_no_task_shows_everything(self):
        """The headless runner polls this from its own loop with NO task. Hiding every
        map there would stop --map working at all - far worse than one map too many."""
        _install([FakeMap("alpha"), FakeMap("beta", shown=False)], task=None)
        self.assertEqual([m.path for m in maps_get_list()], ["alpha", "beta"])

    def test_a_raising_condition_does_not_hide_the_map(self):
        _install([FakeMap("alpha", raises=True)])
        self.assertEqual([m.path for m in maps_get_list()], ["alpha"])

    def test_a_map_with_no_test_method_at_all_is_kept(self):
        """Not every map-like object implements test(); absence must mean shown."""
        class Bare:
            path = "alpha"
        _install([Bare()])
        self.assertEqual([x.path for x in maps_get_list()], ["alpha"])


class TestMapStart(unittest.TestCase):
    """map_start is the canonical launch sequence - it existed twice before, in LM's
    console and the headless runner, and the two had drifted."""

    def setUp(self):
        self.calls = []
        import sbs_utils.procedural.execution as ex
        import sbs_utils.procedural.signal as sig
        import sbs_utils.procedural.cosmos as cos
        self._orig = (ex.task_schedule, ex.set_shared_variable, sig.signal_emit,
                      cos.sim_resume, maps_mod.map_apply_defaults,
                      maps_mod.map_apply_crew)
        ex.task_schedule = lambda l, **k: self.calls.append(("schedule", l, k))
        ex.set_shared_variable = lambda k, v: self.calls.append(("shared", k, v))
        sig.signal_emit = lambda n, d=None: self.calls.append(("signal", n))
        cos.sim_resume = lambda: self.calls.append(("resume",))
        maps_mod.map_apply_defaults = lambda m: self.calls.append(("defaults", m))
        maps_mod.map_apply_crew = lambda m: self.calls.append(("crew", m))

    def tearDown(self):
        import sbs_utils.procedural.execution as ex
        import sbs_utils.procedural.signal as sig
        import sbs_utils.procedural.cosmos as cos
        (ex.task_schedule, ex.set_shared_variable, sig.signal_emit,
         cos.sim_resume, maps_mod.map_apply_defaults,
         maps_mod.map_apply_crew) = self._orig

    def test_none_is_a_no_op(self):
        self.assertIsNone(map_start(None))
        self.assertEqual(self.calls, [])

    def test_performs_the_core_sequence_in_order(self):
        m = FakeMap("alpha")
        self.assertIs(map_start(m), m)
        kinds = [c[0] for c in self.calls]
        # `crew` sits with `defaults` and BEFORE the map is scheduled: what the crew
        # flies has to be settled before the map body can look at it.
        self.assertEqual(kinds, ["defaults", "crew", "resume", "schedule", "shared", "signal"])

    def test_schedules_deferred_so_consoles_repaint_first(self):
        map_start(FakeMap("alpha"))
        sched = next(c for c in self.calls if c[0] == "schedule")
        self.assertTrue(sched[2].get("defer"))

    def test_announces_game_started(self):
        map_start(FakeMap("alpha"))
        self.assertIn(("shared", "GAME_STARTED", True), self.calls)
        self.assertIn(("signal", "game_started"), self.calls)

    def test_does_not_emit_legendarymissions_signals(self):
        """reconcile_player_roster is LM's own contract - a bare mission has no route
        for it, and the library must not invent one."""
        map_start(FakeMap("alpha"))
        self.assertNotIn(("signal", "reconcile_player_roster"), self.calls)


if __name__ == "__main__":
    unittest.main()
