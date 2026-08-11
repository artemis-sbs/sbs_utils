"""Every reader of an AMD body must agree on what a mark IS.

`test_amd_one_grammar.py` pins this for the heading, after the linter and the
formatter each grew a lookalike of `RE_HEADING`. The same thing had happened
again, further down the grammar, and further out of sight:

  * the CHOICE rule existed four times - `amd_core` (reference spans), `amd_lsp`
    (the choice editor), `amd_lint` (via `amd_dialogue`) and `amd_dialogue`
    itself (the runtime). They did not match. `amd_dialogue`'s target class was
    `[\\w.\\-]*`, which cannot match a path target (`florbin/recover`), and its
    anchor was `^-`, which cannot match an indented choice. Either line would
    have parsed clean in the editor and in the linter and then VANISHED at
    runtime, which is the worst available failure: the tooling says the document
    is fine and the game disagrees silently.
  * the `%` VARIANT rule existed five times, and only `amd_dialogue` understood
    gates - so `%{standing < -20} You again.` was a gated line in a hail and a
    line of text literally beginning `{standing < -20}` everywhere else.
  * the style / media / whole-line-link / table rules lived only in the in-game
    renderer, which was fine while the game was the only thing that drew a body.

These are identity assertions, not behavior ones, on purpose. A behavior test
passes happily against two copies that currently agree; only `is` catches the
copy, and the copy is the bug.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import

from sbs_utils.procedural import amd, amd_core, amd_dialogue, amd_lsp
from sbs_utils.pages.layout import text_area


class TestOneChoiceRule(unittest.TestCase):
    def test_every_reader_shares_it(self):
        self.assertIs(amd_core._RE_CHOICE, amd.RE_CHOICE)
        self.assertIs(amd_lsp._RE_CHOICE, amd.RE_CHOICE)
        self.assertIs(amd_dialogue._CHOICE, amd.RE_CHOICE)

    def test_the_linter_reads_the_same_rule(self):
        # amd_lint imports `_CHOICE` from amd_dialogue rather than defining one.
        from sbs_utils.procedural.amd_dialogue import _CHOICE
        self.assertIs(_CHOICE, amd.RE_CHOICE)

    def test_one_choice_parser(self):
        self.assertIs(amd_dialogue._dlg_parse_choice, amd.amd_choice)
        self.assertIs(amd_dialogue._dlg_parse_outcomes, amd.amd_outcomes)

    def test_a_path_target_survives(self):
        # The case amd_dialogue's narrower class could not express.
        choice = amd.amd_choice("- [Recover it](florbin/recover)")
        self.assertEqual(choice["target"], "florbin/recover")

    def test_an_indented_choice_survives(self):
        choice = amd.amd_choice("    - [Go](x)")
        self.assertEqual(choice["target"], "x")

    def test_an_empty_target_is_legal(self):
        # "this answer ends the hail" - the common last beat of a conversation.
        self.assertEqual(amd.amd_choice("- [Understood]()")["target"], "")

    def test_a_bracket_in_the_label_is_not_a_choice(self):
        # The same strictness RE_HEADING applies to its display text.
        self.assertIsNone(amd.amd_choice("- [a]b](k)"))


class TestOneVariantRule(unittest.TestCase):
    def test_gate_rule_is_shared(self):
        self.assertIs(amd_dialogue._GATE, amd.RE_GATE)

    def test_scan_and_chatter_share_the_pool_rule(self):
        from sbs_utils.procedural import amd_chatter, amd_science
        self.assertIs(amd_science._scan_body_lines, amd.amd_variant_pool)
        self.assertIs(amd_chatter._chatter_body_lines, amd.amd_variant_pool)

    def test_the_two_variant_rules_stay_different(self):
        # There are genuinely TWO rules riding the `%` sigil, and merging them
        # would be a silent behavior change rather than a cleanup.
        self.assertEqual(amd.amd_body_variant("%{a > 1} spoken"), ("spoken", "a > 1"))
        self.assertEqual(amd.amd_variant_pool("%{a > 1} scanned"), ["{a > 1} scanned"])

    def test_urge_still_counts_its_sigils(self):
        # A third rule: amd_urge COUNTS `%` to number an escalation stage, so it
        # cannot share the pool rule without flattening every curve to stage 1.
        from sbs_utils.procedural.amd_urge import _urge_pool
        _pool, stages = _urge_pool("% calm\n%% louder\n%%% shouting")
        self.assertEqual(sorted(stages), [1, 2, 3])


class TestOneRichTextRule(unittest.TestCase):
    """The marks that describe how a body is DISPLAYED. They lived only in the
    in-game renderer; a second renderer is exactly when that stops being safe."""

    def test_text_area_shares_them(self):
        self.assertIs(text_area.TextArea.rule_style_def, amd.RE_STYLE_DEF)
        self.assertIs(text_area.TextArea.rule_style_ref, amd.RE_STYLE_REF)
        self.assertIs(text_area.TextArea.rule_link_def, amd.RE_LINK_DEF)
        self.assertIs(text_area.TextArea.rule_link_ref, amd.RE_LINK_REF)
        self.assertIs(text_area.TextArea._whole_link_re, amd.RE_REF_LINK)
        self.assertIs(text_area.TextArea._table_sep_re, amd.RE_TABLE_SEP)
        self.assertIs(text_area.parse_url, amd.amd_parse_url)

    def test_the_dead_lookalike_is_gone(self):
        # A module-level `image_pattern` sat beside `rule_link_ref` and was a
        # near-miss copy of it. Nothing in any repo used it - which is the only
        # reason it never caused the bug it was shaped to cause.
        self.assertFalse(hasattr(text_area, "image_pattern"))


class TestBlocksOwnNoGrammar(unittest.TestCase):
    def test_amd_blocks_defines_no_regex(self):
        # The classifier decides ORDER and boundaries. The moment it compiles a
        # pattern of its own, the printed page and the game can disagree again.
        import re

        from sbs_utils.procedural import amd_blocks
        compiled = [n for n, v in vars(amd_blocks).items()
                    if isinstance(v, re.Pattern) and not hasattr(amd, n)]
        self.assertEqual(compiled, [])


if __name__ == "__main__":
    unittest.main()
