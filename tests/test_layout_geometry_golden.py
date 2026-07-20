"""Golden geometry: Layout.calc must keep producing the same rects.

Captured from a deterministic corpus (tests/layout_corpus.py) BEFORE
Layout.calc was refactored to support content sizing. The refactor extracts
column-width resolution into its own pass so widths can be known before a
content row's height is measured -- valuable, but the kind of change that
silently shifts a rect somewhere unnoticed. This pins every rect so it cannot.

The corpus deliberately covers the parts of calc that INTERACT, since those are
what a refactor breaks: flex vs fixed vs square columns, Hole donation, the box
model, the font cascade that drives em sizing, orientation, nesting, and three
aspect ratios (percent and fixed units diverge as the window changes).

If this fails, read the diff: each line names the aspect, case, row and column,
so it points at the exact geometry that moved rather than just reporting that
a hash changed.

Regenerating the golden file is a DELIBERATE act -- only do it when a rendered
change is intended and reviewed, never to make a red test go green:

    python -m tests.test_layout_geometry_golden --regenerate
"""
import os
import sys
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "layout_geometry_golden.txt")


def _compute():
    FrameContext.context = types.SimpleNamespace(
        sbs=None, sim=None, event=types.SimpleNamespace(client_id=0))
    try:
        from tests import layout_corpus
        return layout_corpus.geometry()
    finally:
        FrameContext.context = None


class TestLayoutGeometryGolden(unittest.TestCase):
    def test_geometry_matches_golden(self):
        actual = _compute()
        with open(GOLDEN, encoding="utf-8") as f:
            expected = f.read().splitlines()

        self.assertEqual(
            len(actual), len(expected),
            f"corpus size changed ({len(expected)} -> {len(actual)}); "
            "regenerate the golden file if that was intended")

        diffs = [(i, e, a) for i, (e, a) in enumerate(zip(expected, actual)) if e != a]
        if diffs:
            head = "\n".join(f"  line {i}:\n    golden {e}\n    actual {a}"
                             for i, e, a in diffs[:12])
            more = f"\n  ... {len(diffs) - 12} more" if len(diffs) > 12 else ""
            self.fail(f"{len(diffs)} geometry line(s) changed:\n{head}{more}")

    def test_corpus_is_deterministic(self):
        # A golden test is only meaningful if the corpus is stable; if this
        # ever fails, the golden comparison above is noise, not a signal.
        self.assertEqual(_compute(), _compute())


def _regenerate():
    lines = _compute()
    with open(GOLDEN, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {len(lines)} lines to {GOLDEN}")


if __name__ == "__main__":
    if "--regenerate" in sys.argv:
        _regenerate()
    else:
        unittest.main()
