"""A built ruin and the crew who can go into it, joined by the library instead of by a
page of MAST every mission had to copy.

What each class is for:

* `QuestSignals` - the three beats a ruin sends by itself. Before this they were MAST in
  one mission's story: `<barrier>_opened` re-sent from `rail_opened`, and `<relic>_taken`
  from a watcher task that ended silently when a suit REELED THE PIECE IN - the pickup is
  deleted inside the ruin, so it never "left the volume" and the quest waited forever.
* `OpenAndClose` - `eva_relic_open` / `eva_relic_close`, by identity.
* `Proximity` - the offer follows the ship. It used to be made once, at build time, and
  never withdrawn: with two ruins the last one built won, and SUIT UP worked from across
  the map.
* `SuitHull` - the exosuit is the default, and a mission without its ship data gets a
  stock hull and ONE warning rather than the `unknown` placeholder.

Everything is read from real `.amd` text through `relics_load` and built by `relic_spawn`,
the calls a mission makes.

    python -m unittest tests.test_eva_relics
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.gui import GuiClient
from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import boarding as B
from sbs_utils.procedural import eva as E
from sbs_utils.procedural import eva_relics as W
from sbs_utils.procedural import ship_data as SD
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.signal import signal_observe, signal_unobserve
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.tickdispatcher import TickDispatcher

# A real console id: the 0x8000... bit is what `is_client_id` tests.
CID = 0x8080000000000041

RUINS = """# [Mission](mission)

## [Relics](relics)

### [The Hollow](hollow)
---
Loc: 0, 0, 20000
---
Older than anyone who could have built it.

### [The Mouth](mouth)
---
Relic: hollow
Chamber: 0, 0, 0, 900
---

### [The Nave](nave)
---
Relic: hollow
Chamber: 3000, 0, 0, 1100
Passage to: mouth 350
---

### [the way in](hollow_door)
---
Relic: hollow
Point: -600, 0, 0
Roles: entrance
---

### [the cradle](hollow_cradle)
---
Relic: hollow
Point: 3000, 0, 0
Roles: relic_piece
Item: beacon_core
---

### [The Seized Hatch](nave_hatch)
---
Relic: hollow
Barrier: 1500, 0, 0, 400
Clear with: beam
---

### [The Cyst](cyst)
---
Loc: 60000, 0, 0
---
A second ruin, far off.

