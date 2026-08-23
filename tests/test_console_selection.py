"""Regression tests for the hangar 'stale home dock / craft' bug.

Two invariants the fix relies on:

* ``set_console_selection`` (and thus set_science/grid/comms/weapons_selection)
  must store ONLY an int id - a None or a raw non-Agent object must fail safe to
  0, never poison the selection blob.
* A selection held by ID and re-resolved with ``to_space_object`` notices when
  the object is destroyed (returns None), whereas the old pattern of holding the
  Agent object never does - ``to_object`` on an Agent is a no-op, so a destroyed
  home dock / craft stayed a live-looking but dead wrapper.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.objects import Npc, PlayerShip
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.procedural.query import (
    set_science_selection,
    get_science_selection,
    get_comms_selection,
    get_grid_selection,
    get_weapons_selection,
    to_blob,
    to_space_object,
    to_object,
    to_id,
    object_exists,
)
from sbs_utils.delete_queue import DeleteQueue

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs import story_nodes  # registers Cosmos MAST nodes (explicit)
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import Agent, clear_shared

MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.timers')
MastGlobals.import_python_module('sbs_utils.procedural.query')


class TestConsoleSelectionStale(unittest.TestCase):
    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.ship = PlayerShip().spawn(0, 0, 0, "Console", "tsn", "Battle Cruiser")
        self.dock = Npc().spawn(1000, 0, 0, "DS1", "tsn", "Starbase", "behav_spaceport")

    # --- set_console_selection hardening ------------------------------------
    def test_set_science_selection_stores_int_id(self):
        set_science_selection(self.ship, self.dock)
        sel = get_science_selection(self.ship)
        self.assertIsInstance(sel, int)
        self.assertEqual(sel, to_id(self.dock))

    def test_none_selection_stored_as_zero(self):
        set_science_selection(self.ship, self.dock)   # first set something real
        set_science_selection(self.ship, None)        # then clear it
        self.assertEqual(get_science_selection(self.ship), 0)

    def test_non_int_selection_coerced_to_zero(self):
        # A raw engine object (any non-Agent, non-int) must not land in the blob.
        class _RawObj:
            pass
        set_science_selection(self.ship, _RawObj())
        self.assertEqual(get_science_selection(self.ship), 0)

    # --- stale-selection resolution (the hangar refactor invariant) ---------
    def test_stale_id_resolves_to_none_but_held_object_does_not(self):
        set_science_selection(self.ship, self.dock)
        held = to_object(self.dock)          # OLD hangar pattern: keep the object
        dock_id = to_id(self.dock)

        # Home dock destroyed while the hangar screen is open.
        self.dock.py_object.destroyed()

        # A held Agent resolves to None as well now: Agent._alive makes to_object
        # validate the INSTANCE, not just the id. Until that landed this returned
        # the dead object, which is what made every `->END if to_object(x) is None`
        # guard written against a held object silently inert - and let writes land
        # on freed memory (ObjectDataBlob::Set, three engine crashes 2026-08-22/23).
        self.assertIsNone(to_object(held))
        # NEW pattern: resolve the stored id -> None, so the selection self-clears.
        self.assertIsNone(to_space_object(dock_id))
        self.assertIsNone(to_space_object(get_science_selection(self.ship)))


class TestSelectionGetterExistenceGuard(unittest.TestCase):
    """The selection getters must not read a deleted object's blob.

    The engine crash (hangar.mast:206): get_science_selection(x) -> to_blob(x) ->
    blob.get(...). When x is a SpawnData whose object has been deleted, to_blob used
    to short-circuit to the cached SpawnData.blob - a DANGLING engine data-set in the
    real engine - and blob.get(...) throws. The getters guard with object_exists().

    There are now TWO layers: to_blob itself retires the cached blob once the agent
    is tombstoned (Agent._alive), and the getters still fail safe to None. The second
    is kept because it is the contract callers rely on, and because it holds even for
    a blob obtained some other way.

    The mock cannot dangle a native pointer, so it stands in with a stale-but-
    readable cached blob. Same contract, observable headlessly.
    """
    def setUp(self):
        SpaceObject.clear()
        DeleteQueue.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.ship = PlayerShip().spawn(0, 0, 0, "Console", "tsn", "Battle Cruiser")
        self.dock = Npc().spawn(1000, 0, 0, "DS1", "tsn", "Starbase", "behav_spaceport")

    def test_getters_return_none_for_deleted_spawndata(self):
        # Give the ship real selections so a stale read would return a concrete id,
        # not a coincidental None.
        set_science_selection(self.ship, self.dock)
        self.assertEqual(get_science_selection(self.ship), to_id(self.dock))

        # Ship deleted while the hangar screen still holds its SpawnData wrapper.
        self.ship.py_object.delete_object()
        DeleteQueue.drain()

        # to_blob now refuses the wrapper's cached blob once the object is gone, so
        # the dangling read is impossible rather than merely guarded downstream.
        self.assertIsNone(to_blob(self.ship), "SpawnData blob retired on delete")
        self.assertFalse(object_exists(self.ship))

        # ...so every getter must fail safe to None instead of reading it.
        self.assertIsNone(get_science_selection(self.ship))
        self.assertIsNone(get_comms_selection(self.ship))
        self.assertIsNone(get_grid_selection(self.ship))
        self.assertIsNone(get_weapons_selection(self.ship))


class _AssertScheduler(MastScheduler):
    """Fail the test on any MAST runtime error (e.g. a deref of a stale object)."""
    def runtime_error(self, message):
        raise AssertionError(f"MAST runtime error: {message}")


class TestHangarSelectionRebuildRuntime(unittest.TestCase):
    """The show_hangar rebuild, in the REAL MAST runtime.

    show_hangar persists the selection as an ID and re-resolves it every rebuild
    (each `jump show_hangar`). This models one rebuild as re-running a resolve
    label: while the dock is alive it records 'here'; once the dock is destroyed
    between rebuilds the resolve returns None and it records 'gone' - the
    self-clear - and must NOT raise a runtime error (the _AssertScheduler turns
    any MAST runtime error into a test failure).

    (The mock cannot reproduce the *engine crash* the old held-object pattern
    caused - a stale Python wrapper's attributes still work in-process - so that
    asymmetry is pinned separately by TestConsoleSelectionStale. This test proves
    the id-resolve rebuild behaves in the actual scheduler.)
    """

    STORY = """
