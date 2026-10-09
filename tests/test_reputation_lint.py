"""`sbs lint` on the reputation lines: an `earns` that moves nothing anybody reads.

`earns guild honset 20` used to be silent and inert - `reputation._axis_sign` makes up an
axis called `honset` on the spot, and no side values it. Same for a side nobody declared.
And the words a standalone mission may now write (`standing`, `earns`, `Values:`,
`Side:` on a character) must lint clean with no vocabulary file of the mission's own.

    python -m unittest tests.test_reputation_lint
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_lint import amd_lint

NL = "\n"

HEAD = NL.join([
    "# [Sample Mission](sample_mission)",
    "",
    "## [Sides](sides)",
    "",
    "### [TSN](tsn)",
    "---",
    "Color: #07F",
    "---",
    "The crew's own side.",
    "",
    "### [Harbor Guild](guild)",
    "---",
    "Color: #0C6",
    "Allies: tsn",
    "Values: honest 40, generous 30",
    "---",
    "The pilots and tug crews.",
    "",
    "## [Characters](characters)",
    "",
    "### [Harbormaster Quill](quill)",
    "---",
    "Side: guild",
    "---",
    "Runs traffic control.",
    "",
])


def _mission(reward="150 credits, earns guild honest 30",
             outcome="earns guild generous 30"):
    return HEAD + NL.join([
        "## [Quests](quests)",
        "",
        "### [Tag the Hulk](tag_hulk)",
        "---",
        "Scope: shared",
        "Starts when: at once",
        "Done when: signal tagged",
        f"Reward: {reward}",
        "---",
        "Hang a beacon on the hulk.",
        "",
        "## [Dialogue](dialogue)",
        "",
        "### [Quill Checks In](quill_hello)",
        "---",
        "Speaker: quill",
        "When: hail",
        "---",
        "%{standing < 30} Artemis, DS 1. State your business.",
        "%{standing >= 30} Artemis! Good to hear a friendly voice.",
        "",
        "- [Just passing through.]()",
        f"- [We paid the tug crews.]() ; {outcome}",
        "- [Open the Guild yard to us.]() if standing >= 30",
        "- [Ask a favor.]() if honest >= 20",
        "",
    ])


def _codes(text, **kw):
    kw.setdefault("cross_file", False)
    return [f.code for f in amd_lint(content=text, **kw)]


def _find(text, code, **kw):
    kw.setdefault("cross_file", False)
    return [f for f in amd_lint(content=text, **kw) if f.code == code]


class WhatAWriterMayNowWrite(unittest.TestCase):
    def test_the_whole_thing_lints_clean(self):
        self.assertEqual(_codes(_mission()), [])
        self.assertEqual(_codes(_mission(), mast_sources=['x = "tsn"']), [])

    def test_earns_is_a_known_outcome_verb_with_no_mission_vocabulary(self):
        self.assertNotIn("unknown-outcome-verb", _codes(_mission()))

    def test_side_on_a_character_is_a_known_field(self):
        self.assertNotIn("unknown-field", _codes(_mission()))

    def test_a_hyphenated_or_spaced_trait_is_the_same_trait(self):
        for spelled in ("by-the-book", "By The Book", "by_the_book"):
            self.assertEqual(_codes(_mission(outcome=f"earns guild {spelled} 5")), [],
                             spelled)

    def test_a_sign_on_the_number_is_fine(self):
        self.assertEqual(_codes(_mission(reward="earns guild honest +10",
                                         outcome="earns guild selfish -5")), [])


class AnUnknownSide(unittest.TestCase):
    def test_in_a_choice(self):
        found = _find(_mission(outcome="earns gild generous 30"), "earns-unknown-side")
        self.assertEqual(len(found), 1)
        self.assertIn("`gild` is not a side", found[0].message)
        self.assertIn("guild, tsn", found[0].message)

    def test_in_a_reward_and_in_a_penalty(self):
        self.assertEqual(len(_find(_mission(reward="150 credits, earns gild honest 30"),
                                   "earns-unknown-side")), 1)
        text = _mission().replace("Reward: 150", "Penalty: earns gild honest -5" + NL
                                  + "Reward: 150")
        self.assertEqual(len(_find(text, "earns-unknown-side")), 1)

    def test_a_character_may_be_regarded_personally(self):
        # Open Universe's captains: `earns vex fearsome 10`. Any key in the mission.
        self.assertEqual(_codes(_mission(outcome="earns quill kind 5")), [])
        self.assertEqual(_codes(_mission(outcome="earns vex kind 5"), known_keys={"vex"}),
                         [])

    def test_a_side_made_in_mast_counts_when_the_mast_was_read(self):
        text = _mission(outcome="earns raider fearsome 5")
        self.assertIn("earns-unknown-side", _codes(text, mast_sources=["x = 1"]))
        self.assertNotIn("earns-unknown-side",
                         _codes(text, mast_sources=['prefab_spawn(p, {"key": "raider"})']))

    def test_a_file_with_no_sides_and_no_mast_is_not_second_guessed(self):
        text = _mission(outcome="earns gild generous 30")
        body = text[text.index("## [Quests]"):]
        self.assertNotIn("earns-unknown-side", _codes("# [M](m)" + NL + NL + body))


class AnUnknownTrait(unittest.TestCase):
    def test_in_a_choice(self):
        found = _find(_mission(outcome="earns guild honset 30"), "earns-unknown-trait")
        self.assertEqual(len(found), 1)
        self.assertIn("`honset` is not a trait", found[0].message)
        self.assertIn("honest", found[0].message)

    def test_in_a_reward(self):
        self.assertEqual(len(_find(_mission(reward="earns guild honset 30"),
                                   "earns-unknown-trait")), 1)

    def test_a_trait_some_side_here_values_is_known(self):
        text = _mission(outcome="earns guild thrifty 5").replace(
            "Values: honest 40, generous 30", "Values: honest 40, thrifty 30")
        self.assertNotIn("earns-unknown-trait", _codes(text))

    def test_it_is_judged_even_where_the_side_cannot_be(self):
        text = _mission(outcome="earns guild honset 30")
        body = text[text.index("## [Quests]"):]
        self.assertIn("earns-unknown-trait", _codes("# [M](m)" + NL + NL + body))


class TheShape(unittest.TestCase):
    def test_no_number(self):
        self.assertIn("earns-shape", _codes(_mission(outcome="earns guild honest")))
        self.assertIn("earns-shape", _codes(_mission(reward="earns guild honest")))

    def test_a_number_written_out(self):
        self.assertIn("earns-shape", _codes(_mission(outcome="earns guild honest ten")))

    def test_a_missing_comma_in_a_reward(self):
        found = _find(_mission(reward="150 credits earns guild honest 30"), "earns-shape")
        self.assertEqual(len(found), 1)
        self.assertIn("comma before `earns`", found[0].message)

    def test_every_message_is_ascii(self):
        for text in (_mission(outcome="earns gild honset 30"),
                     _mission(outcome="earns guild honest"),
                     _mission(reward="150 credits earns guild honest 30")):
            for f in amd_lint(content=text, cross_file=False):
                self.assertTrue(f.message.isascii(), f.message)


if __name__ == "__main__":
    unittest.main()
