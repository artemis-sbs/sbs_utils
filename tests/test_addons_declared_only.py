"""Addons are DECLARED in story.json, never discovered by walking the mission.

`find_add_ons` used to also adopt any `.mastlib`/`.zip` it walked in the mission tree -
from before story.json + __lib__ managed dependencies. That was actively harmful:

  * A stray `.zip` in a mission SUBFOLDER (art pack, backup, download) was treated as an
    addon. It has no `__init__.mast`, so the read failed and the story compiled to ZERO
    labels while a headless --test still reported PASS - measured on hamaksector,
    labels 0/248 with a stray zip vs 281/638 without.
  * A stale `.mastlib` was worse: it loaded, merging labels the mission never declared.

These pin that only the declared list is used, so the walk cannot come back by accident.
"""
import json
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
from sbs_utils.mast.mast import Mast
from sbs_utils import fs


class FindAddOnsDeclaredOnlyTests(unittest.TestCase):
    def setUp(self):
        # mkdtemp + tolerant rmtree: compiling writes mast.compile.log into the mission
        # dir, and TemporaryDirectory's strict cleanup fails on it under Windows.
        import shutil
        self.missions = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.missions, True)
        self.mission = os.path.join(self.missions, "amission")
        self.lib = os.path.join(self.missions, "__lib__")
        os.makedirs(self.mission)
        os.makedirs(self.lib)
        # find_add_ons bails unless a `script` module is loaded (the engine entry point).
        self._script = mock.patch.dict(sys.modules, {"script": mock.Mock()})
        self._script.start()
        self.addCleanup(self._script.stop)
        for target, value in (("get_script_dir", self.mission),
                              ("get_missions_dir", self.missions)):
            p = mock.patch.object(fs, target, return_value=value)
            p.start()
            self.addCleanup(p.stop)

    def _story_json(self, mastlibs):
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"mastlib": mastlibs}, f)

    def _drop_archive(self, relpath):
        path = os.path.join(self.mission, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("notes.txt", "unrelated")
        return path

    def test_declared_mastlibs_are_returned(self):
        self._story_json(["u.Repo.addon.v1.0.0.mastlib"])
        found = Mast().find_add_ons()
        self.assertEqual([os.path.basename(f) for f in found],
                         ["u.Repo.addon.v1.0.0.mastlib"])
        self.assertTrue(found[0].startswith(self.lib), "declared libs resolve in __lib__")

    def test_a_stray_zip_in_a_subfolder_is_ignored(self):
        # The case that took a real mission to zero labels while reporting PASS.
        self._story_json([])
        self._drop_archive(os.path.join("extras", "stray.zip"))
        self.assertEqual(Mast().find_add_ons(), [])

    def test_a_stray_mastlib_in_a_subfolder_is_ignored(self):
        # The quieter case: it WOULD have loaded, merging undeclared content.
        self._story_json([])
        self._drop_archive(os.path.join("extras", "old_build.mastlib"))
        self.assertEqual(Mast().find_add_ons(), [])

    def test_a_stray_archive_does_not_join_the_declared_list(self):
        self._story_json(["u.Repo.addon.v1.0.0.mastlib"])
        self._drop_archive(os.path.join("extras", "stray.zip"))
        self._drop_archive(os.path.join("media", "art.zip"))
        found = Mast().find_add_ons()
        self.assertEqual(len(found), 1, f"only the declared lib should be adopted: {found}")

    def test_no_story_json_means_no_addons(self):
        self._drop_archive(os.path.join("extras", "old_build.mastlib"))
        self.assertEqual(Mast().find_add_ons(), [])


class SourceWinsOverDeclaredLibTests(unittest.TestCase):
    """One story.json serves a clone and a fetched copy.

    A repo that packages its own addons declares them like any consumer, but a CLONE still
    has the source folders. The two loaders are additive, so loading both compiles every
    label twice and dies on the process-global name registry with "Label conflicts with
    shared name" - a message that says nothing about the real cause. Preferring the source
    lets a clone edit its addons in place while a fetched copy (folders stripped by
    export-ignore) uses __lib__.
    """
    LIB = "artemis-sbs.LegendaryMissions.consoles.v1.4.0.mastlib"

    def setUp(self):
        import shutil
        self.missions = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.missions, True)
        self.mission = os.path.join(self.missions, "amission")
        os.makedirs(os.path.join(self.missions, "__lib__"))
        os.makedirs(self.mission)
        self._script = mock.patch.dict(sys.modules, {"script": mock.Mock()})
        self._script.start()
        self.addCleanup(self._script.stop)
        for target, value in (("get_script_dir", self.mission),
                              ("get_missions_dir", self.missions)):
            p = mock.patch.object(fs, target, return_value=value)
            p.start()
            self.addCleanup(p.stop)
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"mastlib": [self.LIB]}, f)

    def _addon_folder(self, name="consoles", with_init=True):
        d = os.path.join(self.mission, name)
        os.makedirs(d, exist_ok=True)
        if with_init:
            with open(os.path.join(d, "__init__.mast"), "w") as f:
                f.write("# addon\n")
        return d

    def test_lib_is_used_when_there_is_no_source(self):
        found = Mast().find_add_ons()
        self.assertEqual([os.path.basename(f) for f in found], [self.LIB])

    def test_source_folder_wins_over_the_declared_lib(self):
        self._addon_folder()
        self.assertEqual(Mast().find_add_ons(), [],
                         "a clone must load its own source, not the packaged copy")

    def test_a_same_named_folder_without_init_does_not_suppress_the_lib(self):
        # A mission that merely has a folder called `consoles` still needs the addon.
        self._addon_folder(with_init=False)
        found = Mast().find_add_ons()
        self.assertEqual([os.path.basename(f) for f in found], [self.LIB])

    def test_only_the_matching_addon_is_skipped(self):
        other = "artemis-sbs.LegendaryMissions.docking.v1.4.0.mastlib"
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            json.dump({"mastlib": [self.LIB, other]}, f)
        self._addon_folder("consoles")
        found = Mast().find_add_ons()
        self.assertEqual([os.path.basename(f) for f in found], [other])

    def test_source_folder_resolution(self):
        self._addon_folder()
        self.assertIsNotNone(Mast.addon_source_folder(self.mission, self.LIB))
        self.assertIsNone(Mast.addon_source_folder(self.mission, "not-a-lib-name"))
        self.assertIsNone(Mast.addon_source_folder(self.mission, "a.b.absent.v1.0.0.mastlib"))


if __name__ == "__main__":
    unittest.main()