== resolve_once ==
    obj = to_space_object(sel_id)
    if obj is None:
        shared last = "gone"
    else:
        shared last = "here"
    ->END
"""

    def setUp(self):
        SpaceObject.clear()
        clear_shared()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.dock = Npc().spawn(1000, 0, 0, "DS1", "tsn", "Starbase", "behav_spaceport")

    def _resolve_frame(self, runner, sel_id):
        """One show_hangar-style rebuild: (re)run the resolve label to ->END."""
        runner.start_task("resolve_once", {"sel_id": sel_id})
        for _ in range(5):
            runner.tick()
        return Agent.SHARED.get_inventory_value("last")

    def test_rebuild_resolves_id_and_self_clears_on_destroy(self):
        mast = Mast()
        errors = mast.compile(self.STORY, "sel_rt_test", mast)
        self.assertEqual(errors, [])
        FrameContext.mast = mast
        runner = _AssertScheduler(mast)
        dock_id = to_id(self.dock)

        # Rebuild 1: dock alive -> resolves the id -> 'here'.
        self.assertEqual(self._resolve_frame(runner, dock_id), "here")

        # Rebuild 2: dock destroyed between rebuilds -> resolves None -> 'gone',
        # without raising.
        self.dock.py_object.destroyed()
        self.assertEqual(self._resolve_frame(runner, dock_id), "gone")


if __name__ == "__main__":
    unittest.main()
