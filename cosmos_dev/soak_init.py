"""Generate a starter soak scenario for a mission (dev-only).

WHAT THIS IS FOR. Writing the first scenario for a new quest mission is otherwise an
archaeology exercise: which map keys exist, which `settings:` a map actually honors, how
much of its board a pilot can even reach. All three are knowable without playing the
mission, so the tool should answer them rather than the author guessing.

WHAT IT CAN AND CANNOT KNOW - and the generated file says so too, because a census that
overstates itself is worse than none:

  * **Quest keys, nesting and goal triggers: static.** `amd_core.parse` returns the same
    tree `quest_grant_amd` walks at runtime, so the whole candidate board is readable from
    the `.amd` files. `sbs lint` already relies on this.
  * **Quests declared inside a loaded `.mastlib`: not seen.** The census walks the
    mission's OWN `.amd` files. A mission that inherits a quest arc from an addon (Storm's
    Beacon takes one from universe_core) will show fewer here than a run reports, and that
    is the tool being honest rather than wrong.
  * **Whether those quests are ever GRANTED: not static.** A mission decides at runtime
    whether to call `quest_grant_amd`, for which agent, and with what `count_scale`; a
    `Held by:` job needs a spawned landmark. So this is the CANDIDATE board. The realized
    one is what `QuestPilot.snapshot()` reports after a run.
  * **A map's option keys: static after a COMPILE.** `metadata:` is applied at compile
    time (`mast/core_nodes/label.py apply_metadata`), so the runner's own boot populates
    each map label's `Properties`, and `_map_property_vars` yields every `var="..."`
    binding - exactly the `settings:` keys that map honors. There is no `@map` text
    scraper anywhere and one should not be written.

THE POINT OF THE ANNOTATION. Every goal is listed as drivable or not. `on_signal` means
completion comes from the mission's own route, which the pilot will not synthesize (that
would test the harness instead of the mission), so an author can see at a glance how much
of the board a soak can reach before they run anything. On Peacetime that is 12 of 19 -
worth knowing up front rather than discovering it in a report.
"""
import glob
import os

# The real goal vocabulary. `amd_quest_data` also yields `on_accept` / `on_complete`,
# which are toast ACTIONS rather than completion triggers - counting them as goals would
# make every quest look drivable.
GOAL_KEYS = ("on_signal", "on_kill", "on_scan", "on_reach", "on_dock", "on_collect",
             "on_tow")
DRIVABLE = tuple(k for k in GOAL_KEYS if k != "on_signal")


def _fence_text(node):
    """The `---` fence of an AMD node as plain text.

    The quest FIELDS live in the fence; `body_lines` is the prose a player reads. Both
    come back as (lineno, text) pairs.
    """
    out = []
    for ln in (getattr(node, "fence_lines", None) or []):
        out.append(ln[1] if isinstance(ln, (tuple, list)) else str(ln))
    return "\n".join(out)


def _goals_of(data):
    """The goal triggers a parsed quest declares, `When:` included.

    A quest authored `When:`/`Starts when:` does NOT get a bare `on_*` key - the parser
    puts it under `start_trigger` as {"trigger": "on_signal", "data": {...}}, and
    `quest_driver._arm_start_trigger` swaps it for the real one at grant time. Filtering
    on `on_*` alone therefore reported a mission like Storm's Beacon as having ZERO
    quests, which is the kind of confident wrong answer that makes a tool worse than
    nothing.
    """
    goals = {k: v for k, v in (data or {}).items() if k in GOAL_KEYS}
    start = (data or {}).get("start_trigger")
    if isinstance(start, dict) and start.get("trigger") in GOAL_KEYS:
        goals.setdefault(start["trigger"], start.get("data") or {})
    return goals


