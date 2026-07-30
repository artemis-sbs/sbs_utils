"""The route-level `once` modifier: `//signal/<name> once`.

`//shared/signal` fixes WHERE a route runs (server, once per emit). It says nothing
about how many times the signal is EMITTED, and init signals get re-emitted for many
reasons. `once` closes that second axis declaratively for work that has no natural key
to be idempotent against; where the work does have a key, prefer `player_ensure` /
`side_ensure`, which stay correct on a DELIBERATE re-emit too.

The flag lives in Agent.SHARED, so reset_mission_state's clear_shared() re-arms every
`once` route on a mission reload; `signal_once_reset` is the explicit in-mission re-arm.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.signal import signal_once_reset

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.signal')

from cosmos_dev.mock import sbs


class _TMastScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0


class SignalOnceTests(unittest.TestCase):
    def _run(self, code, emits_label="go"):
        """Compile, tick main so the routes REGISTER, then run the emitting label.

        The registration commands are appended to main, so a story that emits from main
        before its routes are declared would emit into the void - hence the split.
        """
        mast = Mast()
        clear_shared()
        errors = mast.compile(code, "once_test", mast)
        self.assertEqual(errors, [])
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
        FrameContext.mast = mast
        runner = _TMastScheduler(mast)
        runner.start_task("main")
        self._drain(runner)
        runner.start_task(emits_label)
        self._drain(runner)
        self.runner = runner
        return runner.get_value("output", None)[0].getvalue()

    def _drain(self, runner, limit=60):
        for _ in range(limit):
            if not runner.tick():
                break

    def test_once_runs_a_single_time(self):
        out = self._run('''logger(var="output")

== go ==
    signal_emit("boot")
    signal_emit("boot")
    signal_emit("boot")
    ->END

//signal/boot once
    log("BOOT")
''')
        self.assertEqual(out, "BOOT\n")

    def test_plain_route_is_unaffected(self):
        out = self._run('''logger(var="output")

== go ==
    signal_emit("tick")
    signal_emit("tick")
    ->END

//signal/tick
    log("TICK")
''')
        self.assertEqual(out, "TICK\nTICK\n")

    def test_a_false_condition_does_not_burn_the_shot(self):
        # The `if` entry test is injected BEFORE the once test on purpose: a route that
        # did not run must keep its one shot.
        out = self._run('''logger(var="output")
shared GATE = False

== go ==
    signal_emit("gated")
    GATE = True
    signal_emit("gated")
    signal_emit("gated")
    ->END

//signal/gated once if GATE
    log("GATED")
''')
        self.assertEqual(out, "GATED\n")

    def test_signal_once_reset_rearms(self):
        out = self._run('''logger(var="output")

== go ==
    signal_emit("boot")
    signal_emit("boot")
    signal_once_reset("boot")
    signal_emit("boot")
    signal_emit("boot")
    ->END

//signal/boot once
    log("BOOT")
''')
        self.assertEqual(out, "BOOT\nBOOT\n")

    def test_reset_by_name_leaves_other_routes_armed(self):
        out = self._run('''logger(var="output")

== go ==
    signal_emit("a")
    signal_emit("b")
    signal_once_reset("a")
    signal_emit("a")
    signal_emit("b")
    ->END

//signal/a once
    log("A")

//signal/b once
    log("B")
''')
        self.assertEqual(out, "A\nB\nA\n")

    def test_two_routes_on_one_signal_each_get_a_shot(self):
        out = self._run('''logger(var="output")

== go ==
    signal_emit("boot")
    signal_emit("boot")
    ->END

//signal/boot once
    log("ONE")

//signal/boot once
    log("TWO")
''')
        self.assertEqual(sorted(out.split()), ["ONE", "TWO"])

    def test_clear_shared_rearms(self):
        # reset_mission_state calls clear_shared(), so a mission reload re-arms without
        # anyone having to remember a reset call.
        self._run('''logger(var="output")

== go ==
    signal_emit("boot")
    ->END

//signal/boot once
    log("BOOT")
''')
        clear_shared()
        self.assertEqual(signal_once_reset(), 0, "clear_shared must have dropped the flags")

    def test_route_named_once_still_compiles(self):
        # Backward compatibility: `once` needs leading whitespace to be the modifier.
        out = self._run('''logger(var="output")

== go ==
    signal_emit("once")
    signal_emit("once")
    ->END

//signal/once
    log("NAMED")
''')
        self.assertEqual(out, "NAMED\nNAMED\n")

    def test_shared_once_compiles(self):
        mast = Mast()
        clear_shared()
        errors = mast.compile('''//shared/signal/create_player_ships once
    log("X")
''', "shared_once", mast)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
