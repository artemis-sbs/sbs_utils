"""A boarding party with nowhere to walk still gets the xESS - alone, across the screen.

The crew console was withheld from a party that only talks its way through a place (rooms
written as scenes, no interior, no tile area): a map of nothing beside the device would
have replaced a screen that worked with a mostly empty one. So that party had no console
at all. Its room and its choices went to the crew's MAIL, and the crew were left on the
ePADD app that had offered BEAM DOWN - seen in the engine, 2026-10-03.

The xESS is the boarding party's surface with a floor or without one. And a mission that
loads no boarding console at all is told so, in the log everybody reads.

    python -m unittest tests.test_boarding_console_without_a_map
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_site as S
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.gui import boarding_console as C
from sbs_utils.procedural.gui.console_tab import (gui_tab_back_while_boarded,
                                                  gui_tab_boarded_back_clear)
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

ENG = 0x8000000000000002

MISSION = """# [Mission](mission)

## [The Watch](watch)
---
crew
Ship: Artemis
---

### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering
---

## [Scenes](boarding)

### [The Airlock](airlock)
% Cold.

- [Read the tags](airlock) if medical
- [Return to the ship]()
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        A.boarding_clear()
        gui_tab_boarded_back_clear()
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        self.addCleanup(gui_tab_boarded_back_clear)
        self.addCleanup(C.boarding_panel_width, C.MAP_WIDTH_DEFAULT)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        crew.crew_declare_amd(amd_document(MISSION, data_parser=amd_crew_data))
        self.scenes = dialogue_scenes(amd_section(amd_document(MISSION), "boarding"))
        GuiClient(ENG)
        set_inventory_value(ENG, "CONSOLE_TYPE", "engineering")
        link(self.ship, "consoles", ENG)
        crew.crew_assign(ENG, self.ship, "engineering")


class TheDeviceAloneTests(_Base):
    def build(self):
        """Build the console with the three things it draws swapped for recorders."""
        import sbs_utils.procedural.gui.section as section_mod
        import sbs_utils.procedural.gui.widgets as widgets_mod
        import sbs_utils.procedural.gui.xess as xess_mod
        drawn = {"sections": [], "widgets": [], "device": 0}
        real = (section_mod.gui_section, widgets_mod.gui_layout_widget, xess_mod.gui_xess)
        section_mod.gui_section = lambda style=None: drawn["sections"].append(style)
        widgets_mod.gui_layout_widget = lambda name: drawn["widgets"].append(name)

        def device(cid):
            drawn["device"] += 1
            return {"cid": cid}
        xess_mod.gui_xess = device
        try:
            C.gui_boarding_console(ENG)
        finally:
            (section_mod.gui_section, widgets_mod.gui_layout_widget,
             xess_mod.gui_xess) = real
        return drawn

    def test_a_console_with_no_body_on_a_floor_has_no_ground(self):
        self.assertFalse(C.boarding_has_ground(ENG))

    def test_with_nowhere_to_walk_there_is_no_map(self):
        drawn = self.build()
        self.assertEqual(drawn["widgets"], [])
        self.assertEqual(drawn["sections"], [])

    def test_and_the_device_takes_the_whole_width(self):
        self.build()
        self.assertEqual(C.panel_left(), 1)
        self.assertTrue(C.boarding_identity_area().startswith("area: 1,"))
        self.assertTrue(C.boarding_app_area().startswith("area: 1,"))

    def test_the_device_is_still_built(self):
        self.assertEqual(self.build()["device"], 1)

    def test_an_interior_still_gets_its_map_beside_the_device(self):
        set_inventory_value(ENG, S.KEY_HOST, self.ship)
        self.assertTrue(C.boarding_has_ground(ENG))
        drawn = self.build()
        self.assertEqual(drawn["widgets"], ["ship_internal_view"])
        self.assertEqual(drawn["sections"], ["area:0,0,66,100;"])
        self.assertEqual(C.panel_left(), 67)


class WhatTheDeviceSaysTests(_Base):
    """The two things the first look at the real screen showed missing."""

    def setUp(self):
        super().setUp()
        gui_tab_back_while_boarded("boarding_crew")
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "airlock",
                                              title="The Hulk"))
        self.assertIsNotNone(A.boarding_beam_down(ENG))

    def test_the_bar_names_the_room_not_aboard(self):
        self.assertEqual(C.where_text(ENG), "The Airlock")

    def test_with_no_scene_open_it_still_says_something(self):
        A.boarding_scene_end()
        self.assertEqual(C.where_text(ENG), "aboard")

    def test_a_forwarded_choice_says_whose_job_it_is(self):
        text = A._boarding_beat_text(ENG)
        self.assertIn("[Read the tags (covering for medical)](signal://", text)

    def test_a_choice_of_ones_own_is_not_marked(self):
        text = A._boarding_beat_text(ENG)
        self.assertIn("[Return to the ship](signal://", text)


class _Listen(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class AVisitThatCannotWorkSaysSoTests(_Base):
    def setUp(self):
        super().setUp()
        self.heard = _Listen()
        log = logging.getLogger("mast.runtime")
        log.addHandler(self.heard)
        self.addCleanup(log.removeHandler, self.heard)

    def said(self, needle):
        return [l for l in self.heard.lines if needle in l]

    def test_a_first_room_that_is_not_a_room_is_reported_with_the_rooms_there_are(self):
        self.assertIsNone(A.boarding_visit(self.ship, self.scenes, "airlok", title="T"))
        line = self.said("no room 'airlok'")
        self.assertEqual(len(line), 1)
        self.assertIn("airlock", line[0])

    def test_no_rooms_at_all_says_so(self):
        self.assertIsNone(A.boarding_visit(self.ship, {}, "airlock", title="T"))
        self.assertEqual(len(self.said("none at all")), 1)

    def test_a_mission_with_no_boarding_console_is_told(self):
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "airlock", title="T"))
        self.assertEqual(len(self.said("no boarding console is loaded")), 1)

    def test_and_told_once_however_many_visits_it_opens(self):
        A.boarding_visit(self.ship, self.scenes, "airlock", title="T")
        A.boarding_visit_end()
        A.boarding_visit(self.ship, self.scenes, "airlock", title="T")
        self.assertEqual(len(self.said("no boarding console is loaded")), 1)

    def test_with_the_console_installed_nothing_is_said(self):
        gui_tab_back_while_boarded("boarding_crew")
        self.assertIsNotNone(A.boarding_visit(self.ship, self.scenes, "airlock", title="T"))
        self.assertEqual(self.heard.lines, [])

    def test_the_notice_comes_back_after_a_mission_reset(self):
        A.boarding_visit(self.ship, self.scenes, "airlock", title="T")
        A.boarding_clear()
        self.assertEqual(A.boarding_visit_said_count(), 0)


if __name__ == "__main__":
    unittest.main()
