"""What a suit can DO: the target list, the two verbs, and every refusal said out loud.

The one thing worth reading first: **BEAM does not shoot anything, and that is not a
shortcut.** There is no engine call that fires a beam or subtracts hull or shield from a
space object - the whole beam surface of the API is `set_beam_damages`,
`get_shield_hit_index` and `launch_torpedo`. A suit's beam CUTS a barrier open, which is a
state change we own outright and can therefore test without a bridge.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import eva_tools as T
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural import volume as V
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher

CID = 71
CID2 = 72
RELIC = "tool_relic"


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
        R._RELIC_RECORDS.clear()
        for cid in (CID, CID2):
            GuiClient(cid)
        # A hall with a shut hatch across the middle and a long way round.
        V.volume_define(RELIC, boxes={
            "hall": (0, 0, 0, 2400, 200, 200),
            "wleg": (-2400, 0, 900, 200, 200, 900),
            "eleg": (2400, 0, 900, 200, 200, 900),
            "loop": (0, 0, 1700, 2400, 200, 200),
        })
        R._RELIC_RECORDS[RELIC] = {
            "key": RELIC, "loc": (0, 0, 0), "volume": RELIC,
            "points": {"west end": [-2300, 0, 0, ["entrance"], "The West End"],
                       "east end": [2300, 0, 0, [], "The East End"]},
            # [x, y, z, radius, opens_when, clear_with, display]
            "barriers": {"hatch": [0, 0, 0, 300, None, ["beam"], "The Seized Hatch"]},
            "contents": [],
        }
        R.relic_rails_ensure(RELIC)
        RL.rail_barrier(RELIC, "hatch", (0, 0, 0), 300, display="The Seized Hatch")
        self.events = []
        from sbs_utils.procedural.signal import signal_observe
        signal_observe(self._watch)

    def _watch(self, name, data=None):
        if name == "eva_worked":
            self.events.append(dict(data or {}))

    def tearDown(self):
        TickDispatcher.clear()
        V.volume_clear()
        RL.rail_clear()
        E.eva_clear()
        T.eva_tools_clear()
        R._RELIC_RECORDS.clear()

    def suit_up(self, cid=CID, at=(-200, 0, 0)):
        who = lifeform_spawn("Boarder %d" % cid, "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, RELIC, at[0], at[1], at[2],
                                hull="tsn_shuttle", side="tsn", volume=RELIC)
        E.eva_take(cid, suit, RELIC, volume=RELIC)
        return suit

    def results(self):
        return [e.get("EVA_RESULT") for e in self.events]

    def advance(self, seconds):
        for _ in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()


class WhatIsInReach(_Base):
    def test_a_shut_barrier_within_reach_is_a_target(self):
        self.suit_up()
        rows = T.eva_targets(CID)
        self.assertIn("hatch", [r[0] for r in rows])
        row = [r for r in rows if r[0] == "hatch"][0]
        self.assertEqual(row[1], "The Seized Hatch")
        self.assertEqual(row[2], "barrier")
        self.assertIn(T.VERB_BEAM, row[4])

    def test_out_of_reach_is_not_offered(self):
        self.suit_up(at=(-2300, 0, 0))
        self.assertNotIn("hatch", [r[0] for r in T.eva_targets(CID)])

    def test_an_open_barrier_is_not_offered(self):
        """Nothing to do to a way that is already open."""
        self.suit_up()
        RL.rail_barrier_open(RELIC, "hatch")
        self.assertNotIn("hatch", [r[0] for r in T.eva_targets(CID)])

    def test_the_list_is_nearest_first(self):
        self.suit_up()
        gaps = [r[3] for r in T.eva_targets(CID)]
        self.assertEqual(gaps, sorted(gaps))

    def test_another_boarder_is_not_a_target(self):
        """A suit is a player hull with `__player__` REMOVED, so it is a space object like
        any other - and a party of six is five more things in everybody's reach."""
        self.suit_up(CID)
        self.suit_up(CID2, at=(-180, 0, 0))
        keys = [str(r[0]) for r in T.eva_targets(CID)]
        self.assertNotIn(str(E.eva_my_suit(CID2)), keys)

    def test_no_suit_means_no_targets(self):
        self.assertEqual(T.eva_targets(CID), [])


