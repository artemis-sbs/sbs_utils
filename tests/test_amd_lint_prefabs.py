"""`Prefab:` and `Data:` checked against the mission's prefab catalog (amd_lint_prefabs).

The catalog is the mission's MAST labels typed `prefab/...` (their metadata keys and
`default` lines are the arguments they take) plus the library defaults.

    python -m unittest tests.test_amd_lint_prefabs
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_lint import amd_lint, mast_prefab_table

MAST = '''
=== prefab_station_industry
metadata: ``` yaml
type: prefab/npc/station/industry
display_text: Industry
race_value: terran
```
    jump common_station_create

=== prefab_station_command
metadata: ``` yaml
type: prefab/npc/station/command
```
    jump common_station_create

=== common_station_create
    default docking = "friendly"
    ->END

=== prefab_fleet_raider
metadata: ``` yaml
type: prefab/fleet/raider
race: kralien
fleet_difficulty: 5
```
    ->END
'''

CODES = ("landmark-no-prefab", "landmark-kind-retired", "unknown-prefab", "ambiguous-prefab",
         "unknown-prefab-arg", "prefab-reserved-arg", "data-without-prefab")


def _codes(body, mast=MAST):
    text = "# [Root](root)\n## [Landmarks](landmarks)\n" + body
    return [f.code for f in amd_lint(file_path="m.amd", content=text, mast_sources=[mast],
                                     cross_file=False) if f.code in CODES]


class CatalogTests(unittest.TestCase):
    def test_table_reads_types_metadata_and_jumped_defaults(self):
        t = mast_prefab_table([MAST])
        self.assertIn("npc/station/industry", t["types"])
        args = t["types"]["npc/station/industry"]["args"]
        self.assertIn("race_value", args)
        self.assertIn("docking", args)        # from the body it jumps to
        self.assertEqual(t["names"]["prefab_fleet_raider"], "fleet/raider")


class PrefabLintTests(unittest.TestCase):
    def test_clean(self):
        self.assertEqual(_codes(
            "### [K](k)\n---\nPrefab: npc/station/industry\nLoc: 1, 0, 1\n"
            "Data:\n  Race value: kralien\n  Docking: hostile\n---\n"), [])

    def test_library_default_is_known(self):
        self.assertEqual(_codes("### [K](k)\n---\nPrefab: derelict\nArt: wreck\n---\n"), [])

    def test_exact_default_beats_mast_prefixes(self):
        mast = MAST + ("\n=== prefab_npc_cargo\nmetadata: ``` yaml\ntype: prefab/npc/cargo\n"
                       "```\n    ->END\n")
        self.assertEqual(_codes("### [K](k)\n---\nPrefab: npc\nArt: x\n---\n", mast=mast), [])

    def test_label_name_is_known(self):
        self.assertEqual(_codes("### [K](k)\n---\nPrefab: prefab_fleet_raider\n---\n"), [])

    def test_no_prefab(self):
        self.assertEqual(_codes("### [K](k)\n---\nArt: wreck\n---\n"), ["landmark-no-prefab"])

    def test_kind_retired(self):
        self.assertEqual(_codes("### [K](k)\n---\nKind: derelict\nArt: wreck\n---\n"),
                         ["landmark-kind-retired"])

    def test_unknown_and_ambiguous(self):
        self.assertEqual(_codes("### [K](k)\n---\nPrefab: npc/statoin\n---\n"),
                         ["unknown-prefab"])
        self.assertEqual(_codes("### [K](k)\n---\nPrefab: npc/station\n---\n"),
                         ["ambiguous-prefab"])

    def test_unknown_is_quiet_without_a_catalog(self):
        # An unbuilt mastlib means no catalog was readable: silence, not noise.
        self.assertEqual(_codes("### [K](k)\n---\nPrefab: npc/statoin\n---\n", mast=""), [])

    def test_unknown_and_reserved_arguments(self):
        codes = _codes("### [K](k)\n---\nPrefab: fleet/raider\nData:\n  Fleet difficulty: 3\n"
                       "  Colour: red\n  Range: 9\n---\n")
        self.assertEqual(sorted(codes), ["prefab-reserved-arg", "unknown-prefab-arg"])

    def test_nested_creator_is_checked(self):
        codes = _codes("### [K](k)\n---\nPrefab: point\nGuards:\n  Prefab: fleet/raider\n"
                       "  Count: 2\n  Data:\n    Race: torgoth\n    Speed: 3\n---\n")
        self.assertEqual(codes, ["unknown-prefab-arg"])

    def test_unknown_prefab_offers_the_close_word(self):
        found = [f for f in amd_lint(file_path="m.amd", content="# [Root](root)\n## [Landmarks](landmarks)\n"
                 "### [K](k)\n---\nPrefab: wrekc\nArt: wreck\n---\n", mast_sources=[MAST],
                 cross_file=False) if f.code == "unknown-prefab"]
        self.assertEqual(len(found), 1)
        self.assertIn("Did you mean `wreck`?", found[0].message)

    def test_a_landmark_prefab_under_sides_is_the_wrong_heading(self):
        text = ("# [Root](root)\n## [Sides](sides)\n### [Breaker Cutter](cutter)\n---\n"
                "Prefab: ship\nArt: pirate_strongbow\n---\n")
        codes = [f.code for f in amd_lint(file_path="m.amd", content=text, mast_sources=[MAST],
                                          cross_file=False)]
        self.assertIn("prefab-wrong-record", codes)

    def test_data_without_prefab(self):
        self.assertIn("data-without-prefab",
                      _codes("### [K](k)\n---\nPrefab: point\nGuards:\n  Count: 2\n"
                             "  Prefab:\n---\n") + _codes(
                          "### [K](k)\n---\nArt: x\nData:\n  Race: x\n---\n"))


if __name__ == "__main__":
    unittest.main()
