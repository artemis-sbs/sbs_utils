"""MAST node coverage for the mock test harness (dev-only).

Installs the ``MastTicker.on_enter_node`` seam to record every command that
executes, keyed by ``(label, file, line, node_type)``. Used by the conformance /
systems-test autoplay mode to turn "full systems test" into a measurable number
and to surface routes (comms, damage, focus, …) the autoplayer never exercised.

Not shipped in the .sbslib — this lives in cosmos_dev like the rest of the mock
tooling. See AUTOPLAY_PLAN.md.

Usage::

    from cosmos_dev.coverage import MastCoverage
    cov = MastCoverage().install()
    ...run the mission...
    cov.uninstall()
    print(cov.summary())
    print(cov.uncovered(kinds=("comms", "signal")))
"""
from collections import Counter

from sbs_utils.mast.mastscheduler import MastTicker
from sbs_utils.mast.mast import Mast


def label_kind(label: str) -> str:
    """Classify a label name into a coverage bucket (route type or plain label)."""
    if not label:
        return "label"
    if label.startswith("__route__"):
        body = label[len("__route__"):]
        for p in ("shared/signal", "signal", "comms", "damage", "collision",
                  "spawn", "focus", "select", "dock", "launch", "gui", "console"):
            if body.startswith(p):
                return p
        return "route:other"
    return "label"


class MastCoverage:
    """Records entered MAST nodes via the MastTicker.on_enter_node seam."""

    def __init__(self):
        # (label, file_num, line_num, node_type) -> hit count
        self.nodes: dict = {}
        self._prev = None

    # -- lifecycle ---------------------------------------------------------
    def install(self) -> "MastCoverage":
        self._prev = MastTicker.on_enter_node
        MastTicker.on_enter_node = self._record
        return self

    def uninstall(self) -> None:
        MastTicker.on_enter_node = self._prev
        self._prev = None

    def reset(self) -> None:
        self.nodes.clear()

    def _record(self, label, cmd):
        key = (label, getattr(cmd, "file_num", None),
               getattr(cmd, "line_num", None), cmd.__class__.__name__)
        self.nodes[key] = self.nodes.get(key, 0) + 1

    # -- queries -----------------------------------------------------------
    @property
    def labels_hit(self) -> set:
        return {k[0] for k in self.nodes}

    def summary(self, mast=None) -> dict:
        """Coverage rollup. If ``mast`` (a Mast) is given, compares against all
        defined labels for a percentage and per-category breakdown."""
        hit = self.labels_hit
        out = {
            "nodes_entered": len(self.nodes),
            "labels_hit": len(hit),
        }
        if mast is not None:
            defined = set(mast.labels.keys())
            out["labels_defined"] = len(defined)
            out["labels_pct"] = round(100 * len(hit & defined) / max(1, len(defined)), 1)
            by_def = Counter(label_kind(l) for l in defined)
            by_hit = Counter(label_kind(l) for l in (hit & defined))
            out["by_kind"] = {k: (by_hit.get(k, 0), by_def[k]) for k in sorted(by_def)}
        return out

    def uncovered(self, mast, kinds=None) -> list:
        """Labels defined in ``mast`` but never entered, optionally filtered to
        the given category ``kinds`` (see ``label_kind``)."""
        defined = set(mast.labels.keys())
        missing = sorted(defined - self.labels_hit)
        if kinds is not None:
            kinds = set(kinds)
            missing = [l for l in missing if label_kind(l) in kinds]
        return missing

    def hits_by_file(self) -> dict:
        """filename -> set of entered line numbers (for line-level reporting)."""
        out: dict = {}
        for (_label, fnum, lnum, _cls) in self.nodes:
            name = Mast.get_source_file_name(fnum)
            out.setdefault(name, set()).add(lnum)
        return out
