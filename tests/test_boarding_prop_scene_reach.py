"""A prop's scene happens AT the prop - and a downed crew member's open scene tells the
truth when she comes round. Both engine-seen, author course 3, sitting 4.

  * c3-15: the strongbox scene stayed open on Ross's Act after he walked ~25 cells away,
    and `Take her as a prize` worked from there.
  * c3-14: Dr Hale went DOWN at the yard terminal. A party that is all down comes round
    at the area's entry after `VISIT_REVIVE_SECONDS` at HP 1 - so the shots showed her
    on the landing pad, bar `landing pad - HP 1/3`, with `Dr Ines Hale is DOWN - needs a
    medkit. Nothing can be chosen until then.` standing over terminal buttons that
    worked. She was not down when she pressed (blue, upright, HP 1); what was wrong is
    that the line still said so, and that the terminal's scene had followed her across
    the yard.

THE RULE (`boarding_props`): a prop's scene holds whoever is within its `Reach:` plus
`PROP_SCENE_SLACK` (2, the ring a scene brings companions in from). Further, and the
console leaves the scene - once a second on a tile visit, and at once on a press that
arrives first, which does nothing.

Driven through the REAL console: `gui_boarding_console()` on a page, the Act app open,
its transcript's buttons pressed with `Gui.on_message` - a click on the console.

    python -m unittest tests.test_boarding_prop_scene_reach
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import unittest

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui, GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.vec import Vec3
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui import boarding_console as BC
from sbs_utils.procedural.gui import xess as X
from sbs_utils.procedural.gui import xess_ground  # noqa: F401  (registers Look/Pack/...)
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn

REACH_CID = 0x80000000000000B1
REACH_STORY = """
gui_boarding_console()
await gui()
"""

REACH_YARD = """area: yard
title: Kesh Relay
tileset: g
entry: landing_pad
legend:
  .: dirt
  #: rock
  P: dirt @landing_pad
---
####################
#P.................#
#..................#
####################
"""
REACH_KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

# The terminal at the far end of the yard, as c3-14 writes it.
REACH_PROPS = {"children": [
    {"key": "terminal", "display_text": "Yard terminal",
     "description": "A weatherproof terminal beside the relay door.",
     "data": {"area": "yard", "at": "16, 1", "sprite": "g:dirt", "scene": "terminal"}},
]}

REACH_SCENES = {
    "terminal": {"key": "terminal", "display_text": "The Yard Terminal", "data": {},
                 "description": "% DOOR SEALED. AWAITING CODE.\n"
                                "- [Read the log](terminal_log)\n"
                                "- [Step back]()\n"},
    "terminal_log": {"key": "terminal_log", "display_text": "Nine Days", "data": {},
                     "description": "% Nine days of crew lists.\n"
                                    "- [Step back](terminal)\n"},
}


class ConsolePage(StoryPage):
    story = None


class _ReachBase(unittest.TestCase):
    def setUp(self):
        clear_shared()
        SpaceObject.clear()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.aspect_ratios[REACH_CID] = Vec3(1280, 960, 0)
        self.addCleanup(FrameContext.aspect_ratios.pop, REACH_CID, None)
        for clear in (A.boarding_clear, T.tilemap_clear, BT.boarding_tile_clear,
                      P.boarding_props_clear, C.boarding_checks_clear,
                      K.boarding_combat_clear, X.xess_clear):
            clear()
            self.addCleanup(clear)
        Gui.clients[REACH_CID] = GuiClient(REACH_CID)
        T.tilemap_tileset("g", REACH_KINDS)
        T.tilemap_load(REACH_YARD)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()
        T.tilemap_set_clock(0.0)
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Kesh Relay", area="yard")
        body = lifeform_spawn("Dr Ines Hale", "", "boarding,medical")
        set_inventory_value(body.id, A.JOBS_KEY, ["medical", "science"])
        A.boarding_assign(REACH_CID, body.id)
        self.hale = body.id
        A.boarding_metric_install()
        P.boarding_props_declare(REACH_PROPS)
        P.boarding_props_place()
        P.boarding_props_scenes(REACH_SCENES)
        G.boarding_go_down(REACH_CID)
        # She walks up to the terminal and uses it - the scene opens on her Act.
        self.stand(15, 1)
        result, _ = P.boarding_interact(REACH_CID, "terminal")
        self.assertEqual("scene", result, "fixture: the terminal opened no scene")
        X.xess_open(REACH_CID, X.APP_ACT)

        story = MastStory()
        errors = story.compile(REACH_STORY, "propreach", story)
        self.assertEqual([], errors)
        story.compiler_errors = []
        ConsolePage.story = story
        FrameContext.mast = story
        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.errors.append

    def tearDown(self):
        MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        ConsolePage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        SpaceObject.clear()

    # --- driving the console -----------------------------------------------------------
    def stand(self, x, y):
        T.tilemap_place(self.hale, "yard", x, y)

    def build(self):
        """A fresh page from the current state - the Act app's real builder."""
        Gui.widget_list_sent = {}
        page = ConsolePage()
        Gui.push(REACH_CID, page)
        mock_sbs.sim._time_tick_counter += 30
        page.gui_state = "repaint"
        page.present(FakeEvent(REACH_CID, "gui_present"))
        self.assertEqual([], self.errors)
        return page

    def buttons(self):
        """{label: click tag} of the live buttons in the Act transcript just drawn."""
        area = A._READERS[REACH_CID]["area"]
        self.assertIsNotNone(area, "the Act app drew no transcript")
        return {c["display"]: tag for tag, c in area._choice_map.items()}

    def click(self, tag):
        FrameContext.context = Context(mock_sbs.sim, mock_sbs,
                                       FakeEvent(REACH_CID, "gui_message"))
        Gui.on_message(FakeEvent(client_id=REACH_CID, tag="gui_message", sub_tag=tag))

    def tick(self, n=1):
        visit = {"tile": True, "area": "yard", "down_for": 0}
        for _ in range(n):
            A._visit_tile_tick(visit)

    def scene(self):
        return A.boarding_scene("prop:terminal")

    def text(self):
        return A.boarding_reader_text(REACH_CID)