class ArmingIsItsOwnDecision(_Base):
    def test_arm_and_stow(self):
        self.suit_up()
        self.assertTrue(T.eva_arm(CID, T.VERB_TETHER))
        self.assertEqual(T.eva_armed(CID), T.VERB_TETHER)
        T.eva_disarm(CID)
        self.assertIsNone(T.eva_armed(CID))

    def test_an_unknown_verb_is_refused(self):
        self.assertFalse(T.eva_arm(CID, "photon"))

    def test_arming_is_per_console(self):
        self.suit_up(CID)
        self.suit_up(CID2)
        T.eva_arm(CID, T.VERB_TETHER)
        self.assertIsNone(T.eva_armed(CID2))


class CuttingOpensTheWay(_Base):
    def test_a_cut_takes_time_and_then_opens_it(self):
        self.suit_up()
        T.eva_arm(CID, T.VERB_BEAM)
        self.assertTrue(T.eva_use(CID, "hatch"))
        self.assertFalse(RL.rail_barrier_is_open(RELIC, "hatch"),
                         "it opened instantly - the cut is supposed to take time")
        self.advance(T.CUT_SECONDS + 1.0)
        self.assertTrue(RL.rail_barrier_is_open(RELIC, "hatch"))
        self.assertIn("opened", self.results())

    def test_the_route_opens_with_it(self):
        """The point of the whole verb: a shut way sends you the long way round, and
        cutting it gives you the short one."""
        self.suit_up(at=(-2300, 0, 0))
        self.assertTrue(E.eva_goto(CID, "east end"))
        long_way = E.eva_route(CID)[1]
        E.eva_stop(CID)
        RL.rail_barrier_open(RELIC, "hatch")
        self.assertTrue(E.eva_goto(CID, "east end"))
        self.assertLess(E.eva_route(CID)[1], long_way,
                        "opening the hatch did not shorten the route")

    def test_a_job_in_progress_is_reported(self):
        self.suit_up()
        T.eva_use(CID, "hatch", T.VERB_BEAM)
        target, verb, left, display = T.eva_working(CID)
        self.assertEqual(target, "hatch")
        self.assertEqual(verb, T.VERB_BEAM)
        self.assertGreater(left, 0.0)
        self.assertEqual(display, "The Seized Hatch")

    def test_stopping_leaves_it_shut(self):
        self.suit_up()
        T.eva_use(CID, "hatch", T.VERB_BEAM)
        self.assertTrue(T.eva_abort(CID))
        self.advance(T.CUT_SECONDS + 1.0)
        self.assertFalse(RL.rail_barrier_is_open(RELIC, "hatch"))
        self.assertIn("stopped", self.results())

    def test_two_consoles_cut_independently(self):
        self.suit_up(CID)
        self.suit_up(CID2, at=(-150, 0, 0))
        T.eva_use(CID, "hatch", T.VERB_BEAM)
        self.assertEqual(T.eva_working(CID2)[0], None)


