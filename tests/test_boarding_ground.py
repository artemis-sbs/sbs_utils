"""A boarding party on the ground: beaming into a tile area, props, checks and trouble.

Driven through the production entry points - `boarding_go_down`, `boarding_tile_click`,
`boarding_interact`, `boarding_tile_fire` - not by poking the tables underneath, because
the point is that a crew member's CLICK does the right thing.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural.boarding_site import boarding_arm, boarding_where
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

CID, CID2 = 0x8000000000000031, 0x8000000000000032

AREA = """area: yard
title: The Yard
tileset: g
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  D: dirt @door
---
############
#..........#
#.P........#
#..........#
#######D####
#..........#
#..........#
############
"""

KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

PROPS = {"children": [
    {"key": "door", "display_text": "Yard gate", "description": "A rusted gate.",
     "data": {"area": "yard", "at": "door", "sprite": "g:rock",
              "opens_with": "key gate_key, check engineering 9, cut", "blocks": "yes"}},
    {"key": "coil", "display_text": "Coil", "description": "",
     "data": {"area": "yard", "at": "9, 6", "sprite": "g:dirt", "item": "coil"}},
    {"key": "crate", "display_text": "Crate", "description": "Stencilled STILLWATER.",
     "data": {"area": "yard", "at": "5, 2", "sprite": "g:rock", "blocks": "yes"}},
]}

HOSTILES = {"children": [
    {"key": "glassback", "display_text": "Glassback", "description": "",
     "data": {"area": "yard", "at": "9, 2", "sprite": "g:rock", "hp": "2",
              "damage": "1", "notice": "8", "cooldown": "1", "drops": "venom"}},
]}


TALK = {"any": {"key": "any", "display_text": "a", "data": {},
                "description": "% Hm.\n- [Go]()\n"}}


class GroundBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        SpaceObject.clear()
        clear_shared()
        for clear in (A.boarding_clear, T.tilemap_clear, BT.boarding_tile_clear,
                      P.boarding_props_clear, C.boarding_checks_clear,
                      K.boarding_combat_clear):
            clear()
            self.addCleanup(clear)
        T.tilemap_tileset("g", KINDS)
        T.tilemap_load(AREA)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()
        self.now = 0.0
        T.tilemap_set_clock(0.0)
        A.boarding_metric_install()
        P.boarding_props_install()
        K.boarding_combat_install()
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Yard", area="yard")
        self.bodies = {}
        for cid, name, job in ((CID, "Kovac", "engineering"), (CID2, "Sato", "medical")):
            GuiClient(cid)
            body = lifeform_spawn(name, "", "boarding," + job)
            set_inventory_value(body.id, A.JOBS_KEY, [job])
            A.boarding_assign(cid, body.id)
            self.bodies[cid] = body.id
        self.seen = []
        signal_observe(self._obs)
        self.addCleanup(signal_unobserve, self._obs)

    def _obs(self, name, data):
        self.seen.append((name, dict(data) if isinstance(data, dict) else data))

    def down(self, cid=CID):
        G.boarding_go_down(cid)

    def advance(self, seconds=10.0):
        steps = int(seconds / 0.05)
        for _ in range(steps):
            self.now += 0.05
            T.tilemap_set_clock(self.now)
            T.tilemap_tick()
            K.boarding_hostiles_tick()

    def click(self, x, y, cid=CID):
        return BT.boarding_tile_click(cid, "yard", x, y)


class TestBeamingIntoATileArea(GroundBase):
    def test_going_down_stands_you_on_the_pad(self):
        self.down()
        self.assertEqual(BT.boarding_tile_where(CID), ("yard", 2, 2))
        self.assertEqual(boarding_where(CID), (2, 2))

    def test_the_crew_console_is_told_there_is_somewhere_to_walk(self):
        self.down()
        went = [d for n, d in self.seen if n == "boarding_went_down"][-1]
        self.assertEqual(went["BOARDING_HOST"], "yard")
        self.assertEqual(went["BOARDING_AREA"], "yard")

    def test_two_crew_get_two_colors(self):
        self.down()
        self.down(CID2)
        a = T.tilemap_actor(self.bodies[CID])["color"]
        b = T.tilemap_actor(self.bodies[CID2])["color"]
        self.assertNotEqual(a, b)

    def test_going_up_takes_the_body_off_the_map(self):
        self.down()
        G.boarding_go_up(CID)
        self.assertIsNone(T.tilemap_where(self.bodies[CID]))

    def test_a_click_walks(self):
        self.down()
        self.click(4, 3)
        self.advance(3)
        self.assertEqual(BT.boarding_tile_where(CID), ("yard", 4, 3))


class TestProps(GroundBase):
    def setUp(self):
        super().setUp()
        P.boarding_props_declare(PROPS)
        P.boarding_props_place()
        self.down()

    def test_a_shut_gate_blocks_the_way(self):
        self.assertFalse(T.tilemap_is_open("yard", 7, 4))

    def test_clicking_a_far_prop_walks_up_and_uses_it(self):
        self.click(5, 2)                      # the crate
        self.advance(3)
        at = BT.boarding_tile_where(CID)
        self.assertEqual(abs(at[1] - 5) + abs(at[2] - 2), 1)
        used = [d for n, d in self.seen if n == "boarding_interacted"]
        self.assertEqual(used[-1]["BOARDING_PROP"], "crate")
        self.assertIn("STILLWATER", P.boarding_last_note(CID))

    def test_THE_ENGINEER_CAN_FORCE_THE_GATE_ON_A_GOOD_ROLL(self):
        C.boarding_checks_mode("flat")        # 5 + engineering 2 = 7 < 9
        T.tilemap_place(self.bodies[CID], "yard", 7, 3)
        result, _ = P.boarding_interact(CID, "door")
        self.assertEqual(result, "failed")
        C.boarding_skills_set(self.bodies[CID], {"engineering": 4})   # 5 + 4 = 9
        result, _ = P.boarding_interact(CID, "door")
        self.assertEqual(result, "opened")
        self.assertTrue(T.tilemap_is_open("yard", 7, 4))

    def test_a_key_anyone_carries_opens_it(self):
        P.boarding_give(self.bodies[CID2], "gate_key")
        T.tilemap_place(self.bodies[CID], "yard", 7, 3)
        self.assertEqual(P.boarding_interact(CID, "door")[0], "opened")

    def test_a_helper_beside_you_adds_one(self):
        C.boarding_checks_mode("flat")
        C.boarding_skills_set(self.bodies[CID], {"engineering": 3})    # 8 alone
        self.down(CID2)
        C.boarding_skills_set(self.bodies[CID2], {"engineering": 1})
        T.tilemap_place(self.bodies[CID], "yard", 7, 3)
        T.tilemap_place(self.bodies[CID2], "yard", 6, 3)
        self.assertEqual(P.boarding_interact(CID, "door")[0], "opened")

    def test_picking_up_puts_it_in_the_pack(self):
        P.boarding_prop_open("door")
        T.tilemap_place(self.bodies[CID], "yard", 9, 5)
        self.assertEqual(P.boarding_interact(CID, "coil")[0], "picked")
        self.assertEqual(P.boarding_holding(self.bodies[CID], "coil"), 1)
        self.assertEqual(P.boarding_party_holding("coil"), 1)
        self.assertIsNone(P.boarding_prop_at("yard", 9, 6))

    def test_a_cut_shot_opens_the_gate(self):
        T.tilemap_place(self.bodies[CID], "yard", 7, 2)
        boarding_arm(CID, "cut")
        self.assertTrue(self.click(7, 4))
        self.assertTrue(P.boarding_prop_is_open("door"))

    def test_guards_read_the_pack(self):
        from sbs_utils.procedural.amd_dialogue import dialogue_guard_ok
        lf = self.bodies[CID]
        self.assertFalse(dialogue_guard_ok("holding coil >= 1", lf, None))
        P.boarding_give(lf, "coil")
        self.assertTrue(dialogue_guard_ok("holding coil >= 1", lf, None))
        self.assertTrue(dialogue_guard_ok("party coil >= 1", self.bodies[CID2], None))
        self.assertTrue(dialogue_guard_ok("skill engineering >= 2", lf, None))


class TestChecksInDialogue(GroundBase):
    SCENES = {
        "fix": {"key": "fix", "display_text": "fix", "data": {},
                "description": "% The coupling.\n"
                               "- [Force it](fixed) if engineering ; check engineering 9 else sheared\n"},
        "fixed": {"key": "fixed", "display_text": "f", "data": {},
                  "description": "% It holds.\n- [Done]()\n"},
        "sheared": {"key": "sheared", "display_text": "s", "data": {},
                    "description": "% It shears.\n- [Done]()\n"},
    }

    def test_a_failed_check_goes_to_its_else(self):
        C.boarding_checks_mode("flat")
        A.boarding_scene_begin(self.SCENES, "fix")
        A.boarding_answer(CID, 0, seq=A.boarding_seq())
        self.assertEqual(A.boarding_scene(), "sheared")

    def test_a_passed_check_goes_on(self):
        C.boarding_checks_mode("flat")
        C.boarding_skills_set(self.bodies[CID], {"engineering": 5})
        A.boarding_scene_begin(self.SCENES, "fix")
        A.boarding_answer(CID, 0, seq=A.boarding_seq())
        self.assertEqual(A.boarding_scene(), "fixed")

    def test_skills_come_from_the_roster_by_name(self):
        C.boarding_skills_from_amd({"children": [{"display_text": "Kovac",
                                                  "data": {"skills": "engineering 4, athletics 1"}}]})
        self.assertEqual(C.boarding_skill(self.bodies[CID], "engineering"), 4)
        self.assertEqual(C.boarding_skill(self.bodies[CID2], "medical"), C.JOB_SKILL)
        self.assertEqual(C.boarding_skill(self.bodies[CID2], "athletics"), 0)

    def test_a_seeded_roll_repeats(self):
        C.boarding_checks_seed(3)
        a = [C.boarding_check(self.bodies[CID], "engineering", 8)["roll"] for _ in range(5)]
        C.boarding_checks_seed(3)
        b = [C.boarding_check(self.bodies[CID], "engineering", 8)["roll"] for _ in range(5)]
        self.assertEqual(a, b)


class TestTrouble(GroundBase):
    def setUp(self):
        super().setUp()
        K.boarding_hostiles_declare(HOSTILES)
        K.boarding_hostiles_place()
        self.down()

    def glass(self):
        return K.boarding_hostile("glassback")

    def test_it_notices_chases_and_strikes(self):
        self.advance(4)
        names = [n for n, _ in self.seen]
        self.assertIn("boarding_hostile_noticed", names)
        self.assertIn("boarding_hostile_struck", names)
        self.assertLess(K.boarding_hp(self.bodies[CID]), K.CREW_HP)

    def test_a_crew_member_at_zero_is_down_and_cannot_walk(self):
        K.boarding_hurt(self.bodies[CID], 99)
        self.assertTrue(K.boarding_is_down(self.bodies[CID]))
        self.assertFalse(self.click(3, 2))
        self.assertIn("boarding_party_down", [n for n, _ in self.seen])

    def test_revive(self):
        K.boarding_hurt(self.bodies[CID], 99)
        self.assertTrue(K.boarding_revive(self.bodies[CID]))
        self.assertTrue(K.boarding_can_act(self.bodies[CID]))

    def test_stun_holds_it_still(self):
        T.tilemap_place(self.bodies[CID], "yard", 6, 2)
        boarding_arm(CID, "stun")
        self.assertTrue(self.click(9, 2))
        at = T.tilemap_where(self.glass()["id"])
        self.advance(3)
        self.assertEqual(T.tilemap_where(self.glass()["id"]), at)
        self.assertEqual(K.boarding_hp(self.bodies[CID]), K.CREW_HP)

    def test_full_puts_it_down_and_it_drops_what_it_carried(self):
        T.tilemap_place(self.bodies[CID], "yard", 6, 2)
        boarding_arm(CID, "full")
        self.click(9, 2)
        self.assertEqual(K.boarding_hostile_state("glassback"), "down")
        self.assertIn("hostile_down_glassback", [n for n, _ in self.seen])
        self.assertIsNotNone(P.boarding_prop_at("yard", 9, 2))

    def test_out_of_range_or_sight_misses(self):
        T.tilemap_place(self.bodies[CID], "yard", 2, 6)    # below the rock wall
        boarding_arm(CID, "full")
        self.click(9, 2)
        fired = [d for n, d in self.seen if n == "xess_fired"][-1]
        self.assertFalse(fired["XESS_HIT"])

    def test_a_calmed_hostile_leaves_you_alone(self):
        K.boarding_hostile_calm("glassback")
        self.advance(4)
        self.assertEqual(K.boarding_hp(self.bodies[CID]), K.CREW_HP)

    def test_BEING_HIT_IS_SAID_OUT_LOUD(self):
        """Engine playtest: HP ran out and nothing said so - the crew member only found
        out by being unable to move."""
        from sbs_utils.procedural.gui.boarding_console import where_text
        K.boarding_hurt(self.bodies[CID], 1, by="glassback")
        self.assertIn("Glassback", P.boarding_last_note(CID))
        self.assertIn("HP 2/3", where_text(CID))
        K.boarding_hurt(self.bodies[CID], 5, by="glassback")
        self.assertIn("DOWN", where_text(CID))

    def test_NOBODY_FIGHTS_DURING_A_PARLEY(self):
        """Engine playtest: the sentries kept shooting while the parley was read."""
        rec = self.glass()
        rec["talk"] = "any"
        A.boarding_channel_open("talk:glassback", [CID])
        A.boarding_scene_begin(TALK, "any", channel="talk:glassback")
        self.advance(4)
        self.assertEqual(K.boarding_hp(self.bodies[CID]), K.CREW_HP)

    def test_talking_from_afar_walks_up_first(self):
        rec = self.glass()
        rec["talk"] = "any"
        P._SCENES["doc"] = TALK
        K.boarding_hostile_calm("glassback")
        self.assertTrue(self.click(9, 2))                    # 7 cells away
        self.assertIsNone(A.boarding_scene(A.boarding_channel_of(CID)))
        self.advance(4)
        self.assertEqual(A.boarding_scene(A.boarding_channel_of(CID)), "any")

    def test_orbital_strike(self):
        down = K.boarding_strike("yard", 9, 2, radius=1)
        self.assertEqual(down, ["glassback"])


SIDE = {"children": [
    {"key": "patience_heart", "display_text": "Patience's Heart", "description": "Fit the parts.",
     "data": {"for": "engineering", "state": "active",
              "on_signal": {"name": "hauler_fixed"}}},
    {"key": "survey_team", "display_text": "The Survey Team", "description": "Find them.",
     "data": {"for": "medical", "state": "active"}},
    {"key": "quiet_deputy", "display_text": "The Quiet Deputy", "description": "Harrow.",
     "data": {"for": "security", "state": "active"}},
]}

OTHER = """area: flats
title: Salt Flats
tileset: g
legend:
  .: dirt
