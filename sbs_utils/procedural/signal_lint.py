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


def _signal_route_name(stripped):
    """The name from a `//signal/<name>[ if ...]` header, or None when the line is not a
    plain //signal route (`//shared/signal/...` and `///inline` are NOT plain //signal)."""
    if not stripped.startswith("//signal/"):
        return None
    rest = stripped[len("//signal/"):].split()
    return rest[0] if rest else "?"


def signal_lint(file_path=None, content=None):
    """Return [AmdFinding] (all WARNING) for side-effects inside `//signal` routes in one
    .mast source. See the module docstring + SIGNAL_ROUTING.md."""
    lines = _source_lines(file_path, content)
    findings = []
    cur = None   # name of the //signal route currently open, else None
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        stripped = line.strip()
        # A column-0 structural line ends the current //signal body and maybe opens a new one.
        if not line[:1].isspace() and _STRUCT.match(stripped):
            cur = _signal_route_name(stripped)
            continue
        if cur is None or not stripped or stripped.startswith("#"):
            continue
        for rx, code, human in _SIDE_EFFECTS:
            if rx.search(line):
                findings.append(AmdFinding(
                    i, WARNING, "signal-side-effect-" + code,
                    "//signal/" + cur + " calls " + human + " - runs once PER console; use "
                    "//shared/signal (or split: shared does it + emits a display signal). "
                    "See SIGNAL_ROUTING.md"))
                break   # one finding per line
    return findings
