"""Signal-route linter: flag side-effects inside `//signal/<name>` routes.

A `//signal` route runs ONCE PER CONNECTED CONSOLE (plus the server); only
`//shared/signal` runs server-only-once (see mastscheduler + SIGNAL_ROUTING.md). So a
`//signal` route that SPAWNS, applies a MODIFIER/REWARD, changes QUEST state, SAVES, or
rolls RANDOM duplicates per console - the classic "boss spawned once per console" bug.

This scans .mast source for those side-effect calls inside a `//signal` route body and
returns WARNINGs (advisory - the author confirms it's display-only or converts it). It is
deliberately HIGH-SIGNAL (a short, unambiguous call list) so a hit means something. Reuses
amd_lint's AmdFinding so `sbs lint` prints signal + AMD findings uniformly.
"""
import re
from .amd_lint import AmdFinding, WARNING, _source_lines

# Call patterns that duplicate per console. Kept short + unambiguous on purpose.
_SIDE_EFFECTS = [
    (re.compile(r"\b\w*_spawn\s*\("),                                    "spawn",      "a spawn"),
    (re.compile(r"\bmodifier_add\s*\("),                                 "modifier",   "modifier_add"),
    (re.compile(r"\breputation_apply\s*\("),                             "reputation", "reputation_apply"),
    (re.compile(r"\bquest_(?:mark|on|grant|add|complete|fail)\w*\s*\("), "quest",      "a quest-state change"),
    (re.compile(r"\b(?:universe_save\w*|save_json_data)\s*\("),          "save",       "a save"),
    (re.compile(r"\brandom\.\w+\s*\("),                                  "random",     "random.* (each console rolls independently)"),
    (re.compile(r"\btask_schedule\s*\("),                                "ticker",     "task_schedule (starts a task/ticker per console)"),
]

# A column-0 line that starts a new top-level route/label (ends the current //signal body).
_STRUCT = re.compile(r"^(//|=|@|-{3,})")

# Second axis (see SIGNAL_ROUTING.md): //shared/signal fixes WHERE a route runs, not HOW
# MANY TIMES the signal is emitted. An init route that creates things without a key
# duplicates them when its signal is emitted twice - two addons emitting it, a
# copy-pasted emit, an emit inside a loop, a double-clicked Start button.
_INIT_NAME = re.compile(r"^(?:create|init|setup)_", re.I)
_LOOP = re.compile(r"^(?:for|while)\b")
_EMIT = re.compile(r"\bsignal_emit\s*\(\s*[\"'](?P<name>[A-Za-z0-9_]+)[\"']")
_SPAWN = re.compile(r"\b\w*_spawn\s*\(")
# A keyed create is idempotent, so it is the FIX, not the bug. `*_ensure` by name, plus
# the side prefabs: a side is keyed by definition (side_create -> side_ensure, one agent
# per key) and re-declaring it is a REPAIR, so `prefab_spawn(prefab_side_generic, ...)`
# in a create_sides route is correct rather than a duplication risk.
_KEYED = re.compile(r"\b\w*_ensure\s*\(|\bprefab_side\w*")


def _signal_route_name(stripped):
    """The name from a `//signal/<name>[ if ...]` header, or None when the line is not a
    plain //signal route (`//shared/signal/...` and `///inline` are NOT plain //signal)."""
    if not stripped.startswith("//signal/"):
        return None
    rest = stripped[len("//signal/"):].split()
    return rest[0] if rest else "?"


def _init_route_name(stripped):
    """The name from a `//shared/signal/<name>` header when the name looks like an
    initializer (create_*/init_*/setup_*) AND the route is not already `once`-guarded."""
    if not stripped.startswith("//shared/signal/"):
        return None
    parts = stripped[len("//shared/signal/"):].split()
    if not parts:
        return None
    if "once" in parts[1:]:
        return None   # author declared it one-shot; re-emission cannot duplicate
    return parts[0] if _INIT_NAME.match(parts[0]) else None


# `# lint: allow [code ...]` on the line ABOVE excuses the next line. A comment rather
# than a trailing marker because MAST parses line by line and a trailing `#` on a call is
# not reliably a comment.
#
# It exists because the alternative is worse. `//signal/show_game_results` schedules
# save_game_results_yaml once per console, which is exactly what the ticker rule
# describes - but that task opens with `default shared RESULTS_SAVED` and returns
# immediately when set, so it writes once however many consoles fire it. The rule cannot
# see a guard inside the task it is pointing at, and a linter that flags correct code
# teaches people to stop reading it.
_ALLOW = re.compile(r"^#\s*lint:\s*allow(?P<codes>.*)$", re.I)


