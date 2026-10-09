"""`Repair: x, y, z, radius` - a job a suit does, written like a barrier and in nobody's way.

The four claims, each of which a barrier would get wrong:

* it NEVER severs a route - the rail web routes straight through a repair where the same
  sphere written `Barrier:` shuts the way;
* it is worked with the same tools (`Clear with:`), through the same `eva_use`;
* it reads "Repair" in the suit's Fire app, on the row and while the job runs; and
* finishing it sends the quest signal `<key>_repaired`, once - and `sbs lint` knows a
  quest waiting on that has a sender, as it now does for `<barrier>_opened` and
  `<relic>_taken`.

The station worksite is the shape it was asked for: no walls, no debris, no nebula, one
chamber, a solid sphere where the hull is, an entrance point, and repair jobs.

    python -m unittest tests.test_relic_repair
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import boarding as B
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import eva_tools as T
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_schema import template_fields
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.signal import signal_observe, signal_unobserve
from sbs_utils.tickdispatcher import TickDispatcher

CID = 0x8080000000000051

# A hall with a job across the middle of it - the same sphere the barrier tests shut the
# hall with - and a station worksite beside it.
WORKSITE = """# [Mission](mission)

## [Relics](relics)

### [The Hall](hall)
---
Loc: 0, 0, 0
Walls: none
Debris: 0
---

### [the hall](hall_box)
---
Relic: hall
Box: 0, 0, 0, 2400, 200, 200
---

### [The West End](west_end)
---
Relic: hall
Point: -2300, 0, 0
Roles: entrance
---

### [The East End](east_end)
---
Relic: hall
Point: 2300, 0, 0
---

### [The Coolant Coupling](coupling)
---
Relic: hall
{job}: 0, 0, 0, 300
Clear with: beam
---

### [The Seized Valve](valve)
---
Relic: hall
Repair: 300, 0, 0, 120
Clear with: check engineering 1
---

### [Kessler Station Worksite](worksite)
---
Loc: 40000, 0, 0
Walls: none
Debris: 0
---
A station under repair. No walls, no rocks, no cloud: the space is the work area.

### [the work area](work_area)
---
Relic: worksite
Chamber: 0, 0, 0, 1500
---

### [the hull](station_hull)
---
Relic: worksite
Solid: sphere, 0, 0, 0, 500
---

### [the airlock](airlock)
---
Relic: worksite
Point: 0, 0, -1200
Roles: entrance
---

### [Hull Breach](hull_breach)
---
Relic: worksite
Repair: 0, 0, -560, 80
---