### [The Sac](sac)
---
Relic: cyst
Chamber: 0, 0, 0, 800
---
"""

# The Hollow's entrance point in the world, and somewhere a long way from both ruins.
DOOR = (-600.0, 0.0, 20000.0)
FAR = (-30000.0, 0.0, -30000.0)


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        sbs.resume_sim()
        DeleteQueue.clear()
        GuiClient(CID)
        self.heard = []
        heard = self.heard

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        # The `eva` category is where the wiring says why it did not do something. NOT
        # `mast.runtime`: a fallback that works is not an error, and a line there fails
        # every headless run of the mission.
        handler = _Listen()
        for name in ("mast.runtime", "eva"):
            logging.getLogger(name).addHandler(handler)
            self.addCleanup(logging.getLogger(name).removeHandler, handler)

        self.quest = []
        self.signals = []
        signal_observe(self._watch)
        self.addCleanup(signal_unobserve, self._watch)
        self.addCleanup(reset_mission_state)

        R.relics_load("ruins.amd", content=RUINS)
        for key in ("hollow", "cyst"):
            self.assertIsNotNone(
                R.relic_spawn(key, walls=False, atmosphere=False, marker=False), key)

    def _watch(self, name, data=None):
        self.signals.append(name)
        if name == "quest_signal":
            self.quest.append((data or {}).get("SIGNAL_NAME"))

    def ship(self, at=FAR, name="Artemis"):
        return to_object(player_spawn(at[0], at[1], at[2], name, "tsn",
                                      "tsn_light_cruiser"))

    def move(self, obj, at):
        from sbs_utils.vec import Vec3
        obj.pos = Vec3(at[0], at[1], at[2])

    def advance(self, seconds):
        for _ in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()

    def piece(self):
        ids = R.relic_pieces("hollow")
        self.assertEqual(len(ids), 1, "the relic_piece item must be placed and watched")
        return to_object(ids[0])

    def suit_up(self, relic="hollow"):
        who = lifeform_spawn("Lt Okonkwo", "terran_male", "boarding")
        x, y, z = E.eva_entry(relic)
        suit = E.eva_suit_spawn(who, relic, x, y, z, hull="tsn_shuttle", side="tsn")
        E.eva_take(CID, suit, relic)
        return suit


class RelicHolds(_Base):
    def test_inside_outside_and_unknown(self):
        self.assertTrue(R.relic_holds("hollow", (0, 0, 20000)))
        self.assertTrue(R.relic_holds("hollow", (1500, 0, 20000)))       # the passage
        self.assertFalse(R.relic_holds("hollow", (0, 0, 0)))
        self.assertFalse(R.relic_holds("no_such_relic", (0, 0, 20000)))

    def test_takes_an_object(self):
        self.assertTrue(R.relic_holds("hollow", self.piece()))

    def test_a_relic_with_no_space_holds_nothing(self):
        R.relic_release("hollow")
        self.assertFalse(R.relic_holds("hollow", (0, 0, 20000)))


class QuestSignals(_Base):
    def test_a_barrier_opening_sends_its_quest_signal_once(self):
        self.assertTrue(R.relic_open_barrier("hollow", "nave_hatch"))
        self.assertEqual(self.quest, ["nave_hatch_opened"])
        self.assertIn("rail_opened", self.signals)
        # Already open: nothing happens, and nothing is said twice.
        self.assertFalse(R.relic_open_barrier("hollow", "nave_hatch"))
        self.assertEqual(self.quest, ["nave_hatch_opened"])

    def test_the_piece_leaving_the_ruin_sends_taken(self):
        piece = self.piece()
        self.advance(3)
        self.assertEqual(self.quest, [], "a piece still in its cradle is not taken")
        self.move(piece, (0, 0, 0))                      # towed clear of the ruin
        self.advance(3)
        self.assertEqual(self.quest, ["hollow_taken"])
        self.assertIn("relic_piece_taken", self.signals)

    def test_a_piece_reeled_in_and_collected_sends_taken(self):
        # THE GAP. The pickup is collected - and deleted - INSIDE the ruin, so nothing
        # ever leaves the volume.
        piece = self.piece()
        pid = to_id(piece)
        delete_object(pid)
        DeleteQueue.clear()
        self.advance(3)
        self.assertEqual(self.quest, [], "a piece that vanished is not thereby taken")
        self.assertEqual(R.relic_piece_collected("beacon_core"), "hollow")
        self.assertEqual(self.quest, ["hollow_taken"])

    def test_collected_by_id_names_the_right_piece(self):
        pid = to_id(self.piece())
        self.assertIsNone(R.relic_piece_collected("beacon_core", item_id=pid + 9999))
        self.assertEqual(R.relic_piece_collected("beacon_core", item_id=pid), "hollow")
        self.assertEqual(self.quest, ["hollow_taken"])

    def test_taken_is_never_sent_twice(self):
        piece = self.piece()
        self.move(piece, (0, 0, 0))
        self.advance(3)
        self.assertIsNone(R.relic_piece_collected("beacon_core", item_id=to_id(piece)))
        self.advance(3)
        self.assertEqual(self.quest, ["hollow_taken"])

    def test_an_ordinary_pickup_is_nobodys_piece(self):
        self.assertIsNone(R.relic_piece_collected("salvage"))
        self.assertEqual(self.quest, [])

    def test_a_ruin_torn_down_does_not_read_as_the_piece_leaving(self):
        self.piece()
        R.relic_release("hollow")
        self.advance(3)
        self.assertEqual(self.quest, [])


class OpenAndClose(_Base):
    def test_open_offers_the_ruin_and_opens_a_crew_party(self):
        ship = self.ship()
        self.assertTrue(W.eva_relic_open("hollow", ship=ship))
        offer = E.eva_offered()
        self.assertEqual(offer["relic"], "hollow")
        self.assertEqual(offer["volume"], "hollow")
        invite = B.boarding_invitation()
        self.assertIsNotNone(invite)
        self.assertTrue(invite.get("crew"))
        self.assertEqual(invite["ship"], ship.id)
        self.assertEqual(invite["title"], "The Hollow")
        self.assertEqual(W.eva_relic_opened(), "hollow")

    def test_open_twice_is_the_same_party(self):
        ship = self.ship()
        W.eva_relic_open("hollow", ship=ship)
        first = B.boarding_invitation()
        W.eva_relic_open("hollow", ship=ship)
        self.assertIs(B.boarding_invitation(), first)

    def test_a_missions_own_offer_keeps_its_hull(self):
        # A mission written before this existed still answers `relic_built` itself.
        ship = self.ship()
        E.eva_offer("hollow", volume="hollow", hull="tsn_shuttle")
        B.boarding_invite_crew(ship, title="Mine")
        self.assertTrue(W.eva_relic_open("hollow", ship=ship))
        self.assertEqual(E.eva_offered()["hull"], "tsn_shuttle")
        self.assertEqual(B.boarding_invitation()["title"], "Mine")

    def test_a_missions_own_cast_party_is_never_replaced(self):
        ship = self.ship()
        who = lifeform_spawn("Ensign Vale", "terran_male", "boarding")
        mine = B.boarding_invite(ship, [who], title="The Station", site=None)
        self.assertFalse(W.eva_relic_open("hollow", ship=ship))
        self.assertIs(B.boarding_invitation(), mine)
        # And the door stays BEAM DOWN: no offer was made behind the mission's back.
        self.assertIsNone(E.eva_offered())
        said = [m for m in self.heard if "boarding party of its own" in m]
        self.assertEqual(len(said), 1, self.heard)
        W.eva_relic_open("hollow", ship=ship)
        said = [m for m in self.heard if "boarding party of its own" in m]
        self.assertEqual(len(said), 1, "a refusal is logged once, not every pass")

    def test_an_unknown_relic_is_refused_and_said(self):
        self.assertFalse(W.eva_relic_open("no_such_relic"))
        self.assertTrue(any("no_such_relic" in m for m in self.heard), self.heard)

    def test_close_withdraws_both_halves(self):
        W.eva_relic_open("hollow", ship=self.ship())
        self.assertTrue(W.eva_relic_close("hollow"))
        self.assertIsNone(E.eva_offered())
        self.assertIsNone(B.boarding_invitation())
        self.assertIsNone(W.eva_relic_opened())

    def test_close_waits_for_whoever_is_out(self):
        W.eva_relic_open("hollow", ship=self.ship())
        self.suit_up()
        self.assertFalse(W.eva_relic_close("hollow"))
        self.assertEqual(E.eva_offered()["relic"], "hollow")

    def test_close_of_another_ruin_is_a_no_op(self):
        W.eva_relic_open("hollow", ship=self.ship())
        self.assertFalse(W.eva_relic_close("cyst"))
        self.assertEqual(E.eva_offered()["relic"], "hollow")

    def test_tearing_the_ruin_down_withdraws_it_and_takes_its_suits(self):
        W.eva_relic_open("hollow", ship=self.ship())
        self.suit_up()
        self.assertEqual(len(E.eva_suits("hollow")), 1)
        R.relic_release("hollow")
        DeleteQueue.clear()
        self.assertIsNone(E.eva_offered())
        self.assertEqual(len(E.eva_suits("hollow")), 0)
        # And the console is not left flying a ship that has been deleted.
        self.assertIsNone(E.eva_my_suit(CID))
        self.assertIsNone(E.eva_my_relic(CID))


class Proximity(_Base):
    def test_nothing_is_offered_from_across_the_map(self):
        self.ship(FAR)
        self.assertIsNone(W.eva_relics_pass())
        self.assertIsNone(E.eva_offered())

    def test_the_ruin_the_ship_is_at_is_offered(self):
        ship = self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        self.assertEqual(W.eva_relics_pass(), "hollow")
        self.assertEqual(E.eva_offered()["relic"], "hollow")
        self.assertEqual(B.boarding_invitation()["ship"], ship.id)

    def test_range_is_measured_from_the_entrance(self):
        # 3500 from the entrance point, though well inside 3000 of the far room.
        self.ship((DOOR[0] - 3500, 0, DOOR[2]))
        self.assertIsNone(W.eva_relics_pass())

    def test_leaving_withdraws_it(self):
        ship = self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        W.eva_relics_pass()
        self.move(ship, FAR)
        self.assertIsNone(W.eva_relics_pass())
        self.assertIsNone(E.eva_offered())
        self.assertIsNone(B.boarding_invitation())

    def test_somebody_still_out_keeps_it_open(self):
        ship = self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        W.eva_relics_pass()
        self.suit_up()
        self.move(ship, FAR)
        self.assertEqual(W.eva_relics_pass(), "hollow")
        self.assertEqual(E.eva_offered()["relic"], "hollow")

    def test_a_missions_own_offer_is_never_withdrawn_or_replaced(self):
        # A mission written before this existed offers its ruin the moment it is built,
        # from wherever the ship is. That is the mission saying when.
        ship = self.ship(FAR)
        E.eva_offer("hollow", volume="hollow", hull="tsn_shuttle")
        B.boarding_invite_crew(ship, title="Mine")
        self.assertEqual(W.eva_relics_pass(), "hollow")
        self.assertEqual(E.eva_offered()["hull"], "tsn_shuttle")
        self.assertEqual(B.boarding_invitation()["title"], "Mine")
        # Nor is it traded for the ruin the ship is actually at.
        self.move(ship, (60000 - 1500, 0, 0))
        self.assertEqual(W.eva_relics_pass(), "hollow")

    def test_an_offer_the_mission_takes_over_becomes_the_missions(self):
        ship = self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        self.assertEqual(W.eva_relics_pass(), "hollow")
        E.eva_offer("hollow", volume="hollow", hull="tsn_shuttle")
        self.move(ship, FAR)
        self.assertEqual(W.eva_relics_pass(), "hollow")
        self.assertIsNotNone(E.eva_offered())

    def test_two_ruins_the_offer_follows_the_ship(self):
        # `cyst` was built LAST. Offered at build time, it would be the one on offer.
        ship = self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        self.assertEqual(W.eva_relics_pass(), "hollow")
        self.move(ship, (60000 - 1500, 0, 0))
        self.assertEqual(W.eva_relics_pass(), "cyst")
        self.assertEqual(E.eva_offered()["relic"], "cyst")
        self.assertEqual(B.boarding_invitation()["title"], "The Cyst")

    def test_a_ruin_that_is_not_built_is_not_offered(self):
        R.relic_release("hollow")
        self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        self.assertIsNone(W.eva_relics_pass())

    def test_the_watch_runs_the_pass_on_the_tick(self):
        ship = self.ship(FAR)
        self.assertIsNotNone(W.eva_relics_watch())
        self.assertIs(W.eva_relics_watch(), W.eva_relics_watch())
        self.advance(3)
        self.assertIsNone(E.eva_offered())
        self.move(ship, (DOOR[0] - 2000, 0, DOOR[2]))
        self.advance(3)
        self.assertEqual(E.eva_offered()["relic"], "hollow")
        self.move(ship, FAR)
        self.advance(3)
        self.assertIsNone(E.eva_offered())

    def test_auto_off_is_the_opt_out(self):
        self.assertTrue(W.eva_relics_auto())
        self.assertFalse(W.eva_relics_auto(False))
        self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        self.assertIsNone(W.eva_relics_watch())
        self.advance(3)
        self.assertIsNone(E.eva_offered())

    def test_a_reset_leaves_nothing_on_the_ledger(self):
        self.ship((DOOR[0] - 2000, 0, DOOR[2]))
        W.eva_relics_watch()
        self.advance(3)
        R.relic_open_barrier("hollow", "nave_hatch")
        self.assertEqual(W.eva_relics_count(), 2)
        self.assertEqual(R.relic_quest_signal_count(), 1)
        reset_mission_state()
        self.assertEqual(W.eva_relics_count(), 0)
        self.assertEqual(R.relic_quest_signal_count(), 0)
        leaks = reset_mission_audit()
        for name in ("eva relic wiring", "relic quest signals", "relic contents",
                     "boarding invitation"):
            self.assertNotIn(name, leaks)
        self.assertTrue(W.eva_relics_auto(), "the opt-out is per mission")

    def test_mast_can_call_it(self):
        import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals
        for name in ("eva_relic_open", "eva_relic_close", "eva_relics_watch",
                     "eva_relics_auto", "relic_holds", "relic_piece_collected"):
            self.assertIn(name, MastGlobals.globals, name)


class SuitHull(_Base):
    def setUp(self):
        super().setUp()
        self.addCleanup(SD.extra_ship_data_force, None)

    def _declare_the_exosuit(self):
        """The production path: the setting on, and the boarding addon's own file."""
        import os
        from sbs_utils import fs
        SD.extra_ship_data_force(True)
        media = os.path.join(fs.get_missions_dir(), "LegendaryMissions", "media")
        self.assertTrue(SD.add_extra("lm_eva_ships", path=media),
                        "LegendaryMissions/media/lm_eva_ships must load")

    def test_without_its_ship_data_the_suit_is_a_stock_hull_and_says_so_once(self):
        self.assertIsNone(SD.get_ship_data_for("lm_eva_suit"),
                          "the exosuit is a mod hull: absent until a mission declares it")
        self.assertEqual(E.eva_suit_hull(), "tsn_shuttle")
        self.assertEqual(E.eva_suit_hull(), "tsn_shuttle")
        said = [m for m in self.heard if "lm_eva_suit" in m]
        self.assertEqual(len(said), 1, self.heard)
        self.assertIn("EXTRA_SHIP_DATA", said[0])

    def test_the_exosuit_is_the_default_once_declared(self):
        self._declare_the_exosuit()
        self.assertEqual(E.eva_suit_hull(), "lm_eva_suit")
        self.assertEqual([m for m in self.heard if "suit hull" in m], [])

    def test_a_suit_is_spawned_as_the_exosuit(self):
        self._declare_the_exosuit()
        who = lifeform_spawn("Lt Okonkwo", "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, "hollow", *E.eva_entry("hollow"), side="tsn")
        self.assertEqual(suit.art_id, "lm_eva_suit")

    def test_a_suit_asked_for_in_a_hull_nobody_has_is_the_stock_one(self):
        who = lifeform_spawn("Lt Okonkwo", "terran_male", "boarding")
        suit = E.eva_suit_spawn(who, "hollow", *E.eva_entry("hollow"), side="tsn",
                                hull="no_such_hull")
        self.assertEqual(suit.art_id, "tsn_shuttle")
        self.assertEqual(len([m for m in self.heard if "no_such_hull" in m]), 1)

    def test_a_mission_can_still_name_its_own(self):
        E.eva_set_suit_hull("tsn_light_cruiser")
        self.assertEqual(E.eva_suit_hull(), "tsn_light_cruiser")


if __name__ == "__main__":
    unittest.main()
