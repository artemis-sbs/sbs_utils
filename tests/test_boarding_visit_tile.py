"""`boarding_visit` on a tile map: a visit with somewhere to walk and no first room.

`boarding_visit` owns a visit from start to finish, and until now it could only own a
TEXT one: it needs a first room, and its watcher ends the visit the moment no party scene
is open - which on a tile map is always. So Dawnline opened its party by hand, and handed
out side stories, revived a fallen party and ended the night in routes of its own.

A tile visit is `area` given and `first` left out, and nothing else: the text visit is
untouched (tests/test_boarding_visit.py is its proof and is not edited).

    python -m unittest tests.test_boarding_visit_tile
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_quests as Q
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import crew
from sbs_utils.procedural import signal as S
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural.amd import amd_choice_label
from sbs_utils.procedural.amd_dialogue import dialogue_scenes
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.quest import quest_get_state, QuestState
from sbs_utils.procedural.quest_driver import quest_grant_amd
from sbs_utils.procedural.settings import settings_get_defaults
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.signal import signal_observe, signal_unobserve
from sbs_utils.procedural.spawn import player_spawn

HELM = 0x8000000000000001
SCI = 0x8000000000000002
ENG = 0x8000000000000003

AREA = """area: landing
title: The Landing
tileset: vt
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  T: dirt @terminal
  B: dirt @beacon
---
############
#..........#
#.P....T...#
#..........#
#........B.#
############
"""

KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

WORLD = """# [Mission](mission)

## [Quests](quests)

### [Light the Beacon](light)
---
Scope: shared
Starts when: at once
Win: The beacon is lit. The convoy has its way home.
---
Get the beacon lit.

### [Keep the Relay](keep)
---
Scope: shared
Starts when: at once
Lose: The relay is slag, and the convoy flies on blind.
---
Do not break it.

## [Side Stories](side_stories)

### [The Reading](reading)
---
For: science
Done when: signal reading_taken
---
Take the reading.

## [Props](props)

### [Terminal](terminal)
---
Area: landing
Mark: terminal
Scene: terminal_read
Blocks: yes
---
A terminal.

### [Beacon](beacon)
---
Area: landing
Mark: beacon
Scene: beacon_scene
Blocks: yes
---
The beacon.

## [Scenes](scenes)

### [The terminal](terminal_read)
% One line, repeating.

- [Read it](terminal_read) ; learn manifest
- [Step back]()

### [The beacon](beacon_scene)
% Dark. A panel hangs open.

- [Light it]() ; completes light
- [Tear the panel out]() ; fails keep
- [Leave it]()
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        TickDispatcher.clear()
        crew.crew_clear()
        self.addCleanup(reset_mission_state)
        self.addCleanup(TickDispatcher.clear)
        self.addCleanup(crew.crew_clear)
        T.tilemap_tileset("vt", KINDS)
        T.tilemap_load(AREA)
        T.tilemap_set_clock(0.0)
        self.now = 0.0
        self.doc = amd_document(WORLD, data_parser=amd_mission_data)
        self.scenes = dialogue_scenes(amd_section(self.doc, "scenes"))
        self.stories = amd_section(self.doc, "side_stories")
        P.boarding_props_declare(amd_section(self.doc, "props"))
        P.boarding_props_place()
        P.boarding_props_install()
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        self.sit(HELM, "helm")
        self.sit(SCI, "science")
        self.seen = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)
        settings = settings_get_defaults()
        self.addCleanup(settings.__setitem__, "BOARDING_AUTO_BEAM",
                        settings.get("BOARDING_AUTO_BEAM", False))

    def _obs(self, name, data):
        self.seen.append((name, dict(data) if isinstance(data, dict) else data))

    def named(self, name):
        return [d for n, d in self.seen if n == name]

    def sit(self, client_id, console):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        link(self.ship, "consoles", client_id)
        crew.crew_assign(client_id, self.ship, console)

    def advance(self, seconds):
        """Real ticks: the visit's own watcher, the walk and the hostiles all run."""
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            self.now += 1.0 / TICKS_PER_SECOND
            T.tilemap_set_clock(self.now)
            TickDispatcher.dispatch_tick()
            sbs.sim._time_tick_counter += 1

    def open(self, **kw):
        kw.setdefault("title", "Kesh Relay")
        kw.setdefault("area", "landing")
        return A.boarding_visit(self.ship, self.scenes, **kw)

    def down(self, client_id=HELM):
        self.assertIsNotNone(A.boarding_beam_down(client_id))
        self.assertTrue(G.boarding_go_down(client_id))
        return A.boarding_me(client_id)

    def use(self, client_id, prop, starts_with):
        lf = A.boarding_me(client_id)
        at = T.tilemap_where(P.boarding_prop(prop)["id"])
        T.tilemap_place(lf, at[0], at[1] - 1, at[2])
        self.assertEqual(P.boarding_interact(client_id, prop)[0], "scene")
        labels = [amd_choice_label(c.get("label")) for c in A.boarding_choices(client_id)]
        index = next(i for i, text in enumerate(labels) if text.startswith(starts_with))
        self.assertTrue(A.boarding_answer(client_id, index, A.boarding_seq_for(client_id)))


