"""Shared unit-test reset.

One definition of "fresh per-mission state" for mock-based tests, built on the same
runtime entry point the dev runner uses (handlerhooks.reset_mission_state) so tests
can't drift from real reset semantics. Replaces the copy-pasted setUp boilerplate:

    Agent.clear(); clear_shared(); sbs.create_new_sim()
    FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
"""
from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.helpers import FrameContext, Context, FakeEvent


def reset_mock(sbs):
    """Reset every per-mission runtime registry (dispatchers + Agent + shared via
    reset_mission_state), start a fresh mock sim, and point FrameContext at it.

    `sbs` is the mock module (``cosmos_dev.mock.sbs`` or ``cosmos_dev.mockgui.sbs``).
    Returns the new sim. Call it as the first line of a mock test's setUp."""
    reset_mission_state()
    sbs.create_new_sim()
    FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
    return sbs.sim
