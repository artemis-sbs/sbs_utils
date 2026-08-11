"""amd_blocks - one AMD body -> typed blocks.

Fixtures are PYTHON STRINGS rather than checked-in `.amd` files, for the reason
`tests/amd_corpus.py` records: `core.autocrlf=true` would let a developer's git
config decide a fixture's bytes, and how a body's lines are split is exactly what
these tests pin.

The sharpest cases here are the ones where two marks look alike and mean
different things - a choice against a bullet, a callout against a transition, a
style declaration against a synopsis - because those are the pairs a second
renderer gets wrong.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd_blocks import amd_blocks, amd_blocks_text
from sbs_utils.procedural.amd_core import parse


def kinds(blocks):
    return [b["type"] for b in blocks]


def one(blocks, kind):
    hits = [b for b in blocks if b["type"] == kind]
    assert len(hits) == 1, f"expected one {kind}, got {kinds(blocks)}"
    return hits[0]


class TestBlockTypes(unittest.TestCase):
    def test_paragraph_is_the_fallback(self):
        # The rule that keeps the format growable: a line the grammar does not
        # claim is prose, forever.
        blocks = amd_blocks_text("Just a sentence.\nAnd another on the same run.")
        self.assertEqual(kinds(blocks), ["paragraph"])
        self.assertEqual(blocks[0]["text"],
                         "Just a sentence. And another on the same run.")

    def test_blank_line_separates_paragraphs(self):
        blocks = amd_blocks_text("One.\n\nTwo.")
        self.assertEqual(kinds(blocks), ["paragraph", "paragraph"])

    def test_cue_direction_and_speech(self):
        blocks = amd_blocks_text("@vex (comms)\n(shaken)\n% You are a long way out.")
        self.assertEqual(kinds(blocks), ["cue", "direction", "speech"])
        self.assertEqual(blocks[0]["speaker"], "vex")
        self.assertEqual(blocks[0]["surface"], "comms")
        self.assertEqual(blocks[1]["text"], "shaken")

    def test_consecutive_variants_merge_into_one_set(self):
        # Three `%` lines are ONE choice of what to say, not three things said.
        blocks = amd_blocks_text("% Brave.\n% Or stupid.\n% Hard to say which.")
        self.assertEqual(kinds(blocks), ["speech"])
        self.assertEqual(len(one(blocks, "speech")["variants"]), 3)

    def test_variant_gate_is_read(self):
        blocks = amd_blocks_text("%{standing < -20} You again.")
        variant = one(blocks, "speech")["variants"][0]
        self.assertEqual(variant["gate"], "standing < -20")
        self.assertEqual(variant["text"], "You again.")

    def test_choice_with_guard_and_outcomes(self):
        blocks = amd_blocks_text(
            "- [Pay the toll](paid) if credits > 200 ; costs 200 credits, signal paid")
        choice = one(blocks, "choice")
        self.assertEqual(choice["label"], "Pay the toll")
        self.assertEqual(choice["target"], "paid")
        self.assertEqual(choice["guard"], "credits > 200")
        self.assertEqual(choice["outcomes"],
                         [["costs", "200", "credits"], ["signal", "paid"]])

    def test_outcomes_split_before_the_guard(self):
        # A guard is free text; read second, it swallows the whole tail and the
        # outcome is lost without a word.
        choice = one(amd_blocks_text("- [Go](x) if a > 1 ; signal went"), "choice")
        self.assertEqual(choice["guard"], "a > 1")
        self.assertEqual(choice["outcomes"], [["signal", "went"]])

    def test_a_choice_is_not_a_bullet(self):
        blocks = amd_blocks_text("- [Go](x)\n- an ordinary bullet")
        self.assertEqual(kinds(blocks), ["choice", "list"])

    def test_lists(self):
        blocks = amd_blocks_text("- one\n- two")
        self.assertEqual(one(blocks, "list")["items"], ["one", "two"])
        blocks = amd_blocks_text("1. first\n2. second")
        self.assertTrue(one(blocks, "list")["ordered"])

    def test_table(self):
        blocks = amd_blocks_text("|a|b|\n|:--|--:|\n|1|2|")
        table = one(blocks, "table")
        self.assertEqual(table["rows"], [["a", "b"], ["1", "2"]])
        self.assertEqual(table["aligns"], ["l", "r"])

    def test_a_lone_pipe_line_is_prose(self):
        # A table needs two rows. One `|` line is a sentence about a pipe.
        self.assertEqual(kinds(amd_blocks_text("| not a table")), ["paragraph"])

    def test_media_and_ref_link(self):
        blocks = amd_blocks_text("![](image://nebula?scale=0.5)\n"
                                 "[Read on](ref://chapter2)")
        media = one(blocks, "media")
        self.assertEqual((media["ns"], media["url"]), ("image", "nebula"))
        self.assertEqual(media["options"], {"scale": "0.5"})
        self.assertEqual(one(blocks, "link")["target"], "chapter2")

    def test_a_line_that_merely_starts_with_a_bracket_is_prose(self):
        # RE_LINK_REF has to claim media mid-sentence, so it is permissive; the
        # scheme is what makes a line media.
        self.assertEqual(kinds(amd_blocks_text("[note] see the log")), ["paragraph"])

    def test_style_declaration_is_not_a_synopsis(self):
        # `= ` requires the space precisely so `=$name` stays a style line.
        blocks = amd_blocks_text("=$hdr font:gui-2;color:white;\n= an author note")
        self.assertEqual(kinds(blocks), ["style", "synopsis"])
        self.assertEqual(one(blocks, "style")["name"], "hdr")

    def test_callout_beats_transition(self):
        # Both open with `>`. A callout is `>` followed by `[!KIND]`.
        blocks = amd_blocks_text("> [!NOTE] Heads up\n> the rest of it\n\n> CUT TO:")
        self.assertEqual(kinds(blocks), ["callout", "transition"])
        callout = one(blocks, "callout")
        self.assertEqual(callout["kind"], "note")
        self.assertEqual(callout["title"], "Heads up")
        self.assertEqual(callout["lines"], ["the rest of it"])

    def test_bare_transition(self):
        self.assertEqual(one(amd_blocks_text("FADE IN:"), "transition")["text"],
                         "FADE IN:")

    def test_rule_and_break(self):
        self.assertEqual(kinds(amd_blocks_text("<hr>\n<br>")), ["rule", "break"])

    def test_comments_are_dropped(self):
        self.assertEqual(kinds(amd_blocks_text("// gone\nkept")), ["paragraph"])

    def test_wikilinks_are_recorded_on_the_paragraph(self):
        blocks = amd_blocks_text("See [[vex|the Ash-Captain]] about it.")
        self.assertEqual(one(blocks, "paragraph")["links"],
                         [{"target": "vex", "alias": "the Ash-Captain"}])


class TestFromNode(unittest.TestCase):
    def test_fence_lines_are_not_body(self):
        # amd_core appends every non-heading, non-fence line to body_lines and
        # then resets body_start past the closing `---`. Filtering on body_start
        # is what keeps the facts out of the prose.
        doc = parse("# [R](r)\n---\nSide: tsn\n---\nreal body\n")
        blocks = amd_blocks(doc.by_key["r"], doc=doc)
        self.assertEqual([b["text"] for b in blocks if b["type"] == "paragraph"],
                         ["real body"])
        self.assertNotIn("tsn", repr(blocks))

    def test_a_stray_line_before_the_fence_makes_it_prose(self):
        # Documented on RE_SYNOPSIS: a body line before the `---` means the
        # fence is no longer the record's first content, so the whole thing
        # reads as prose and every field in it is silently lost. Pinned here
        # because a renderer that quietly recovered them would disagree with
        # the game.
        doc = parse("# [R](r)\nstray\n---\nSide: tsn\n---\nreal body\n")
        self.assertEqual(doc.by_key["r"].data, {})

    def test_synopsis_never_reaches_a_player(self):
        doc = parse("# [R](r)\n= the twist is that he lied\nvisible prose\n")
        node = doc.by_key["r"]
        self.assertIn("synopsis", kinds(amd_blocks(node, doc=doc)))
        player = amd_blocks(node, doc=doc, profile="player")
        self.assertNotIn("synopsis", kinds(player))
        self.assertNotIn("twist", repr(player))

    def test_transclusion_resolves(self):
        doc = parse("# [A](a)\n![[b]]\n\n# [B](b)\nborrowed words\n")
        block = one(amd_blocks(doc.by_key["a"], doc=doc), "transclude")
        self.assertTrue(block["resolved"])
        self.assertEqual([b["text"] for b in block["blocks"]], ["borrowed words"])

    def test_unresolved_transclusion_still_says_so(self):
        # A printed page should show that something was meant to be here, the way
        # the linter reports the same target as dangling.
        block = one(amd_blocks(parse("# [A](a)\n![[nope]]\n").by_key["a"],
                               doc=parse("# [A](a)\n![[nope]]\n")), "transclude")
        self.assertFalse(block["resolved"])
        self.assertEqual(block["reason"], "unresolved")

    def test_self_transclusion_terminates(self):
        doc = parse("# [A](a)\n![[a]]\n")
        block = one(amd_blocks(doc.by_key["a"], doc=doc), "transclude")
        self.assertEqual(block["reason"], "cycle")

    def test_mutual_transclusion_terminates(self):
        doc = parse("# [A](a)\n![[b]]\n\n# [B](b)\n![[a]]\n")
        outer = one(amd_blocks(doc.by_key["a"], doc=doc), "transclude")
        inner = one(outer["blocks"], "transclude")
        self.assertEqual(inner["reason"], "cycle")


class TestPlayerProfile(unittest.TestCase):
    """`player` is a HARD filter, not a stylesheet class - "print to PDF" and
    "view source" have to agree about what a player was told."""

    def setUp(self):
        self.text = ("- [Pay](paid) if credits > 200 ; costs 200 credits\n"
                     "%{standing < -20} You again.\n")

    def test_guard_outcomes_and_target_are_absent(self):
        blocks = amd_blocks_text(self.text, profile="player")
        choice = one(blocks, "choice")
        self.assertEqual(choice["label"], "Pay")
        self.assertIsNone(choice["guard"])
        self.assertEqual(choice["outcomes"], [])
        self.assertEqual(choice["target"], "")
        self.assertNotIn("credits > 200", repr(blocks))

    def test_speech_gate_is_absent_but_the_line_survives(self):
        variant = one(amd_blocks_text(self.text, profile="player"),
                      "speech")["variants"][0]
        self.assertEqual(variant["text"], "You again.")
        self.assertIsNone(variant["gate"])

    def test_author_profile_keeps_all_of_it(self):
        blocks = amd_blocks_text(self.text)
        self.assertEqual(one(blocks, "choice")["guard"], "credits > 200")
        self.assertEqual(one(blocks, "speech")["variants"][0]["gate"],
                         "standing < -20")


if __name__ == "__main__":
    unittest.main()
