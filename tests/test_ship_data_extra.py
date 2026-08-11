"""`ship_data_add_extra` - the wrapper over the engine's extra-ship-data hook.

`sbs.add_extra_ship_data` was being called raw from mission code, which left three
problems with nowhere to live: it is newer than some engines a mission may meet,
so a bare call is an AttributeError on an older one; it is not fully landed, and
there was no way to stop using it without editing every caller; and the ENGINE
knowing about the ships is a different thing from SBS_UTILS knowing about them.

The split those tests pin: the library merge ALWAYS happens, the engine call is
gated. So turning the engine side off costs the engine-side effects and keeps the
stats - which is the same division the runtime-mod work already measured, where
stats travel through the library and artfileroot does not.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import tempfile
import unittest
from unittest import mock

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 - import first, circular import
# Registers itself as `sbs` in sys.modules, which is what the wrapper imports.
from cosmos_dev.mock import sbs  # noqa: F401
from sbs_utils.procedural import ship_data as sd

SHIPS = """{
  "#ship-list": [
    {"key": "wrapper_probe", "name": "Wrapper Probe", "side": "TSN",
     "artfileroot": "tsn_light_cruiser", "shield_front_max": 777.0}
  ]
}"""


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(sd.ship_data_reset_for_mission)
        self.addCleanup(sd.ship_data_extra_enable, True)
        sd.ship_data_extra_reset()
        sd.ship_data_extra_enable(True)

    def write(self, name="extraProbe", ext=".json", text=SHIPS):
        path = os.path.join(self.tmp.name, name + ext)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return name


class TestTheSwitch(_Fixture):
    def test_enabled_by_default(self):
        self.assertTrue(sd.ship_data_extra_enabled())

    def test_off_means_the_engine_is_never_called(self):
        name = self.write()
        sd.ship_data_extra_enable(False)
        with mock.patch("sbs.add_extra_ship_data",
                        side_effect=AssertionError("called the engine"),
                        create=True):
            reached = sd.ship_data_add_extra(name, self.tmp.name)
        self.assertFalse(reached)

    def test_off_still_merges_into_the_library(self):
        # This is the whole design: the ships must still exist as far as
        # sbs_utils is concerned, so headless runs and every lookup are unchanged.
        name = self.write()
        sd.ship_data_extra_enable(False)
        sd.ship_data_add_extra(name, self.tmp.name)
        entry = sd.get_ship_data_for("wrapper_probe")
        self.assertIsNotNone(entry, "the library lost the ships when the engine "
                                    "call was disabled")
        self.assertEqual(entry.get("shield_front_max"), 777.0)

    def test_on_calls_the_engine_with_filename_and_path(self):
        name = self.write()
        with mock.patch("sbs.add_extra_ship_data", create=True) as engine:
            reached = sd.ship_data_add_extra(name, self.tmp.name)
        self.assertTrue(reached)
        engine.assert_called_once_with(name, self.tmp.name)


class TestRobustness(_Fixture):
    def test_an_older_engine_without_the_hook_is_not_fatal(self):
        name = self.write()
        with mock.patch("sbs.add_extra_ship_data",
                        side_effect=AttributeError("no such thing"), create=True):
            reached = sd.ship_data_add_extra(name, self.tmp.name)
        self.assertFalse(reached)
        # ...and the ships still arrived, which is the point of not being fatal.
        self.assertIsNotNone(sd.get_ship_data_for("wrapper_probe"))

    def test_a_missing_file_is_not_fatal(self):
        # Matching the engine's habit: a mod with a broken path should be a ship
        # with no stats, not a dead mission.
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.ship_data_add_extra("nothing_here", self.tmp.name)

    def test_the_extension_is_searched_the_way_the_engine_searches_it(self):
        # The filename is passed WITHOUT one, so a mod can switch format without
        # the caller changing.
        name = self.write(ext=".yaml", text=SHIPS)
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.ship_data_add_extra(name, self.tmp.name)
        self.assertIsNotNone(sd.get_ship_data_for("wrapper_probe"))


class TestTheRecord(_Fixture):
    def test_it_records_what_was_loaded_and_whether_the_engine_heard(self):
        name = self.write()
        sd.ship_data_extra_enable(False)
        sd.ship_data_add_extra(name, self.tmp.name)
        loaded = sd.ship_data_extra_loaded()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][0], name)
        self.assertFalse(loaded[0][2], "reached_engine should be False when off")

    def test_the_record_does_not_survive_a_mission_boundary(self):
        # cosmos_dev reuses one interpreter across missions where the engine
        # forks; an unreset container is how run 2 inherits run 1.
        name = self.write()
        sd.ship_data_extra_enable(False)
        sd.ship_data_add_extra(name, self.tmp.name)
        sd.ship_data_reset_for_mission()
        self.assertEqual(sd.ship_data_extra_loaded(), [])

    def test_it_is_in_the_reset_ledger(self):
        # An unregistered per-mission container is invisible to the soak
        # audit, and the point of the ledger is that nothing may be invisible.
        from sbs_utils.handlerhooks import _RESET_PROBES, reset_mission_audit
        self.assertIn("ship_data_extra", _RESET_PROBES)

        name = self.write()
        sd.ship_data_extra_enable(False)
        sd.ship_data_add_extra(name, self.tmp.name)
        self.assertEqual(reset_mission_audit().get("ship_data_extra"), 1,
                         "the audit should SEE the loaded file before a reset")
        sd.ship_data_reset_for_mission()
        self.assertNotIn("ship_data_extra", reset_mission_audit(),
                         "and nothing after - a non-empty entry is a leak")


if __name__ == "__main__":
    unittest.main()
