"""`science_update_scan_data` survives a never-scanned target, and writes a readable list.

WHY THIS EXISTS. The function's own docstring offers it as the way to "inject scan data
without requiring the player to scan first" - and that is precisely the case it could not
survive:

    tab_list = so.data_set.get("scan_type_list", 0)
    if tab_list != 0:
        if tab_list.find(tab) == -1:

The ENGINE answers `None` for a field that was never set, and the `0` there is a SLOT INDEX,
not a default. `None != 0` is True, so it called `None.find(...)` and raised
`AttributeError: 'NoneType' object has no attribute 'find'` on a real bridge.

**It ran clean headless for years** because the mock answers with a typed default - the mock
blob table carries `"scan_type_list": ""` - and `"".find(tab)` is a perfectly good -1. That is
the engine-None-vs-mock-default divergence in its purest form, and it is why a green mock run
is not evidence for a data_set read.

Two more defects sat in the same three lines and are covered here too: the append had no
separator, so two tabs became the single unreadable token `"scanintel"`, and `find()`
substring-matched, so "intel" counted as present inside "no_intel".

    python -m unittest tests.test_science_scan_tabs
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import Context, FrameContext, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.spawn import npc_spawn, player_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.science import science_update_scan_data


def _tabs(target_id):
    raw = to_object(target_id).data_set.get("scan_type_list", 0)
    return [t.strip() for t in str(raw or "").split(",") if t.strip()]


class ScanTabListTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.origin = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.target = to_id(npc_spawn(1000, 0, 0, "Raider", "raider", "raider_light",
                                      "behav_npcship"))

    def tearDown(self):
        SpaceObject.clear()
        FrameContext.context = None

    def _unset_the_key(self):
        """Answer None for scan_type_list, the way the ENGINE does for a never-set field.

        The mock cannot reproduce this on its own - its blob table hands back a typed default
        - so the divergence has to be staged deliberately or the test proves nothing.
        """
        blob = to_object(self.target).data_set
        real_get = blob.get

        def engine_get(key, index=0):
            if key == "scan_type_list":
                return None
            return real_get(key, index)

        blob.get = engine_get

    def test_a_never_scanned_target_does_not_raise(self):
        # THE REGRESSION. This is the exact call the Director makes from //enable/science.
        self._unset_the_key()
        science_update_scan_data(self.origin, self.target, "Director")

    def test_the_tab_is_recorded_on_a_never_scanned_target(self):
        science_update_scan_data(self.origin, self.target, "Director", tab="intel")
        self.assertIn("intel", _tabs(self.target))

    def test_the_scan_text_lands_on_the_origin_side(self):
        # Scan data is stored per the ORIGIN's side, which is what makes one pass mark a
        # whole side's objects known.
        science_update_scan_data(self.origin, self.target, "Director")
        side = to_object(self.origin).side
        self.assertEqual(to_object(self.target).data_set.get("scan", side), "Director")

    def test_two_tabs_stay_two_tokens(self):
        # The append had no separator, so these used to fuse into "scanintel" - one token no
        # consumer can read, and every consumer splits on ",".
        science_update_scan_data(self.origin, self.target, "a", tab="scan")
        science_update_scan_data(self.origin, self.target, "b", tab="intel")
        self.assertEqual(_tabs(self.target), ["scan", "intel"])

    def test_the_same_tab_twice_is_recorded_once(self):
        science_update_scan_data(self.origin, self.target, "a", tab="intel")
        science_update_scan_data(self.origin, self.target, "b", tab="intel")
        self.assertEqual(_tabs(self.target), ["intel"])

    def test_a_substring_tab_is_not_mistaken_for_a_match(self):
        # find() said "intel" was already present inside "no_intel".
        science_update_scan_data(self.origin, self.target, "a", tab="no_intel")
        science_update_scan_data(self.origin, self.target, "b", tab="intel")
        self.assertEqual(sorted(_tabs(self.target)), ["intel", "no_intel"])

    def test_a_missing_origin_or_target_is_a_no_op(self):
        science_update_scan_data(None, self.target, "x")
        science_update_scan_data(self.origin, None, "x")
        self.assertEqual(_tabs(self.target), [])


if __name__ == "__main__":
    unittest.main()
