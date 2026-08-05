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


def command_line_dict():
    """The `key=value` launch arguments, parsed.

    Bare flags are absent - see :func:`command_line_has` for those.

    Returns:
        dict[str, str]: empty when the runtime has no command line.
    """
    sbs = _sbs()
    fn = getattr(sbs, "command_line_dict", None) if sbs is not None else None
    if fn is None:
        return {}
    try:
        return dict(fn() or {})
    except Exception:
        return {}


def command_line_get(key, default=None):
    """One `key=value` argument, or `default`.

    The key is matched case-insensitively and without surrounding spaces, because a launch
    argument is typed by a person or pasted from a script and `Map=` should not behave
    differently from `map=`.
    """
    if key is None:
        return default
    wanted = str(key).strip().lower()
    for k, v in command_line_dict().items():
        if str(k).strip().lower() == wanted:
            return v
    return default


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
