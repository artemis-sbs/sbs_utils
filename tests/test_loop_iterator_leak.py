"""A loop's iterator must not outlive the loop, or be inherited by another task.

`LoopStart` keeps its iterator in task scope and decides "am I already running?" by
whether that latch is set. Two things broke on that:

  * The latch was keyed by the loop VARIABLE (`p__iter`), and `task_schedule` copies the
    caller's scope by default - so a child running `for p in players:` found the parent's
    `p__iter`, concluded it was mid-loop, and kept pulling from the PARENT's iterator.
  * Nothing clears the latch when a loop is left early. `jump` out of the body never
    reaches `LoopEnd`, so an abandoned iterator stayed in scope indefinitely.

Together they are how LegendaryMissions' server console leaked game-code presets into a
map label: the console leaves `for p in presets:` via `jump game_code_reload`, and
`default_player_friendly_eyes` then ran `for p in players:` against the console's preset
iterator. The engine log showed `p` holding a preset dict while `o`, iterating the very
same `players` one line above, held a correct agent id - the asymmetry that identified it.

Silent when the types happen to be compatible, so these tests pin the mechanism rather
than the crash it produced.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # registers Cosmos MAST nodes (explicit)
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.helpers import FrameContext, Context, FakeEvent

MastGlobals.import_python_module('sbs_utils.procedural.execution')

from cosmos_dev.mock import sbs

NEWLINE = chr(10)


class _TScheduler(MastScheduler):
    def runtime_error(self, message):
        raise AssertionError(f"RUNTIME ERROR: {message}")


class _FakeSim:
    def __init__(self):
        self.time_tick_counter = 0

    def tick(self):
        self.time_tick_counter += 30


def _run(lines, start, wants):
    """Compile, run every task to completion, and return the first `wants` value seen."""
    mast = Mast()
    clear_shared()
    Agent.clear()
    errors = mast.compile(NEWLINE.join(lines), "loop_leak_test", mast)
    assert errors == [], errors
    FrameContext.context = Context(_FakeSim(), sbs, FakeEvent())
    FrameContext.mast = mast
    runner = _TScheduler(mast)
    root = runner.start_task(start)
    for _ in range(200):
        if root.done:
            break
        root.tick()
    for task in list(runner.tasks):
        for _ in range(200):
            if task.done:
                break
            task.tick()
    for task in runner.tasks:
        got = task.get_symbols().get(wants)
        if got is not None:
            return got
    return None


class TestLoopIteratorLeak(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()

    def tearDown(self):
        clear_shared()
        Agent.clear()

    def test_a_scheduled_task_does_not_inherit_a_loop_in_progress(self):
        """The reported bug, in miniature: same loop variable, two tasks."""
        seen = _run([
            "== leak_parent ==",
            "    stuff = [{'name': 'TwoShips'}, {'name': 'ThreeShips'}]",
            "    for p in stuff:",
            "        jump leak_after",       # leaves the loop mid-iteration
            "== leak_after ==",
            "    task_schedule(leak_child)",
            "    ->END",
            "",
            "== leak_child ==",
            "    seen = []",
            "    for p in [11, 22]:",
            "        seen = seen + [p]",
            "    ->END",
        ], "leak_parent", "seen")
        self.assertEqual(seen, [11, 22],
                         "child iterated the parent's abandoned iterator")

    def test_re_entering_a_label_restarts_its_loop(self):
        """Same task, same loop: jumping out and coming back must start over, not resume."""
        # Both jump targets are inline labels of the SAME top-level label - an inline
        # name only resolves inside its parent's scope.
        seen = _run([
            "== reenter_start ==",
            "    passes = 0",
            "    seen = []",
            "---again",
            "    for x in [1, 2, 3]:",
            "        seen = seen + [x]",
            "        jump left_early",
            "---left_early",
            "    passes = passes + 1",
            "    jump again if passes < 2",
            "    ->END",
        ], "reenter_start", "seen")
        # Two visits, each taking the FIRST element and leaving.
        self.assertEqual(seen, [1, 1])

    def test_an_ordinary_loop_still_iterates(self):
        seen = _run([
            "== plain_loop ==",
            "    seen = []",
            "    for x in [1, 2, 3]:",
            "        seen = seen + [x]",
            "    ->END",
        ], "plain_loop", "seen")
        self.assertEqual(seen, [1, 2, 3])

    def test_nested_loops_still_iterate(self):
        """`for p` / `for o` over the same list - the shape the LM label uses."""
        seen = _run([
            "== nested_loop ==",
            "    seen = []",
            "    for a in [1, 2]:",
            "        for b in [10, 20]:",
            "            seen = seen + [a * b]",
            "    ->END",
        ], "nested_loop", "seen")
        self.assertEqual(seen, [10, 20, 20, 40])

    def test_continue_still_advances(self):
        """`continue` returns to LoopStart without passing LoopEnd, so it owes the same
        continuation token - without it the loop restarts forever."""
        seen = _run([
            "== cont_loop ==",
            "    seen = []",
            "    for x in [1, 2, 3, 4]:",
            "        continue if x == 2",
            "        seen = seen + [x]",
            "    ->END",
        ], "cont_loop", "seen")
        self.assertEqual(seen, [1, 3, 4])

    def test_break_still_stops(self):
        seen = _run([
            "== break_loop ==",
            "    seen = []",
            "    for x in [1, 2, 3, 4]:",
            "        break if x == 3",
            "        seen = seen + [x]",
            "    ->END",
        ], "break_loop", "seen")
        self.assertEqual(seen, [1, 2])

    def test_two_loops_sharing_a_variable_name_do_not_collide(self):
        """Site-keyed latches: the second loop is its own loop, not a resumption."""
        seen = _run([
            "== twice_loop ==",
            "    seen = []",
            "    for i in [1, 2]:",
            "        seen = seen + [i]",
            "    for i in [7, 8]:",
            "        seen = seen + [i]",
            "    ->END",
        ], "twice_loop", "seen")
        self.assertEqual(seen, [1, 2, 7, 8])


if __name__ == "__main__":
    unittest.main()
