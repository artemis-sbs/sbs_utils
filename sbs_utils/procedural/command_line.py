"""The engine's launch arguments, readable from a mission.

New in engine 1.3.5, alongside the exe's own arguments (`autostartserver`,
`autostartclient`, `clientautoconnectip=`, `defaultmission=`). Those get Cosmos running
without a mouse; these are what let the MISSION react to how it was launched - which is the
difference between "automation can start the engine" and "automation can start the engine
ON A PARTICULAR MAP".

MEASURED on engine 1.3.5, not assumed::

    Artemis3-x64-release.exe autostartserver defaultmission=cli_probe map=test_all bareflag

    command_line_list() -> ['F:\\...\\Artemis3-x64-release.exe', 'autostartserver',
                            'defaultmission=cli_probe', 'map=test_all', 'bareflag']
    command_line_dict() -> {'defaultmission': 'cli_probe', 'map': 'test_all'}

Two things follow, and both matter:

* **`key=value` arguments the engine does not recognize survive to the dict.** `map=` is
  not an engine flag, and it arrived intact. So a mission can define its own launch
  arguments without the engine knowing about them.
* **Bare flags are list-only.** `autostartserver` and `bareflag` never reach the dict, so
  presence-style switches must be read with :func:`command_line_has`.

The list also carries the executable path at index 0, in argv tradition - so a caller
counting arguments must not treat `len()` as "how many arguments were passed".

Everything here degrades to empty rather than raising. A mission must run identically when
launched by hand, and under `cosmos_dev` where there is no engine command line at all.
"""

from ..helpers import FrameContext


def _sbs():
    """The sbs module for this frame, or None outside a frame (import time, tests)."""
    context = FrameContext.context
    return getattr(context, "sbs", None) if context is not None else None


def command_line_list():
    """Every launch argument as a list of strings, INCLUDING the exe path at index 0.

    Returns:
        list[str]: empty when the runtime has no command line (the mock) or the engine
        predates 1.3.5.
    """
    sbs = _sbs()
    fn = getattr(sbs, "command_line_list", None) if sbs is not None else None
    if fn is None:
        return []
    try:
        return list(fn() or [])
    except Exception:
        return []


def _raw_dict():
    """The engine's `key=value` arguments, unscoped. Internal - see command_line_dict."""
    sbs = _sbs()
    fn = getattr(sbs, "command_line_dict", None) if sbs is not None else None
    if fn is None:
        return {}
    try:
        return dict(fn() or {})
    except Exception:
        return {}


def _raw_get(key, default=None):
    """One unscoped argument, matched case-insensitively."""
    if key is None:
        return default
    wanted = str(key).strip().lower()
    for k, v in _raw_dict().items():
        if str(k).strip().lower() == wanted:
            return v
    return default


# Arguments that mean something about THIS MISSION, and so must not follow you into a
# different one. The rest (`seed=`, `run=`, `record=`, `test=`, the engine's own) are
# properties of the LAUNCH and are right either way.
_MISSION_SCOPED = ("profile", "map", "console")
_dropped_warned = set()


def _is_mission_scoped(key):
    k = str(key).strip().lower()
    return k in _MISSION_SCOPED or k.startswith("var.")


def command_line_mission_changed():
    """Whether `run_next_mission` has moved us off the mission we were LAUNCHED with.

    The launch arguments belong to the PROCESS, and `run_next_mission` swaps the mission
    without touching argv - so `profile=`, `map=`, `console=` and `var.NAME=` follow you
    into a mission they were never meant for. Right for a rerun of the same mission (which
    is the common case, and stays working); wrong for the pause screen's `mission_select`,
    `get_startup_mission_name()`, or `remote_mission_pick`.

    `defaultmission=` is the only baseline available. The engine forks a fresh process per
    mission, so nothing held in memory can survive to say what we started as.

    Deliberately fail-safe: **no baseline means "not changed"**, i.e. exactly today's
    behavior. Launched from the menu with no `defaultmission=`, or on an engine that does
    not pass it through, nothing here engages and nothing is dropped. Compared on the
    folder BASENAME, case-insensitively, so `defaultmission=legendarymissions` and a
    `LegendaryMissions` folder still count as the same mission.

    Returns:
        bool: True only when both names are known and they differ.
    """
    launched = _raw_get("defaultmission")
    if not launched:
        return False
    try:
        from ..fs import get_mission_name
        current = get_mission_name()
    except Exception:
        return False
    if not current:
        return False
    launched = str(launched).strip().replace("\\", "/").rstrip("/")
    launched = launched.rsplit("/", 1)[-1]
    return launched.casefold() != str(current).strip().casefold()


