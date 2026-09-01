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



def setUpModule():
    """Extra ship data is off by DEFAULT (the `EXTRA_SHIP_DATA` setting), so these
    force it on rather than skipping: everything below describes the feature, and a
    mission that turns the setting on gets exactly this behaviour.

    Was a module-level skip from 2026-08-27 to 2026-09-01, while the switch was a
    hardcoded constant and there was no way to ask for the feature at all.
    """
    from sbs_utils.procedural.ship_data import extra_ship_data_force
    extra_ship_data_force(True)


def tearDownModule():
    from sbs_utils.procedural.ship_data import extra_ship_data_force
    extra_ship_data_force(None)

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

    def test_on_calls_the_engine_with_one_fully_pathed_file(self):
        # ONE argument, and it carries NO SUFFIX - the engine appends `.yaml`, then
        # `.json`, itself, exactly as the engine team's own sample does
        # (`add_extra_ship_data("data/missions/BeamArcTest/extraShipDataAAA")`).
        # Handing it the full filename made it answer `RuntimeError: End of input
        # while parsing an object` on a valid file - and that is the LUCKY case: the
        # call raises nothing for a file it cannot open, so the same mistake read as
        # "engine told: True" on another mod that was equally not loaded.
        name = self.write(ext=".yaml", text=SHIPS)
        # Pin the install root somewhere unrelated to the temp dir. `_engine_path`
        # rewrites a path UNDER the install into the root-relative form the engine
        # wants, so without pinning this the assertion silently depends on where
        # tempfile happens to live - it passed here and failed on a machine whose
        # temp dir sat inside the faked root.
        with mock.patch("sbs_utils.fs.get_artemis_dir",
                        return_value=os.path.join(self.tmp.name, "no", "such")),              mock.patch("sbs.add_extra_ship_data", create=True) as engine:
            reached = sd.add_extra(name, self.tmp.name)
        self.assertTrue(reached)
        engine.assert_called_once_with(os.path.join(self.tmp.name, name))

    def test_the_engine_is_told_the_name_without_the_extension(self):
        # We still READ the file ourselves to merge it library-side and to lint its
        # shape, but the engine is pointed at the STEM and does its own search. A
        # `.json` that we opened must not arrive with `.json` on it.
        name = self.write(ext=".json", text=SHIPS)
        with mock.patch("sbs_utils.fs.get_artemis_dir",
                        return_value=os.path.join(self.tmp.name, "no", "such")),              mock.patch("sbs.add_extra_ship_data", create=True) as engine:
            sd.add_extra(name, self.tmp.name)
        arg = engine.call_args[0][0]
        self.assertFalse(arg.endswith(".json"), arg)
        self.assertTrue(arg.endswith(name), arg)

    def test_a_missing_file_never_reaches_the_engine(self):
        # Nothing read means nothing to point at. Handing the engine a guess is
        # silent - it does not raise for a path it cannot open - so the only honest
        # move is not to call it, and to let the missing-file warning speak.
        with mock.patch("sbs.add_extra_ship_data", create=True) as engine:
            reached = sd.add_extra("nothing_here", self.tmp.name)
        self.assertFalse(reached)
        self.assertEqual(engine.call_args_list, [])

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

    def test_a_new_engine_rejecting_the_call_is_not_fatal(self):
        # The TypeError shape specifically: pybind answers a wrong-arity call with
        # one, and this wrapper's whole job is to survive it loudly rather than
        # quietly. Both LM's monsters and its turrets died here.
        name = self.write()
        with mock.patch("sbs.add_extra_ship_data",
                        side_effect=TypeError("incompatible function arguments"),
                        create=True):
            reached = sd.add_extra(name, self.tmp.name)
        self.assertFalse(reached)
        self.assertIsNotNone(sd.get_ship_data_for("wrapper_probe"))

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
        used = engine.call_args[0][0].replace("/", os.sep)
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
        # The exact string the engine was to be handed is recorded too, because
        # `extra_replay` has to re-issue THAT after create_new_sim() wipes the table,
        # and because a report that cannot say what path was used cannot be acted on.
        self.assertFalse(str(loaded[0][3]).endswith(".json"), loaded[0])
        self.assertTrue(str(loaded[0][3]).endswith(name), loaded[0])

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
        self.assertEqual(self._check("ships/TSNfighter"), [])

    def test_the_case_does_not_have_to_match(self):
        self.assertEqual(self._check("ships/tsnfighter"), [])

    def test_art_that_is_missing_is_named_with_its_hull(self):
        self.assertEqual(self._check("ships/tsn-fighter"), [("t", "ships/tsn-fighter")])

    def test_a_bare_root_is_reported_even_though_the_art_is_right_there(self):
        """The rule this check exists to enforce, and it is not about the file existing.

        `TSNfighter.obj` is sitting in graphics/ships in this fixture. On engine 1.3.6 a
        BARE artfileroot still asserts - artfileroot resolves against data/graphics now,
        so the name has to carry `ships/`. The hull spawns fine on the server and kills
        the first client that draws it, so "the art is there" is the wrong question."""
        self.assertEqual(self._check("TSNfighter"), [("t", "TSNfighter")])

    def test_a_path_out_of_graphics_is_followed_not_skipped(self):
        """A mod reaches art it ships itself by climbing out of data/graphics, and that
        is the one spelling engine 1.3.6 opens. The check used to SKIP any root with a
        slash, which under the new convention is every root - so it validated nothing."""
        import os
        pack = os.path.join(self.install.name, "data", "missions", "pack", "ships")
        os.makedirs(pack)
        open(os.path.join(pack, "God_Phoenix.obj"), "w").close()
        self.assertEqual(self._check("../missions/pack/ships/God_Phoenix"), [])
        self.assertEqual(self._check("../missions/pack/ships/nope"),
                         [("t", "../missions/pack/ships/nope")])

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

    def test_a_path_to_mod_art_IS_judged_now(self):
        """The opposite of what this test used to assert, and deliberately.

        It read: "a mod keeping its own graphics folder writes a relative PATH, that
        resolves somewhere this check does not look, so it must not be called missing."
        On engine 1.3.6 that reasoning inverts. `../missions/<pack>/ships/<name>` is the
        ONE spelling the engine opens for mod-carried art (measured, one copy of the art
        per candidate), so it lands inside the install and is perfectly checkable - and
        it is the art MOST worth checking, because a mod ships its own and a pack that
        failed to unpack looks exactly like one that did until a client draws a hull.

        The old path in that assertion also no longer exists: `anime_mods/anime_ships`
        was retired when the mod moved to a media pack."""
        self.assertEqual(
            self._check("../missions/nowhere_at_all/ships/God_Phoenix"),
            [("t", "../missions/nowhere_at_all/ships/God_Phoenix")])

    def test_art_genuinely_outside_the_install_is_still_left_alone(self):
        """The carve-out that survives: a root climbing clear of the install really is
        somewhere this function cannot judge, so it must not be reported as missing."""
        self.assertEqual(self._check("../../../elsewhere/ships/God_Phoenix"), [])

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
        # Real files on disk, because the replay now re-issues the exact path the
        # engine was handed - and there is no such path for a file that was never
        # found. A fake path here would assert on a code branch that no longer runs.
        self.write("extraProbe")
        self.write("extraOther")
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path=self.tmp.name)
            sd.add_extra("extraOther", path=self.tmp.name)
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            count = sd.extra_replay()
        self.assertEqual(count, 2)
        self.assertEqual([os.path.basename(c.args[0]) for c in told.call_args_list],
                         ["extraProbe", "extraOther"])

    def test_it_says_nothing_and_does_nothing_with_no_files(self):
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            self.assertEqual(sd.extra_replay(), 0)
        self.assertEqual(told.call_args_list, [])

    def test_a_file_that_was_never_found_is_not_replayed(self):
        # It was recorded (a report should still say it was asked for), but there is
        # no file to point the engine at, so replaying it would be a guess.
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path="some/where")
        self.assertEqual(len(sd.extra_loaded()), 1)
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            self.assertEqual(sd.extra_replay(), 0)
        self.assertEqual(told.call_args_list, [])

    def test_the_switch_still_wins(self):
        self.write("extraProbe")
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path=self.tmp.name)
        sd.extra_enable(False)
        self.addCleanup(sd.extra_enable, True)
        with mock.patch("sbs.add_extra_ship_data", create=True) as told:
            self.assertEqual(sd.extra_replay(), 0)
        self.assertEqual(told.call_args_list, [])

    def test_sim_create_replays_them(self):
        from sbs_utils.procedural import cosmos
        self.write("extraProbe")
        with mock.patch("sbs.add_extra_ship_data", create=True):
            sd.add_extra("extraProbe", path=self.tmp.name)
        with (mock.patch("sbs.add_extra_ship_data", create=True) as told,
              mock.patch("sbs_utils.procedural.ship_data_mod.ship_data_flush_mod_file"),
              mock.patch("sbs_utils.helpers.FrameContext.context", mock.MagicMock())):
            cosmos.sim_create()
        self.assertEqual([os.path.basename(c.args[0]) for c in told.call_args_list],
                         ["extraProbe"])


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


