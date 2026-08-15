"""`add_extra` - the wrapper over the engine's extra-ship-data hook.

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
import builtins
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
        self.addCleanup(sd.extra_enable, True)
        sd.ship_data_reset_for_mission()
        # Seed the cache so nothing here needs the COSMOS INSTALL. `get_ship_data`
        # loads `shipData` from `get_artemis_data_dir()`, which exists on a
        # developer machine and not in this repo - so these tests passed locally
        # and failed the moment the data dir was taken away, which is what CI is.
        # A non-None cache short-circuits that load, and `merge_mod_ship_yaml`
        # prepends into it, which is exactly the path under test.
        sd.ship_data_cache = {"#ship-list": []}
        sd.extra_reset()
        sd.extra_enable(True)

    def write(self, name="extraProbe", ext=".json", text=SHIPS):
        path = os.path.join(self.tmp.name, name + ext)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return name


class TestTheSwitch(_Fixture):
    def test_enabled_by_default(self):
        self.assertTrue(sd.extra_enabled())

    def test_off_means_the_engine_is_never_called(self):
        name = self.write()
        sd.extra_enable(False)
        with mock.patch("sbs.add_extra_ship_data",
                        side_effect=AssertionError("called the engine"),
                        create=True):
            reached = sd.add_extra(name, self.tmp.name)
        self.assertFalse(reached)

    def test_off_still_merges_into_the_library(self):
        # This is the whole design: the ships must still exist as far as
        # sbs_utils is concerned, so headless runs and every lookup are unchanged.
        name = self.write()
        sd.extra_enable(False)
        sd.add_extra(name, self.tmp.name)
        entry = sd.get_ship_data_for("wrapper_probe")
        self.assertIsNotNone(entry, "the library lost the ships when the engine "
                                    "call was disabled")
        self.assertEqual(entry.get("shield_front_max"), 777.0)

    def test_on_calls_the_engine_with_filename_and_path(self):
        name = self.write()
        # Pin the install root somewhere unrelated to the temp dir. `_engine_path`
        # rewrites a path UNDER the install into the root-relative form the engine
        # wants, so without pinning this the assertion silently depends on where
        # tempfile happens to live - it passed here and failed on a machine whose
        # temp dir sat inside the faked root.
        with mock.patch("sbs_utils.fs.get_artemis_dir",
                        return_value=os.path.join(self.tmp.name, "no", "such")),              mock.patch("sbs.add_extra_ship_data", create=True) as engine:
            reached = sd.add_extra(name, self.tmp.name)
        self.assertTrue(reached)
        engine.assert_called_once_with(name, self.tmp.name)

    def test_an_absolute_path_under_the_install_is_made_root_relative(self):
        # The engine's own example is ("extraShipDataAAA", "data/missions/BeamArcTest") -
        # relative to the Cosmos root, not absolute and not relative to the mission.
        root = self.tmp.name
        folder = os.path.join(root, "data", "missions", "Demo")
        os.makedirs(folder, exist_ok=True)
        with mock.patch("sbs_utils.fs.get_artemis_dir", return_value=root):
            self.assertEqual(sd._engine_path(folder), "data/missions/Demo")


class TestRobustness(_Fixture):
    def test_an_older_engine_without_the_hook_is_not_fatal(self):
        name = self.write()
        with mock.patch("sbs.add_extra_ship_data",
                        side_effect=AttributeError("no such thing"), create=True):
            reached = sd.add_extra(name, self.tmp.name)
        self.assertFalse(reached)
        # ...and the ships still arrived, which is the point of not being fatal.
        self.assertIsNotNone(sd.get_ship_data_for("wrapper_probe"))

    def test_a_missing_file_is_not_fatal(self):
        # Matching the engine's habit: a mod with a broken path should be a ship
        # with no stats, not a dead mission.
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("nothing_here", self.tmp.name)

    def test_the_extension_is_searched_the_way_the_engine_searches_it(self):
        # The filename is passed WITHOUT one, so a mod can switch format without
        # the caller changing.
        name = self.write(ext=".yaml", text=SHIPS)
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra(name, self.tmp.name)
        self.assertIsNotNone(sd.get_ship_data_for("wrapper_probe"))


class TestLogicalPaths(_Fixture):
    """An addon cannot put a file where the engine can read it - a mastlib is a
    zip - so it ships hulls in its media pack and names them logically here."""

    def test_the_folder_is_chosen_by_the_FILE_not_by_existing(self):
        # An addon's logical folder name usually matches its own source folder:
        # `turrets/` is both the mastlib's name and a real directory in the
        # mission. Picking the first directory that exists picks the addon
        # folder - which is exactly where the file no longer is.
        import sbs_utils.fs as fs
        mission = os.path.join(self.tmp.name, "Mission")
        decoy = os.path.join(mission, "turrets")          # exists, holds nothing
        real = os.path.join(mission, "media", "turrets")  # holds the file
        os.makedirs(decoy)
        os.makedirs(real)
        with open(os.path.join(real, "extraShipData_turrets.yaml"), "w") as f:
            f.write(SHIPS)
        old_dir, fs.script_dir = fs.script_dir, mission
        try:
            with mock.patch("sbs.add_extra_ship_data", create=True) as engine:
                sd.add_extra("turrets/extraShipData_turrets")
        finally:
            fs.script_dir = old_dir
        used = engine.call_args[0][1].replace("/", os.sep)
        self.assertIn(os.path.join("media", "turrets"), used,
                      "resolved to the decoy addon folder instead of the media pack")
        self.assertIsNotNone(sd.get_ship_data_for("wrapper_probe"))


class TestTheRecord(_Fixture):
    def test_it_records_what_was_loaded_and_whether_the_engine_heard(self):
        name = self.write()
        sd.extra_enable(False)
        sd.add_extra(name, self.tmp.name)
        loaded = sd.extra_loaded()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0][0], name)
        self.assertFalse(loaded[0][2], "reached_engine should be False when off")

    def test_the_record_does_not_survive_a_mission_boundary(self):
        # cosmos_dev reuses one interpreter across missions where the engine
        # forks; an unreset container is how run 2 inherits run 1.
        name = self.write()
        sd.extra_enable(False)
        sd.add_extra(name, self.tmp.name)
        sd.ship_data_reset_for_mission()
        self.assertEqual(sd.extra_loaded(), [])

    def test_it_is_in_the_reset_ledger(self):
        # An unregistered per-mission container is invisible to the soak
        # audit, and the point of the ledger is that nothing may be invisible.
        from sbs_utils.handlerhooks import _RESET_PROBES, reset_mission_audit
        self.assertIn("ship_data_extra", _RESET_PROBES)

        name = self.write()
        sd.extra_enable(False)
        sd.add_extra(name, self.tmp.name)
        self.assertEqual(reset_mission_audit().get("ship_data_extra"), 1,
                         "the audit should SEE the loaded file before a reset")
        sd.ship_data_reset_for_mission()
        self.assertNotIn("ship_data_extra", reset_mission_audit(),
                         "and nothing after - a non-empty entry is a leak")


if __name__ == "__main__":
    unittest.main()


class TestItSaysWhenItFoundNothing(_Fixture):
    """A missing extra-ship-data file must not be silent.

    It stayed silent for a day and cost an afternoon: LegendaryMissions moved its
    monster hulls out of the mastlib and into its media pack, LM_TestRange never
    declared that pack, and the whole failure surfaced as seven conformance
    assertions reporting `beamCount 0` - which reads as "combat is broken", not as
    "the file was never found".
    """

    def test_a_missing_file_is_logged_with_where_it_looked(self):
        with mock.patch("sbs_utils.procedural.ship_data.get_mission_dir",
                        return_value=os.path.join("nowhere", "at", "all")), \
             mock.patch("sbs.add_extra_ship_data", create=True), \
             mock.patch("sbs_utils.procedural.execution.log") as logged:
            sd.add_extra("prefabs/extraShipData_monsters", mod="LM")
        said = " ".join(str(c) for c in logged.call_args_list)
        self.assertIn("extraShipData_monsters", said)
        self.assertIn("shared_media", said)

    def test_a_file_that_is_there_says_nothing(self):
        with mock.patch("sbs_utils.procedural.ship_data.get_mission_dir",
                        return_value=self.tmp.name), \
             mock.patch("sbs.add_extra_ship_data", create=True), \
             mock.patch("sbs_utils.procedural.execution.log") as logged:
            sd.add_extra("hulls", mod="LM")
        self.assertEqual(logged.call_args_list, [])

    def setUp(self):
        # _Fixture seeds the ship-data cache, so `add_extra` can merge without the Cosmos
        # install. Without it this class read the real shipData on a developer machine and
        # nothing at all on CI, where the miss now reports itself and broke the
        # "says nothing" assertion below.
        super().setUp()
        with open(os.path.join(self.tmp.name, "hulls.yaml"), "w", encoding="utf-8") as f:
            f.write(_JSON_HULLS)


# The engine reads extra ship data as HJSON, so a fixture written as block YAML is not a
# neutral choice - it is the bug. Keep the good shape here, and test the bad one on purpose.
_JSON_HULLS = """{
  "#ship-list": [
    {"key": "t_hull", "name": "T", "hullpoints": 10}
  ]
}
"""

_BLOCK_HULLS = """#ship-list:
  - key: t_hull
    name: T
    hullpoints: 10
