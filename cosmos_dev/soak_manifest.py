"""Per-mission soak scenarios and the ratcheting baseline (dev-only).

WHY A FILE PER SCENARIO. A soak today is a hand-assembled command line, and the flags
that matter are the ones easiest to leave off: `--exercise-dwell` defaults to 3, at which
a watcher keyed to a one-second tick fires ZERO times, so a run can be green and have
executed none of the code you meant to test. A scenario file makes the settings part of
the mission, reviewable in a diff, and identical between the person running it tonight
and CI running it next month.

WHAT `expect:` ADDS. Today a run passes when nothing raised. That is not the same as the
mission working: a run that completed no quest, entered no comms route and ended nothing
at all still prints PASS. `expect:` is the positive half - the quests that should finish,
the routes that must be entered.

DECLARED VERSUS DRIFTED, and the distinction is what keeps this usable. A route named in
`expect.routes_covered` is a CONTRACT - one missing fails the run, no tolerance. A route
that merely appeared in past runs is a DRIFT signal, and a few may go missing without
meaning anything: `pr_poacher_surrender` needs a poacher's shields below half inside the
window, so it fires most runs and not all. Measured, with eight blessed runs, one fresh
run in three still lost a route. `expect.route_tolerance` (default 3) is that allowance.
Quests are not tolerated this way - they are discrete and few, and a quest that stops
completing means something.

WHY A RATCHET AND NOT A FIXED LIST. A long mission does not finish everything every run,
so an absolute manifest would be red most mornings and get ignored - the failure mode
every noisy check reaches eventually. The baseline records what runs have ACTUALLY
achieved; a later run fails only when it achieves less.

AND WHY IT IS AN INTERSECTION, NOT A UNION. The first version unioned each blessed run in,
which demands EVERYTHING EVER SEEN. Measured: a baseline blessed from a single run then
reported 17 routes as regressed on the next one, all of it ordinary variance. What a
ratchet wants is what is RELIABLY achieved, so the baseline keeps a run count plus a
per-item seen count and demands only the items seen in EVERY blessed run. Blessing more
runs therefore RELAXES a flaky item and keeps a dependable one - the right direction, and
the opposite of what union did.

It still cannot drift down on its own: counts change only when somebody runs
--soak-bless. An ordinary failing run never edits the baseline.

THE ROUTE HALF IS THE ONE THAT WOULD HAVE CAUGHT THE TETHER BUG. `LM_TETHER_BREAK_DAMAGE`
was a Python module constant that the MAST namespace never exported, so the grav-tether
`//damage/object` route raised a NameError on every hit - once per shot, for the rest of
the mission. Nothing headless ever shot a ship that was towing, so the route was never
entered and every run reported PASS. Coverage knew; nothing asked it.
"""
import json
import os


class SoakScenario:
    """One named scenario: how to run the mission, and what to expect of it."""

    def __init__(self, path, data):
        self.path = path
        self.name = os.path.splitext(os.path.basename(path))[0]
        d = data or {}
        self.map = d.get("map")
        self.profile = d.get("profile")
        self.seed = d.get("seed")
        self.seconds = d.get("seconds")
        self.runs = int(d.get("runs", 1) or 1)
        self.settings = d.get("settings") or {}
        self.strict_blob = bool(d.get("strict_blob", True))
        drive = d.get("drive") or {}
        self.accept = drive.get("accept_quests", "all")
        self.goals = bool(drive.get("goals", True))
        self.consoles = drive.get("consoles") or []
        self.dwell = drive.get("dwell")
        self.clicks = drive.get("clicks") or []
        expect = d.get("expect") or {}
        self.expect_quests = list(expect.get("quests_complete") or [])
        self.expect_routes = list(expect.get("routes_covered") or [])
        self.expect_game_end = expect.get("game_end")
        # How many BASELINE routes may go missing before a run is called a regression.
        # Declared routes are never subject to this - see check_expectations.
        self.route_tolerance = int(expect.get("route_tolerance", 3) or 0)

    # -- baseline ---------------------------------------------------------------
    @property
    def baseline_path(self):
        return os.path.join(os.path.dirname(self.path), self.name + ".baseline.json")

    def load_baseline(self):
        try:
            with open(self.baseline_path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def demanded(self):
        """(quests, routes) the baseline actually requires: seen in EVERY blessed run.

        Also reads the original list-shaped baseline, which had no run count and simply
        required everything listed, so an existing file keeps working.
        """
        base = self.load_baseline()
        runs = int(base.get("runs", 0) or 0)

        def pick(key):
            val = base.get(key)
            if isinstance(val, dict):
                return {k for k, n in val.items() if int(n or 0) >= runs}
            return set(val or ())        # legacy list form
        return pick("quests_complete"), pick("routes_covered")

    def save_baseline(self, result):
        """Fold one run into the ratchet. Only ever called on an explicit --soak-bless.

        Counts, not sets: an item must appear in every blessed run to be demanded, so
        blessing a second run RELAXES whatever the first reached by luck. See the module
        docstring for why union was wrong.
        """
        base = self.load_baseline()
        runs = int(base.get("runs", 0) or 0)

        def fold(key):
            prev = base.get(key)
            if isinstance(prev, dict):
                counts = {k: int(n or 0) for k, n in prev.items()}
            else:
                # Migrating a legacy list: it was required, so treat it as seen in every
                # run so far. Never silently drops what the old file demanded.
                counts = {k: runs for k in (prev or ())}
            for item in (result.get(key) or ()):
                counts[item] = counts.get(item, 0) + 1
            return dict(sorted(counts.items()))

        # Record the SHORTEST duration ever blessed. A baseline is only meaningful for a
        # run at least as long as the ones that produced it: a shorter run legitimately
        # reaches less, and reporting that as regression is the false alarm that teaches
        # people to ignore the soak. Measured - a 60s run against a 90s baseline reported
        # `explore_nebula` as regressed purely for lack of time.
        secs = result.get("seconds")
        prev_secs = base.get("seconds")
        if secs and prev_secs:
            secs = min(float(secs), float(prev_secs))
        elif not secs:
            secs = prev_secs
        merged = {"runs": runs + 1,
                  "seconds": secs,
                  "quests_complete": fold("quests_complete"),
                  "routes_covered": fold("routes_covered")}
        tmp = self.baseline_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(merged, indent=2) + "\n")
        os.replace(tmp, self.baseline_path)
        return self.baseline_path


