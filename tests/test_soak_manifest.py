"""Tests for the soak scenario manifest and its ratcheting baseline.

The ratchet is the part worth testing hard: it decides what turns a green run red at
three in the morning, and both ways of getting it wrong are bad. Too strict and the soak
is red every night and gets ignored; too loose and a regression slides through. The cases
below pin the exact boundary - in particular that a goal the pilot CANNOT drive never
fails a run, and that the demand is what EVERY blessed run reached rather than what any
of them ever reached.
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.soak_manifest import SoakScenario, check_expectations, load_scenario


def _scenario(tmp, **data):
    path = os.path.join(tmp, "s.yaml")
    open(path, "w", encoding="utf-8").close()
    return SoakScenario(path, data)


class CheckExpectationsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def _baseline(self, sc, runs=1, **data):
        """Write a baseline in the CURRENT (counted) shape: seen in every blessed run."""
        payload = {"runs": runs}
        for k, v in data.items():
            payload[k] = {item: runs for item in v}
        with open(sc.baseline_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def test_no_expectations_and_no_baseline_passes(self):
        """A brand new scenario demands nothing - it has never seen anything work."""
        sc = _scenario(self.tmp)
        fails, result = check_expectations(sc, {"complete": ["a"]}, {"damage/object"}, None)
        self.assertEqual(fails, [])
        self.assertEqual(result["quests_complete"], ["a"])

    def test_declared_quest_is_enforced_immediately(self):
        sc = _scenario(self.tmp, expect={"quests_complete": ["job_barge"]})
        fails, _ = check_expectations(sc, {"complete": []}, set(), None)
        self.assertEqual(len(fails), 1)
        self.assertIn("job_barge", fails[0])

    def test_baseline_quest_regression_fails(self):
        """The ratchet: something that completed before and does not now is a failure."""
        sc = _scenario(self.tmp)
        self._baseline(sc, quests_complete=["job_gunnery"])
        fails, _ = check_expectations(sc, {"complete": []}, set(), None)
        self.assertTrue(any("job_gunnery" in f for f in fails))

    def test_a_DECLARED_route_is_a_contract(self):
        """The case that would have caught the grav-tether NameError.

        `LM_TETHER_BREAK_DAMAGE` lived behind a `//damage/object` route nothing headless
        ever entered, so every run passed. A route somebody wrote into `expect:` fails on
        a single absence - no tolerance, because writing it down IS the assertion.
        """
        sc = _scenario(self.tmp, expect={"routes_covered": ["damage/object"]})
        fails, _ = check_expectations(sc, {"complete": []}, {"comms"}, None)
        self.assertTrue(any("damage/object" in f for f in fails), fails)

    def test_baseline_drift_within_tolerance_passes(self):
        """A few baseline routes may vanish without meaning anything.

        Some routes are probabilistic - `pr_poacher_surrender` needs a poacher's shields
        below half inside the window. Measured: with EIGHT blessed runs, one fresh run in
        three still lost one. Failing on that is how a check becomes noise.
        """
        sc = _scenario(self.tmp)
        self._baseline(sc, routes_covered=["a", "b", "c", "d", "e"])
        fails, _ = check_expectations(sc, {"complete": []}, {"a", "b"}, None)
        self.assertEqual(fails, [], "3 missing is within the default tolerance")

    def test_baseline_drift_beyond_tolerance_fails(self):
        """A collapse is still a collapse."""
        sc = _scenario(self.tmp)
        self._baseline(sc, routes_covered=["a", "b", "c", "d", "e"])
        fails, _ = check_expectations(sc, {"complete": []}, {"a"}, None)
        self.assertTrue(any("previously covered" in f for f in fails), fails)

    def test_tolerance_is_configurable(self):
        sc = _scenario(self.tmp, expect={"route_tolerance": 0})
        self._baseline(sc, routes_covered=["a", "b"])
        fails, _ = check_expectations(sc, {"complete": []}, {"a"}, None)
        self.assertTrue(any("previously covered" in f for f in fails), fails)

    def test_a_declared_route_is_not_excused_by_the_tolerance(self):
        """Declared and drifted are counted separately, so a contract cannot hide in the
        allowance."""
        sc = _scenario(self.tmp, expect={"routes_covered": ["must"], "route_tolerance": 9})
        self._baseline(sc, routes_covered=["must", "a"])
        fails, _ = check_expectations(sc, {"complete": []}, {"a"}, None)
        self.assertTrue(any("must" in f for f in fails), fails)

    def test_route_still_covered_passes(self):
        sc = _scenario(self.tmp, expect={"routes_covered": ["damage/object"]})
        self._baseline(sc, routes_covered=["damage/object"])
        fails, _ = check_expectations(
            sc, {"complete": []}, {"damage/object", "comms"}, None)
        self.assertEqual(fails, [])

    def test_undrivable_goal_never_fails_the_run(self):
        """A quest the pilot structurally cannot drive is a HARNESS limit, not a bug.

        `on_signal` completion comes from the mission's own route; synthesizing it would
        test the harness instead of the mission. Such quests are reported as NOT DRIVABLE
        and must not turn the build red, or every soak of a real job board is red forever.
        """
        sc = _scenario(self.tmp, expect={"quests_complete": ["job_barge"]})
        snap = {"complete": [], "unreachable": {"job_barge": "on_signal"}}
        fails, _ = check_expectations(sc, snap, set(), None)
        self.assertEqual(fails, [])

    def test_game_end_expectation(self):
        sc = _scenario(self.tmp, expect={"game_end": "win"})
        fails, _ = check_expectations(sc, {"complete": []}, set(), None)
        self.assertTrue(any("did not end" in f for f in fails))

        fails, _ = check_expectations(sc, {"complete": []}, set(), ("lost", False))
        self.assertTrue(any("ended in lose" in f for f in fails))

        fails, _ = check_expectations(sc, {"complete": []}, set(), ("won", True))
        self.assertEqual(fails, [])

    def test_game_end_none_is_not_checked(self):
        sc = _scenario(self.tmp, expect={"game_end": "none"})
        fails, _ = check_expectations(sc, {"complete": []}, set(), None)
        self.assertEqual(fails, [])


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_bless_demands_only_what_EVERY_run_reached(self):
        """The ratchet is an intersection, and this is the case that made it one.

        Union demanded everything ever seen, so a baseline blessed from one run reported
        17 routes as regressed on the next - all ordinary variance. Here `a` and `r1`
        appeared once each across two blessed runs, so neither is demanded; `b` appeared
        in both and is.
        """
        sc = _scenario(self.tmp)
        sc.save_baseline({"quests_complete": ["a", "b"], "routes_covered": ["r1"]})
        sc.save_baseline({"quests_complete": ["b", "c"], "routes_covered": []})
        quests, routes = sc.demanded()
        self.assertEqual(quests, {"b"})
        self.assertEqual(routes, set())
        self.assertEqual(sc.load_baseline()["runs"], 2)

    def test_bless_never_forgets_what_it_saw(self):
        """Relaxing the DEMAND is not the same as losing the evidence.

        The counts stay in the file, so a flaky item is visible as flaky rather than
        vanishing - which is what makes it possible to tell "never reached" from
        "reached 3 times in 5".
        """
        sc = _scenario(self.tmp)
        sc.save_baseline({"quests_complete": ["a", "b"], "routes_covered": []})
        sc.save_baseline({"quests_complete": ["b"], "routes_covered": []})
        counts = sc.load_baseline()["quests_complete"]
        self.assertEqual(counts, {"a": 1, "b": 2})

    def test_a_single_blessed_run_demands_all_of_it(self):
        sc = _scenario(self.tmp)
        sc.save_baseline({"quests_complete": ["a"], "routes_covered": ["r1"]})
        self.assertEqual(sc.demanded(), ({"a"}, {"r1"}))

    def test_legacy_list_baseline_still_demanded(self):
        """An older baseline file has no run count; everything it lists was required."""
        sc = _scenario(self.tmp)
        with open(sc.baseline_path, "w", encoding="utf-8") as f:
            json.dump({"quests_complete": ["a"], "routes_covered": ["r1"]}, f)
        self.assertEqual(sc.demanded(), ({"a"}, {"r1"}))

    def test_blessing_over_a_legacy_baseline_keeps_its_demands(self):
        """Migration must not quietly drop what the old file already demanded."""
        sc = _scenario(self.tmp)
        with open(sc.baseline_path, "w", encoding="utf-8") as f:
            json.dump({"quests_complete": ["a"], "routes_covered": []}, f)
        sc.save_baseline({"quests_complete": ["a"], "routes_covered": []})
        self.assertEqual(sc.demanded()[0], {"a"})

    def test_baseline_records_the_shortest_blessed_duration(self):
        """A baseline is only meaningful for a run at least as long as the ones behind it."""
        sc = _scenario(self.tmp)
        sc.save_baseline({"quests_complete": [], "routes_covered": [], "seconds": 600})
        sc.save_baseline({"quests_complete": [], "routes_covered": [], "seconds": 90})
        self.assertEqual(sc.load_baseline()["seconds"], 90)

    def test_short_run_against_a_long_baseline_is_flagged(self):
        """The false alarm that teaches people to ignore a soak.

        A 60s run against a 90s baseline reported a route as regressed purely for lack of
        time. The regression still shows - it might be real - but it is labelled unproven.
        """
        from cosmos_dev.soak_manifest import baseline_duration_warning
        sc = _scenario(self.tmp)
        sc.save_baseline({"quests_complete": [], "routes_covered": [], "seconds": 90})
        self.assertIsNotNone(baseline_duration_warning(sc, 60))
        self.assertIsNone(baseline_duration_warning(sc, 90))
        self.assertIsNone(baseline_duration_warning(sc, 600))

    def test_no_duration_recorded_means_no_warning(self):
        from cosmos_dev.soak_manifest import baseline_duration_warning
        sc = _scenario(self.tmp)
        sc.save_baseline({"quests_complete": [], "routes_covered": []})
        self.assertIsNone(baseline_duration_warning(sc, 30))

    def test_missing_baseline_reads_as_empty(self):
        sc = _scenario(self.tmp)
        self.assertEqual(sc.load_baseline(), {})


class LoadScenarioTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_missing_scenario_returns_none(self):
        self.assertIsNone(load_scenario(self.tmp, "nope"))

    def test_loads_and_defaults(self):
        soaks = os.path.join(self.tmp, "soaks")
        os.makedirs(soaks)
        with open(os.path.join(soaks, "demo.yaml"), "w", encoding="utf-8") as f:
            f.write("map: m1\nseed: 3\nseconds: 45\n"
                    "drive:\n  dwell: 20\n  consoles: [helm]\n"
                    "expect:\n  routes_covered: [damage/object]\n")
        sc = load_scenario(self.tmp, "demo")
        self.assertEqual(sc.map, "m1")
        self.assertEqual(sc.seed, 3)
        self.assertEqual(sc.dwell, 20)
        self.assertEqual(sc.consoles, ["helm"])
        self.assertEqual(sc.expect_routes, ["damage/object"])
        # strict_blob defaults ON for a scenario: the engine answers None where the mock
        # answers a typed default, and that gap shipped two crashes.
        self.assertTrue(sc.strict_blob)
        # Accepting every offered quest is the default, because a board nobody accepts is
        # the exact thing the pilot exists to reach.
        self.assertEqual(sc.accept, "all")


if __name__ == "__main__":
    unittest.main()
