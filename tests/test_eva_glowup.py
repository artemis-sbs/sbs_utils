"""The rest of the EVA glow-up: what a crew in suits can do besides fly and talk.

* a quest's `reach <role>` counts a SUIT arriving, not only a player ship;
* a suit picks things up for the ship that sent it (`eva_suit_home`);
* an item's `Art:` may be a fallback chain, so pack art still spawns as something
  collectable in a mission without the pack;
* the Tasks app follows the crew member into a suit;
* `relic_section` reads another section of a relic's own file (its side stories);
* lint: `Done when: signal X` is a wait, a relic's `Starts when: signal X` consumes a
  signal, and the library's own outcome verbs are known.

Run: python -m unittest tests.test_eva_glowup
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import volume as V
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id

CID = 0x8000000000000001
RELIC = "gl_relic"

CONTENT = """# [Glow](gl_doc)

## [Relics](relics)

### [Glow Relic](gl_relic)
---
Loc: 0, 0, 0
Containment: none
---

### [hall](hall)
---
Relic: gl_relic
Box: 0, 0, 0, 1500, 300, 300
---

### [the end](far_end)
---
Relic: gl_relic
Point: 1200, 0, 0
Roles: gl_end
Scene: gl_end_look
---

### [the gate](gl_gate)
---
Relic: gl_relic
Prop: -900, 0, 0
Dress: generic-cylinder
Facing: 1, 0, 0
---

### [the find](gl_find)
---
Relic: gl_relic
Point: -1200, 0, 0
Item: gl_thing
Starts when: signal gl_found
---

## [Dialogue](dialogue)

### [The End](gl_end_look)
---
---
% The end of the hall.

- [Look](gl_end_look) ; check science 5 else gl_end_look, signal gl_found
- [Leave]()

## [Side Stories](side_stories)

### [The End](gl_story)
---
For: science
State: active
Done when: signal gl_found
Leads to: far_end
---
Get to the end.
"""


class _Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        TickDispatcher.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        R.relics_clear()
        A.boarding_clear()
        GuiClient(CID)
        R.relics_load("gl_test.amd", content=CONTENT)
        R.relic_volume(R.relic_record(RELIC))

    def tearDown(self):
        A.boarding_clear()
        E.eva_clear()
        R.relics_clear()
        RL.rail_clear()
        V.volume_clear()
        TickDispatcher.clear()

    def suit_up(self, at=(0, 0, 0), home=None):
        who = lifeform_spawn("Lt Glow", "terran_male", "boarding,science")
        A.boarding_assign(CID, who)
        suit = E.eva_suit_spawn(who, RELIC, at[0], at[1], at[2], hull="tsn_shuttle",
                                side="tsn")
        E.eva_take(CID, suit, RELIC, volume=RELIC, home=home)
        return who, suit


class QuestsCountSuits(_Base):
    def test_a_suit_arriving_completes_a_reach(self):
        from sbs_utils.procedural import quest_driver as QD
        from sbs_utils.procedural.quest import quest_add, quest_get_state, QuestState
        quest_add(CID, "gl_reach", "Reach the End", "",
                  state=QuestState.ACTIVE, data={"on_reach": {"role": "gl_end",
                                                              "radius": 400}})
        R.relic_contents_arm(RELIC)                 # the role marker at the point
        self.suit_up(at=(1200, 0, 100))
        QD.quest_tick_reach()
        self.assertEqual(quest_get_state(CID, "gl_reach"), QuestState.COMPLETE)


def amd_doc_section(doc, key):
    from sbs_utils.procedural.amd_doc import amd_section
    return amd_section(doc, key)


class ASuitCollectsForItsShip(_Base):
    def test_the_home_ship_is_found_from_the_suit(self):
        from sbs_utils.procedural.spawn import player_spawn
        ship = player_spawn(0, 0, 5000, "Home", "tsn", "tsn_light_cruiser")
        _who, suit = self.suit_up(home=ship)
        self.assertEqual(E.eva_suit_home(suit), to_id(ship))

    def test_a_suit_with_nobody_in_it_has_no_home(self):
        self.assertIsNone(E.eva_suit_home(123456))


class ItemArtChains(unittest.TestCase):
    def test_the_first_known_key_wins(self):
        from sbs_utils.procedural.items import _item_art
        self.assertEqual(_item_art("not_a_ship_key_xyz, alien_1a"), "alien_1a")
        self.assertEqual(_item_art("alien_1a"), "alien_1a")
        self.assertEqual(_item_art("unknown"), "unknown")


class TheTasksAppFollowsTheCrew(_Base):
    def test_tasks_are_available_in_a_suit(self):
        from sbs_utils.procedural.gui import xess_ground as G
        self.assertFalse(G._tasks_available(CID))
        self.suit_up()
        self.assertTrue(G._tasks_available(CID))

    def test_the_scan_app_is_available_in_a_suit(self):
        from sbs_utils.procedural.gui import xess as X
        self.assertFalse(X._scan_available(CID))
        self.suit_up()
        self.assertTrue(X._scan_available(CID))


class RelicSections(_Base):
    def test_a_relic_reads_its_own_side_stories(self):
        section = R.relic_section(RELIC, "side_stories")
        self.assertEqual([n.get("key") for n in section["children"]], ["gl_story"])

    def test_an_unknown_relic_has_none(self):
        self.assertIsNone(R.relic_section("nope", "side_stories"))

    def test_a_prop_is_scenery_not_a_place(self):
        rec = R.relic_record(RELIC)
        self.assertIn("gl_gate", rec.get("props"))
        self.assertNotIn("gl_gate", rec.get("points"))

    def test_a_prop_set_piece_stands_where_it_is_put(self):
        made, skip = R.relic_setpieces_place(RELIC, roles="gl_wall")
        self.assertEqual(made, 1)
        self.assertEqual(skip, set())


class TheLint(unittest.TestCase):
    def rules(self, content):
        from sbs_utils.procedural.amd_lint import amd_lint
        return [str(f).rsplit("(", 1)[-1].rstrip(")") for f in amd_lint(content=content)]

    def test_done_when_is_a_wait(self):
        from sbs_utils.procedural import amd_core as C
        doc = C.parse(CONTENT)
        story = [n for n in doc.nodes if n.key == "gl_story"][0]
        self.assertEqual([(r.kind, r.value) for r in story.refs],
                         [("wait_signal", "gl_found")])

    def test_the_library_verbs_are_known(self):
        self.assertNotIn("unknown-outcome-verb", self.rules(CONTENT))

    def test_a_relic_trigger_consumes_a_signal(self):
        from sbs_utils.procedural import amd_core as C
        from sbs_utils.procedural.amd_lint import amd_lint_cross_file
        doc = C.parse(CONTENT)
        found = amd_lint_cross_file(doc, mast_sources=[""])
        self.assertNotIn("signal-no-route",
                         [str(f).rsplit("(", 1)[-1].rstrip(")") for f in found])


if __name__ == "__main__":
    unittest.main()
