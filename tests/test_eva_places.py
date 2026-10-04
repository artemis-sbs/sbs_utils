"""A relic's places SAY something when a suit gets there - the EVA half of the boarding
party's props.

Everything here runs against a relic read from AMD TEXT through `relics_load`, the way a
shipped ruin is, rather than a hand-filled record: the place's `Scene:` / `Scan:` fields,
its file's own `## Dialogue` section, a `Hidden:` place, and a barrier a check can clear
all have to survive the real reader to mean anything. Consoles are real client ids (the
0x8000 bit), and the relic is ARMED - an unarmed relic has no markers, and every "was it
revealed" answer is trivially True on one.

Run: python -m unittest tests.test_eva_places
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import eva_places as P
from sbs_utils.procedural import eva_tools as T
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.signal import signal_observe, signal_unobserve

C1 = 0x8000000000000001
C2 = 0x8000000000000002
C3 = 0x8000000000000003
RELIC = "thall"
PATH = "thall_test.amd"

CONTENT = """# [The Test Hall](thall_doc)

## [Relics](relics)

### [The Test Hall](thall)
---
Loc: 0, 0, 0
Containment: none
---
A hall for testing. This prose is for the AUTHOR and must never reach a player.

### [west room](west)
---
Relic: thall
Box: -1800, 0, 0, 900, 300, 300
---

### [middle](mid)
---
Relic: thall
Box: 0, 0, 0, 1000, 300, 300
---

### [east room](east)
---
Relic: thall
Box: 1800, 0, 0, 900, 300, 300
Scan: A long room with a stone table at the far end.
---

### [the door](door)
---
Relic: thall
Point: -2500, 0, 0
Roles: entrance
---

### [the altar](altar)
---
Relic: thall
Point: 1800, 0, 0
Roles: thall_altar
Scene: altar_look
Scan: A stone table under a carved sky.
---
The altar sits on a box solid so the rails skirt it - AUTHOR NOTES.

### [the niche](niche)
---
Relic: thall
Point: 2500, 0, 200
Roles: thall_niche
Hidden: yes
---

### [the seal](seal)
---
Relic: thall
Barrier: 0, 0, 0, 250
Clear with: beam, check engineering 12
---

## [Dialogue](dialogue)

### [altar_look](altar_look)
---
Backdrop: pic:altar_test
---
% A stone table under a carved sky.
- [Read the carving](altar_read) ; check science 7 else altar_blank, reveal niche, signal thall_niche_found
- [Force the seal](altar_done) ; open seal
- [Leave it](altar_done)

### [altar_read](altar_read)
---
---
% The carving is a map.

### [altar_blank](altar_blank)
---
---
% It means nothing to you.

### [altar_done](altar_done)
---
---
% You move on.
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
        T.eva_tools_clear()
        P.eva_places_clear()
        R.relics_clear()
        R.relic_contents_clear()
        A.boarding_clear()
        self._prev_metric = D._METRIC_RESOLVER
        A.boarding_metric_install()
        C.boarding_checks_mode("flat")
        for cid in (C1, C2, C3):
            GuiClient(cid)
        R.relics_load(PATH, content=getattr(self, "content", CONTENT))
        rec = R.relic_record(RELIC)
        R.relic_volume(rec)
        R.relic_rails_ensure(RELIC)
        R.relic_contents_arm(RELIC)
        self.events = []
        signal_observe(self._watch)

    def tearDown(self):
        signal_unobserve(self._watch)
        from sbs_utils.procedural.gui.image import ImageAtlas
        ImageAtlas.all.pop("pic:altar_test", None)
        A.boarding_clear()
        D.dialogue_set_metric_resolver(self._prev_metric)
        P.eva_places_clear()
        T.eva_tools_clear()
        E.eva_clear()
        R.relic_contents_clear()
        R.relics_clear()
        RL.rail_clear()
        V.volume_clear()
        TickDispatcher.clear()

    def _watch(self, name, data=None):
        self.events.append((name, dict(data or {})))

    def emitted(self, name):
        return [d for n, d in self.events if n == name]

    def suit_up(self, cid, at, name=None, skills=None):
        who = lifeform_spawn(name or "Boarder %x" % (cid & 0xff), "terran_male",
                             "boarding")
        A.boarding_assign(cid, who)
        suit = E.eva_suit_spawn(who, RELIC, at[0], at[1], at[2],
                                hull="tsn_shuttle", side="tsn", volume=RELIC)
        E.eva_take(cid, suit, RELIC, volume=RELIC)
        if skills:
            C.boarding_skills_set(who, skills)
        return who, suit

    def transcript(self, cid):
        return A.boarding_reader_text(cid)

    def art(self, key):
        from sbs_utils.procedural.gui.image import gui_image_add_atlas
        gui_image_add_atlas(key, "media/probe/rt_sheet", 0, 0, 8, 8)

    def pick(self, cid, label):
        labels = [c.get("label") for c in A.boarding_choices(cid)]
        return A.boarding_answer(cid, labels.index(label))