"""

_COMMENTED = """# a comment that comes first

""" + _JSON_HULLS


class TestItSaysWhenTheEngineCannotReadTheShape(_Fixture):
    """The engine parses extra ship data as HJSON: no `- item` sequences, no whitespace in
    a key. PyYAML accepts both shapes, so a block-YAML file works in every test and every
    headless run and is rejected only by the engine - silently, until a spawn fails for a
    hull it was never given. Measured on LegendaryMissions' turrets, 2026-08-14."""

    def _write(self, text):
        with open(os.path.join(self.tmp.name, "hulls.yaml"), "w", encoding="utf-8") as f:
            f.write(text)

    def _load(self):
        with (mock.patch("sbs_utils.procedural.ship_data.get_mission_dir",
                         return_value=self.tmp.name),
              mock.patch("sbs.add_extra_ship_data", create=True),
              mock.patch("sbs_utils.procedural.execution.log") as logged):
            sd.add_extra("hulls", mod="LM")
        return " ".join(str(c) for c in logged.call_args_list)

    def test_block_yaml_is_called_out(self):
        self._write(_BLOCK_HULLS)
        said = self._load()
        self.assertIn("HJSON", said)
        self.assertIn("hulls", said)

    def test_json_passes_without_comment(self):
        self._write(_JSON_HULLS)
        self.assertEqual(self._load(), "")

    def test_comments_before_the_brace_are_fine(self):
        self._write(_COMMENTED)
        self.assertEqual(self._load(), "")

    def test_the_shape_test_itself(self):
        self.assertTrue(sd._looks_like_hjson(_JSON_HULLS))
        self.assertTrue(sd._looks_like_hjson("# only comments"))
        self.assertFalse(sd._looks_like_hjson(_BLOCK_HULLS))