def census_quests(mission_dir):
    """Every quest an `.amd` under `mission_dir` declares.

    Returns a list of dicts: `key` (the '/'-joined path `quest_mark_active` would take),
    `display`, `goals` ({goal_key: trigger}), `drivable` (bool), and `file`.
    """
    from sbs_utils.procedural.amd_core import parse
    from sbs_utils.procedural.amd_quest import amd_quest_data

    found = []
    for path in sorted(glob.glob(os.path.join(mission_dir, "**", "*.amd"), recursive=True)):
        try:
            doc = parse(None, file_path=path)
        except Exception:
            continue        # a broken .amd is `sbs lint`'s problem, not this tool's
        rel = os.path.relpath(path, mission_dir)

        def walk(node, prefix, section):
            for child in (node.children or []):
                key = f"{prefix}/{child.key}" if prefix else child.key
                data = {}
                try:
                    data = amd_quest_data(_fence_text(child)) or {}
                except Exception:
                    data = {}
                goals = _goals_of(data)
                if goals:
                    found.append({
                        "key": key,
                        "section": section,
                        "display": getattr(child, "display", None) or child.key,
                        "goals": goals,
                        "drivable": any(k in DRIVABLE for k in goals),
                        "file": rel,
                    })
                # The depth-1 node is the SECTION. Below it, keys are relative to that
                # section, because that is what a mission hands to `quest_grant_amd`.
                walk(child, key if section else "", section or child.key)

        # THE KEY A MISSION ACTUALLY USES IS RELATIVE TO WHAT IT GRANTED, and a mission
        # grants either the whole document or one section of it. Both shapes are in the
        # corpus: LM's siege quests are granted as a document (`purge_infestation`), its
        # job board as a section (`quest_grant_amd(p.id, amd_section(PR_DOC, "jobs"))`,
        # so the live key is `job_barge`, NOT `jobs/job_barge`). Emitting the full path
        # would hand the author a key that never matches anything in `expect:`.
        #
        # So: record the key relative to the depth-1 section, and carry the section name
        # separately for the comment. Verified against a live run - the pilot reports
        # `florbin/trail` and `job_gunnery`, which is exactly what this produces.
        for title in (doc.root.children or []):
            walk(title, "", None)
    return found


def _census_comment(census):
    """The census, rendered as the comment block that heads a generated scenario."""
    if not census:
        return ["# No quests found in this mission's .amd files. The pilot will still",
                "# exercise selections, comms and consoles, but `expect:` has nothing to",
                "# ratchet on - consider whether a soak is the right tool here."]
    drivable = [q for q in census if q["drivable"]]
    lines = [
        f"# QUEST CENSUS - {len(census)} declared, {len(drivable)} with a goal the pilot",
        "# can drive directly. This is the CANDIDATE board: whether a mission actually",
        "# grants a quest is a runtime decision, so treat it as an upper bound.",
        "#",
    ]
    for q in sorted(census, key=lambda q: (q.get("section") or "", q["key"]))[:60]:
        kinds = ",".join(sorted(q["goals"]))
        mark = "drive" if q["drivable"] else " ---- "
        sect = f"  (in '{q['section']}')" if q.get("section") else ""
        lines.append(f"#   [{mark}] {q['key']:<30} {kinds}{sect}")
    if len(census) > 60:
        lines.append(f"#   ... and {len(census) - 60} more")
    lines += [
        "#",
        "# `----` means the goal is `on_signal`: completion comes from the mission's own",
        "# route, and the pilot will NOT fire it - synthesizing that would test the",
        "# harness rather than the mission. Those are reached, if at all, by the world",
        "# sweeps and the comms walk, and are reported as NOT DRIVABLE rather than failed.",
        "#",
        "# Keys are written the way a RUN reports them - relative to the section the",
        "# mission grants - so they can be pasted straight into `expect:`.",
    ]
    return lines


