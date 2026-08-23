"""A loop inside an inline block must not eat the block's injected data.

An inline block is how a widget handler runs - `on gui_message(w):`, a comms
button, an event route - and the `data=` a widget was built with lives on the
`label_stack` entry that pushed the block.

`for`/`while` implement iteration by moving the instruction pointer inside one
label, and they used to do it through `jump()`, which unwinds `pop_on_jump` "to
get back to the main flow". So the first loop in a handler POPPED the handler's
own frame, and every injected variable vanished from that point on:

    fab_btn = gui_button("Build", data={"rk": key, "rnames": names})
    on gui_message(fab_btn):
        for n in rnames:           # reads fine - then eats the block
            ...
        signal_emit("build", {"recipe": rk})    # NameError: name 'rk' is not defined

Found in LegendaryMissions' Fabricator (fabrication/beacon_tabs.mast), where the
Build button could not build anything. Two things made it hard to see: an EMPTY
loop does it too, and the failure is reported against a line that has no loop on
it. The `cosmos-gui` skill recommends `data=` as the reliable escape from the
OTHER for-loop trap (a handler registered inside a loop), which walked straight
into this one.

The loops now use `jump_in_label`, which moves the pointer without unwinding.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers Cosmos nodes)
from sbs_utils.agent import clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

import sbs_utils.procedural.execution as ex  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.execution')
import sbs_utils.procedural.signal as _sig  # noqa: F401
MastGlobals.import_python_module('sbs_utils.procedural.signal')

from cosmos_dev.mock import sbs


class _CollectingScheduler(MastScheduler):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.errors = []

    def runtime_error(self, message):
        self.errors.append(message)


class _FakeSim:
    time_tick_counter = 0


DATA = {"rk": "sensor", "rb": True, "rnames": ["monster", "mode"],
        "rdefs": {"monster": "shark", "mode": "attract"}}


class TestLoopInInlineBlock(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self._saved = MastGlobals.globals.get("record")
        MastGlobals.globals["record"] = lambda *a: self.seen.append(a)
        MastGlobals.globals["noop"] = lambda *a: None

    def tearDown(self):
        if self._saved is None:
            MastGlobals.globals.pop("record", None)
        else:
            MastGlobals.globals["record"] = self._saved
        MastGlobals.globals.pop("noop", None)

    def run_handler(self, body, data=None, expect_error=None):
        """Park a task, push an inline block with data, run it to the end.

        This is what MessageTrigger.on_message does for `on gui_message(w):`.
        """
        code = ("=== start ===\n    await signal_next('never_fires')\n    ->END\n\n"
                "=== handler ===\n" + body)
        mast = Mast()
        clear_shared()
        errors = mast.compile(code, "loop_inline", mast)
        self.assertEqual(errors, [], f"did not compile: {errors}")
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
        FrameContext.mast = mast
        runner = _CollectingScheduler(mast)
        task = runner.start_task("start")
        for _ in range(3):
            runner.tick()
        task.push_inline_block("handler", 0, dict(data or DATA))
        for _ in range(40):
            runner.tick()
        if expect_error is None:
            self.assertEqual(runner.errors, [],
                             "MAST runtime error:\n" + "\n".join(runner.errors))
        else:
            self.assertTrue(any(expect_error in e for e in runner.errors),
                            f"expected {expect_error!r} in {runner.errors}")
        return self.seen

    def test_data_survives_an_empty_for(self):
        """The reported case: no items, and the data still vanished."""
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        noop(rn)\n"
            "    record(rk)\n"
            "    ->END\n",
            dict(DATA, rnames=[]))
        self.assertEqual(seen, [("sensor",)])

    def test_data_survives_a_for_that_iterates(self):
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        noop(rn)\n"
            "    record(rk)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor",)])

    def test_data_survives_a_for_nested_in_an_if(self):
        """The exact shape of the Fabricator's Build handler."""
        seen = self.run_handler(
            "    if rb:\n"
            "        prog = {}\n"
            "        for rn in rnames:\n"
            "            prog[rn] = rdefs[rn]\n"
            "        record(rk, prog)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor", {"monster": "shark",
                                            "mode": "attract"})])

    def test_data_survives_two_loops(self):
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        noop(rn)\n"
            "    for rn2 in rnames:\n"
            "        noop(rn2)\n"
            "    record(rk)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor",)])

    def test_data_survives_a_break(self):
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        break\n"
            "    record(rk)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor",)])

    def test_data_survives_a_continue(self):
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        continue\n"
            "    record(rk)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor",)])

    def test_data_survives_a_while_loop(self):
        seen = self.run_handler(
            "    n = 0\n"
            "    for x while n < 3:\n"
            "        n = n + 1\n"
            "    record(rk)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor",)])

    def test_the_data_is_readable_INSIDE_the_loop_too(self):
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        record(rk, rn)\n"
            "    ->END\n")
        self.assertEqual(seen, [("sensor", "monster"), ("sensor", "mode")])

    def test_a_real_jump_still_unwinds_the_block(self):
        """The behavior jump() is FOR must be unchanged.

        Leaving the label really does abandon the inline context, so the
        injected data must be UNDEFINED on the other side - otherwise the fix
        has merely widened the leak instead of closing it. `rk` is not None
        there, it does not exist, so reading it is the NameError this asserts.
        """
        seen = self.run_handler(
            "    for rn in rnames:\n"
            "        noop(rn)\n"
            "    jump elsewhere\n"
            "\n=== elsewhere ===\n"
            "    record(rk)\n"
            "    ->END\n",
            expect_error="name 'rk' is not defined")
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
