"""A `;` in a name must not break the quest-log listbox (PRM-19).

`;` is the style-string separator, so a name interpolated raw into `$text:{name};...`
closes the property early and the rest of the name is parsed as further style
properties - which corrupts the row. `gui_text_escape` (helpers.py) backtick-quotes a
dynamic value so `:` and `;` stay literal; it was added for issue #569 and applied to
the mission-selection screen, but the quest log was never converted.

This bites the LIVE quests tab and the end-game results screen equally, because
`quest_log_template` is shared by both - and a quest TITLE with a `;` trips it with no
player input at all.

    python -m unittest tests.test_quest_log_escape
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
import sbs_utils.procedural.gui as G
from sbs_utils.helpers import gui_text_escape
from sbs_utils.procedural.quest import quest_log_template, QuestState
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.gui import gui_list_box_header


NASTY = "Artemis; color:red"   # a ship name (or quest title) a player can type


class GuiTextEscapeTests(unittest.TestCase):
    """The helper's contract, which the template relies on."""

    def test_semicolon_is_quoted_not_dropped(self):
        out = gui_text_escape(NASTY)
        self.assertTrue(out.startswith("`") and out.endswith("`"),
                        f"value not backtick-quoted: {out!r}")
        self.assertIn(";", out, "the semicolon must survive, quoted - not be stripped")

    def test_empty_and_none_emit_nothing(self):
        # `$text:;` with no stray backtick (issue #641).
        self.assertEqual(gui_text_escape(None), "")
        self.assertEqual(gui_text_escape(""), "")


class _Recorder:
    """Stand in for the GUI layer: record props, build nothing, never raise.

    quest_log_template imports its GUI functions INSIDE the function body, so
    replacing them on the module is enough - and it keeps the test off the live
    page/layout machinery, which is not what is under test here.
    """

    def __init__(self):
        self.texts = []

    def install(self):
        self._saved = {n: getattr(G, n) for n in ("gui_row", "gui_text", "gui_icon_name")}
        G.gui_row = lambda *a, **k: None
        G.gui_icon_name = lambda *a, **k: None
        G.gui_text = lambda props, *a, **k: self.texts.append(props)

    def restore(self):
        for n, fn in self._saved.items():
            setattr(G, n, fn)


class QuestLogTemplateEscapeTests(unittest.TestCase):
    """The template must never hand a raw `;` to the style parser."""

    def _render(self, item):
        rec = _Recorder()
        rec.install()
        try:
            quest_log_template(item)
        finally:
            rec.restore()
        self.assertTrue(rec.texts, "template produced no $text props to check")
        return rec.texts

    def _assert_escaped(self, props_list):
        """Any `$text:` carrying our nasty value must have it backtick-quoted."""
        checked = 0
        for props in props_list:
            if "$text:" not in props or "Artemis" not in props:
                continue
            checked += 1
            value = props.split("$text:", 1)[1]
            self.assertTrue(
                value.startswith("`"),
                f"dynamic value not escaped - its ';' will terminate the property: {props!r}")
            self.assertIn("Artemis; color:red`", value,
                          f"name did not survive intact inside the quotes: {props!r}")
        self.assertTrue(checked, "the nasty value never reached a $text prop")

    def test_leaf_row_title_is_escaped(self):
        """A quest TITLE with a `;` - an AMD author trips this with no player input."""
        row = MastDataObject({
            "agent_id": 0, "key": "job", "group": "You", "indent": 0,
            "title": NASTY, "state": int(QuestState.ACTIVE),
            "state_label": "Active", "progress": 0, "desc": "",
            "kind": "job", "need": 0, "reward": "", "remaining": "",
        })
        self._assert_escaped(self._render(row))

    def test_group_header_label_is_escaped(self):
        """The group header carries the SHIP NAME - the case that was reported."""
        hdr = gui_list_box_header(NASTY, False, 1, True, {}, visual_indent=0)
        self._assert_escaped(self._render(hdr))

    def test_parent_quest_header_label_is_escaped(self):
        """A parent quest header (its data carries a `key`) takes the other branch."""
        hdr = gui_list_box_header(NASTY, False, 1, True,
                                  {"key": "arc", "state": int(QuestState.ACTIVE)},
                                  visual_indent=0)
        self._assert_escaped(self._render(hdr))


if __name__ == "__main__":
    unittest.main()