def signal_lint(file_path=None, content=None):
    """Return [AmdFinding] (all WARNING) for side-effects inside `//signal` routes in one
    .mast source. See the module docstring + SIGNAL_ROUTING.md."""
    lines = _source_lines(file_path, content)
    findings = []
    cur = None        # name of the //signal route currently open, else None
    cur_init = None   # name of the unguarded //shared/signal init route open, else None
    loops = []        # indents of for/while headers still open
    allow = None      # codes a `# lint: allow` comment excuses on the NEXT line
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            m = _ALLOW.match(stripped)
            if m:
                # Bare `# lint: allow` excuses everything on the next line; naming codes
                # excuses only those.
                allow = {c.strip() for c in m.group("codes").replace(",", " ").split()}
            continue
        indent = len(line) - len(line.lstrip())
        while loops and indent <= loops[-1]:
            loops.pop()
        # A column-0 structural line ends the current body and maybe opens a new one.
        if not line[:1].isspace() and _STRUCT.match(stripped):
            cur = _signal_route_name(stripped)
            cur_init = _init_route_name(stripped)
            loops.clear()
            continue

        # Loop tracking is GLOBAL, not scoped to a route body: the emit-in-loop case
        # that shipped was in a plain `===` label, not a signal route.
        if _LOOP.match(stripped):
            loops.append(indent)

        # An INIT emit inside a loop fires N times - setup runs N times. Scoped to
        # init-shaped names on purpose: emitting a per-item signal from a loop
        # (quest_signal, fabricate, nebula_within_change) is a normal, correct pattern,
        # so flagging every emit-in-loop was pure noise.
        def _excused(code):
            return allow is not None and (not allow or code in allow)

        emit = _EMIT.search(line)
        if emit and loops and _INIT_NAME.match(emit.group("name")) and not _excused("signal-emit-in-loop"):
            findings.append(AmdFinding(
                i, WARNING, "signal-emit-in-loop",
                "signal_emit(\"" + emit.group("name") + "\") is inside a loop - its "
                "routes run once per iteration. Emit once after the loop, or make the "
                "handler idempotent (*_ensure). See SIGNAL_ROUTING.md"))

        # An init route that creates without a key duplicates on a second emit.
        if (cur_init and _SPAWN.search(line) and not _KEYED.search(line)
                and not _excused("signal-init-unkeyed-spawn")):
            findings.append(AmdFinding(
                i, WARNING, "signal-init-unkeyed-spawn",
                "//shared/signal/" + cur_init + " spawns without a stable key - a second "
                "emit duplicates it. Use a keyed create (player_ensure/side_ensure) so a "
                "re-emit is a no-op, or mark the route `once`. See SIGNAL_ROUTING.md"))

        if cur is None:
            allow = None
            continue
        for rx, code, human in _SIDE_EFFECTS:
            if rx.search(line) and not _excused("signal-side-effect-" + code):
                findings.append(AmdFinding(
                    i, WARNING, "signal-side-effect-" + code,
                    "//signal/" + cur + " calls " + human + " - runs once PER console; use "
                    "//shared/signal (or split: shared does it + emits a display signal). "
                    "See SIGNAL_ROUTING.md"))
                break   # one finding per line
        allow = None        # a directive excuses exactly one line
    return findings


def _scan_project_file(content):
    """(emit_sites, unguarded_init_routes) for one source: `[(name, line)]` and the set
    of unguarded `//shared/signal/<init>` route names whose body spawns without a key."""
    emit_sites = []
    init_routes = set()
    cur_init = None
    allow = None        # `# lint: allow` excuses the next line here too
    for i, raw in enumerate(_source_lines(None, content), start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            m = _ALLOW.match(stripped)
            if m:
                allow = {c.strip() for c in m.group("codes").replace(",", " ").split()}
            continue
        if not line[:1].isspace() and _STRUCT.match(stripped):
            cur_init = _init_route_name(stripped)
            allow = None
            continue
        m = _EMIT.search(line)
        if m:
            emit_sites.append((m.group("name"), i))
        excused = allow is not None and (not allow or "signal-init-unkeyed-spawn" in allow)
        if cur_init and _SPAWN.search(line) and not _KEYED.search(line) and not excused:
            init_routes.add(cur_init)
        allow = None
    return emit_sites, init_routes


def signal_lint_project(sources):
    """Whole-mission signal checks a single file cannot see.

    An initialization signal emitted from MORE THAN ONE place is the setup for the
    duplicate-everything bug: two addons emitting it, a copy-pasted emit, a mission
    emitting what its console already emits. Harmless when the handler is idempotent,
    so this only fires when the handler actually spawns WITHOUT a key and is not
    `once`-guarded - i.e. when a second emit really would duplicate.

    Args:
        sources: iterable of ``(path, content)`` for the mission's .mast sources.

    Returns:
        list: ``(path, AmdFinding)`` pairs, anchored at each emit site.
    """
    emits = {}
    risky = set()
    for path, content in sources:
        sites, init_routes = _scan_project_file(content)
        risky |= init_routes
        for name, line in sites:
            emits.setdefault(name, []).append((path, line))

    findings = []
    for name in sorted(risky):
        sites = emits.get(name, [])
        if len(sites) < 2:
            continue
        where = ", ".join(f"{p}:{ln}" for p, ln in sites)
        for path, line in sites:
            findings.append((path, AmdFinding(
                line, WARNING, "signal-multi-emit",
                "\"" + name + "\" initializes by spawning without a key and is emitted "
                "from " + str(len(sites)) + " places (" + where + ") - a second emit "
                "duplicates what it creates. Make the handler idempotent (*_ensure), "
                "mark the route `once`, or emit from one place. See SIGNAL_ROUTING.md")))
    return findings