class TheTileVisitOpensTests(_Base):
    def test_it_opens_the_party_and_begins_no_scene(self):
        invite = self.open()
        self.assertIsNotNone(invite)
        self.assertTrue(invite.get("crew"))
        self.assertEqual(A.boarding_invite_area(), "landing")
        self.assertEqual(A.boarding_invite_title(), "Kesh Relay")
        self.assertFalse(A.boarding_is_open())
        visit = A.boarding_visiting()
        self.assertTrue(visit.get("tile"))
        self.assertEqual(visit.get("area"), "landing")
        self.assertEqual(A.boarding_place(), "Kesh Relay")

    def test_it_is_not_ended_for_want_of_a_scene(self):
        """The whole reason a tile mission could not use `boarding_visit`."""
        self.open()
        self.advance(6)
        self.assertIsNotNone(A.boarding_visiting())
        self.assertIsNotNone(A.boarding_invitation())
        self.assertEqual(self.named("boarding_visit_ended"), [])

    def test_an_area_that_does_not_exist_opens_nothing_and_says_so(self):
        import logging
        lines = []

        class H(logging.Handler):
            def emit(self, record):
                lines.append(record.getMessage())
        h = H()
        logging.getLogger("mast.runtime").addHandler(h)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, h)
        self.assertIsNone(self.open(area="landng"))
        self.assertIsNone(A.boarding_invitation())
        self.assertIsNone(A.boarding_visiting())
        self.assertIn("no tile area 'landng'", "\n".join(lines))
        self.assertIn("landing", "\n".join(lines))

    def test_going_down_stands_you_at_the_entry(self):
        self.open()
        me = self.down()
        self.assertEqual(T.tilemap_where(me), ("landing", 2, 2))

    def test_the_scenes_are_wired_to_the_props(self):
        self.open()
        self.down()
        self.use(HELM, "terminal", "Read it")
        self.assertEqual(A.boarding_learned("manifest"), 1)

    def test_one_visit_at_a_time(self):
        self.open()
        self.assertIsNone(self.open())

    def test_a_first_room_makes_it_the_text_visit_it_always_was(self):
        """`area` with a first room is not new: the scene is begun and watched."""
        invite = A.boarding_visit(self.ship, self.scenes, "terminal_read", area="landing")
        self.assertIsNotNone(invite)
        self.assertEqual(A.boarding_scene(), "terminal_read")
        self.assertFalse(A.boarding_visiting().get("tile", False))
        self.assertNotIn(A._visit_on_signal, S._signal_observers)


class StoriesTests(_Base):
    def test_each_story_goes_to_its_person_as_they_arrive(self):
        self.open(stories=self.stories)
        self.advance(2)
        self.assertEqual(Q.boarding_quests_of(A.boarding_reserved(SCI)), [])
        sci = self.down(SCI)
        self.advance(2)
        self.assertEqual(Q.boarding_quests_of(sci), ["reading"])
        helm = self.down(HELM)
        self.advance(2)
        self.assertEqual(Q.boarding_quests_of(helm), [])


class UpAndDownAgainTests(_Base):
    def test_beaming_up_does_not_end_the_visit(self):
        self.open()
        self.down()
        self.assertTrue(G.boarding_go_up(HELM))
        self.advance(4)
        self.assertIsNotNone(A.boarding_visiting())
        self.assertIsNotNone(A.boarding_invitation())

    def test_the_same_console_can_go_back_down_as_itself(self):
        self.open()
        first = self.down()
        T.tilemap_place(first, "landing", 5, 3)
        G.boarding_go_up(HELM)
        self.assertIsNone(T.tilemap_where(first))
        again = self.down()
        self.assertEqual(again, first)
        self.assertEqual(T.tilemap_where(again), ("landing", 2, 2))

    def test_what_was_learned_is_still_known(self):
        self.open()
        self.down()
        self.use(HELM, "terminal", "Read it")
        G.boarding_go_up(HELM)
        self.advance(2)
        self.down()
        self.assertEqual(A.boarding_learned("manifest"), 1)