### [Antenna Mast](antenna_mast)
---
Relic: worksite
Repair: 560, 0, 0, 80
Clear with: tether
---
"""


def _doc(job="Repair"):
    return WORKSITE.replace("{job}", job)


class _Base(unittest.TestCase):
    job = "Repair"

    def setUp(self):
        reset_mock(sbs)
        sbs.resume_sim()
        DeleteQueue.clear()
        GuiClient(CID)
        self.addCleanup(reset_mission_state)
        self.quest, self.worked, self.signals = [], [], []
        signal_observe(self._watch)
        self.addCleanup(signal_unobserve, self._watch)
        R.relics_load("worksite.amd", content=_doc(self.job))
        for key in ("hall", "worksite"):
            self.assertIsNotNone(R.relic_spawn(key, atmosphere=False, marker=False), key)

    def _watch(self, name, data=None):
        self.signals.append(name)
        if name == "quest_signal":
            self.quest.append((data or {}).get("SIGNAL_NAME"))
        if name == "eva_worked":
            self.worked.append((data or {}).get("EVA_RESULT"))

    def suit_up(self, relic="hall", at=(-200, 0, 0), jobs="boarding"):
        who = lifeform_spawn("Lt Okonkwo", "terran_male", jobs)
        B.boarding_assign(CID, who)
        suit = E.eva_suit_spawn(who, relic, at[0], at[1], at[2], hull="tsn_shuttle",
                                side="tsn")
        E.eva_take(CID, suit, relic)
        return suit

    def advance(self, seconds):
        for _ in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()

    def row(self, key):
        rows = [r for r in T.eva_targets(CID) if r[0] == key]
        return rows[0] if rows else None


class TheReader(_Base):
    def test_the_field_is_the_relic_archetypes(self):
        self.assertIn("repair", template_fields("relic", include_internal=True))

    def test_a_repair_is_read_in_a_barriers_shape(self):
        jobs = R.relic_repairs("hall")
        self.assertEqual(jobs["coupling"][:4], [0.0, 0.0, 0.0, 300.0])
        self.assertEqual(jobs["coupling"][5], ["beam"])
        self.assertEqual(jobs["coupling"][6], "The Coolant Coupling")
        self.assertEqual(R.relic_barriers("hall"), {}, "a repair is not a barrier")
        self.assertEqual(R.relic_part_info("hall", "coupling")["kind"], "repair")

    def test_the_station_worksite_builds_bare(self):
        self.assertEqual(len(role(R.relic_wall_role("worksite"))), 0,
                         "Walls: none and Debris: 0 dress nothing")
        self.assertEqual(sorted(R.relic_repairs("worksite")),
                         ["antenna_mast", "hull_breach"])
        # The solid is the hull: its middle is not somewhere a suit can be.
        self.assertFalse(R.relic_holds("worksite", (40000, 0, 0)))
        self.assertTrue(R.relic_holds("worksite", (40000, 0, -1200)))


class NeverInTheWay(_Base):
    def test_a_route_goes_straight_through_a_repair(self):
        route = RL.rail_route("hall", (-2300, 0, 0), "east_end")
        self.assertTrue(route, "a repair across the hall must not shut the hall")
        self.assertEqual(RL.rail_barriers("hall"), [])

    def test_it_is_somewhere_the_crew_can_be_sent(self):
        self.suit_up("worksite", at=(40000, 0, -1200))
        names = [name for name, _label, _pos in E.eva_points(CID)]
        self.assertIn("hull_breach", names)
        self.assertTrue(E.eva_goto(CID, "hull_breach"))

    def test_it_has_a_marker_that_blocks_nothing(self):
        marks = [to_object(i) for i in role(R.RELIC_REPAIR_ROLE)]
        self.assertEqual(len(marks), 4)
        for obj in marks:
            self.assertEqual(obj.engine_object.exclusion_radius, 0)


class TheSameSphereAsABarrier(_Base):
    """The control: written `Barrier:`, the very same line shuts the hall."""
    job = "Barrier"

    def test_the_barrier_does_sever_the_route(self):
        self.assertFalse(RL.rail_route("hall", (-2300, 0, 0), "east_end"))
        self.assertNotIn("coupling", R.relic_repairs("hall"))


class DoingOne(_Base):
    def test_it_is_a_target_of_kind_repair_with_its_own_verbs(self):
        self.suit_up()
        key, label, kind, _gap, verbs = self.row("coupling")
        self.assertEqual((label, kind), ("The Coolant Coupling", "repair"))
        self.assertEqual(verbs, (T.VERB_BEAM,))
        self.assertEqual(self.row("valve")[4], (T.VERB_WORK,))

    def test_no_clear_with_means_the_beam_as_for_a_barrier(self):
        self.suit_up("worksite", at=(40000, 0, -800))
        self.assertEqual(self.row("hull_breach")[4], (T.VERB_BEAM,))

    def test_the_beam_does_it_and_the_quest_hears_it_once(self):
        self.suit_up()
        self.assertTrue(T.eva_use(CID, "coupling", T.VERB_BEAM))
        self.assertEqual(T.eva_working_kind(CID), "repair")
        self.advance(T.CUT_SECONDS + 1)
        self.assertEqual(self.worked[-1], "repaired")
        self.assertEqual(self.quest, ["coupling_repaired"])
        self.assertIn("relic_repaired", self.signals)
        self.assertTrue(R.relic_repair_fixed("hall", "coupling"))
        self.assertIsNone(self.row("coupling"), "a job that is done is off the list")
        self.assertFalse(R.relic_repair_done("hall", "coupling"))
        self.assertEqual(self.quest, ["coupling_repaired"])

    def test_the_wrong_tool_is_refused_by_name(self):
        self.suit_up()
        self.assertFalse(T.eva_use(CID, "coupling", T.VERB_TETHER))
        self.assertEqual(self.worked[-1], "wrong tool")

    def test_a_check_does_it_by_hand(self):
        self.suit_up(jobs="boarding,engineering")
        self.assertEqual(T.eva_barrier_check("hall", "valve"), ("engineering", 1))
        self.assertTrue(T.eva_use(CID, "valve", T.VERB_WORK))
        self.advance(T.WORK_SECONDS + 1)
        # DC 1: any roll at all does it, so this is about the path, not the dice.
        self.assertEqual(self.worked[-1], "repaired")
        self.assertEqual(self.quest, ["valve_repaired"])

    def test_picking_a_repair_does_not_lock_the_suits_weapons_on_it(self):
        self.suit_up()
        self.assertTrue(T.eva_aim(CID, "coupling"))
        self.assertEqual(T.eva_selected_target(CID), "coupling")
        self.assertFalse(T.eva_aimed(CID), "a beam fires at the weapons lock")

    def test_a_job_whose_marker_is_gone_can_still_be_done(self):
        self.suit_up()
        for oid in list(role(R.RELIC_REPAIR_ROLE)):
            sbs.delete_object(oid)
        DeleteQueue.clear()
        self.assertTrue(T.eva_aim(CID, "coupling"))
        self.assertTrue(T.eva_use(CID, "coupling", T.VERB_BEAM))
        self.advance(T.CUT_SECONDS + 1)
        self.assertEqual(self.quest, ["coupling_repaired"])

    def test_a_story_beat_can_do_one_too(self):
        self.assertTrue(R.relic_repair_done("worksite", "antenna_mast"))
        self.assertEqual(self.quest, ["antenna_mast_repaired"])
        self.assertFalse(R.relic_repair_done("worksite", "no_such_job"))


class TheFireApp(_Base):
    """The rows and the banner the suit's Fire app actually sends."""

    def test_the_row_and_the_running_job_both_say_repair(self):
        self.suit_up()
        from sbs_utils.procedural.gui import xess as X
        captured = {}

        def fake_list_box(rows, *a, **kw):
            captured["rows"] = rows

            class _LB:
                def get_value(self):
                    return None
            return _LB()

        texts = []
        import sbs_utils.procedural.gui.listbox as LBM
        import sbs_utils.procedural.gui.text as TXM
        import sbs_utils.procedural.gui.row as RWM
        import sbs_utils.procedural.gui.button as BTM
        import sbs_utils.procedural.gui.message as MSM
        for mod, name, fn in (
                (LBM, "gui_list_box", fake_list_box),
                (TXM, "gui_text", lambda props, *a, **kw: texts.append(props)),
                (RWM, "gui_row", lambda *a, **kw: None),
                (BTM, "gui_button", lambda *a, **kw: None),
                (MSM, "gui_message_callback", lambda *a, **kw: None)):
            orig = getattr(mod, name)
            setattr(mod, name, fn)
            self.addCleanup(setattr, mod, name, orig)
        orig_head = X.gui_xess_head
        X.gui_xess_head = lambda *a, **kw: None
        self.addCleanup(setattr, X, "gui_xess_head", orig_head)

        X._work_app(CID)
        labels = {row[0]: row[1] for row in captured["rows"]}
        self.assertTrue(labels["coupling"].startswith("Repair: The Coolant Coupling"),
                        labels)
        self.assertTrue(any("A Repair takes the tool it names." in t for t in texts))

        T.eva_use(CID, "coupling", T.VERB_BEAM)
        del texts[:]
        X._work_app(CID)
        self.assertTrue(any("REPAIR - The Coolant Coupling" in t for t in texts), texts)
        self.assertFalse(any("BEAM - " in t for t in texts), texts)


