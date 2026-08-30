"""A ship name reaching the engine must be 7-bit ASCII.

The engine ACCEPTS non-ASCII everywhere it was tested on 2026-08-30: `name_tag` stores
and returns it byte-identical up to 2048 UTF-8 bytes, `print()` in the embedded
interpreter is fine, the GUI style parser accepts it, and it survives a client
connecting. Only the RENDERER is wrong - it expands the UTF-8 bytes into characters, so
the name draws as a long run of garbage. Confirmed on screen, which is the only place it
could be confirmed.

`names.py` seeds the Kralien generator from alphabets containing s-circumflex and
u-breve, so roughly 40% of Kralien names hit it. The NAME DATA IS DELIBERATELY LEFT
ALONE: folding at `set_name` keeps the generator's flavour, catches every other source
of a name (a crew typing one in the lobby, a game code's SHIP_LOADOUT, a mod roster),
and makes the revert one line when the engine is fixed.

These tests pin the behaviour AND the revert switch, so turning `ASCII_NAMES` off does
not quietly fail a test that looks unrelated.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.spaceobject as SO
from sbs_utils.spaceobject import ascii_name
import sbs_utils.names as names


class TestAsciiName(unittest.TestCase):
    def test_ascii_is_returned_unchanged(self):
        """The common path must not copy, translate or allocate."""
        for s in ("Artemis", "DS 1", "Captain's Davey Jones of the Mistress", ""):
            self.assertIs(ascii_name(s), s)

    def test_the_two_characters_names_py_actually_emits(self):
        self.assertEqual(ascii_name("Rŭrhi-Mŭrhi"), "Rurhi-Murhi")
        self.assertEqual(ascii_name("Ŝenzo-Yenzo"), "Senzo-Yenzo")

    def test_the_rest_of_the_esperanto_family(self):
        self.assertEqual(ascii_name("ĉĝĥĵ"), "cghj")
        self.assertEqual(ascii_name("ĈĜĤĴ"), "CGHJ")

    def test_accents_decompose_rather_than_vanish(self):
        # A person typing a name in the lobby is the likely source here, and losing the
        # letter entirely would be worse than losing the accent.
        self.assertEqual(ascii_name("Café Naïve"), "Cafe Naive")

    def test_typographic_punctuation_becomes_its_ascii_twin(self):
        self.assertEqual(ascii_name("‘q’"), "'q'")
        self.assertEqual(ascii_name("a—b"), "a-b")

    def test_unmappable_characters_are_dropped_not_placeheld(self):
        # A run of '?' is exactly the garbage this exists to prevent.
        out = ascii_name("中文 ok \U0001F680")
        self.assertTrue(out.isascii())
        self.assertIn("ok", out)
        self.assertNotIn("?", out)

    def test_every_generated_kralien_name_folds_to_ascii(self):
        """The real-world case, at volume - the raw generator fails this."""
        raw = [names.name_random_kralien(i) for i in range(2000)]
        self.assertTrue(any(not n.isascii() for n in raw),
                        "generator no longer emits non-ASCII; this test is now vacuous "
                        "and the workaround may be removable")
        for n in raw:
            self.assertTrue(ascii_name(n).isascii())

    def test_non_strings_pass_through(self):
        for v in (None, 7, ["a"]):
            self.assertIs(ascii_name(v), v)

    def test_the_revert_switch_works(self):
        """ASCII_NAMES = False is the whole revert. Pin it so it stays that simple."""
        prev = SO.ASCII_NAMES
        try:
            SO.ASCII_NAMES = False
            self.assertEqual(ascii_name("Rŭrhi"), "Rŭrhi")
        finally:
            SO.ASCII_NAMES = prev
        self.assertEqual(ascii_name("Rŭrhi"), "Rurhi")


if __name__ == "__main__":
    unittest.main()