class TestItSaysWhenTheArtIsNotThere(unittest.TestCase):
    """A hull whose artfileroot does not exist spawns fine on the server and then asserts
    on the first client that draws it - a modal dialog on a player's machine, from a typo.
    LM's turrets asked for `tsn-fighter` when the art is `TSNfighter`."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.install = tempfile.TemporaryDirectory()
        self.addCleanup(self.install.cleanup)
        self.ships = os.path.join(self.install.name, "data", "graphics", "ships")
        os.makedirs(self.ships)
        for name in ("TSNfighter.obj", "TSNfighter_diffuse.png"):
            open(os.path.join(self.ships, name), "w").close()

    def _check(self, art):
        text = ('{"#ship-list": [{"key": "t", "name": "T", "artfileroot": "' + art
                + '"}]}')
        with mock.patch("sbs_utils.fs.get_artemis_dir", return_value=self.install.name):
            return sd._art_that_is_not_there(text)

    def test_art_that_exists_is_not_reported(self):
        self.assertEqual(self._check("TSNfighter"), [])

    def test_the_case_does_not_have_to_match(self):
        self.assertEqual(self._check("tsnfighter"), [])

    def test_art_that_is_missing_is_named_with_its_hull(self):
        self.assertEqual(self._check("tsn-fighter"), [("t", "tsn-fighter")])

    def test_it_still_checks_without_pyyaml_installed(self):
        """Parsing must go through the BUNDLED `sbs_utils.yaml`. A bare `import yaml`
        reaches site-packages PyYAML, which exists on a developer machine and NOWHERE this
        actually runs - not in the embedded engine (site is off), not on a CI runner that
        installs nothing. The broad `except` in the check would then turn that ImportError
        into "no art is missing", so the check silently did nothing everywhere it mattered
        and only ever passed locally (2026-08-15)."""
        real = builtins.__import__

        def no_pyyaml(name, g=None, l=None, fl=(), lvl=0):
            if name == "yaml" and lvl == 0:
                raise ImportError("No module named yaml")
            return real(name, g, l, fl, lvl)

        with mock.patch.object(builtins, "__import__", no_pyyaml):
            self.assertEqual(self._check("tsn-fighter"), [("t", "tsn-fighter")])

    def test_a_path_to_mod_art_is_not_judged(self):
        """A mod keeping its own graphics folder writes a relative PATH as its artfileroot.
        That resolves somewhere this check does not look, so it must not be called missing -
        VisualTestRange keeps `modart_relpath` as the specimen."""
        self.assertEqual(
            self._check("../../missions/anime_mods/anime_ships/graphics/ships/God_Phoenix"),
            [])

    def test_it_stays_quiet_with_no_install_to_check(self):
        with mock.patch("sbs_utils.fs.get_artemis_dir", return_value="/nowhere/at/all"):
            found = sd._art_that_is_not_there(
                '{"#ship-list": [{"key": "t", "artfileroot": "whatever"}]}')
        self.assertEqual(found, [])


class TestItSurvivesTheSimBeingRebuilt(_Fixture):
    """`create_new_sim()` rebuilds the engine's ship data table and drops everything
    `add_extra_ship_data` was told beforehand - and a mission registers at story load,
    which is always before its first map calls sim_create. Nothing reports the loss: the
    library keeps its merged copy, so the ships look fine until a spawn asks the engine
    for one. LM's monsters were unspawnable from the first map start for exactly this
    reason (2026-08-14)."""

    def test_every_file_is_told_to_the_engine_again(self):
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path="some/where")
            sd.add_extra("extraOther", path="else/where")
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            count = sd.extra_replay()
        self.assertEqual(count, 2)
        self.assertEqual([c.args[0] for c in told.call_args_list],
                         ["extraProbe", "extraOther"])

    def test_it_says_nothing_and_does_nothing_with_no_files(self):
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            self.assertEqual(sd.extra_replay(), 0)
        self.assertEqual(told.call_args_list, [])

    def test_the_switch_still_wins(self):
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path="some/where")
        sd.extra_enable(False)
        self.addCleanup(sd.extra_enable, True)
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            self.assertEqual(sd.extra_replay(), 0)
        self.assertEqual(told.call_args_list, [])

    def test_sim_create_replays_them(self):
        from sbs_utils.procedural import cosmos
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path="some/where")
        with (mock.patch("sbs.add_extra_ship_data", create=True) as told,
              mock.patch("sbs_utils.procedural.ship_data_mod.ship_data_flush_mod_file"),
              mock.patch("sbs_utils.helpers.FrameContext.context", mock.MagicMock())):
            cosmos.sim_create()
        self.assertEqual([c.args[0] for c in told.call_args_list], ["extraProbe"])


class TestItSaysWhenTheInstallCannotBeRead(_Fixture):
    """`get_ship_data` used to return None when `shipData` was missing or unreadable, and
    every caller subscripts what it returns - so the failure was spent somewhere else, as
    `TypeError: 'NoneType' object is not subscriptable` from whichever line looked next,
    naming neither the file nor the install. CI reproduced it exactly, having no Cosmos
    install at all (2026-08-15)."""

    def test_a_missing_ship_data_file_is_named(self):
        sd.ship_data_cache = None
        with (mock.patch.object(sd, "load_data", return_value=None),
              mock.patch("sbs_utils.procedural.execution.log") as logged):
            data = sd.get_ship_data()
        self.assertEqual(data, {"#ship-list": []})
        said = " ".join(str(c) for c in logged.call_args_list)
        self.assertIn("shipData", said)

    def test_a_merge_after_that_reports_instead_of_crashing(self):
        """The path CI actually died on: an add-on prepending its hulls into a cache that
        was never loaded."""
        sd.ship_data_cache = None
        with (mock.patch.object(sd, "load_data", return_value=None),
              mock.patch("sbs_utils.procedural.execution.log")):
            out = sd.merge_mod_ship_yaml('{"#ship-list": [{"key": "x"}]}', "probe")
        self.assertEqual([e["key"] for e in out["#ship-list"]], ["x"])

    def test_extra_ship_data_without_a_ship_list_is_not_fatal(self):
        sd.ship_data_cache = None
        with (mock.patch.object(sd, "load_data", return_value={"something": "else"}),
              mock.patch("sbs_utils.procedural.execution.log") as logged):
            data = sd.get_ship_data()
        self.assertEqual(data["#ship-list"], [])
        self.assertIn("#ship-list", " ".join(str(c) for c in logged.call_args_list))
