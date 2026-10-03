"""A mission's SHARED folder is part of the mission to every tool.

An author's own Siege bosses live in `<missions>/common_data/bosses`, where an update to
LegendaryMissions cannot delete them. The game read them from there; nothing else did:

  * `sbs lint LegendaryMissions` never looked outside the mission folder, so the lesson's
    "check it" step had nothing to show.
  * The editor served a file opened there as a lone file: `Trigger:`, `Flies:`, `Named:`
    were all unknown fields, and `Part of: siege_mission` pointed at nothing.
  * A boss named like a shipped one replaces it in the list, and the duplicate-name check
    only looked at files in the same folder.

    python -m unittest tests.test_amd_shared_folder
"""
import os
import shutil
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_vocab as V
from sbs_utils.procedural.amd_lint import amd_lint

VOCAB = '''from sbs_utils.procedural.amd_vocab import amd_register_shared_folder


def _declare():
    amd_register_shared_folder("bosses", beside="maps/bosses")


_declare()
'''

BOSS = """# [{name}]({key})
---
Boss
---
Arrives late.
"""


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path


class SharedFolderTests(unittest.TestCase):
    def setUp(self):
        self.missions = tempfile.mkdtemp(prefix="shared_folder_")
        self.addCleanup(shutil.rmtree, self.missions, True)
        self.mission = os.path.join(self.missions, "Siege")
        _write(os.path.join(self.mission, "story.json"), "{}")
        _write(os.path.join(self.mission, "siege_amd.py"), VOCAB)
        self.shipped = _write(os.path.join(self.mission, "maps", "bosses", "warlord.amd"),
                              BOSS.format(name="Warlord", key="warlord"))
        self.other = os.path.join(self.missions, "Other")
        _write(os.path.join(self.other, "story.json"), "{}")
        self.mine = _write(os.path.join(self.missions, "common_data", "bosses", "queen.amd"),
                           BOSS.format(name="Corsair Queen", key="queen"))
        # A save beside it is not a shared folder, and not an .amd.
        _write(os.path.join(self.missions, "common_data", "saves", "slot_1.yaml"), "x: 1\n")

    def test_the_declaration_is_read_without_running_the_file(self):
        self.assertEqual(V.mission_shared_folders(self.mission), {"bosses": "maps/bosses"})
        self.assertEqual(V.mission_shared_folders(self.other), {})

    def test_a_non_literal_declaration_is_not_guessed_at(self):
        _write(os.path.join(self.other, "other_amd.py"),
               "NAME = 'bosses'\namd_register_shared_folder(NAME)\n")
        self.assertEqual(V.mission_shared_folders(self.other), {})

    def test_the_missions_shared_files(self):
        got = [os.path.normcase(p) for p in V.shared_amd_files(self.mission)]
        self.assertEqual(got, [os.path.normcase(os.path.abspath(self.mine))])
        self.assertEqual(V.shared_amd_files(self.other), [])

    def test_a_shared_file_finds_the_mission_that_reads_it(self):
        self.assertEqual(os.path.normcase(V.shared_folder_owner(self.mine)),
                         os.path.normcase(os.path.abspath(self.mission)))

    def test_a_folder_nobody_declared_has_no_owner(self):
        stray = _write(os.path.join(self.missions, "common_data", "notes", "a.amd"), "# [A](a)\n")
        self.assertIsNone(V.shared_folder_owner(stray))
        self.assertIsNone(V.shared_folder_owner(self.shipped))

    def test_the_two_folders_are_neighbors_both_ways(self):
        there = [os.path.normcase(p) for p in V.shared_neighbor_folders(self.mine)]
        self.assertEqual(there, [os.path.normcase(os.path.dirname(os.path.abspath(self.shipped)))])
        back = [os.path.normcase(p) for p in V.shared_neighbor_folders(self.shipped)]
        self.assertEqual(back, [os.path.normcase(os.path.dirname(os.path.abspath(self.mine)))])

    def test_a_file_elsewhere_in_the_mission_has_no_neighbors(self):
        elsewhere = _write(os.path.join(self.mission, "maps", "quests.amd"), "# [Q](q)\n")
        self.assertEqual(V.shared_neighbor_folders(elsewhere), [])

    def test_my_boss_named_like_a_shipped_one_is_reported(self):
        _write(self.mine, BOSS.format(name="Warlord", key="queen"))
        found = [f for f in amd_lint(file_path=self.mine, cross_file=False)
                 if f.code == "duplicate-boss-name"]
        self.assertEqual(len(found), 1)
        self.assertIn("warlord.amd", found[0].message)

    def test_and_the_shipped_one_hears_about_mine(self):
        _write(self.mine, BOSS.format(name="Warlord", key="queen"))
        codes = [f.code for f in amd_lint(file_path=self.shipped, cross_file=False)]
        self.assertIn("duplicate-boss-name", codes)

    def test_a_name_of_its_own_is_quiet(self):
        codes = [f.code for f in amd_lint(file_path=self.mine, cross_file=False)]
        self.assertNotIn("duplicate-boss-name", codes)


class TheEditorTests(unittest.TestCase):
    """The language server finds the mission for a file that is in no mission folder."""

    def setUp(self):
        self.missions = tempfile.mkdtemp(prefix="shared_folder_lsp_")
        self.addCleanup(shutil.rmtree, self.missions, True)
        self.mission = os.path.join(self.missions, "Siege")
        _write(os.path.join(self.mission, "story.json"), "{}")
        _write(os.path.join(self.mission, "siege_amd.py"), VOCAB)
        _write(os.path.join(self.mission, "maps", "siege_quests.amd"),
               "# [Siege](siege_mission)\n---\nArc\nScope: shared\n---\nHold.\n")
        self.mine = _write(os.path.join(self.missions, "common_data", "bosses", "queen.amd"),
                           BOSS.format(name="Corsair Queen", key="queen"))

    def test_the_root_is_the_owning_mission(self):
        from sbs_utils.procedural import amd_lsp
        self.assertEqual(os.path.normcase(amd_lsp._mission_root(self.mine)),
                         os.path.normcase(os.path.abspath(self.mission)))

    def test_the_index_holds_the_missions_keys_and_the_shared_file(self):
        from sbs_utils.procedural import amd_lsp
        amd_lsp._index_cache.pop(os.path.abspath(self.mission), None)
        root = amd_lsp._mission_root(self.mine)
        self.addCleanup(amd_lsp._index_cache.pop, root, None)
        index = amd_lsp._mission_index(root, {})
        self.assertIn("siege_mission", index["known"])
        self.assertIn("queen", index["known"])
        paths = [p for p, _u, _d in index["docs"]]
        self.assertIn(os.path.normcase(os.path.abspath(self.mine)), paths)


if __name__ == "__main__":
    unittest.main()
