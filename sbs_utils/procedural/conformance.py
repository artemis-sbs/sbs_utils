"""Play a mission for N sim-seconds in the REAL engine and write a verdict.

    Artemis3-x64-release.exe autostartserver defaultmission=X map=Y test=30

Writes `<mission>/records/verdict.json` once the mission has run that long. A launcher
starts the engine, waits, reads the file, and kills the process.

WHY A FILE AND NOT AN EXIT CODE. The engine exposes no way for a mission to end the
process - there is no quit, exit or shutdown in the pybind surface. So the mission cannot
fail a build directly; it can only leave evidence. The launcher supplies the exit code.

WHAT THIS CHECKS, AND WHAT IT DOES NOT. Runtime errors, whether the mission reached the
requested duration, and the engine version. It does **not** measure MAST label coverage -
that lives in `cosmos_dev`, which is not in the shipped `.sbslib` and so does not exist in
the engine. `cosmos_dev`'s headless `--test` is therefore the STRONGER check, and this is
deliberately the weaker one that runs where the mock cannot go.

That distinction is worth keeping straight, because a verdict claiming more than it checked
is worse than no verdict: a run that executed nothing at all can still reach 30 seconds
without a runtime error, and the honest report for that is "no errors, and I did not look
at whether anything happened". `reached` and `errors` are reported separately for exactly
that reason - a green `errors: 0` is not by itself a pass.
"""

import json
import logging
import os

from ..helpers import FrameContext
from .command_line import command_line_get

_seconds = None            # None = not resolved, 0 = not requested
_written = False
_counter = None


class _ErrorCounter(logging.Handler):
    """Counts records on the `mast.runtime` logger.

    That logger is where `MastScheduler.runtime_error` sends everything, so it is the one
    place a MAST failure is guaranteed to pass through in the engine - the same source
    behind `mast.runtime.log`.
    """

    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.count = 0
        self.first = None

    def emit(self, record):
        self.count += 1
        if self.first is None:
            try:
                self.first = str(record.getMessage())[:400]
            except Exception:
                self.first = "<unformattable>"


def _sim_seconds():
    """Sim time, or None when there is no simulation yet.

    `FrameContext.sim_seconds` RAISES rather than returning zero when the context has no
    sim - and this is called from `tick_the_rest`, on every tick of the shipped library.
    An exception there would take down every mission, recording or not, so it is caught
    here rather than trusted.
    """
    try:
        return FrameContext.sim_seconds
    except Exception:
        return None


def conformance_seconds():
    """How long `test=` asked for, or 0 when it was not requested."""
    global _seconds, _counter
    if _seconds is not None:
        return _seconds
    raw = (command_line_get("test") or "").strip()
    if not raw:
        _seconds = 0
        return 0
    try:
        _seconds = max(1, int(float(raw)))
    except ValueError:
        from .execution import log
        log(f"test='{raw}' is not a number of seconds - not running a conformance pass",
            "conformance", "warning")
        _seconds = 0
        return 0
    if _counter is None:
        _counter = _ErrorCounter()
        logging.getLogger("mast.runtime").addHandler(_counter)
    return _seconds


def conformance_tick():
    """Write the verdict once the mission has run long enough. Cheap when not requested."""
    global _written
    if _written or not conformance_seconds():
        return
    now = _sim_seconds()
    if now is None or now < _seconds:
        return
    _written = True
    conformance_write(now)


def conformance_write(sim_seconds=None):
    """Write the verdict now. Returns the path, or None."""
    try:
        from ..fs import get_mission_dir
        folder = os.path.join(get_mission_dir(), "records")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "verdict.json")
    except Exception:
        return None

    try:
        version = FrameContext.context.sbs.get_game_version()
    except Exception:
        version = ""

    errors = _counter.count if _counter is not None else 0
    now = sim_seconds if sim_seconds is not None else (_sim_seconds() or 0)
    asked = _seconds or 0
    entry = {
        # Which runtime produced this. An engine report and a mock report otherwise look
        # identical, and one has already been mistaken for the other.
        "runtime": "engine" if version else "mock",
        "version": version,
        "asked_seconds": asked,
        "sim_seconds": round(now, 2),
        "reached": bool(asked and now >= asked),
        "errors": errors,
        "first_error": _counter.first if _counter is not None else None,
        "run": (command_line_get("run") or "").strip(),
        "map": (command_line_get("map") or "").strip(),
        "verdict": "PASS" if (errors == 0 and asked and now >= asked) else "FAIL",
        # Said plainly in the artifact, not just in the docs: this is the weaker check.
        "note": "runtime errors only - MAST label coverage is not measured in the engine; "
                "cosmos_dev --test is the stronger check",
    }
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(json.dumps(entry, indent=2) + "\n")
        os.replace(tmp, path)
    except OSError:
        return None
    return path


def conformance_reset():
    """Drop state at a mission boundary. Registered with the reset ledger."""
    global _seconds, _written, _counter
    if _counter is not None:
        logging.getLogger("mast.runtime").removeHandler(_counter)
    _seconds = None
    _written = False
    _counter = None


def conformance_error_count():
    """Runtime errors seen so far. Reset-ledger probe."""
    return _counter.count if _counter is not None else 0
