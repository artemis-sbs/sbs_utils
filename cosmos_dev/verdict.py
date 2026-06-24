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
from sbs_utils.helpers import FrameContext


class MastVerdict:
    """Records MAST runtime errors (and explicitly-reported exceptions) via the
    MastScheduler.on_runtime_error seam. ``ok`` is True iff nothing was recorded."""

    def __init__(self):
        self.errors: list = []   # [{source, message, label}]
        self._prev = None

    # -- lifecycle ---------------------------------------------------------
    def install(self) -> "MastVerdict":
        self._prev = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self._record
        return self

    def uninstall(self) -> None:
        MastScheduler.on_runtime_error = self._prev
        self._prev = None

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

    def record_exception(self, exc, where=None) -> None:
        """Record a Python exception the runner caught outside MAST (e.g. in an
        event handler), so it also counts against the verdict."""
        self.errors.append({"source": "python", "message": f"{type(exc).__name__}: {exc}",
                            "label": where})

    # -- result ------------------------------------------------------------
    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def report(self) -> str:
        if not self.errors:
            return "PASS - no runtime errors"
        lines = [f"FAIL - {len(self.errors)} runtime error(s):"]
        for e in self.errors:
            loc = f" [{e['label']}]" if e.get("label") else ""
            first = str(e["message"]).splitlines()[0] if e["message"] else ""
            lines.append(f"  ({e['source']}){loc} {first}")
        return "\n".join(lines)