class EveryRefusalIsSaidOutLoud(_Base):
    """A verb that fails silently is indistinguishable from a broken screen - which has
    already been reported from a bridge, on the other body model."""

    def test_out_of_reach(self):
        self.suit_up(at=(-2300, 0, 0))
        self.assertFalse(T.eva_use(CID, "hatch", T.VERB_BEAM))
        self.assertIn("out of reach", self.results())

    def test_the_wrong_tool(self):
        """The hatch says `Clear with: beam`. A tether on it is a refusal with a reason,
        not a press that does nothing."""
        self.suit_up()
        self.assertFalse(T.eva_use(CID, "hatch", T.VERB_TETHER))
        self.assertIn("wrong tool", self.results())

    def test_no_suit(self):
        self.assertFalse(T.eva_use(CID, "hatch", T.VERB_BEAM))
        self.assertIn("no suit", self.results())

    def test_already_working(self):
        self.suit_up()
        self.assertTrue(T.eva_use(CID, "hatch", T.VERB_BEAM))
        self.assertFalse(T.eva_use(CID, "hatch", T.VERB_BEAM))
        self.assertIn("already working", self.results())

    def test_every_report_names_the_console_and_the_target(self):
        self.suit_up()
        T.eva_use(CID, "hatch", T.VERB_TETHER)
        self.assertTrue(self.events)
        e = self.events[-1]
        self.assertEqual(e["EVA_CLIENT"], CID)
        self.assertEqual(e["EVA_TARGET"], "hatch")
        self.assertEqual(e["EVA_VERB"], T.VERB_TETHER)


class HaulingAFind(_Base):
    def _drop_salvage(self, at=(-150, 0, 0)):
        from sbs_utils.procedural.spawn import terrain_spawn
        got = terrain_spawn(at[0], at[1], at[2], "Torgoth alloy", "#,item",
                            "generic-sphere", "behav_asteroid")
        obj = getattr(got, "py_object", got)
        return obj.id if hasattr(obj, "id") else obj

    def test_salvage_in_reach_is_offered_for_the_tether(self):
        self.suit_up()
        self._drop_salvage()
        rows = [r for r in T.eva_targets(CID) if r[2] == "haul"]
        self.assertTrue(rows, "nothing haulable was offered")
        self.assertIn(T.VERB_TETHER, rows[0][4])

    def test_tethering_something_small_attaches(self):
        self.suit_up()
        item = self._drop_salvage()
        self.assertTrue(T.eva_use(CID, item, T.VERB_TETHER))
        from sbs_utils.procedural.grav_tether import grav_tether_involves
        self.assertTrue(grav_tether_involves(item))

    def test_something_too_heavy_is_refused_by_name(self):
        """THE TRAP THIS CHECK EXISTS FOR. `grav_tether` silently REVERSES the engine pair
        when the target is twice the source's mass or more, and a suit is the smallest
        thing in any relic - so an unchecked tether reels the BOARDER into the cargo."""
        self.suit_up()
        item = self._drop_salvage()
        from sbs_utils.procedural import grav_tether as G
        self.addCleanup(G.grav_tether_set_mass_fn, None)
        G.grav_tether_set_mass_fn(
            lambda obj: 100.0 if str(getattr(obj, "id", obj)) == str(item) else 1.0)
        self.assertFalse(T.eva_use(CID, item, T.VERB_TETHER))
        self.assertIn("too heavy", self.results())
        from sbs_utils.procedural.grav_tether import grav_tether_involves
        self.assertFalse(grav_tether_involves(item),
                         "it attached anyway - the boarder is about to be reeled in")


class TheJobsPassIsShared(_Base):
    def test_one_watcher_however_many_ask(self):
        self.suit_up(CID)
        self.suit_up(CID2, at=(-150, 0, 0))
        first = T.eva_tools_watch()
        self.assertIs(T.eva_tools_watch(), first)

    def test_the_probe_does_not_conjure_state_by_asking(self):
        self.assertEqual(T.eva_tools_working(), 0)
        self.assertEqual(T.eva_tools_working(), 0)

    def test_stowing_the_suits_stops_everything(self):
        self.suit_up()
        T.eva_use(CID, "hatch", T.VERB_BEAM)
        self.assertEqual(T.eva_tools_working(), 1)
        E.eva_clear()
        self.assertEqual(T.eva_tools_working(), 0)


if __name__ == "__main__":
    unittest.main()
