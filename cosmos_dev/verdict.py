"""Runtime-error verdict for the mock test harness (dev-only).

Installs the ``MastScheduler.on_runtime_error`` seam to capture every MAST
runtime error during a run, plus an explicit ``record_exception`` for Python
exceptions the runner catches. Turns a headless mock run into a pass/fail:
``verdict.ok`` is False if anything was recorded. Pairs with MastCoverage
(cosmos_dev/coverage.py) — coverage says how much ran, verdict says whether it
ran cleanly.

Not shipped in the .sbslib. See AUTOPLAY_PLAN.md.

Usage::

    from cosmos_dev.verdict import MastVerdict
    v = MastVerdict().install()
    ...run the mission...
    v.uninstall()
    assert v.ok, v.report()
"""
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mast import Mast
from sbs_utils.helpers import FrameContext


class MastVerdict:
    """Records MAST runtime errors (and explicitly-reported exceptions) via the
    MastScheduler.on_runtime_error seam, plus COMPILE errors via Mast.on_compile_error.
    ``ok`` is True iff nothing was recorded."""

    def __init__(self):
        self.errors: list = []   # [{source, message, label}]
        self._prev = None
        self._prev_compile = None
        self._prev_amd = None

    # -- lifecycle ---------------------------------------------------------
    def install(self) -> "MastVerdict":
        self._prev = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self._record
        self._prev_compile = Mast.on_compile_error
        Mast.on_compile_error = self._record_compile
        # Third seam, same shape as the other two. Without it a broken .amd could
        # not fail anything: .amd has no compile step, so a document that does not
        # parse rendered an empty panel and the run still reported PASS.
        from sbs_utils.procedural import amd_error as _amd
        self._prev_amd = _amd.on_amd_error
        _amd.on_amd_error = self._record_amd
        return self

    def uninstall(self) -> None:
        MastScheduler.on_runtime_error = self._prev
        Mast.on_compile_error = self._prev_compile
        from sbs_utils.procedural import amd_error as _amd
        _amd.on_amd_error = self._prev_amd
        self._prev = None
        self._prev_compile = None
        self._prev_amd = None

    def reset(self) -> None:
        self.errors.clear()

    # -- recording ---------------------------------------------------------
    def _record(self, message):
        label = None
        try:
            t = FrameContext.task
            if t is not None:
                label = t.active_label
        except Exception:
            pass
        self.errors.append({"source": "mast", "message": str(message), "label": label})

    def _record_compile(self, errors, file_name=None) -> None:
        """Record MAST compile errors (via the Mast.on_compile_error seam), so a
        headless --test FAILs on a mission/addon that doesn't compile - the engine
        catches these, the mock used to run on with the bad file silently empty."""
        if isinstance(errors, (list, tuple)):
            msg = " ".join(str(e).strip() for e in errors if str(e).strip())
        else:
            msg = str(errors)
        self.errors.append({"source": "compile", "message": msg, "label": file_name})

    def _record_amd(self, message, file_path=None, line=None, severity="error") -> None:
        """Record an AMD failure (via the amd_error.on_amd_error seam).

        ERRORS only. AMD warnings are a linter concern - the shipped corpus has
        legitimate ones - and counting them here would make every real mission fail
        its own conformance run."""
        if severity != "error":
            return
        where = f"{file_path}:{line}" if (file_path and line) else (file_path or None)
        self.errors.append({"source": "amd", "message": str(message), "label": where})

    def record_exception(self, exc, where=None) -> None:
        """Record a Python exception the runner caught outside MAST (e.g. in an
        event handler), so it also counts against the verdict."""
        self.errors.append({"source": "python", "message": f"{type(exc).__name__}: {exc}",
                            "label": where})

    def sweep_runtime_log(self, path="mast.runtime.log") -> int:
        """Count anything in ``mast.runtime.log`` that did not reach a seam, and
        record ONE error if the log has content the verdict does not.

        The seams above cover the paths that call them, and library code that
        catches its own exception and only logs it does not. That is the gap this
        closes: the log is written by ``logger.error`` exclusively, so a non-empty
        log means at least one error happened, whatever route it took.

        Cheap and blunt on purpose -- it makes the log the source of truth rather
        than a place to remember to look. `Mast()` opens the handler with mode "w",
        so the file is empty at the start of a run.

        LIMITATION: a ``run_next_mission`` reload re-opens the handler in "w" mode
        and TRUNCATES it, so errors from a previous mission in the same process are
        lost to this check. The seams still catch those as they happen.

        Returns the number of bytes found (0 when clean or unreadable).
        """
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return 0
        if not text.strip():
            return 0
        # Already-recorded errors log here too, so only complain when the log is
        # the ONLY witness -- otherwise every failing run reports twice.
        if not self.errors:
            first = next((l.strip() for l in text.splitlines() if l.strip()), "")
            self.errors.append({
                "source": "log",
                "message": f"{first}  (see {path} -- logged but not raised)",
                "label": None})
        return len(text)

    # -- result ------------------------------------------------------------
    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def report(self) -> str:
        if not self.errors:
            return "PASS - no runtime errors"
        lines = [f"FAIL - {len(self.errors)} error(s) (compile/runtime):"]
        for e in self.errors:
            loc = f" [{e['label']}]" if e.get("label") else ""
            first = str(e["message"]).splitlines()[0] if e["message"] else ""
            lines.append(f"  ({e['source']}){loc} {first}")
        return "\n".join(lines)
