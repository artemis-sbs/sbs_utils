"""State providers: a library module's per-mission state, kept by a mission that saves.

`persist_provider_register(name, snapshot_fn, restore_fn)` is the hook. The module that
OWNS a piece of state says how to write it down and how to take it back; a mission that
saves asks for all of it in one call (`persist_providers_snapshot`) and hands all of it
back in one call (`persist_providers_restore`). What this file pins:

* a blob goes out and comes back to the provider that wrote it, and to nobody else;
* a blob under a name nobody claims is KEPT - an addon that is not loaded tonight does
  not lose its state - and is handed to a provider that registers late;
* a provider that raises does not take its saved state down with it;
* every provider is told on a restore, so "nothing was saved" replaces what was there;
* the per-mission reset keeps the library's own providers and drops a mission's, and
  leaves nothing on the reset ledger.

    python -m unittest tests.test_persist_providers
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.procedural import persistence as P

LIBRARY = ["boarding_facts", "boarding_hostiles", "boarding_props", "relics"]


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.addCleanup(reset_mission_state)
        self.held = {}

    def provider(self, name="probe"):
        """A provider that keeps one dict, registered the way a mission would."""
        held = self.held.setdefault(name, {})

        def snapshot():
            return dict(held)

        def restore(blob):
            held.clear()
            held.update(blob or {})

        P.persist_provider_register(name, snapshot, restore)
        return held


class TheHook(_Base):
    def test_the_librarys_own_providers_are_registered_by_importing_it(self):
        import sbs_utils.handlerhooks  # noqa: F401 - what a mission has loaded anyway
        self.assertEqual(P.persist_provider_names(), LIBRARY)

    def test_a_blob_goes_out_and_comes_back(self):
        held = self.provider()
        held["doors"] = ["a", "b"]
        saved = P.persist_providers_snapshot()
        self.assertEqual(saved, {"probe": {"doors": ["a", "b"]}})
        held.clear()
        self.assertEqual(P.persist_providers_restore(saved), LIBRARY[:3] + ["probe", "relics"])
        self.assertEqual(held, {"doors": ["a", "b"]})

    def test_a_provider_with_nothing_to_keep_is_left_out(self):
        self.provider()
        self.assertEqual(P.persist_providers_snapshot(), {})

    def test_restore_tells_every_provider_so_nothing_is_left_over(self):
        held = self.provider()
        held["doors"] = ["a"]
        # A new game: the save holds nothing under this name.
        P.persist_providers_restore({})
        self.assertEqual(held, {}, "nothing saved means nothing kept")
        held["doors"] = ["a"]
        P.persist_providers_restore(None)
        self.assertEqual(held, {})

    def test_a_blob_nobody_claims_is_kept_verbatim(self):
        blob = {"not_loaded_tonight": {"anything": [1, 2, {"deep": True}]}}
        P.persist_providers_restore(blob)
        self.assertEqual(P.persist_providers_snapshot(), blob)
        # ...through any number of saves.
        self.assertEqual(P.persist_providers_snapshot(), blob)

    def test_a_provider_that_registers_late_is_handed_its_blob(self):
        P.persist_providers_restore({"probe": {"doors": ["a"]}})
        held = self.provider()
        self.assertEqual(held, {"doors": ["a"]})
        held["doors"] = ["a", "b"]
        self.assertEqual(P.persist_providers_snapshot(), {"probe": {"doors": ["a", "b"]}})

    def test_a_snapshot_that_raises_keeps_what_was_restored(self):
        def boom():
            raise RuntimeError("the module is broken tonight")

        P.persist_provider_register("probe", boom, lambda blob: None)
        P.persist_providers_restore({"probe": {"doors": ["a"]}})
        self.assertEqual(P.persist_providers_snapshot(), {"probe": {"doors": ["a"]}})

    def test_a_restore_that_raises_does_not_stop_the_others(self):
        def boom(blob):
            raise RuntimeError("cannot take it back")

        P.persist_provider_register("a_broken", lambda: None, boom)
        held = self.provider("z_fine")
        done = P.persist_providers_restore({"z_fine": {"k": 1}, "a_broken": {"x": 1}})
        self.assertEqual(held, {"k": 1})
        self.assertNotIn("a_broken", done)

    def test_touch_is_a_flag_the_saver_polls(self):
        self.assertFalse(P.persist_providers_dirty())
        P.persist_provider_touch("probe")
        self.assertTrue(P.persist_providers_dirty())
        P.persist_providers_snapshot()
        self.assertFalse(P.persist_providers_dirty(), "written down: clean again")
        P.persist_provider_touch()
        P.persist_providers_restore({})
        self.assertFalse(P.persist_providers_dirty())


class TheReset(_Base):
    def test_a_missions_provider_is_dropped_and_the_librarys_are_kept(self):
        self.provider()
        self.assertIn("probe", P.persist_provider_names())
        reset_mission_state()
        self.assertEqual(P.persist_provider_names(), LIBRARY)

    def test_nothing_is_left_on_the_reset_ledger(self):
        held = self.provider()
        held["doors"] = ["a"]
        P.persist_providers_restore({"probe": {"doors": ["a"]}, "stranger": {"k": 1}})
        P.persist_provider_touch()
        self.assertGreater(P.persist_providers_count(), 0)
        reset_mission_state()
        self.assertEqual(P.persist_providers_count(), 0)
        self.assertEqual(reset_mission_audit(), {})

    def test_a_mission_that_never_saves_leaves_nothing_registered(self):
        """Loading the library registers its four providers and nothing else; a mission
        that never calls snapshot or restore is not on the ledger for it."""
        self.assertEqual(P.persist_providers_count(), 0)
        self.assertEqual(reset_mission_audit(), {})

    def test_mast_can_call_the_hook(self):
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        for name in ("persist_provider_register", "persist_providers_snapshot",
                     "persist_providers_restore", "persist_providers_dirty"):
            self.assertIn(name, MastGlobals.globals, name)


if __name__ == "__main__":
    unittest.main()