class ThePlaceIsRead(_Base):
    def test_a_place_keeps_its_scene_and_scan(self):
        self.assertEqual(R.relic_part_scene(RELIC, "altar"), "altar_look")
        self.assertEqual(R.relic_part_scan(RELIC, "altar"),
                         "A stone table under a carved sky.")

    def test_the_prose_is_never_the_scan(self):
        """A shipped relic's prose explains its MECHANICS to the author."""
        self.assertNotIn("AUTHOR", R.relic_part_scan(RELIC, "altar") or "")
        self.assertIsNone(R.relic_part_scan(RELIC, "door"))

    def test_the_relic_file_registers_its_own_dialogue(self):
        self.assertIsNotNone(D.dialogue_scene("altar_look"))

    def test_points_are_still_a_positional_list(self):
        """`points` is indexed by position; the new facts must not have grown it."""
        pt = R.relic_record(RELIC).get("points")["altar"]
        self.assertEqual(pt[:3], [1800.0, 0.0, 0.0])
        self.assertEqual(len(pt), 6)

    def test_a_box_room_is_found_by_position(self):
        self.assertEqual(R.relic_part_at(RELIC, (1700, 0, 0)), "east")
        self.assertEqual(R.relic_part_at(RELIC, (0, 50, 0)), "mid")