QUESTS = """
## [Quests](quests)

### [Mend the coupling](q_mend)
---
Done when: signal coupling_repaired
---

### [Open the hatch](q_hatch)
---
Done when: signal hatch_opened
---

### [Take the core](q_take)
---
Done when: signal hall_taken
---

### [Never](q_never)
---
Done when: signal nothing_sends_this
---
"""

PIECE_AND_HATCH = """
### [the hatch](hatch)
---
Relic: hall
Barrier: 1200, 0, 0, 150
Clear with: beam
---

### [the cradle](cradle)
---
Relic: hall
Point: 2000, 0, 0
Roles: relic_piece
---
"""


class LintKnowsWhoSendsThem(unittest.TestCase):
    def _unfired(self, text):
        found = amd_lint(content=text, mast_sources=["# an empty story\n"])
        return sorted(f.message.split("`")[3] for f in found if f.code == "unfired-signal")

    def test_a_record_in_the_file_is_the_sender(self):
        doc = _doc().replace("\n### [Kessler", PIECE_AND_HATCH + "\n### [Kessler") + QUESTS
        self.assertEqual(self._unfired(doc), ["nothing_sends_this"])

    def test_without_the_record_the_wait_is_still_reported(self):
        self.assertEqual(self._unfired(_doc() + QUESTS),
                         ["hall_taken", "hatch_opened", "nothing_sends_this"])

    def test_a_repair_is_a_part_and_lints_clean(self):
        codes = [f.code for f in amd_lint(content=_doc(), cross_file=False)]
        for code in ("unknown-field", "relic-barrier-seals", "relic-disconnected",
                     "relic-section-stray"):
            self.assertNotIn(code, codes, codes)

    def test_a_short_or_flat_repair_is_reported(self):
        short = _doc().replace("Repair: 300, 0, 0, 120", "Repair: 300, 0, 0")
        self.assertIn("relic-short-part",
                      [f.code for f in amd_lint(content=short, cross_file=False)])
        flat = _doc().replace("Repair: 300, 0, 0, 120", "Repair: 300, 0, 0, 0")
        self.assertIn("relic-bad-radius",
                      [f.code for f in amd_lint(content=flat, cross_file=False)])


if __name__ == "__main__":
    unittest.main()
