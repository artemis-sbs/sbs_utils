"""An add-on can declare ships the ENGINE knows, with no build step.

The rule this rests on was measured, not assumed: the engine reads a mission's
`extraShipData.json` **inside `create_new_sim()`**. Confirmed on engine 1.3.4 with a file
that did not exist when Cosmos launched - a script wrote it, called `sim_create()`, and the
engine knew the ship. So the condition is "the file exists before sim_create()", which a
script can satisfy, and `sbs mod merge` is unnecessary.

The flush lives INSIDE `sim_create()` rather than behind a signal emitted just before it. A
signal route is synchronous only while nothing in it awaits, and an add-on's route is
someone else's code: one `await` would put the write after the sim was created, silently,
on that mod's machine only.

Most of these tests are about what it refuses to do. Writing a file into someone's mission
folder is the kind of thing that has to be conservative.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import json
import os
import shutil
import tempfile
import unittest

# Settle the import order before anything reaches procedural.comms (see test_grid_mod_api).
import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural import ship_data_mod as sdm
from sbs_utils.procedural.ship_data import SHIP_DATA_MOD_KEY


_MOD_A = """
{"#ship-list": [{"key": "mod_a_ship", "name": "Mod A", "side": "TSN",
                 "artfileroot": "tsn_light_cruiser", "shields": [111, 111]}]}
"""

_MOD_B = """
{"#ship-list": [{"key": "mod_b_ship", "name": "Mod B", "side": "TSN",
                 "artfileroot": "tsn_light_cruiser", "shields": [222, 222]}]}
"""



def setUpModule():
    """Skipped while the extra-ship-data hot fix is in force.

    HOT FIX 2026-08-27: `ship_data.EXTRA_SHIP_DATA_DISABLED` switches the whole
    feature off, and everything below describes that feature - so these would report
    the fix as a fault. Skipped rather than deleted or marked expected-failure: they
    are the contract the feature has to satisfy again, and they come back on their own
    the moment the flag is cleared, with no edit here.
    """
    from sbs_utils.procedural.ship_data import EXTRA_SHIP_DATA_DISABLED
    if EXTRA_SHIP_DATA_DISABLED:
        raise unittest.SkipTest(
            "extra ship data is off (ship_data.EXTRA_SHIP_DATA_DISABLED)")

class _Tmp(unittest.TestCase):
    def setUp(self):
        sdm.ship_data_mod_reset()
        self.dir = tempfile.mkdtemp(prefix="shipdatamod_")
        self.path = os.path.join(self.dir, sdm.EXTRA_SHIP_DATA)

    def tearDown(self):
        sdm.ship_data_mod_reset()
        shutil.rmtree(self.dir, ignore_errors=True)

    def _read(self):
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _keys(self):
        return [e["key"] for e in self._read()["#ship-list"]]


class TestDeclaring(_Tmp):
    def test_an_addon_declares_ships(self):
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        self.assertEqual(sdm.ship_data_pending_count(), 1)
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(self._keys(), ["mod_a_ship"])

    def test_several_addons_accumulate(self):
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_merge_mod(_MOD_B, "ModB")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(sorted(self._keys()), ["mod_a_ship", "mod_b_ship"])

    def test_entries_are_stamped_with_their_mod(self):
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(self._read()["#ship-list"][0][SHIP_DATA_MOD_KEY], "ModA")

    def test_the_library_sees_them_immediately(self):
        """Without waiting for a sim - queries and the *_keys helpers should work at once."""
        from sbs_utils.procedural.ship_data import get_ship_data_for
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        self.assertIsNotNone(get_ship_data_for("mod_a_ship"))

    def test_a_mod_file_with_comments_is_accepted(self):
        """The shipped extraShipData example opens with // lines and every hand-written one
        copies it, so a mod's file almost certainly has them.

        Found by running the mission, not by writing this test: YAML read the comment's
        colon as a mapping, the parse failed, and ship_data_merge_mod returned None without
        complaining. The declaration just vanished.
        """
        commented = ("// what this mod ships: two ships\n"
                     "// second line\n" + _MOD_A)
        self.assertEqual(sdm.ship_data_merge_mod(commented, "ModA"), 1)
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(self._keys(), ["mod_a_ship"])

    def test_junk_is_ignored_not_fatal(self):
        for bad in (None, "", "[]", "{}", '{"#ship-list": "nope"}', "not: [valid"):
            self.assertIsNone(sdm.ship_data_merge_mod(bad, "Bad"))
        self.assertEqual(sdm.ship_data_pending_count(), 0)

    def test_a_collision_between_two_mods_is_reported(self):
        from sbs_utils.procedural import execution
        said, real = [], execution.log
        execution.log = lambda m, *a, **k: said.append(m)
        try:
            sdm.ship_data_merge_mod(_MOD_A, "ModA")
            sdm.ship_data_merge_mod(_MOD_A, "ModB")
        finally:
            execution.log = real
        self.assertTrue(any("collision" in m and "ModA" in m and "ModB" in m for m in said),
                        said)


class TestRefusals(_Tmp):
    """What it will NOT do. Writing into someone's mission folder has to be conservative."""

    def test_nothing_pending_writes_nothing(self):
        """A mission that never asked for this must not find its folder written to."""
        self.assertIsNone(sdm.ship_data_flush_mod_file(self.dir))
        self.assertFalse(os.path.exists(self.path))

    def test_hand_authored_entries_are_preserved(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"#ship-list": [{"key": "mine", "name": "Hand written"}]}, f)
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(sorted(self._keys()), ["mine", "mod_a_ship"])

    def test_a_hand_authored_key_wins_over_a_mod(self):
        """Someone wrote that by hand, on purpose."""
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"#ship-list": [{"key": "mod_a_ship", "name": "MINE"}]}, f)
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)
        entries = self._read()["#ship-list"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["name"], "MINE")

    def test_reflushing_does_not_mistake_our_own_output_for_the_missions(self):
        """A generated entry must still read back as generated on the next run.

        The key-based merge means the list cannot grow either way, so a length check proves
        nothing here. What it would cost is subtler: an entry read back as hand-authored
        would take over its own key, so the mission would warn about a collision with
        itself every run and the mod could never update its own ship. Assert the marking
        survives and nothing is reported.
        """
        from sbs_utils.procedural import execution
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)

        said, real = [], execution.log
        execution.log = lambda m, *a, **k: said.append(m)
        try:
            sdm.ship_data_flush_mod_file(self.dir)
            sdm.ship_data_flush_mod_file(self.dir)
        finally:
            execution.log = real

        self.assertEqual(self._keys(), ["mod_a_ship"])
        self.assertEqual(self._read()["#ship-list"][0].get(SHIP_DATA_MOD_KEY), "ModA",
                         "the entry stopped being recognizable as generated")
        self.assertEqual(said, [], "re-flushing reported a collision with its own output")

    def test_a_removed_mod_disappears(self):
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_merge_mod(_MOD_B, "ModB")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(len(self._keys()), 2)
        sdm.ship_data_mod_reset()
        sdm.ship_data_merge_mod(_MOD_A, "ModA")      # ModB no longer enabled
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(self._keys(), ["mod_a_ship"])

    def test_an_unparseable_file_is_left_alone(self):
        """Better to contribute nothing than to clobber something we cannot read."""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{ this is not json at all ")
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        self.assertIsNone(sdm.ship_data_flush_mod_file(self.dir))
        with open(self.path, encoding="utf-8") as f:
            self.assertIn("not json", f.read())

    def test_a_commented_hjson_file_is_still_read(self):
        """The shipped example is HJSON and opens with // lines."""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('// a comment\n{"#ship-list": [{"key": "mine"}]}\n')
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertEqual(sorted(self._keys()), ["mine", "mod_a_ship"])

    def test_the_previous_file_is_recoverable(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"#ship-list": [{"key": "mine"}]}, f)
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertTrue(os.path.exists(self.path + ".bak"))

    def test_no_temp_file_is_left_behind(self):
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        sdm.ship_data_flush_mod_file(self.dir)
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_it_never_touches_the_base_ship_data(self):
        import inspect
        src = inspect.getsource(sdm)
        self.assertNotIn("shipData.yaml", src.replace("data/shipData.yaml", ""))