def load_scenario(mission_folder, name):
    """Load `<mission>/soaks/<name>.yaml`. Returns None when there is none.

    `soaks/`, not `soak/`: LegendaryMissions already has a `soak/` ADDON that churns the
    pre-start window, and a scenario file sitting inside it reads like configuration for
    that addon rather than for the harness.

    Raises only for a file that exists and cannot be read - a scenario that is present
    but broken must not be silently treated as absent, because the run would then quietly
    become an ordinary unasserted `--test`.
    """
    if not name:
        return None
    path = name
    if not os.path.isabs(path) or not os.path.isfile(path):
        cand = os.path.join(mission_folder, "soaks", name)
        for p in (cand, cand + ".yaml", cand + ".yml"):
            if os.path.isfile(p):
                path = p
                break
        else:
            return None
    from sbs_utils.fs import load_yaml_string
    with open(path, encoding="utf-8") as f:
        data = load_yaml_string(f.read())
    return SoakScenario(path, data)


def baseline_duration_warning(scenario, ran_seconds):
    """A caution when this run was SHORTER than the runs the baseline was blessed from.

    Returned rather than raised: a short run is a legitimate thing to do (a quick check
    before a long soak), it just cannot be judged against a longer baseline. Saying so is
    what separates "this regressed" from "you did not give it time".
    """
    base = scenario.load_baseline()
    blessed = base.get("seconds")
    if not blessed or not ran_seconds:
        return None
    if float(ran_seconds) >= float(blessed):
        return None
    return (f"this run was {float(ran_seconds):g}s but the baseline was blessed from runs "
            f"of at least {float(blessed):g}s - a shorter run reaches less, so treat any "
            f"regression below as unproven")


def check_expectations(scenario, quest_snapshot, covered_routes, game_end):
    """Compare a finished run against the scenario and its baseline.

    Returns (failures, result) - `failures` is a list of human-readable strings (empty
    means pass), `result` is what this run achieved, for the baseline.

    Both halves are checked the same way: the DEMAND is what the scenario declares, plus
    what the baseline has seen in EVERY blessed run. So an explicit expectation is
    enforced from day one, while everything else only has to not regress - and only if it
    has proven itself repeatable.
    """
    complete = set(quest_snapshot.get("complete") or ())
    # A goal the pilot structurally cannot drive is not a mission failure. Excusing them
    # here (rather than never recording them) keeps the report honest: they are listed as
    # NOT DRIVABLE in the run output, they just do not fail the build.
    unreachable = set((quest_snapshot.get("unreachable") or {}).keys())
    routes = set(covered_routes or ())

    base_quests, base_routes = scenario.demanded()
    want_quests = set(scenario.expect_quests) | base_quests

    failures = []
    missing_q = sorted((want_quests - complete) - unreachable)
    if missing_q:
        failures.append("quest(s) that previously completed did not this run: "
                        + ", ".join(missing_q))
    # TWO KINDS OF ROUTE DEMAND, because they answer different questions.
    #
    # A DECLARED route is a contract: somebody wrote it down because that path matters
    # (the grav-tether `//damage/object` NameError lived behind a route nothing entered).
    # One missing is a failure, always.
    #
    # A BASELINE route is a drift detector, and some routes are simply probabilistic -
    # `pr_poacher_surrender` needs a poacher's shields to fall below half inside the run
    # window. Measured: even with EIGHT blessed runs, one fresh run in three lost a route
    # to ordinary variance. Failing on that teaches people to ignore the soak, so the
    # baseline half tolerates a few and reports the number either way.
    declared_missing = sorted(set(scenario.expect_routes) - routes)
    if declared_missing:
        failures.append("declared route(s) not entered: " + ", ".join(declared_missing))
    drift = sorted((base_routes - routes) - set(scenario.expect_routes))
    if drift and len(drift) > scenario.route_tolerance:
        failures.append(
            f"{len(drift)} route(s) previously covered were not entered "
            f"(tolerance {scenario.route_tolerance}): " + ", ".join(drift[:15])
            + (" ..." if len(drift) > 15 else ""))
    want_end = scenario.expect_game_end
    if want_end and want_end != "none":
        if game_end is None:
            failures.append(f"mission did not end (expected game_end: {want_end})")
        elif want_end in ("win", "lose"):
            _msg, is_win = game_end
            got = "win" if is_win else "lose"
            if got != want_end:
                failures.append(f"mission ended in {got}, expected {want_end}")

    result = {"quests_complete": sorted(complete), "routes_covered": sorted(routes)}
    return failures, result