class TestTheSameFileTwiceDoesNotDoubleTheHulls(_Fixture):
    """The merge REPLACES by key. Nothing covered this, and it cost twice.

    `add_extra` merges the file it read, and the MOCK's `sbs.add_extra_ship_data` merges it
    a second time (the real engine does not merge library-side at all), so a blind prepend
    doubles every hull on the first call and doubles again on each repeat - 51 became 102
    became 204. Only a COUNT shows it: `get_ship_data_for` returns the newest copy, so
    every lookup keeps working while `filter_ship_data_by_side` quietly answers with twice
    the fleet.
    """

    def _hulls(self, key):
        cache = sd.ship_data_cache or {}
        return [e for e in cache.get("#ship-list") or []
                if isinstance(e, dict) and e.get("key") == key]

    def test_one_declare_yields_one_entry_per_key(self):
        name = self.write()
        sd.add_extra(name, self.tmp.name, mod="probe")
        self.assertEqual(len(self._hulls("wrapper_probe")), 1)

    def test_declaring_it_again_replaces_rather_than_appends(self):
        name = self.write()
        sd.add_extra(name, self.tmp.name, mod="probe")
        sd.add_extra(name, self.tmp.name, mod="probe")
        sd.add_extra(name, self.tmp.name, mod="probe")
        self.assertEqual(len(self._hulls("wrapper_probe")), 1,
                         "three declares must leave one entry, not three")

    def test_the_replay_record_is_not_duplicated_either(self):
        # extra_replay() walks this list, so a duplicate record re-issues the engine call
        # once per copy - and extra_loaded() is what the reset ledger counts, so it also
        # reads as a leak at a mission boundary.
        name = self.write()
        sd.add_extra(name, self.tmp.name, mod="probe")
        sd.add_extra(name, self.tmp.name, mod="probe")
        self.assertEqual(len(sd.extra_loaded()), 1)
