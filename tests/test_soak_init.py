"""Tests for the soak scenario generator.

The census is the part worth pinning. It is the first thing an author reads about a new
mission, and every way it can be wrong is quiet: a key that does not match what a run
reports is pasted into `expect:` and simply never satisfied, and a goal filter that is too
narrow reports a mission as having no quests at all. Both happened while building it, and
both are covered below.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.soak_init import (DRIVABLE, GOAL_KEYS, _goals_of, build_scenario_text,
                                  census_quests, write_scenario)


class GoalExtractionTests(unittest.TestCase):
    def test_plain_goal_keys(self):
        self.assertEqual(_goals_of({"on_kill": {"role": "raider"}}),
                         {"on_kill": {"role": "raider"}})

    def test_start_trigger_counts_as_a_goal(self):
        """`When:` does not produce a bare `on_*` key.

        The parser files it under `start_trigger`, and `quest_driver._arm_start_trigger`
        swaps it in at grant time. Filtering on `on_*` alone reported Storm's Beacon - a
        whole shipped campaign - as having ZERO quests.
        """
        data = {"start_trigger": {"trigger": "on_signal", "data": {"name": "beacon_lit"}}}
        self.assertEqual(_goals_of(data), {"on_signal": {"name": "beacon_lit"}})

    def test_toast_actions_are_not_goals(self):
        """`On accept:` / `On complete:` are stage directions, not completion triggers.

        They parse to `on_accept` / `on_complete`, which start with `on_` - so a naive
        prefix filter marks every quest as having a goal, and every one as drivable.
        """
        data = {"on_accept": "toast hello", "on_complete": "toast bye"}
        self.assertEqual(_goals_of(data), {})

    def test_on_signal_is_not_drivable(self):
        self.assertIn("on_signal", GOAL_KEYS)
        self.assertNotIn("on_signal", DRIVABLE)


class CensusTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def _amd(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_key_is_relative_to_the_granted_section(self):
        """THE KEY MUST MATCH WHAT A RUN REPORTS, or it is useless in `expect:`.

        A mission grants either a whole document or one section of it, and both shapes are
        in the corpus. LM grants its job board as a section, so the live key is
        `job_barge` - emitting `jobs/job_barge` would hand the author a key that never
        matches. Verified against a real run, which reports `job_gunnery` and
        `florbin/trail`.
        """
        self._amd("m.amd", "\n".join([
            "# [Mission](mission)",
            "",
            "## [Jobs](jobs)",
            "",
            "### [Tow the Barge](job_barge)",
            "---",
            "Job",
            "Done when: signal barge_delivered",
            "---",
            "Haul it home.",
            "",
            "#### [Hail](hail)",
            "---",
            "Done when: signal ghost_hailed",
            "---",
            "Say hello.",
            "",
        ]))
        got = {q["key"]: q for q in census_quests(self.tmp)}
        self.assertIn("job_barge", got, f"expected a section-relative key, got {sorted(got)}")
        self.assertEqual(got["job_barge"]["section"], "jobs")
        # A nested arc step keeps its parent, because that is how the run names it.
        self.assertIn("job_barge/hail", got)

    def test_document_level_quest_keeps_its_bare_key(self):
        """Granted as a document, not a section - so there is no prefix to strip."""
        self._amd("m.amd", "\n".join([
            "# [Siege](siege_quests)",
            "",
            "## [Purge the Infestation](purge_infestation)",
            "---",
            "Done when: kill 5 monster",
            "---",
            "Clear them out.",
            "",
        ]))
        got = {q["key"]: q for q in census_quests(self.tmp)}
        self.assertIn("purge_infestation", got)
        self.assertIsNone(got["purge_infestation"]["section"])

    def test_drivable_flag(self):
        self._amd("m.amd", "\n".join([
            "# [Mission](mission)",
            "",
            "## [Scan Job](scan_job)",
            "---",
            "Done when: scan 3 anomaly",
            "---",
            "Scan them.",
            "",
            "## [Signal Job](signal_job)",
            "---",
            "Done when: signal thing_done",
            "---",
            "Wait for it.",
            "",
        ]))
        got = {q["key"]: q for q in census_quests(self.tmp)}
        self.assertTrue(got["scan_job"]["drivable"])
        self.assertFalse(got["signal_job"]["drivable"])

    def test_a_mission_with_no_amd_is_not_an_error(self):
        self.assertEqual(census_quests(self.tmp), [])


class ScenarioTextTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_scenario_parses_as_the_yaml_a_scenario_loader_expects(self):
        """A generated file must LOAD, or the generator has produced decoration.

        Round-tripped through the real loader rather than a yaml parse, so the field names
        are checked too.
        """
        from sbs_utils.fs import load_yaml_string
        from cosmos_dev.soak_manifest import SoakScenario
        text = build_scenario_text("my_map", "My Map", ["PLAYER_COUNT", "DIFFICULTY"], [])
        data = load_yaml_string(text)
        sc = SoakScenario(os.path.join(self.tmp, "my_map.yaml"), data)
        self.assertEqual(sc.map, "my_map")
        self.assertEqual(sc.accept, "all")
        self.assertTrue(sc.goals)
        self.assertTrue(sc.strict_blob)
        # The dwell default of 3 is a documented trap - watchers keyed to a one-second
        # tick fire zero times. A generated scenario must not ship it.
        self.assertGreaterEqual(sc.dwell, 10)

    def test_option_keys_are_listed_for_the_author(self):
        text = build_scenario_text("m", None, ["PLAYER_COUNT", "SIEGE_TIMEOUT"], [])
        self.assertIn("PLAYER_COUNT", text)
        self.assertIn("SIEGE_TIMEOUT", text)

    def test_census_marks_undrivable_goals(self):
        census = [{"key": "a", "section": None, "goals": {"on_signal": {}},
                   "drivable": False, "display": "A", "file": "m.amd"},
                  {"key": "b", "section": None, "goals": {"on_scan": {}},
                   "drivable": True, "display": "B", "file": "m.amd"}]
        text = build_scenario_text("m", None, [], census)
        self.assertIn("[drive] b", text)
        self.assertIn("2 declared, 1 with a goal", text)

    def test_write_does_not_clobber_an_edited_scenario(self):
        """Regenerating must never silently discard an author's work."""
        path, wrote = write_scenario(self.tmp, "m", "first")
        self.assertTrue(wrote)
        path2, wrote2 = write_scenario(self.tmp, "m", "second")
        self.assertEqual(path, path2)
        self.assertFalse(wrote2)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "first")
        _p, wrote3 = write_scenario(self.tmp, "m", "third", force=True)
        self.assertTrue(wrote3)


if __name__ == "__main__":
    unittest.main()