class TestOrdering(_Tmp):
    def test_sim_create_flushes_first(self):
        """The whole design: the file must exist BEFORE create_new_sim(), because that is
        when the engine reads it. Asserted by recording the order."""
        import sbs_utils.procedural.cosmos as cosmos
        from sbs_utils.helpers import FrameContext

        order = []

        class _FakeSbs:
            def create_new_sim(self):
                order.append("create_new_sim")

        class _Ctx:
            sbs = _FakeSbs()

        real_flush = sdm.ship_data_flush_mod_file
        sdm.ship_data_flush_mod_file = lambda *a, **k: order.append("flush")
        saved = FrameContext.context
        FrameContext.context = _Ctx()
        try:
            cosmos.sim_create()
        finally:
            FrameContext.context = saved
            sdm.ship_data_flush_mod_file = real_flush

        self.assertEqual(order, ["flush", "create_new_sim"],
                         "the ship data must be written before the sim is created")

    def test_a_second_sim_create_does_not_rewrite_the_file(self):
        """LM's server console can create a sim more than once in a session (map restart).

        The entries have not changed, so the second pass must leave the file's mtime alone
        rather than rewriting identical content - a mission folder that churns on every map
        change is the kind of thing that shows up as a dirty working tree.
        """
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        self.assertIsNotNone(sdm.ship_data_flush_mod_file(self.dir))
        first = os.stat(self.path).st_mtime_ns
        self.assertIsNone(sdm.ship_data_flush_mod_file(self.dir),
                          "the second flush rewrote an unchanged file")
        self.assertEqual(os.stat(self.path).st_mtime_ns, first)

    def test_reset_drops_pending_entries(self):
        sdm.ship_data_merge_mod(_MOD_A, "ModA")
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        self.assertEqual(sdm.ship_data_pending_count(), 0)

    def test_registered_in_the_reset_ledger(self):
        from sbs_utils.handlerhooks import _RESET_PROBES
        self.assertIn("ship_data_mod", _RESET_PROBES)

    def test_mast_can_call_it(self):
        """An add-on that cannot call ship_data_merge_mod cannot declare a ship."""
        import sys
        import cosmos_dev.mock.sbs as mock
        sys.modules.setdefault("sbs", mock)
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals
        for name in ("ship_data_merge_mod", "ship_data_flush_mod_file"):
            self.assertIn(name, MastGlobals.globals,
                          f"{name} is not callable from MAST - add its module to the "
                          "import list in mast_sbs/mast_sbs_procedural.py")


if __name__ == "__main__":
    unittest.main()