class APartyThatIsAllDownTests(_Base):
    def fell(self, lf):
        T.tilemap_place(lf, "landing", 8, 1)
        K.boarding_hurt(lf, 99, by="orbit")
        self.assertTrue(K.boarding_is_down(lf))

    def test_it_comes_round_at_the_entry(self):
        self.open()
        me = self.down()
        self.fell(me)
        self.advance(A.VISIT_REVIVE_SECONDS - 3)
        self.assertTrue(K.boarding_is_down(me), "revived too soon to read what happened")
        self.advance(5)
        self.assertFalse(K.boarding_is_down(me))
        self.assertEqual(T.tilemap_where(me), ("landing", 2, 2))
        self.assertEqual(K.boarding_hp(me), 1)

    def test_the_mission_is_told_so_it_can_say_what_that_cost(self):
        self.open()
        me = self.down()
        self.fell(me)
        self.advance(A.VISIT_REVIVE_SECONDS + 2)
        told = self.named("boarding_party_revived")
        self.assertEqual(len(told), 1)
        self.assertEqual(told[0]["BOARDING_WHO"], [me])
        self.assertEqual(told[0]["BOARDING_AREA"], "landing")

    def test_one_of_two_down_is_left_for_the_other_to_help(self):
        self.open()
        me, other = self.down(HELM), self.down(SCI)
        self.fell(me)
        self.advance(A.VISIT_REVIVE_SECONDS + 4)
        self.assertTrue(K.boarding_is_down(me))
        self.assertEqual(self.named("boarding_party_revived"), [])
        self.assertFalse(K.boarding_is_down(other))

    def test_someone_still_aboard_does_not_keep_the_party_down(self):
        """The crew member who stayed on the bridge is not down there to help."""
        self.open()
        me = self.down(HELM)                    # SCI never beams down
        self.fell(me)
        self.advance(A.VISIT_REVIVE_SECONDS + 2)
        self.assertFalse(K.boarding_is_down(me))


class TheGameEndingEndsTheVisitTests(_Base):
    def setUp(self):
        super().setUp()
        quest_grant_amd(Agent.SHARED_ID, amd_section(self.doc, "quests"))

    def test_completing_a_quest_that_wins_ends_the_game_with_its_sentence(self):
        self.open()
        self.down()
        self.use(HELM, "beacon", "Light it")
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "light"), QuestState.COMPLETE)
        over = self.named("game_over")
        self.assertEqual(len(over), 1)
        self.assertIs(over[0]["WIN"], True)
        self.assertEqual(over[0]["TEXT"], "The beacon is lit. The convoy has its way home.")

    def test_failing_a_quest_that_loses_ends_it_with_that_sentence(self):
        self.open()
        self.down()
        self.use(HELM, "beacon", "Tear the panel out")
        over = self.named("game_over")
        self.assertEqual(len(over), 1)
        self.assertIs(over[0]["WIN"], False)
        self.assertEqual(over[0]["TEXT"], "The relay is slag, and the convoy flies on blind.")

    def test_and_that_ends_the_visit_and_brings_everyone_home(self):
        """With NO tick after it: the results screen pauses the sim, and a visit left
        for its watcher to close would stay open behind the results."""
        self.open()
        me = self.down()
        self.use(HELM, "beacon", "Light it")
        self.assertIsNone(A.boarding_visiting())
        self.assertIsNone(A.boarding_invitation())
        self.assertEqual(A.boarding_held(HELM), [])
        self.assertIsNone(T.tilemap_where(me))
        self.assertEqual(get_inventory_value(HELM, "CONSOLE_TYPE", None), "helm")
        ended = self.named("boarding_visit_ended")
        self.assertEqual(len(ended), 1)
        self.assertEqual(ended[0]["BOARDING_TITLE"], "Kesh Relay")
        self.assertEqual([c for c in A.boarding_channels() if c != A.PARTY], [])
        self.assertNotIn(A._visit_on_signal, S._signal_observers)

    def test_an_ending_that_leads_to_another_scene_does_not_open_it(self):
        """`- [Light it](epilogue) ; completes light`: everybody is home by the time the
        choice would walk on, so there is nobody to show the next scene to."""
        self.scenes["beacon_scene"]["description"] = self.scenes["beacon_scene"][
            "description"].replace("[Light it]()", "[Light it](terminal_read)")
        self.open()
        self.down()
        self.use(HELM, "beacon", "Light it")
        self.assertIsNone(A.boarding_visiting())
        self.assertEqual([c for c in A.boarding_channels() if c != A.PARTY], [])
        self.assertFalse(A.boarding_any_open())

    def test_the_game_ending_some_other_way_ends_it_too(self):
        """A timer, a `Fails when:` - anything that completes or fails the quest."""
        from sbs_utils.procedural.quest_driver import quest_mark_failed
        self.open()
        me = self.down()
        quest_mark_failed(Agent.SHARED_ID, "keep")
        self.assertIsNone(A.boarding_visiting())
        self.assertIsNone(T.tilemap_where(me))

    def test_walking_away_from_the_beacon_ends_nothing(self):
        self.open()
        self.down()
        self.use(HELM, "beacon", "Leave it")
        self.advance(3)
        self.assertEqual(self.named("game_over"), [])
        self.assertIsNotNone(A.boarding_visiting())

    def test_a_mission_can_still_end_it_itself(self):
        self.open()
        me = self.down()
        self.assertTrue(A.boarding_visit_end())
        self.assertIsNone(T.tilemap_where(me))
        self.assertEqual(len(self.named("boarding_visit_ended")), 1)

    def test_the_mission_reset_drops_the_visit_and_stops_listening(self):
        self.open()
        A.boarding_clear()
        self.assertIsNone(A.boarding_visiting())
        self.assertNotIn(A._visit_on_signal, S._signal_observers)


