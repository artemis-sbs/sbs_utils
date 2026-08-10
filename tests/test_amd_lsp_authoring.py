"""Tests for the AMD language server's authoring help: what completion offers WHERE,
and what hover explains.

    python -m unittest tests.test_amd_lsp_authoring
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_lsp as L
from sbs_utils.procedural.amd_core import parse

SRC = chr(10).join([
    "# [The Coils Overheat](ramscoop/coils)",
    "---",
    "Beat",
    "Starts when: revealed",
    "",
    "---",
    "Engineering reports the coils running hot.",
    "",
])
INDEX = {"known": {"ramscoop", "other_key"}}


def _labels(line, char):
    doc = parse(SRC, "x.amd")
    r = L._completion(INDEX, doc, {"line": line, "character": char}, SRC)
    return [i["label"] for i in r["items"]]


def _hover(line, char=3):
    doc = parse(SRC, "x.amd")
    h = L._hover(INDEX, doc, {"line": line, "character": char}, SRC)
    return (h or {}).get("contents", {}).get("value", "")


class CompletionIsPositionAware(unittest.TestCase):
    """It used to ignore position entirely and answer every request with the mission's
    node keys - so typing a fence offered keys and never a field name or a noun."""

    def test_the_kind_line_offers_nouns(self):
        labels = _labels(2, 4)
        self.assertIn("Beat", labels)
        self.assertIn("Arc", labels)
        self.assertNotIn("ramscoop", labels)

    def test_it_offers_a_MENU_not_the_validation_vocabulary(self):
        """48 entries counting every plural and section alias is a wall, not a choice."""
        labels = _labels(2, 4)
        self.assertLess(len(labels), 20)
        for noise in ("beats", "arcs", "cast", "crew", "bounties", "scenario", "lines"):
            self.assertNotIn(noise, labels, noise)
        self.assertNotIn("lifeform", labels)      # the author word is Character
        self.assertIn("Character", labels)

    def test_a_noun_says_what_it_implies(self):
        doc = parse(SRC, "x.amd")
        r = L._completion(INDEX, doc, {"line": 2, "character": 4}, SRC)
        beat = next(i for i in r["items"] if i["label"] == "Beat")
        self.assertIn("show: when done", beat.get("detail") or "")

    def test_a_fence_line_offers_field_labels(self):
        labels = _labels(4, 0)
        self.assertIn("Done when:", labels)
        self.assertIn("Fails when:", labels)

    def test_field_labels_are_sentence_case(self):
        self.assertNotIn("Done When:", _labels(4, 0))

    def test_internal_fields_are_not_offered(self):
        labels = _labels(4, 0)
        for gone in ("Fail after:", "Fail on signal:", "On kill:", "Win text:"):
            self.assertNotIn(gone, labels, gone)

    def test_after_a_label_it_offers_that_field_s_values(self):
        labels = _labels(3, 13)
        self.assertIn("revealed", labels)
        self.assertIn("accepted", labels)

    def test_the_body_still_offers_node_keys(self):
        self.assertIn("other_key", _labels(6, 5))


class HoverExplainsTheFence(unittest.TestCase):
    """Every field and noun carries an explanation in the schema; none of it used to
    reach the one place someone wonders what a word means."""

    def test_a_noun_hover_says_what_it_implies(self):
        v = _hover(2)
        self.assertIn("Beat", v)
        self.assertIn("show: when done", v)

    def test_a_field_hover_shows_the_schema_hint(self):
        v = _hover(3)
        self.assertIn("Starts when", v)
        self.assertIn("revealed", v)

    def test_the_canonical_spelling_is_readable(self):
        self.assertNotIn("Starts_when", _hover(3))

    def test_a_retired_field_says_so(self):
        src = chr(10).join(["# [x](k)", "---", "Beat", "Fail after: 5 minutes", "---", "p", ""])
        doc = parse(src, "x.amd")
        v = (L._hover(INDEX, doc, {"line": 3, "character": 3}, src) or {})
        self.assertIn("still parses", v.get("contents", {}).get("value", ""))


ACTION_SRC = chr(10).join([
    "# [The trap closes](ambush)",
    "---",
    "Beat",
    "Action:",
    "  - DS1 hails ds1_brief",
    "  - ",
    "Reward: 5 credits",
    "---",
    "Body text.",
    "",
])


def _action_labels(line, char):
    doc = parse(ACTION_SRC, "x.amd")
    r = L._completion({"known": {"ds1_brief", "other_key"}}, doc,
                      {"line": line, "character": char}, ACTION_SRC)
    return [i["label"] for i in r["items"]]


class CompletionInsideAnActionBlock(unittest.TestCase):
    """A direction is a LIST ITEM, so it carries no colon and `_fence_context` read it
    as "typing a field label" - offering field names in the one place a field name can
    never go, and never offering the verbs or the scene keys that DO go there."""

    def test_the_verbs_are_offered_after_the_actor(self):
        labels = _action_labels(4, len("  - DS1 "))
        self.assertIn("hails", labels)
        self.assertIn("becomes", labels)
        self.assertNotIn("Reward:", labels)

    def test_node_keys_are_offered_after_a_node_typed_verb(self):
        # `hails` declares operand_ref="node", which is the same thing
        # `dangling-action-ref` checks - so completion offers exactly what lint accepts.
        labels = _action_labels(4, len("  - DS1 hails "))
        self.assertIn("ds1_brief", labels)
        self.assertIn("other_key", labels)

    def test_a_verb_that_names_no_record_offers_nothing(self):
        # `becomes` takes a role, which is minted in MAST and in spawn CSVs - guessing
        # would offer the wrong vocabulary confidently.
        doc = parse(ACTION_SRC, "x.amd")
        src = ACTION_SRC.replace("  - DS1 hails ds1_brief", "  - DS1 becomes a")
        doc = parse(src, "x.amd")
        r = L._completion({"known": {"ds1_brief"}}, doc,
                          {"line": 4, "character": len("  - DS1 becomes ")}, src)
        self.assertEqual(r["items"], [])

    def test_an_empty_item_offers_who_acts(self):
        labels = _action_labels(5, len("  - "))
        self.assertIn("ds1_brief", labels)

    def test_a_field_line_outside_the_block_is_unaffected(self):
        labels = _action_labels(6, 0)
        self.assertNotIn("hails", labels)


if __name__ == "__main__":
    unittest.main()
