"""The linter, the formatter and the reader must agree on what a heading IS.

amd_lint and amd_fmt each carried their own lookalike of RE_HEADING with greedy
`.*` groups. Being MORE permissive than the reader is the dangerous direction:

  * the LINTER treats a line as a valid heading, so it does not raise
    `broken-heading` -- and the parser meanwhile drops that line into the parent's
    body, so the record silently vanishes. The one rule written to catch this
    exact failure was blind to it.
  * the FORMATTER re-emits a line as a heading that the reader does not read as
    one, which is a formatter that can rewrite prose into structure.

Two copies of a grammar is how the tooling and the game came to disagree about
the same file; this pins that there is now one.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd import RE_HEADING
from sbs_utils.procedural import amd_fmt, amd_lint
from sbs_utils.procedural.amd_lint import amd_lint_structural
from sbs_utils.procedural.quest import document_get_amd_file


# Each of these looks like a heading and is NOT one to the reader.
NOT_HEADINGS = (
    "# [a]b](k)",          # a `]` inside the display text
    "# [a](b)c)",          # a `)` inside the key
    "# [a](b) trailing",   # anything after the link
)
IS_HEADING = "# [Real](real)"


class TestOneGrammar(unittest.TestCase):
    def test_all_three_share_one_rule(self):
        self.assertIs(amd_lint._RE_SECTION, RE_HEADING)
        self.assertIs(amd_fmt._RE_SECTION, RE_HEADING)

    def test_the_reader_rejects_them(self):
        for line in NOT_HEADINGS:
            with self.subTest(line=line):
                doc = document_get_amd_file(None, "r", content=line + "\n")
                self.assertEqual(doc.get("children"), [],
                                 "the reader made a record out of " + line)

    def test_the_linter_now_flags_them(self):
        for line in NOT_HEADINGS:
            with self.subTest(line=line):
                codes = [f.code for f in amd_lint_structural(content=line + "\n")]
                self.assertIn("broken-heading", codes,
                              "linter stayed quiet about " + line)

    def test_a_real_heading_is_still_quiet(self):
        codes = [f.code for f in amd_lint_structural(content=IS_HEADING + "\n")]
        self.assertEqual(codes, [])
        doc = document_get_amd_file(None, "r", content=IS_HEADING + "\n")
        self.assertEqual(len(doc.get("children")), 1)

    def test_the_formatter_leaves_a_non_heading_alone(self):
        for line in NOT_HEADINGS:
            with self.subTest(line=line):
                out = amd_fmt.format_text(line + "\n")
                self.assertEqual(out.strip(), line,
                                 "formatter rewrote a non-heading")

    def test_the_formatter_is_idempotent(self):
        src = IS_HEADING + "\n" + "\n".join(NOT_HEADINGS) + "\nbody\n"
        once = amd_fmt.format_text(src)
        self.assertEqual(once, amd_fmt.format_text(once))

    def test_heading_level_jump_tracking_survived(self):
        # Depth tracking runs off the same match; a stricter rule must not stop
        # the jump check from seeing legitimate headings.
        src = "# [a](a)\n#### [deep](d)\n"
        codes = [f.code for f in amd_lint_structural(content=src)]
        self.assertIn("heading-level-jump", codes)


if __name__ == "__main__":
    unittest.main()