class ArrivingOpensTheScene(_Base):
    def test_arriving_opens_it_for_that_console(self):
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.assertEqual(ch, P.eva_place_channel(RELIC, "altar"))
        self.assertTrue(A.boarding_is_open(ch))
        self.assertEqual(A.boarding_channel_of(C1), ch)
        self.assertIn("A stone table under a carved sky.", self.transcript(C1))
        self.assertTrue(self.emitted("eva_place_scene"))

    def test_the_autopilot_arriving_opens_it(self):
        """The production path: a route ending at the place, in `eva_tick`."""
        self.suit_up(C1, (1800, 0, 0))
        from sbs_utils.procedural.inventory import set_inventory_value
        set_inventory_value(C1, E.KEY_ROUTE, [(1800.0, 0.0, 0.0)])
        set_inventory_value(C1, E.KEY_DEST, "altar")
        E.eva_tick()
        self.assertTrue(A.boarding_is_open(P.eva_place_channel(RELIC, "altar")))
        arrived = self.emitted("eva_arrived")
        self.assertEqual([d["EVA_POINT"] for d in arrived], ["altar"])

    def test_a_suit_alongside_is_pulled_in_and_a_far_one_is_not(self):
        self.suit_up(C1, (1800, 0, 0))
        self.suit_up(C2, (1700, 0, 100))
        self.suit_up(C3, (-1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.assertEqual(A.boarding_channel_of(C2), ch)
        self.assertNotEqual(A.boarding_channel_of(C3), ch)

    def test_it_plays_once_and_then_the_place_reads_its_scan(self):
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        A.boarding_channel_close(ch)
        self.suit_up(C2, (1800, 0, 0))
        self.assertIsNone(P.eva_place_arrive(C2, RELIC, "altar", first_visit=True))
        self.assertFalse(A.boarding_is_open(ch))
        self.assertIn("A stone table under a carved sky.", self.transcript(C2))

    def test_a_later_suit_joins_a_scene_still_going(self):
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.suit_up(C2, (-1800, 0, 0))
        self.assertEqual(P.eva_place_arrive(C2, RELIC, "altar"), ch)
        self.assertEqual(A.boarding_channel_of(C2), ch)

    def test_a_place_with_no_scene_is_quiet(self):
        self.suit_up(C1, (-2500, 0, 0))
        self.assertIsNone(P.eva_place_arrive(C1, RELIC, "door"))

    def test_switched_off_it_does_nothing(self):
        self.suit_up(C1, (1800, 0, 0))
        P.eva_places_enabled(False)
        self.assertIsNone(P.eva_place_arrive(C1, RELIC, "altar"))

    def test_the_reset_forgets(self):
        self.suit_up(C1, (1800, 0, 0))
        P.eva_place_arrive(C1, RELIC, "altar")
        self.assertEqual(P.eva_places_count(), 1)
        P.eva_places_clear()
        self.assertEqual(P.eva_places_count(), 0)


class AnAnswerThatLeadsNowhere(_Base):
    """`- [Leave it](altar_gone)`, and there is no scene `altar_gone`.

    The scene ended and the console stayed in the place's channel, which had nothing in
    it: no line, no choice, no way out. Measured by the lesson "Places that speak".
    """
    content = CONTENT.replace("- [Leave it](altar_done)", "- [Leave it](altar_gone)")

    def test_it_ends_the_scene_and_brings_the_console_back(self):
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.assertEqual(A.boarding_channel_of(C1), ch)
        self.assertTrue(self.pick(C1, "Leave it"))
        self.assertFalse(A.boarding_is_open(ch))
        self.assertNotEqual(A.boarding_channel_of(C1), ch)
        self.assertEqual(A.boarding_channel_of(C1), A.PARTY)
        ended = self.emitted("boarding_scene_ended")
        self.assertEqual([d["BOARDING_CHANNEL"] for d in ended], [ch])

    def test_an_answer_that_leads_somewhere_is_unchanged(self):
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.assertTrue(self.pick(C1, "Force the seal"))
        self.assertTrue(A.boarding_is_open(ch))
        self.assertEqual(A.boarding_channel_of(C1), ch)


class AScenePlaceNamesThatIsNotThere(_Base):
    """`Scene: altar_lok`. The place said nothing, and the only line about it went to a
    log category nothing reads."""
    content = CONTENT.replace("Scene: altar_look", "Scene: altar_lok")

    def test_it_is_said_where_the_author_will_see_it_and_once(self):
        import logging
        heard = []

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        handler = _Listen()
        logging.getLogger("mast.runtime").addHandler(handler)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, handler)
        self.suit_up(C1, (1800, 0, 0))
        self.assertIsNone(P.eva_place_arrive(C1, RELIC, "altar"))
        self.assertIsNone(P.eva_place_arrive(C1, RELIC, "altar"))
        said = [line for line in heard if "altar_lok" in line]
        self.assertEqual(len(said), 1, heard)
        self.assertIn("'altar'", said[0])


class ThePicture(_Base):
    def test_the_scenes_backdrop_is_its_picture(self):
        self.art("pic:altar_test")
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.assertEqual(A.boarding_line_image(ch), "pic:altar_test")
        self.assertIn("image://pic:altar_test", self.transcript(C1))

    def test_a_backdrop_the_art_does_not_have_draws_nothing(self):
        self.suit_up(C1, (1800, 0, 0))
        ch = P.eva_place_arrive(C1, RELIC, "altar")
        self.assertIsNone(A.boarding_line_image(ch))
        self.assertNotIn("image://", self.transcript(C1))


class ChecksAndVerbs(_Base):
    def test_a_failed_check_stops_everything_after_it(self):
        """`; check science 7 else altar_blank, reveal niche, signal ...` - the reveal
        and the signal are what SUCCESS does, and used to run on a failure too."""
        self.suit_up(C1, (1800, 0, 0))                     # science 0: 5 + 0 < 7
        P.eva_place_arrive(C1, RELIC, "altar")
        self.assertTrue(self.pick(C1, "Read the carving"))
        self.assertEqual(A.boarding_scene(P.eva_place_channel(RELIC, "altar")),
                         "altar_blank")
        self.assertTrue(RL.rail_is_hidden(RELIC, "niche"))
        self.assertFalse([n for n, _ in self.events if n == "thall_niche_found"])

    def test_the_roll_goes_in_the_transcript(self):
        self.suit_up(C1, (1800, 0, 0))
        P.eva_place_arrive(C1, RELIC, "altar")
        self.pick(C1, "Read the carving")
        self.assertIn("rolled 5", self.transcript(C1))

    def test_a_passed_check_reveals_the_hidden_place(self):
        self.suit_up(C1, (1800, 0, 0), skills={"science": 3})     # 5 + 3 >= 7
        P.eva_place_arrive(C1, RELIC, "altar")
        self.pick(C1, "Read the carving")
        self.assertEqual(A.boarding_scene(P.eva_place_channel(RELIC, "altar")),
                         "altar_read")
        self.assertFalse(RL.rail_is_hidden(RELIC, "niche"))
        lit = self.emitted("relic_marker_lit")
        self.assertEqual([(d["RELIC_KEY"], d["RELIC_POINT"]) for d in lit],
                         [(RELIC, "niche")])
        self.assertIn("thall_niche_found", [n for n, _ in self.events])

    def test_a_suit_alongside_helps(self):
        self.suit_up(C1, (1800, 0, 0), skills={"science": 1})     # 5 + 1 = 6 alone
        self.suit_up(C2, (1750, 0, 50), skills={"science": 1})    # + 1 help = 7
        P.eva_place_arrive(C1, RELIC, "altar")
        self.pick(C1, "Read the carving")
        self.assertEqual(A.boarding_scene(P.eva_place_channel(RELIC, "altar")),
                         "altar_read")

    def test_open_falls_through_to_the_relics_barrier(self):
        self.suit_up(C1, (1800, 0, 0))
        P.eva_place_arrive(C1, RELIC, "altar")
        self.pick(C1, "Force the seal")
        opened = self.emitted("rail_opened")
        self.assertEqual([d["RAIL_BARRIER"] for d in opened], ["seal"])


class WorkingABarrierByHand(_Base):
    def advance(self, seconds):
        for _ in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()

    def test_a_check_in_clear_with_offers_the_work_verb(self):
        self.suit_up(C1, (-200, 0, 0))
        row = [r for r in T.eva_targets(C1) if r[0] == "seal"][0]
        self.assertEqual(row[4], (T.VERB_BEAM, T.VERB_WORK))
        self.assertEqual(T.eva_barrier_check(RELIC, "seal"), ("engineering", 12))

    def test_a_good_try_opens_it(self):
        self.suit_up(C1, (-200, 0, 0), skills={"engineering": 7})   # 5 + 7 >= 12
        self.assertTrue(T.eva_arm(C1, T.VERB_WORK))
        self.assertTrue(T.eva_use(C1, "seal"))
        self.advance(T.WORK_SECONDS + 1.0)
        worked = [d["EVA_RESULT"] for d in self.emitted("eva_worked")]
        self.assertIn("opened", worked)
        self.assertIn("rolled 5", self.transcript(C1))

    def test_a_bad_try_fails_and_must_be_waited_out(self):
        self.suit_up(C1, (-200, 0, 0))                              # 5 + 0 < 12
        T.eva_arm(C1, T.VERB_WORK)
        T.eva_use(C1, "seal")
        self.advance(T.WORK_SECONDS + 1.0)
        self.assertIn("failed", [d["EVA_RESULT"] for d in self.emitted("eva_worked")])
        self.assertTrue(RL.rail_barriers(RELIC, shut_only=True))
        self.assertFalse(T.eva_use(C1, "seal"))
        self.assertEqual(self.emitted("eva_worked")[-1]["EVA_RESULT"], "not yet")


class TheNavMarks(_Base):
    def test_a_quest_leading_to_a_place_marks_it(self):
        from sbs_utils.procedural.boarding_hints import eva_leads
        from sbs_utils.procedural import boarding_hints as H
        self.suit_up(C1, (-2500, 0, 0))
        orig = H._leads_of
        H._leads_of = lambda holder: ["altar", "not_a_place"]
        try:
            self.assertEqual(eva_leads(C1), ["altar"])
            self.assertEqual(E.eva_point_hint(C1, "altar"), "lead")
            E.eva_visit_note(C1, "altar")
            self.assertEqual(eva_leads(C1), [])
        finally:
            H._leads_of = orig

    def test_a_marks_order(self):
        from sbs_utils.procedural.gui import xess as X
        self.assertEqual(X._nav_mark(("a", "A", True, True, "lead")), X.NAV_MARK_LEAD)
        self.assertEqual(X._nav_mark(("a", "A", True, True, "find")), X.NAV_MARK_FIND)
        self.assertEqual(X._nav_mark(("a", "A", True, True, "")), X.NAV_MARK_VISITED)
        self.assertEqual(X._nav_mark(("a", "A", False, True)), X.NAV_MARK_SEEN)


class TheLint(unittest.TestCase):
    def rules(self, content):
        from sbs_utils.procedural.amd_lint import amd_lint
        return [str(f).rsplit("(", 1)[-1].rstrip(")") for f in amd_lint(content=content)]

    def test_the_test_relic_is_clean(self):
        self.assertEqual(self.rules(CONTENT), [])

    def test_a_walls_chain_ending_in_a_built_in_style_is_fine(self):
        ok = CONTENT.replace("Containment: none", "Containment: none\nWalls: torgoth, plates")
        self.assertEqual(self.rules(ok), [])

    def test_a_walls_chain_with_no_built_in_style_warns(self):
        bad = CONTENT.replace("Containment: none", "Containment: none\nWalls: torgoth")
        self.assertIn("relic-unknown-walls", self.rules(bad))

    def test_an_unknown_way_to_clear_warns(self):
        bad = CONTENT.replace("Clear with: beam, check engineering 12", "Clear with: kick")
        self.assertIn("relic-unknown-clear", self.rules(bad))

    def test_a_scene_that_is_not_there_warns(self):
        bad = CONTENT.replace("Scene: altar_look", "Scene: altar_nope")
        self.assertIn("dangling-scene", self.rules(bad))


if __name__ == "__main__":
    unittest.main()