---
.....
.....
"""


class TestPersonalQuests(GroundBase):
    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import boarding_quests as Q
        from sbs_utils.procedural import quest
        self.Q, self.quest = Q, quest
        Q.boarding_quests_clear()
        self.addCleanup(Q.boarding_quests_clear)
        self.down()
        self.down(CID2)

    def test_each_quest_goes_to_its_crew_member(self):
        got = self.Q.boarding_quests_grant(SIDE)
        self.assertEqual(got["patience_heart"], self.bodies[CID])
        self.assertEqual(got["survey_team"], self.bodies[CID2])
        self.assertIsNotNone(self.quest.quest_get(self.bodies[CID], "patience_heart"))
        self.assertIsNone(self.quest.quest_get(self.bodies[CID2], "patience_heart"))

    def test_granting_again_grants_nothing_twice(self):
        self.Q.boarding_quests_grant(SIDE)
        self.assertEqual(self.Q.boarding_quests_grant(SIDE), {})

    def test_an_unclaimed_quest_goes_to_the_party(self):
        self.Q.boarding_quests_grant(SIDE)
        self.assertEqual(self.Q.boarding_quests_open_unclaimed(SIDE), ["quiet_deputy"])
        self.assertTrue(self.Q.boarding_quest_is_open("quiet_deputy"))

    def test_a_signal_completes_the_owners_quest(self):
        from sbs_utils.procedural.quest_driver import quest_on_signal
        self.Q.boarding_quests_grant(SIDE)
        quest_on_signal("hauler_fixed")
        self.assertTrue(self.quest.quest_is_complete(self.bodies[CID], "patience_heart"))

    def test_the_console_shows_its_own_quests(self):
        from sbs_utils.procedural.quest_driver import quest_holder_for_client
        label, holder = quest_holder_for_client(CID)
        self.assertEqual(holder, self.bodies[CID])
        self.assertEqual(label, "Kovac")


class TestTheWayOut(GroundBase):
    """Playtest: in the Gnaw, nobody could see how to leave. Look lists the exits."""

    def setUp(self):
        super().setUp()
        T.tilemap_load(OTHER)
        area = T.tilemap_area("yard")
        area["marks"]["to_flats"] = {(10, 6)}
        area["mark_at"][(10, 6)] = "to_flats"
        self.down()

    def test_look_lists_the_exits_by_where_they_go(self):
        from sbs_utils.procedural.gui import xess_ground as XG
        self.assertEqual(XG._exits(CID), [("to_flats", "Salt Flats")])

    def test_going_walks_there_and_through(self):
        from sbs_utils.procedural.gui import xess_ground as XG
        T.tilemap_place(self.bodies[CID], "yard", 9, 6)
        XG._go_exit(CID, "to_flats")
        self.advance(3)
        self.assertEqual(BT.boarding_tile_where(CID)[0], "flats")

    def test_an_unknown_place_is_not_offered(self):
        from sbs_utils.procedural.gui import xess_ground as XG
        T.tilemap_area("flats")["known"] = False
        self.assertEqual(XG._exits(CID), [])


class TestTransporter(GroundBase):
    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import boarding_quests as Q
        self.Q = Q
        Q.boarding_quests_clear()
        self.addCleanup(Q.boarding_quests_clear)
        T.tilemap_load(OTHER)
        self.down()

    def test_beam_to_another_area(self):
        ok, _ = self.Q.boarding_transport(CID, "flats")
        self.assertTrue(ok)
        self.assertEqual(BT.boarding_tile_where(CID)[0], "flats")

    def test_jammed_says_why(self):
        self.Q.boarding_transport_jam(True, "The raider is jamming us")
        ok, text = self.Q.boarding_transport(CID, "flats")
        self.assertFalse(ok)
        self.assertIn("raider", text)

    def test_an_unknown_site_has_no_lock(self):
        T.tilemap_area("flats")["known"] = False
        self.assertFalse(self.Q.boarding_transport(CID, "flats")[0])
        self.assertNotIn("flats", self.Q.boarding_transport_targets(CID))

    def test_leaving_an_area_leaves_its_conversation(self):
        scenes = {"s": {"key": "s", "display_text": "s", "data": {},
                        "description": "% Hm.\n- [Go]()\n"}}
        A.boarding_encounter(scenes, "s", CID)
        self.Q.boarding_transport(CID, "flats")
        self.assertEqual(A.boarding_channel_of(CID), A.boarding_party_channel())


LEADS = {"children": [
    {"key": "patience_heart", "display_text": "Patience's Heart", "description": "",
     "data": {"for": "engineering", "state": "active", "leads_to": "coil, glassback"}},
]}


class TestWhatIsLeftToExplore(GroundBase):
    """Playtest: nothing said which things still mattered. Hints badge them."""

    def setUp(self):
        super().setUp()
        from sbs_utils.procedural import boarding_hints as H
        from sbs_utils.procedural import boarding_quests as Q
        self.H = H
        Q.boarding_quests_clear()
        self.addCleanup(Q.boarding_quests_clear)
        P.boarding_props_declare(PROPS)
        P.boarding_props_place()
        K.boarding_hostiles_declare(HOSTILES)
        K.boarding_hostiles_place()
        K._HOSTILES["glassback"]["talk"] = "any"
        K.boarding_hostile_calm("glassback")
        P._SCENES["doc"] = TALK
        T.tilemap_load(OTHER)
        area = T.tilemap_area("yard")
        area["marks"]["to_flats"] = {(10, 6)}
        area["mark_at"][(10, 6)] = "to_flats"
        self.down()
        T.tilemap_reveal_all("yard")
        self.Q = Q

    def hints(self):
        return self.H.boarding_hints(CID, "yard")

    def test_untouched_things_and_new_places_are_badged(self):
        h = self.hints()
        self.assertEqual(h[(5, 2)], "new")        # the crate: something to look at
        self.assertEqual(h[(9, 6)], "new")        # the coil: an item
        self.assertEqual(h[(9, 2)], "new")        # somebody nobody has talked to
        self.assertEqual(h[(10, 6)], "way")       # the Salt Flats: never been there

    def test_NOTHING_UNSEEN_IS_BADGED(self):
        T.tilemap_area("yard")["explored"] = {(2, 2)}
        self.assertEqual(self.hints(), {})

    def test_used_and_talked_to_are_no_longer_badged(self):
        T.tilemap_place(self.bodies[CID], "yard", 9, 5)
        P.boarding_interact(CID, "coil")
        self.assertTrue(K.boarding_talk(CID, "glassback"))
        h = self.hints()
        self.assertNotIn((9, 6), h)
        self.assertNotIn((9, 2), h)

    def test_a_visited_place_is_not_new(self):
        T.tilemap_reveal("flats", 0, 0)
        self.assertNotIn((10, 6), self.hints())

    def test_a_quest_lead_outranks_new(self):
        self.Q.boarding_quests_grant(LEADS)
        h = self.hints()
        self.assertEqual(h[(9, 6)], "lead")
        self.assertEqual(h[(9, 2)], "lead")
        self.assertEqual(h[(5, 2)], "new")
        places = self.H.boarding_lead_places(CID)
        self.assertEqual([p[0] for p in places], ["coil", "glassback"])
        self.assertTrue(places[0][2].startswith("here, "))

    def test_another_consoles_lead_is_not_mine(self):
        self.Q.boarding_quests_grant(LEADS)
        self.down(CID2)
        self.assertEqual(self.H.boarding_leads(CID2), [])

    def test_further_off_lists_bearing_and_puts_leads_first(self):
        self.Q.boarding_quests_grant(LEADS)
        poi = self.H.boarding_points_of_interest(CID)
        self.assertEqual(poi[0][5], "lead")
        crate = next(p for p in poi if p[1] == "crate")
        self.assertEqual((crate[3], crate[4]), (3, "E"))

    def test_go_to_walks_up_and_uses_it(self):
        self.assertTrue(self.H.boarding_go_to(CID, "crate"))
        self.advance(3)
        self.assertTrue(P.boarding_prop("crate")["touched"])
        self.assertNotIn((5, 2), self.hints())

    def test_badges_need_a_sprite(self):
        self.assertEqual(self.H.boarding_hint_badges(CID, "yard"), {})
        self.H.boarding_hint_style(new="g:dirt")
        self.addCleanup(self.H.boarding_hint_style, new="")
        self.assertEqual(self.H.boarding_hint_badges(CID, "yard")[(5, 2)], "g:dirt")


if __name__ == "__main__":
    unittest.main()