def command_line_scope_reset():
    """Forget which dropped arguments have been reported. Called from
    ``reset_mission_state`` so a switched mission says it once, not once per run."""
    _dropped_warned.clear()


def _note_dropped(key):
    """Say a mission-scoped argument was dropped - once per key.

    Silence here would be the worst outcome: `profile=house` doing nothing after a mission
    switch looks identical to a profile that failed to parse, and a same-named profile in
    the new mission quietly meaning something else is worse still.
    """
    shown = str(key).strip()
    if shown.lower() in _dropped_warned:
        return
    _dropped_warned.add(shown.lower())
    try:
        from .execution import log
        log(f"{shown}= was passed for another mission and does not apply here - "
            f"ignoring it", "command_line", "warning")
    except Exception:
        pass


def command_line_dict():
    """The `key=value` launch arguments, parsed.

    Bare flags are absent - see :func:`command_line_has` for those. Mission-scoped
    arguments are omitted once `run_next_mission` has switched missions; see
    :func:`command_line_mission_changed`.

    Returns:
        dict[str, str]: empty when the runtime has no command line.
    """
    raw = _raw_dict()
    if not raw or not command_line_mission_changed():
        return raw
    out = {}
    for k, v in raw.items():
        if _is_mission_scoped(k):
            _note_dropped(k)
        else:
            out[k] = v
    return out


def command_line_get(key, default=None):
    """One `key=value` argument, or `default`.

    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`.

    A mission-scoped argument (`profile=`, `map=`, `console=`, `var.NAME=`) reads as
    absent once we have switched missions, so every caller gets the scoping without having
    to remember it.
    """
    if key is None:
        return default
    if _is_mission_scoped(key) and command_line_mission_changed():
        _note_dropped(key)
        return default
    return _raw_get(key, default)


def command_line_has(flag):
    """Whether a BARE flag was passed, e.g. `autostartserver`.

    Bare flags never reach `command_line_dict`, so this walks the list. The exe path at
    index 0 is skipped - otherwise a mission launched from a folder called `autostartserver`
    would match, which is absurd but free to rule out.
    """
    if flag is None:
        return False
    wanted = str(flag).strip().lower()
    return any(str(a).strip().lower() == wanted for a in command_line_list()[1:])


def command_line_run_tag():
    """A label for this launch, from `run=` - for naming logs and artifacts.

    A soak that plays a mission repeatedly produces one set of files per run, and a report
    with no run identity in it is unactionable: "it broke" without "on which run" cannot be
    chased. `cosmos_dev` already prints a run index for its in-process restarts; this is the
    same idea for separately launched processes, which cannot share a counter.

    Returns:
        str: the tag, or "" when none was given - so a caller can always concatenate it.
    """
    return (command_line_get("run") or "").strip()


def command_line_report():
    """Every launch argument this library understands, and whether it landed.

    For a mission or a probe to print at startup. Worth having because the failure mode of
    a launch argument is silence: a mistyped one selects nothing, changes nothing, and the
    run proceeds looking healthy. Printing what was understood turns that into something
    visible in the first line of a log.
    """
    known = ("map", "console", "profile", "seed", "run")
    args = command_line_dict()
    lines = []
    for name in known:
        if name in {k.lower() for k in args}:
            lines.append(f"  {name} = {command_line_get(name)}")
    for key, value in sorted(args.items()):
        if str(key).lower().startswith("var."):
            lines.append(f"  {key} = {value}")
    # What was passed but does not apply here. Reported rather than hidden: an argument
    # silently absent is indistinguishable from one that was never typed.
    if command_line_mission_changed():
        for key, value in sorted(_raw_dict().items()):
            if _is_mission_scoped(key):
                lines.append(f"  {key} = {value}   (for another mission - ignored)")
    if not lines:
        return "no launch arguments"
    return "launch arguments:\n" + "\n".join(lines)
