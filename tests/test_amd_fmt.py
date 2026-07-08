"""amd_fmt - the canonical AMD formatter.

Verifies the normalizations, idempotence, and the safety invariant: formatting
never changes the parsed model (same node keys + reference values/kinds).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd_fmt import format_text
from sbs_utils.procedural.amd_core import parse


def _model(text):
    doc = parse(text)
    return (sorted(doc.keys), sorted((r.kind, str(r.value), r.owner) for r in doc.refs))


class TestFormat(unittest.TestCase):
    def test_strips_trailing_ws_and_normalizes_heading(self):
        src = "#   [Root](root)   \n##\t[Child](child)\t\n"
        self.assertEqual(format_text(src), "# [Root](root)\n## [Child](child)\n")

    def test_body_heading_spacing(self):
        self.assertEqual(format_text("# [R](r)\n##   Objective\n"),
                         "# [R](r)\n## Objective\n")

    def test_fence_normalized_to_three_dashes(self):
        src = "# [R](r)\n-----\nCenter: 0, 0\n- - -\n"  # only the all-dash lines are fences
        # second "fence" here is `- - -` which is NOT all-dashes -> left as body.
        out = format_text("# [R](r)\n----\nCenter: 0, 0\n----\nbody\n")
        self.assertEqual(out, "# [R](r)\n---\nCenter: 0, 0\n---\nbody\n")

    def test_fence_content_preserved(self):
        src = "# [R](r)\n---\nCitation: keep   spaced   words\n---\n"
        # internal spacing of YAML values is preserved (only trailing ws stripped)
        self.assertIn("Citation: keep   spaced   words", format_text(src))

    def test_collapses_blank_runs_and_trims_edges(self):
        src = "\n\n# [R](r)\n\n\n\nbody\n\n\n"
        self.assertEqual(format_text(src), "# [R](r)\n\nbody\n")

    def test_single_trailing_newline(self):
        self.assertEqual(format_text("# [R](r)"), "# [R](r)\n")
        self.assertEqual(format_text(""), "")

    def test_idempotent(self):
        src = "\n#  [R](r)  \n\n\n##   Objective\n---\nAt: 1, 2\n---\n- [go](x)  \n"
        once = format_text(src)
        self.assertEqual(format_text(once), once)


class TestSafety(unittest.TestCase):
    def test_model_unchanged_by_formatting(self):
        src = ("\n#  [Root](root) \n"
               "## [Dialogue](dialogue)\n### [A](a)\n% hi\n- [go](b)  \n### [B](b)\n"
               "## [N](narrative)\n### [Go](go)\n----\nWhen: reach 2, -1\nThen: reveal go2\n----\n"
               "#### [Go2](go2)\n\n\nbody\n")
        self.assertEqual(_model(src), _model(format_text(src)))


if __name__ == "__main__":
    unittest.main()
