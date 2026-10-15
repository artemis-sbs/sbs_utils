"""A quest-log row's identity survives a rebuild; its index does not.

The Quest Log repaints whenever a listed quest changes state and carried its selection
across by INDEX, so the selection jumped to another quest when the rows re-sorted. These
are the helpers LegendaryMissions' quest_tab.mast now carries it by.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.gui.listbox import gui_list_box_header
from sbs_utils.procedural.quest import (quest_log_row_key, quest_log_index_of,
                                        quest_log_hint_rekey)


def _row(key, agent=7, group="Game", title=None):
    return MastDataObject({"agent_id": agent, "key": key, "group": group,
                           "title": title or key, "state": 1})


class QuestLogRowKey(unittest.TestCase):
    def test_a_rebuilt_row_has_the_same_identity(self):
        self.assertEqual(quest_log_row_key(_row("alpha")), quest_log_row_key(_row("alpha")))

    def test_the_same_key_on_another_holder_is_another_row(self):
        self.assertNotEqual(quest_log_row_key(_row("alpha", agent=7)),
                            quest_log_row_key(_row("alpha", agent=8)))

    def test_a_parent_quest_header_is_the_row_it_was(self):
        """A quest becomes a header when its first step appears - still the same quest."""
        row = _row("arc")
        header = gui_list_box_header("arc", False, 1, True, _row("arc"))
        self.assertEqual(quest_log_row_key(header), quest_log_row_key(row))

    def test_a_section_header_is_keyed_by_its_label(self):
        a = gui_list_box_header("Game", False, 0, True, {"section": "Game"})
        b = gui_list_box_header("Game", False, 0, True, {"section": "Game"})
        self.assertEqual(quest_log_row_key(a), quest_log_row_key(b))
        self.assertNotEqual(quest_log_row_key(a), quest_log_row_key(_row("Game")))

    def test_none_is_none(self):
        self.assertIsNone(quest_log_row_key(None))


class QuestLogIndexOf(unittest.TestCase):
    def _items(self, *keys):
        return [gui_list_box_header("Game", False, 0, True, {"section": "Game"})] + \
            [_row(k) for k in keys]

    def test_the_index_follows_the_quest_after_a_reorder(self):
        key = quest_log_row_key(_row("charlie"))
        self.assertEqual(quest_log_index_of(self._items("alpha", "bravo", "charlie"), key), 3)
        self.assertEqual(quest_log_index_of(self._items("bravo", "charlie", "alpha"), key), 2)

    def test_a_quest_no_longer_listed_has_no_index(self):
        key = quest_log_row_key(_row("bravo"))
        self.assertIsNone(quest_log_index_of(self._items("alpha", "charlie"), key))

    def test_no_key_no_index(self):
        self.assertIsNone(quest_log_index_of(self._items("alpha"), None))


class QuestLogHintRekey(unittest.TestCase):
    def test_the_selection_is_replaced_and_the_view_kept(self):
        hint = {"cur": 4, "selected_index": 2, "slot": 1, "count": 9}
        out = quest_log_hint_rekey(hint, None)
        self.assertEqual(out, {"cur": 4, "selected_index": None, "slot": 1, "count": 9})
        self.assertEqual(hint["selected_index"], 2, "the caller's hint was modified")

    def test_no_hint_stays_no_hint(self):
        self.assertIsNone(quest_log_hint_rekey(None, 3))


if __name__ == "__main__":
    unittest.main()
