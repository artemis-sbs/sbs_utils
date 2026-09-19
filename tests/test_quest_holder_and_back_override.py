"""A console whose ship is not its own.

A pilot on the flight deck is assigned to the CARRIER, so the quest screens listed the
carrier's quests as "Ship"; `quest_holder_set` names another holder (the Flight Wing).
And a pilot in the cockpit picked the Hangar console, so every screen's
`gui_tab_back(CONSOLE_SELECT)` sent Back to the hangar; `gui_tab_back_override` fixes
that without touching the call sites.

    python -m unittest tests.test_quest_holder_and_back_override
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  breaks a circular import
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent, get_story_id
from sbs_utils.gui import GuiClient
from sbs_utils.procedural.quest import quest_add
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.offer import offer_clear
from sbs_utils.procedural import quest_driver as QD

CID = 0x8080000000000001


def _holder():
    a = Agent()
    a.id = get_story_id()
    a.add()
    return a.id


class QuestHolderTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        offer_clear()
        GuiClient(CID)
        self.carrier = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="Carrier"))
        self.wing = _holder()
        quest_add(self.carrier, "patrol", "Carrier Patrol", "")
        quest_add(self.carrier, "escort", "Carrier Escort", "", state=1)
        quest_add(self.wing, "cover", "Wing Cover", "")
        quest_add(self.wing, "strike", "Wing Strike", "", state=1)

    def tearDown(self):
        QD.quest_holder_clear(CID)
        offer_clear()

    def _titles(self, items):
        return [r.get("title") for r in items if QD._quest_offer_row(r) is not None]

    def _sections(self, items):
        return [getattr(i, "label", None) for i in items if QD._quest_offer_row(i) is None]

    def test_without_an_override_the_ship_is_listed(self):
        self.assertEqual(self._titles(QD.quest_tab_items(CID, self.carrier)), ["Carrier Escort"])
        self.assertEqual(self._titles(QD.quest_offers_tab_items(CID, self.carrier, "hangar")),
                         ["Carrier Patrol"])

    def test_the_holder_replaces_the_ship_under_its_own_label(self):
        QD.quest_holder_set(CID, self.wing, "Flight Wing")
        taken = QD.quest_tab_items(CID, self.carrier)
        self.assertEqual(self._titles(taken), ["Wing Strike"])
        self.assertIn("Flight Wing", self._sections(taken))
        self.assertEqual(self._titles(QD.quest_offers_tab_items(CID, self.carrier, "hangar")),
                         ["Wing Cover"])

    def test_clearing_gives_the_ship_back(self):
        QD.quest_holder_set(CID, self.wing, "Flight Wing")
        QD.quest_holder_clear(CID)
        self.assertEqual(self._titles(QD.quest_tab_items(CID, self.carrier)), ["Carrier Escort"])

    def test_the_offer_provider_asks_about_the_holder_too(self):
        QD.quest_holder_set(CID, self.wing, "Flight Wing")
        titles = [r.get("title") for r in QD.quest_offer_rows(CID, self.carrier)]
        self.assertEqual(titles, ["Wing Cover"])


class BackOverrideTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        GuiClient(CID)

    def tearDown(self):
        from sbs_utils.procedural.gui.console_tab import gui_tab_back_override_clear
        gui_tab_back_override_clear(CID)

    def test_the_override_replaces_what_a_screen_asks_for(self):
        from sbs_utils.procedural.gui.console_tab import _back_tab_for, gui_tab_back_override
        self.assertEqual(_back_tab_for(CID, "hangar"), "hangar")
        gui_tab_back_override(CID, "cockpit")
        self.assertEqual(_back_tab_for(CID, "hangar"), "cockpit")

    def test_clearing_restores_the_screens_choice(self):
        from sbs_utils.procedural.gui.console_tab import (
            _back_tab_for, gui_tab_back_override, gui_tab_back_override_clear)
        gui_tab_back_override(CID, "cockpit")
        gui_tab_back_override_clear(CID)
        self.assertEqual(_back_tab_for(CID, "hangar"), "hangar")


if __name__ == "__main__":
    unittest.main()
