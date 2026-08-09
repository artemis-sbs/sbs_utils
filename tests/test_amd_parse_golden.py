"""Golden parse: document_get_amd_file must keep producing the same tree.

Captured from a deterministic corpus (tests/amd_corpus.py) BEFORE the AMD
reader grew a schema memo, a parsed-document cache and a quest generation
counter. Each of those touches a hot path, and the failure mode they share is
silent: a field that stops resolving still produces a tree, still renders a
panel, and still reports PASS. This pins every field of every node so it
cannot.

The contract this enforces, in one line: NO AUTHORED .amd MAY PARSE
DIFFERENTLY. Two changes are allowed to move a line here and both are
additive -- trait aliases (labels that are UNDECLARED today start resolving)
and the encoding unification (files that are MISDECODED today start decoding).
Anything else that turns this red is a regression, not a new golden.

If it fails, read the diff: each line names case, node path and field, so it
points at the exact value that moved rather than reporting that a hash changed.

Regenerating is a DELIBERATE act -- only when a parse change is intended and
reviewed, never to make a red test go green:

    python -m tests.test_amd_parse_golden --regenerate
"""
import os
import sys
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

GOLDEN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "amd_parse_golden.txt")


def _compute():
    from tests import amd_corpus
    return amd_corpus.parse_lines()


class TestAmdParseGolden(unittest.TestCase):
    def test_parse_matches_golden(self):
        actual = _compute()
        with open(GOLDEN, encoding="utf-8") as f:
            expected = f.read().splitlines()

        if len(actual) != len(expected):
            gone = [l for l in expected if l not in actual][:6]
            new = [l for l in actual if l not in expected][:6]
            self.fail(
                f"corpus size changed ({len(expected)} -> {len(actual)}); "
                f"regenerate ONLY if intended.\n  missing: {gone}\n  added:   {new}")

        diffs = [(i, e, a) for i, (e, a) in enumerate(zip(expected, actual)) if e != a]
        if diffs:
            head = "\n".join(f"  line {i}:\n    golden {e}\n    actual {a}"
                             for i, e, a in diffs[:12])
            more = f"\n  ... {len(diffs) - 12} more" if len(diffs) > 12 else ""
            self.fail(f"{len(diffs)} parsed field(s) changed:\n{head}{more}")

    def test_corpus_is_deterministic(self):
        # A golden test is only meaningful if the corpus is stable; if this ever
        # fails, the comparison above is noise, not a signal.
        self.assertEqual(_compute(), _compute())

    def test_parsing_twice_in_one_process_agrees(self):
        # The cache-poisoning check. Once document_get_amd_file memoizes, a
        # second parse in the same process must still hand back an unmutated
        # tree -- and the corpus post-passes (transclusion, wikilinks) MUTATE
        # what they walk, so this is the assertion that a shared cached tree
        # would break.
        first = _compute()
        second = _compute()
        third = _compute()
        self.assertEqual(first, second)
        self.assertEqual(second, third)


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
