from sbs_utils.helpers import FrameContext
def _is_mission_scoped (key):
    ...
def _note_dropped (key):
    """Say a mission-scoped argument was dropped - once per key.
    
    Silence here would be the worst outcome: `profile=house` doing nothing after a mission
    switch looks identical to a profile that failed to parse, and a same-named profile in
    the new mission quietly meaning something else is worse still."""
def _raw_dict ():
    """The engine's `key=value` arguments, unscoped. Internal - see command_line_dict."""
def _raw_get (key, default=None):
    """One unscoped argument, matched case-insensitively."""
def _sbs ():
    """The sbs module for this frame, or None outside a frame (import time, tests)."""
def command_line_dict ():
    """The `key=value` launch arguments, parsed.
    
    Bare flags are absent - see :func:`command_line_has` for those. Mission-scoped
    arguments are omitted once `run_next_mission` has switched missions; see
    :func:`command_line_mission_changed`.
    
    Returns:
        dict[str, str]: empty when the runtime has no command line."""
def command_line_get (key, default=None):
    """One `key=value` argument, or `default`.
    
    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`.
    
    A mission-scoped argument (`profile=`, `map=`, `console=`, `var.NAME=`) reads as
    absent once we have switched missions, so every caller gets the scoping without having
    to remember it."""
def command_line_has (flag):
    """Whether a BARE flag was passed, e.g. `autostartserver`.
    
    Bare flags never reach `command_line_dict`, so this walks the list. The exe path at
    index 0 is skipped - otherwise a mission launched from a folder called `autostartserver`
    would match, which is absurd but free to rule out."""
def command_line_list ():
    """Every launch argument as a list of strings, INCLUDING the exe path at index 0.
    
    Returns:
        list[str]: empty when the runtime has no command line (the mock) or the engine
        predates 1.3.5."""
def command_line_mission_changed ():
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
        bool: True only when both names are known and they differ."""
def command_line_report ():
    """Every launch argument this library understands, and whether it landed.
    
    For a mission or a probe to print at startup. Worth having because the failure mode of
    a launch argument is silence: a mistyped one selects nothing, changes nothing, and the
    run proceeds looking healthy. Printing what was understood turns that into something
    visible in the first line of a log."""
def command_line_run_tag ():
    """A label for this launch, from `run=` - for naming logs and artifacts.
    
    A soak that plays a mission repeatedly produces one set of files per run, and a report
    with no run identity in it is unactionable: "it broke" without "on which run" cannot be
    chased. `cosmos_dev` already prints a run index for its in-process restarts; this is the
    same idea for separately launched processes, which cannot share a counter.
    
    Returns:
        str: the tag, or "" when none was given - so a caller can always concatenate it."""
def command_line_scope_reset ():
    """Forget which dropped arguments have been reported. Called from
    ``reset_mission_state`` so a switched mission says it once, not once per run."""
