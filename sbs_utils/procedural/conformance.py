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
    soak = _soak_result()
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
    if soak is not None:
        # A soak run measures MORE than `test=` alone, so the note above stops being true
        # and must not be left standing - a verdict that understates itself sends people
        # to the mock for an answer they already have.
        entry["soak"] = soak
        entry["note"] = ("scenario expectations checked; MAST coverage measured via the "
                         "shipped MastTicker.on_enter_node seam")
        if soak.get("failures"):
            entry["verdict"] = "FAIL"
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
    soak_reset()
    if _counter is not None:
        logging.getLogger("mast.runtime").removeHandler(_counter)
    _seconds = None
    _written = False
    _counter = None


def conformance_error_count():
    """Runtime errors seen so far. Reset-ledger probe."""
    return _counter.count if _counter is not None else 0


# --- soak= : the harness, in the real engine ---------------------------------------
#
# WHY THIS LIVES IN THE SHIPPED LIBRARY. `tick_the_rest` is the one place reached every
# tick, and it already calls `conformance_tick()`. The harness itself (the pilot, the
# scenario loader, the coverage collector) ships separately in the cosmos_dev sbslib, so
# everything here is imported LAZILY and every failure degrades to "no soak" rather than
# to a broken mission. A mission that does not declare that sbslib must behave exactly as
# it did before this existed.
#
# WHAT IT ADDS OVER `test=` ALONE. `test=` counts runtime errors and says so honestly -
# its own docstring points out that a run which executed nothing at all still passes.
# With the scenario loaded, the verdict also carries which quests completed and which
# routes were entered, and `MastTicker.on_enter_node` (shipped, in mastscheduler) makes
# the coverage half possible in the engine for the first time.

_soak_name = None          # None = not resolved, "" = not requested
_soak_scenario = None
_soak_pilot = None
_soak_cov = None
_soak_failed = False


def soak_name():
    """The scenario `soak=` asked for, or "" when it was not requested."""
    global _soak_name
    if _soak_name is None:
        _soak_name = (command_line_get("soak") or "").strip()
    return _soak_name


def soak_active():
    """Whether a soak scenario is loaded and driving. Cheap once resolved."""
    global _soak_scenario, _soak_pilot, _soak_cov, _soak_failed
    if _soak_failed or not soak_name():
        return False
    if _soak_scenario is not None:
        return True
    try:
        from ..fs import get_mission_dir
        from cosmos_dev.soak_manifest import load_scenario
        from cosmos_dev.quest_pilot import QuestPilot
        from cosmos_dev.coverage import MastCoverage
    except ImportError as e:
        # The usual cause, and worth naming rather than leaving as a silent no-op: the
        # mission's story.json does not declare the cosmos_dev sbslib.
        _soak_failed = True
        from .execution import log
        log(f"soak='{soak_name()}' but the harness is not loadable ({e}) - add the "
            "cosmos_dev sbslib to this mission's story.json", "conformance", "warning")
        return False
    try:
        sc = load_scenario(get_mission_dir(), soak_name())
    except Exception as e:
        sc = None
        from .execution import log
        log(f"soak scenario '{soak_name()}' failed to load: {e}", "conformance", "warning")
    if sc is None:
        _soak_failed = True
        from .execution import log
        log(f"no soak scenario '{soak_name()}' under <mission>/soaks/", "conformance",
            "warning")
        return False
    _soak_scenario = sc
    _soak_pilot = QuestPilot(FrameContext.context.sbs, accept=sc.accept, goals=sc.goals)
    _soak_cov = MastCoverage().install()
    from .execution import log
    log(f"soak scenario '{soak_name()}' active", "conformance")
    return True


def soak_tick():
    """Drive the pilot one step. Called from `tick_the_rest`, guarded and cheap."""
    if not soak_active():
        return
    try:
        _soak_pilot.step()
    except Exception as e:
        # A throw in the HARNESS is not a mission finding. Count it, do not let it end
        # the tick - this runs inside the shipped event handler.
        try:
            _soak_pilot.errors += 1
        except Exception:
            pass
        logging.getLogger("mast.runtime").warning(f"soak pilot step failed: {e}")


def _soak_result():
    """The scenario half of the verdict, or None when no soak is running."""
    if _soak_scenario is None or _soak_pilot is None:
        return None
    from cosmos_dev.soak_manifest import check_expectations
    snap = _soak_pilot.snapshot()
    routes = _soak_covered_routes()
    try:
        failures, result = check_expectations(_soak_scenario, snap, routes, None)
    except Exception as e:
        return {"error": f"expectation check failed: {e}"}
    return {
        "scenario": _soak_scenario.name,
        # DID THE PILOT ACTUALLY RUN? Without this a soak can report PASS having driven
        # nothing at all - coverage still accrues from the mission's own execution, so
        # `routes_covered` alone cannot tell the two apart. `steps` at 0 means `step()`
        # returned early every tick (usually no server task yet), which is a HARNESS
        # problem wearing a green verdict.
        "pilot_steps": getattr(_soak_pilot, "steps", 0),
        "quests_seen": len(snap.get("complete") or ()) + len(snap.get("active") or ()),
        "quests_complete": result["quests_complete"],
        "routes_covered_count": len(result["routes_covered"]),
        "not_drivable": sorted(snap.get("unreachable") or {}),
        "accepted": snap.get("accepted"),
        "failures": failures,
    }


def _soak_covered_routes():
    """Entered route paths, normalized the way a scenario names them.

    Shares `soak_manifest.normalize_route` with the mock leg on purpose: two copies of
    this rule would drift, and a route the engine called one thing and the mock another
    would look like a regression in whichever leg ran second.
    """
    if _soak_cov is None:
        return set()
    try:
        from cosmos_dev.soak_manifest import normalize_routes
        return normalize_routes(_soak_cov.labels_hit)
    except Exception:
        return set()


def soak_reset():
    """Drop soak state at a mission boundary. Called from `conformance_reset`."""
    global _soak_name, _soak_scenario, _soak_pilot, _soak_cov, _soak_failed
    if _soak_cov is not None:
        try:
            _soak_cov.uninstall()
        except Exception:
            pass
    _soak_name = None
    _soak_scenario = None
    _soak_pilot = None
    _soak_cov = None
    _soak_failed = False