def build_scenario_text(map_path, map_display, prop_vars, census, seconds=600, seed=7):
    """The scenario file, as text. Heavily commented on purpose - see peacetime.yaml."""
    lines = [
        f"# Soak scenario for @map/{map_path}" + (f' ("{map_display}")' if map_display else ""),
        "#",
        "# Generated by `mission_runner --soak-init`. Edit freely; the comments below are",
        "# what the generator could work out, not rules.",
        "#",
        "# Run it:   python -m cosmos_dev.tools.mission_soak <mission> "
        f"{map_path} --runs 3",
        "#",
        "# NOTE: a soak truncates mast.runtime.log in the mission directory, so the",
        "# supervisor runs against an auto-managed copy. Do not point a run at a folder",
        "# somebody is playing in the engine.",
        "",
        f"map: {map_path}",
        f"seed: {seed}",
        f"seconds: {seconds}",
        "",
    ]

    if prop_vars:
        lines += [
            "# Every option this map exposes, straight from its `Properties:` metadata.",
            "# These are the ONLY setting keys it honors; anything else is silently inert.",
            "settings:",
        ]
        for v in prop_vars:
            lines.append(f"  # {v}:")
        lines += [
            "  # Autoplay is the greedy combat bot, and it is what made --runs soaks",
            "  # diverge. The pilot drives instead.",
            "  AUTO_PLAY:",
            "    enable: false",
            "",
        ]
    else:
        lines += ["settings:",
                  "  AUTO_PLAY:",
                  "    enable: false",
                  ""]

    lines += [
        "drive:",
        "  accept_quests: all      # quest_mark_active - the Accept button's whole body",
        "  goals: true             # drive each active quest's declared goal",
        "  consoles: [helm, weapons, engineering, comms, science]",
        "  # NOT the default of 3. At dwell 3 a console is swapped away in under a",
        "  # sim-second, so `on change` watchers keyed to a one-second tick fire exactly",
        "  # zero times - which is how a NameError in a watcher reached a real engine",
        "  # session under a green headless run. Budget dwell x (5 + extras) / 3 seconds.",
        "  dwell: 20",
        "",
    ]
    lines += _census_comment(census)
    lines += [
        "",
        "expect:",
        "  # Deliberately empty. The ratchet in <name>.baseline.json is the real demand,",
        "  # and it only ever holds what runs have actually achieved. Naming things here",
        "  # that the harness has never reached makes the soak red every morning, and a",
        "  # check people ignore is worse than no check.",
        "  #",
        "  # Build it instead:  ... --soak-bless   (a few runs; the baseline demands only",
        "  # what EVERY blessed run reached, so blessing more runs relaxes flaky items).",
        "  quests_complete: []",
        "",
        "  # A route named HERE is a contract: if it is not entered, the run fails, with",
        "  # no tolerance. This is the right home for a path you know matters - the",
        "  # grav-tether NameError lived behind a //damage/object route nothing headless",
        "  # ever entered, so every run passed for months.",
        "  routes_covered: []",
        "",
        "  # How many routes the BASELINE learned may go missing before it counts as a",
        "  # regression. Some are probabilistic (a surrender needs shields below half",
        "  # inside the window), and failing on those is how a check becomes noise.",
        "  route_tolerance: 3",
        "  game_end: none",
        "",
        "# The engine answers None for a data_set field nobody set; the mock answers a",
        "# typed default. That gap is how two crashes shipped green.",
        "strict_blob: true",
        "",
    ]
    return "\n".join(lines)


def maps_already_covered(mission_dir):
    """Map keys some existing scenario already targets.

    Keyed on each scenario's `map:` field rather than its FILENAME, because a
    hand-written scenario is usually named for the job it does rather than for the map -
    `peacetime.yaml` drives `peacetime_remastered`. Checking filenames only meant
    regenerating produced a second scenario for a map that already had one, which is not
    an overwrite but is just as unhelpful.
    """
    covered = {}
    soaks = os.path.join(mission_dir, "soaks")
    if not os.path.isdir(soaks):
        return covered
    from sbs_utils.fs import load_yaml_string
    for fn in sorted(os.listdir(soaks)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(soaks, fn)
        try:
            with open(path, encoding="utf-8") as f:
                data = load_yaml_string(f.read()) or {}
        except Exception:
            continue
        m = data.get("map")
        if m:
            covered.setdefault(str(m), fn)
    return covered


def write_scenario(mission_dir, map_path, text, force=False):
    """Write `<mission>/soaks/<map_path>.yaml`. Returns (path, written)."""
    soaks = os.path.join(mission_dir, "soaks")
    os.makedirs(soaks, exist_ok=True)
    safe = str(map_path).replace("/", "_")
    path = os.path.join(soaks, f"{safe}.yaml")
    if os.path.exists(path) and not force:
        return path, False
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, True