class AutoBeamTests(_Base):
    def test_it_is_off_unless_the_setting_says_so(self):
        self.assertIs(settings_get_defaults().get("BOARDING_AUTO_BEAM"), False)
        self.open()
        self.advance(4)
        self.assertEqual(A.boarding_held(HELM), [])
        self.assertEqual(self.named("boarding_went_down"), [])

    def test_off_written_as_text_is_off(self):
        """A launch line hands a setting over as text, and `"0"` is true to Python."""
        for word in ("0", "no", "false", 0):
            settings_get_defaults()["BOARDING_AUTO_BEAM"] = word
            self.open()
            self.advance(2)
            self.assertEqual(A.boarding_held(HELM), [], word)
            A.boarding_visit_end()
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = "1"
        self.open()
        self.advance(2)
        self.assertNotEqual(A.boarding_held(HELM), [])

    def test_on_it_sends_every_console_down_with_nobody_pressing_anything(self):
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = True
        self.open()
        self.advance(2)
        for cid in (HELM, SCI):
            self.assertTrue(BT.boarding_tile_on(cid), cid)
            self.assertEqual(get_inventory_value(cid, "CONSOLE_TYPE", None), A.BOARDING_CONSOLE)
        self.assertEqual(len(self.named("boarding_went_down")), 2)

    def test_a_console_that_arrives_late_is_sent_down_too(self):
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = True
        self.open()
        self.advance(2)
        self.sit(ENG, "engineering")
        self.advance(4)
        self.assertTrue(BT.boarding_tile_on(ENG))

    def test_a_console_put_on_the_ship_without_the_picker_goes_too(self):
        """The headless runner's stand-in console: on the ship, at a station, and never
        linked - because choosing a ship on the picker is what links one."""
        GuiClient(ENG)
        set_inventory_value(ENG, "CONSOLE_TYPE", "engineering")
        sbs.assign_client_to_ship(ENG, self.ship)
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = True
        self.open()
        self.advance(4)
        self.assertTrue(BT.boarding_tile_on(ENG))

    def test_a_console_on_another_ship_is_left_alone(self):
        other = to_id(player_spawn(900, 0, 0, "Intrepid", "tsn", "tsn_light_cruiser"))
        GuiClient(ENG)
        set_inventory_value(ENG, "CONSOLE_TYPE", "engineering")
        sbs.assign_client_to_ship(ENG, other)
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = True
        self.open()
        self.advance(4)
        self.assertFalse(BT.boarding_tile_on(ENG))
        self.assertEqual(A.boarding_held(ENG), [])

    def test_once_each_so_beaming_up_sticks(self):
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = True
        self.open()
        self.advance(2)
        G.boarding_go_up(HELM)
        self.advance(4)
        self.assertFalse(BT.boarding_tile_on(HELM))

    def test_it_works_for_a_text_visit_too(self):
        settings_get_defaults()["BOARDING_AUTO_BEAM"] = True
        A.boarding_visit(self.ship, self.scenes, "terminal_read", title="The Hulk")
        self.advance(2)
        self.assertNotEqual(A.boarding_held(HELM), [])
        self.assertEqual(get_inventory_value(HELM, "CONSOLE_TYPE", None), A.BOARDING_CONSOLE)


if __name__ == "__main__":
    unittest.main()
