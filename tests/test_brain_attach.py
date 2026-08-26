"""Brain attachment: one root per agent, and nothing lost on the way down the tree.

These pin four defects in `brain_add` / `brain_add_parent` that are all silent - a brain
that is never registered simply never runs, and nothing logs it. They were found while
asking whether autoplay could be hosted in a brain (it can), but every one of them is a
live bug independent of that: `brain_add(role("__player__"), ...)` or any other set-valued
call hits the first one today.

Run:
    python -m unittest tests.test_brain_attach
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.procedural.brain import (
    BrainType, brain_add, brain_add_parent, brain_clear)
from sbs_utils.mast.mast_node import MastNode
from sbs_utils.procedural.inventory import get_inventory_value, has_inventory


def make_agent():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a


class _FakeLabel(MastNode):
    """Stands in for a MAST label.

    Subclasses MastNode on purpose: `brain_add_parent` dispatches on `str` or `MastNode`
    and SILENTLY DROPS anything else, so a plain stand-in object attaches nothing and the
    test would pass or fail for the wrong reason.
    """
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.labels = {}
        self.loc = 0

    def __repr__(self):
        return f"<label {self.name}>"


class BrainAttachTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)

    def _brain_of(self, agent):
        return get_inventory_value(agent.id, "__BRAIN__", None)

    # -- 1. the set bug --------------------------------------------------------
    def test_every_agent_in_a_set_gets_its_own_root(self):
        """`brain_add` over a set must attach one brain per agent.

        `parent` is a function PARAMETER and was never reset between loop iterations, so
        agent #1 created the root and agents #2..N saw `parent is not None` and had their
        nodes hung under agent #1's tree - never getting a `__BRAIN__` entry of their own.
        `has_inventory("__BRAIN__")` is the tick loop's registry, so those agents' brains
        simply never ran. Latent only because every shipped call passes a single id.
        """
        a, b, c = make_agent(), make_agent(), make_agent()
        lbl = _FakeLabel("patrol")
        brain_add({a.id, b.id, c.id}, {"label": lbl})

        registry = set(has_inventory("__BRAIN__"))
        for agent in (a, b, c):
            self.assertIn(agent.id, registry,
                          f"agent {agent.id} never entered the brain registry")
            root = self._brain_of(agent)
            self.assertIsNotNone(root)
            self.assertEqual(root.agent, agent.id,
                             "the root must belong to the agent it was attached to")
            self.assertEqual(len(root.children), 1,
                             "each agent should get exactly its own one child")

    def test_a_set_does_not_pile_children_onto_the_first_agent(self):
        """The other half of the same bug, stated from the victim's side."""
        a, b, c = make_agent(), make_agent(), make_agent()
        brain_add([a.id, b.id, c.id], {"label": _FakeLabel("patrol")})
        self.assertEqual(len(self._brain_of(a).children), 1,
                         "agent #1 must not collect the other agents' nodes")

    def test_a_second_call_extends_the_same_root(self):
        """Adding twice appends siblings; it must not build a second root."""
        a = make_agent()
        brain_add(a.id, {"label": _FakeLabel("one")})
        first_root = self._brain_of(a)
        brain_add(a.id, {"label": _FakeLabel("two")})
        self.assertIs(self._brain_of(a), first_root)
        self.assertEqual(len(first_root.children), 2)

    # -- 2. the list branch ----------------------------------------------------
    def test_a_bare_list_keeps_client_id_and_data(self):
        """`brain_add_parent`'s list branch dropped BOTH, silently.

        It recursed as `brain_add_parent(parent, agent, l, None)` - no data, no client_id -
        so every child of a bare list fell back to `client_id=0` and lost its data dict.
        `client_id` decides which console's GUI task the leaf runs on, so this quietly
        moved work to the server.
        """
        a = make_agent()
        brain_add(a.id, [_FakeLabel("x"), _FakeLabel("y")], data={"k": 1}, client_id=7)
        root = self._brain_of(a)
        self.assertEqual(len(root.children), 2)
        for child in root.children:
            self.assertEqual(child.client_id, 7, "client_id was dropped by the list branch")
            self.assertEqual(child.data, {"k": 1}, "data was dropped by the list branch")

    def test_a_child_dict_without_data_inherits_it(self):
        """{"label": x} says nothing about data, so it should get what the caller passed.

        The dict branch read `label.get("data")` unconditionally, nulling the inherited
        value - so a bare label and a `{"label": ...}` dict in the SAME list ended up with
        different data for no stated reason.
        """
        a = make_agent()
        brain_add(a.id, [{"label": _FakeLabel("x")}], data={"k": 1})
        self.assertEqual(self._brain_of(a).children[0].data, {"k": 1})

    def test_an_explicit_child_data_still_wins(self):
        a = make_agent()
        brain_add(a.id, [{"label": _FakeLabel("x"), "data": {"mine": 2}}], data={"k": 1})
        self.assertEqual(self._brain_of(a).children[0].data, {"mine": 2})

    def test_root_carries_the_client_id_it_was_created_with(self):
        a = make_agent()
        brain_add(a.id, {"label": _FakeLabel("x")}, client_id=3)
        self.assertEqual(self._brain_of(a).client_id, 3)

    # -- 3. a Sequence root ----------------------------------------------------
    def test_a_sequence_root_can_be_asked_for(self):
        """A Select root runs children until the FIRST success, so siblings starve.

        That is right for a priority list of behaviours and wrong for a set of independent
        per-console jobs, where every node should run each pass. LM works around it today
        with `elite_brain_attach`, whose comment says exactly this. Without a way to ask
        for a Sequence root there is no way to express "run all of these".
        """
        a = make_agent()
        brain_add(a.id, {"label": _FakeLabel("x")}, root_type=BrainType.Sequence)
        root = self._brain_of(a)
        self.assertEqual(root.brain_type, BrainType.Sequence)

    def test_the_root_is_still_a_select_by_default(self):
        """Backwards compatibility: every existing caller must keep the Select root."""
        a = make_agent()
        brain_add(a.id, {"label": _FakeLabel("x")})
        self.assertEqual(self._brain_of(a).brain_type, BrainType.Select)

    def test_root_type_is_ignored_once_a_root_exists(self):
        """A later call must not silently re-type an agent's existing tree."""
        a = make_agent()
        brain_add(a.id, {"label": _FakeLabel("x")})
        brain_add(a.id, {"label": _FakeLabel("y")}, root_type=BrainType.Sequence)
        self.assertEqual(self._brain_of(a).brain_type, BrainType.Select)

    # -- 4. the leaf-task leak -------------------------------------------------
    def test_a_leaf_that_does_not_finish_is_ended(self):
        """An unfinished leaf must be ended, or it is ticked forever AND re-created.

        `yield success`/`yield fail` resolve to BT_SUCCESS/BT_FAIL, which mark the task
        done. Anything else - an `await` (OK_RUN_AGAIN) or `yield idle` (OK_IDLE) - left a
        live task on the scheduler while the brain started a fresh one next pass: one
        immortal task per pass, forever, with the leaf appearing to do nothing because a
        non-success also makes a Select fall through.
        """
        from sbs_utils.mast.pollresults import PollResults
        from sbs_utils.procedural.brain import Brain

        ended = []

        class _Task:
            tick_result = PollResults.OK_RUN_AGAIN
            def jump(self, *a, **k): pass
            def set_variable(self, *a, **k): pass
            def tick_in_context(self): pass
            def end(self): ended.append(True)

        class _Host:
            def start_task(self, *a, **k): return _Task()

        a = make_agent()
        brain = Brain(a.id, _FakeLabel("leaky"), None, 0)
        Brain._warned_leaf.clear()
        import sbs_utils.procedural.brain as B
        real = B.get_inventory_value
        B.get_inventory_value = lambda *a, **k: _Host()
        try:
            res = brain.run_sub_label(0)
        finally:
            B.get_inventory_value = real
        self.assertEqual(res, PollResults.OK_RUN_AGAIN, "the result must still be reported")
        self.assertEqual(ended, [True], "the unfinished leaf was not ended")

    def test_a_leaf_that_finishes_is_left_alone(self):
        """success/fail already dispose themselves; ending them again would be wrong."""
        from sbs_utils.mast.pollresults import PollResults
        from sbs_utils.procedural.brain import Brain

        ended = []

        class _Task:
            tick_result = PollResults.BT_SUCCESS
            def jump(self, *a, **k): pass
            def set_variable(self, *a, **k): pass
            def tick_in_context(self): pass
            def end(self): ended.append(True)

        class _Host:
            def start_task(self, *a, **k): return _Task()

        a = make_agent()
        brain = Brain(a.id, _FakeLabel("clean"), None, 0)
        import sbs_utils.procedural.brain as B
        real = B.get_inventory_value
        B.get_inventory_value = lambda *a, **k: _Host()
        try:
            brain.run_sub_label(0)
        finally:
            B.get_inventory_value = real
        self.assertEqual(ended, [], "a completed leaf must not be ended again")

    # -- housekeeping ----------------------------------------------------------
    def test_brain_clear_removes_the_agent_from_the_registry(self):
        a = make_agent()
        brain_add(a.id, {"label": _FakeLabel("x")})
        self.assertIn(a.id, set(has_inventory("__BRAIN__")))
        brain_clear(a.id)
        self.assertIsNone(self._brain_of(a))


if __name__ == "__main__":
    unittest.main()
