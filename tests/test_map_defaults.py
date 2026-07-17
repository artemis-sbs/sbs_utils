"""map_apply_defaults - a map's `Defaults:` metadata seeds its Properties vars as SET-IF-ABSENT
shared variables (so a map-local property var like JOBS_SELECT has a starting value without
being promoted to global settings or defaulted in the map body).

Run: python -m unittest tests.test_map_defaults
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.maps import map_get_defaults, map_apply_defaults
from sbs_utils.procedural.execution import get_shared_variable, set_shared_variable


class FakeMapLabel:
    """Stand-in for a @map Label: metadata keys live in its inventory."""
    def __init__(self, inv):
        self._inv = inv

    def get_inventory_value(self, key, default=None):
        return self._inv.get(key, default)


class MapDefaultsTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def test_get_defaults_reads_metadata_key(self):
        m = FakeMapLabel({"Defaults": {"JOBS_SELECT": "some"}})
        self.assertEqual(map_get_defaults(m), {"JOBS_SELECT": "some"})
        # lowercase fallback
        m2 = FakeMapLabel({"defaults": {"X": 1}})
        self.assertEqual(map_get_defaults(m2), {"X": 1})
        # none declared
        self.assertIsNone(map_get_defaults(FakeMapLabel({})))

    def test_sets_absent_var(self):
        map_apply_defaults(FakeMapLabel({"Defaults": {"JOBS_SELECT": "some"}}))
        self.assertEqual(get_shared_variable("JOBS_SELECT"), "some")

    def test_does_not_override_existing_var(self):
        set_shared_variable("DIFFICULTY", 5)   # already seeded (e.g. by settings.yaml)
        map_apply_defaults(FakeMapLabel({"Defaults": {"DIFFICULTY": 9}}))
        self.assertEqual(get_shared_variable("DIFFICULTY"), 5)   # settings win

    def test_falsy_existing_value_is_still_present(self):
        # a var deliberately set to 0 / "" is "present" and must not be re-defaulted
        set_shared_variable("MODE", 0)
        map_apply_defaults(FakeMapLabel({"Defaults": {"MODE": 3}}))
        self.assertEqual(get_shared_variable("MODE"), 0)

    def test_idempotent_and_multi_var(self):
        m = FakeMapLabel({"Defaults": {"A": "x", "B": 2}})
        map_apply_defaults(m)
        set_shared_variable("A", "changed")   # simulate an operator edit on the panel
        map_apply_defaults(m)                  # second pass (map-task start) must not clobber
        self.assertEqual(get_shared_variable("A"), "changed")
        self.assertEqual(get_shared_variable("B"), 2)

    def test_none_and_no_defaults_are_safe(self):
        map_apply_defaults(None)                 # no crash
        map_apply_defaults(FakeMapLabel({}))     # no Defaults -> no-op
        map_apply_defaults(FakeMapLabel({"Defaults": "not a dict"}))  # ignored, no crash


if __name__ == "__main__":
    unittest.main()