class AtThePropItAnswers(_ReachBase):
    def test_a_press_beside_the_terminal_moves_the_scene_on(self):
        """The fixture: the click path reaches `boarding_answer` and is accepted."""
        self.build()
        tags = self.buttons()
        self.assertIn("Read the log", tags)
        self.click(tags["Read the log"])
        self.assertEqual("terminal_log", self.scene(), "the console's press did nothing")

    def test_standing_a_little_off_she_is_still_in_it(self):
        """Within Reach + slack (the ring companions are brought in from): kept."""
        self.stand(16 - (1 + P.PROP_SCENE_SLACK), 1)
        self.tick()
        self.assertEqual("prop:terminal", A.boarding_channel_of(REACH_CID))
        self.build()
        self.click(self.buttons()["Read the log"])
        self.assertEqual("terminal_log", self.scene())


class WalkedAwayFromTheProp(_ReachBase):
    """c3-15: the strongbox scene answered from ~25 cells away."""

    def test_a_press_from_across_the_yard_does_nothing(self):
        self.build()
        tags = self.buttons()
        self.stand(2, 2)                       # walked off; no repaint yet
        self.click(tags["Read the log"])
        self.assertEqual("terminal", self.scene(),
                         "a press from across the yard applied the choice")
        self.assertNotEqual("prop:terminal", A.boarding_channel_of(REACH_CID),
                            "she is still in the terminal's scene")
        self.assertNotIn("chosen://", self.text(), "the refused press was written down")
        self.assertNotIn("Nine days", self.text())

    def test_the_tick_takes_her_out_of_the_scene(self):
        self.build()
        self.stand(2, 2)
        self.tick()
        self.assertNotEqual("prop:terminal", A.boarding_channel_of(REACH_CID),
                            "walking away left the scene open on her console")
        self.build()
        self.assertEqual({}, self.buttons(), "her Act still offers the terminal's choices")
        self.assertTrue(self.text().rstrip().endswith("The conversation is over."))

    def test_walking_back_up_picks_it_up_where_it_was(self):
        self.stand(2, 2)
        self.tick()
        self.stand(15, 1)
        self.assertEqual("scene", P.boarding_interact(REACH_CID, "terminal")[0])
        self.build()
        self.click(self.buttons()["Read the log"])
        self.assertEqual("terminal_log", self.scene())


class DownAtTheTerminal(_ReachBase):
    """c3-14: down at the terminal, then the party comes round on the landing pad."""

    def test_while_down_the_bar_says_so_and_a_press_does_nothing(self):
        self.build()
        tags = self.buttons()
        K.boarding_hurt(self.hale, 99)
        self.assertEqual("DOWN - needs a medkit", BC.where_text(REACH_CID))
        self.click(tags["Read the log"])       # a button drawn before she fell
        self.assertEqual("terminal", self.scene(), "a downed member's press applied")
        self.build()
        self.assertEqual({}, self.buttons(), "her buttons are still live while she is down")
        self.assertIn("Dr Ines Hale is DOWN - needs a medkit.", self.text())

    def test_come_round_on_the_pad_the_transcript_says_she_is_up_and_the_scene_is_left(self):
        self.build()
        tags = self.buttons()
        K.boarding_hurt(self.hale, 99)
        self.build()
        self.tick(A.VISIT_REVIVE_SECONDS)
        self.assertFalse(K.boarding_is_down(self.hale), "fixture: the party did not come round")
        self.assertEqual(("yard", 1, 1), T.tilemap_where(self.hale)[:3],
                         "fixture: she was not stood on the pad")
        # What the engine's bar showed, and right: she is up, at HP 1.
        self.assertEqual("landing pad - HP 1/3", BC.where_text(REACH_CID))
        self.click(tags["Read the log"])       # her old button, from the pad
        self.assertEqual("terminal", self.scene(), "the terminal answered a press from the pad")
        self.build()
        self.assertEqual({}, self.buttons(),
                         "the terminal's buttons followed her to the landing pad")
        text = self.text()
        down = text.index("Dr Ines Hale is DOWN")
        up = text.index("Dr Ines Hale is back on their feet.")
        self.assertLess(down, up, "the DOWN line was left standing as the last word")
        self.assertTrue(text.rstrip().endswith("The conversation is over."))

    def test_revived_where_she_fell_her_choices_come_back_under_the_line_saying_so(self):
        """A medkit beside the terminal: up again, still there, still in the scene."""
        self.build()
        K.boarding_hurt(self.hale, 99)
        self.build()
        K.boarding_revive(self.hale)
        self.tick()
        self.build()
        tags = self.buttons()
        self.assertIn("Read the log", tags)
        text = self.text()
        self.assertLess(text.index("is back on their feet."), text.index("Read the log"))
        self.click(tags["Read the log"])
        self.assertEqual("terminal_log", self.scene())


if __name__ == "__main__":
    unittest.main()
