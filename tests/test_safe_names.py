"""A name reaching the engine must not carry the engine's own control characters.

`ascii_name` (test_ascii_names.py) covers the RENDERER's non-ASCII bug. This covers a
different class: characters that are perfectly good ASCII but mean something to the
engine, so they corrupt whatever draws the name instead of merely looking wrong.

  ^   the engine's line break, and the separator in `send_client_widget_list`. Backtick
      quoting does NOT neutralise it - `text_area` says so explicitly - so a caret in a
      name splits it across two lines on every screen that draws it.
  ;   terminates a style property. `gui_text_escape` protects the callers that use it,
      but the common mission spelling is a hand-built `f"$text:{name};"`, and there the
      name ends early and its tail is parsed as styling.
  `   the quoting delimiter itself.
  control characters, newline included.

Two paths had to be covered, and only one of them existed before: `set_name` folded the
name, but `spawn_common` writes `name_tag` directly, so every npc_spawn / player_spawn /
terrain_spawn name skipped even the ASCII fold. The typein is the third - it is where a
player-typed ship name enters, and it only ever stripped the backtick.

`:` is deliberately NOT stripped: legitimate in a name, and it cannot start a property
on its own.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import Context, FrameContext, FakeEvent
from sbs_utils.spaceobject import SpaceObject, safe_name
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.pages.layout.text_input import TextInput


class TestSafeName(unittest.TestCase):
    def test_a_clean_name_is_returned_unchanged(self):
        """The common path must not copy or allocate."""
        for s in ("Artemis", "DS 1", "Home: Reborn", "double  space", ""):
            self.assertIs(safe_name(s), s)

    def test_caret_becomes_a_space(self):
        # Dropping it would run the words together; the caret was a break.
        self.assertEqual(safe_name("Ares^Beta"), "Ares Beta")

    def test_semicolon_becomes_a_space(self):
        self.assertEqual(safe_name("Ares;color:red"), "Ares color:red")

    def test_newline_and_other_controls_become_a_space(self):
        self.assertEqual(safe_name("Ares\nBeta"), "Ares Beta")
        self.assertEqual(safe_name("Ares\r\tBeta\x00"), "Ares Beta")

    def test_backtick_is_dropped_not_spaced(self):
        # Matches gui_text_escape, which strips its own delimiter.
        self.assertEqual(safe_name("A`res"), "Ares")

    def test_whitespace_runs_collapse_only_when_something_was_stripped(self):
        self.assertEqual(safe_name("Ares^^^Beta"), "Ares Beta")
        self.assertEqual(safe_name("  ^Ares^  "), "Ares")
        # ...but a name that was already clean keeps its spacing verbatim.
        self.assertEqual(safe_name("Ares  Beta "), "Ares  Beta ")

    def test_colon_survives(self):
        self.assertEqual(safe_name("Home: Reborn"), "Home: Reborn")

    def test_the_ascii_fold_still_applies(self):
        """safe_name is the single call a name path needs - it does both jobs."""
        self.assertEqual(safe_name("Rŭrhi^Mŭrhi"), "Rurhi Murhi")

    def test_non_strings_pass_through(self):
        # None is a legal name at every spawn entry point.
        for v in (None, 7, ["a"]):
            self.assertIs(safe_name(v), v)


class TestNameReachesTheEngineClean(unittest.TestCase):
    """End to end, through the two writers of `name_tag`."""

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _spawn(self, name):
        sd = npc_spawn(0, 0, 0, name, "tsn", "behav_npcship", "behav_npcship")
        return to_object(sd.id)

    def test_spawn_sanitises(self):
        """The path that had NO sanitising at all - it wrote the blob directly."""
        obj = self._spawn("Ares^Beta;x")
        self.assertEqual(obj.name, "Ares Beta x")
        self.assertEqual(obj.space_object().data_set.get("name_tag", 0), "Ares Beta x")

    def test_spawn_sanitises_the_comms_id_too(self):
        # `_comms_id` is derived from the name inside spawn_common; it must not be
        # built from the raw one.
        obj = self._spawn("Ares^Beta")
        self.assertNotIn("^", obj.comms_id)

    def test_rename_sanitises(self):
        obj = self._spawn("Ares")
        obj.name = "Beta^Gamma"
        self.assertEqual(obj.name, "Beta Gamma")
        self.assertEqual(obj.space_object().data_set.get("name_tag", 0), "Beta Gamma")


class TestTypeinRejectsTheCaret(unittest.TestCase):
    """The typein is where a player-typed ship name enters.

    Stripped here as well as in `safe_name`, because the value also round-trips to the
    bound variable and to persistence, and because the box itself would show the break.
    Dropped rather than spaced: a keystroke that silently becomes a space reads as a bug.
    """

    def test_caret_is_dropped(self):
        self.assertEqual(TextInput._sanitize("Ares^Beta"), "AresBeta")

    def test_backtick_still_dropped(self):
        self.assertEqual(TextInput._sanitize("A`res"), "Ares")

    def test_controls_dropped(self):
        self.assertEqual(TextInput._sanitize("Ares\nBeta\x00"), "AresBeta")

    def test_punctuation_a_player_may_legitimately_type_survives(self):
        # ':' and ';' are safe here - _text_prop re-quotes the value on every present.
        self.assertEqual(TextInput._sanitize("hi: there; ok"), "hi: there; ok")

    def test_empty_and_none_survive(self):
        self.assertEqual(TextInput._sanitize(""), "")
        self.assertIsNone(TextInput._sanitize(None))

    def test_a_typed_caret_is_pushed_back_to_the_box(self):
        """on_message must repaint when it had to change the value."""
        ti = TextInput("7", "")
        ti._value = "Ares"
        marked = []
        ti.mark_value_dirty = lambda *a, **k: marked.append(True)
        ti.update_variable = lambda *a, **k: None
        ti.on_message(FakeEvent(sub_tag="7", value_tag="Ares^Beta"))
        self.assertEqual(ti._value, "AresBeta")
        self.assertTrue(marked, "the box still shows the caret the player typed")


if __name__ == "__main__":
    unittest.main()
