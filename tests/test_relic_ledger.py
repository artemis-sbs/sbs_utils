"""A ruin REMEMBERS what was done in it: between visits, and across a saved game.

`relic_release` forgets what is standing in a ruin, because a galaxy tears the system down
behind the crew. It used to forget what had HAPPENED there as well, so the ruin was rebuilt
from its file on the way back: every barrier shut, every repair undone, the piece the crew
carried out sitting where it had always been.

The ledger is what happened - opened barriers, done repairs, taken pieces, contents whose
trigger has fired - keyed by the author's own names. What this file pins:

* leave and come back the SAME EVENING (release, build again): the hatch is open and has
  no body, the job is done, the piece is not there;
* stop and CONTINUE (the state provider's snapshot, a mission reset, a restore, build):
  the same;
* restored state is not news: `<barrier>_opened`, `<relic>_taken` and `<key>_repaired`
  are not sent a second time, by the rebuild or by anything the crew does next;
* a mission that never saves and a ruin nobody touched are built exactly as before;
* nothing is left on the reset ledger.

Everything is read from real `.amd` text through `relics_load` and built by `relic_spawn`.

    python -m unittest tests.test_relic_ledger
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.handlerhooks import reset_mission_audit, reset_mission_state
from sbs_utils.procedural import amd_relics as R
from sbs_utils.procedural import persistence as P
from sbs_utils.procedural import rails as RL
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.signal import signal_emit, signal_observe, signal_unobserve
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.vec import Vec3

RUINS = """# [Mission](mission)

## [Relics](relics)

### [The Hollow](hollow)
---
Loc: 0, 0, 20000
Walls: none
Debris: 0
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

### [the niche](hollow_niche)
---
Relic: hollow
Point: 3300, 0, 300
Item: salvage
Starts when: signal niche_found
---

### [The Seized Hatch](nave_hatch)
---
Relic: hollow
Barrier: 1500, 0, 0, 400
Clear with: beam
---

### [The Inner Seal](inner_seal)
---
Relic: hollow
Barrier: 3000, 0, 600, 200
Opens when: signal seal_released
---

### [The Coolant Coupling](coupling)
---
Relic: hollow
Repair: 200, 0, 0, 120
---

### [The Cyst](cyst)
---
Loc: 60000, 0, 0
Walls: none
Debris: 0
---
A second ruin, far off, that nobody goes into.

### [The Sac](sac)
---
Relic: cyst
Chamber: 0, 0, 0, 800
---

### [The Membrane](membrane)
---
Relic: cyst
Barrier: 0, 0, 0, 200
---
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        sbs.resume_sim()
        DeleteQueue.clear()
        self.addCleanup(reset_mission_state)
        self.quest = []
        signal_observe(self._watch)
        self.addCleanup(signal_unobserve, self._watch)
        self.load()
        self.build()

    def _watch(self, name, data=None):
        if name == "quest_signal":
            self.quest.append((data or {}).get("SIGNAL_NAME"))

    def load(self):
        R.relics_load("ruins.amd", content=RUINS)

    def build(self, *keys):
        for key in keys or ("hollow", "cyst"):
            self.assertIsNotNone(
                R.relic_spawn(key, atmosphere=False, marker=False), key)

    def tick(self, seconds=2):
        for _ in range(int(seconds * 30)):
            sbs.physics_tick(1 / 30)
            TickDispatcher.dispatch_tick()

    def leave(self, key="hollow"):
        """What a galaxy does as the crew jumps away: let the ruin go, then delete what
        was standing in it."""
        ids = [rec.get("id") for k, rec in list(R._ARMED.items())
               if len(k) == 3 and k[1] == key and rec.get("id") is not None]
        R.relic_release(key)
        for oid in ids:
            if to_object(oid) is not None:
                delete_object(oid)
        DeleteQueue.clear()

    def play_the_ruin(self):
        """The evening: cut the hatch, release the seal, do the job, find the niche,
        carry the piece out."""
        self.assertTrue(R.relic_open_barrier("hollow", "nave_hatch"))
        signal_emit("seal_released")
        signal_emit("niche_found")
        self.tick()
        self.assertTrue(R.relic_repair_done("hollow", "coupling"))
        piece = to_object(R.relic_pieces("hollow")[0])
        piece.pos = Vec3(-30000, 0, -30000)
        self.tick()
        self.assertEqual(sorted(self.quest), ["coupling_repaired", "hollow_taken",
                                              "inner_seal_opened", "nave_hatch_opened"])

    def shut(self, key="hollow"):
        return sorted(k for k, _b in RL.rail_barriers(key, shut_only=True))

    def assert_as_it_was_left(self):
        self.assertEqual(self.shut(), [], "both barriers stay open")
        bodies = [k for k in R._ARMED if k[0] == "barrier_obj" and k[1] == "hollow"]
        self.assertEqual(bodies, [], "an open barrier has no body to shoot")
        self.assertTrue(R.relic_repair_fixed("hollow", "coupling"))
        self.assertEqual(R.relic_repair_jobs("hollow", open_only=True), [])
        self.assertEqual(R.relic_pieces("hollow"), [], "the piece is not put back")
        self.assertEqual(R.relic_contents_state("hollow", "hollow_niche"), "placed",
                         "a trigger that fired stays fired")


class NothingHappened(_Base):
    def test_an_untouched_ruin_is_built_from_its_file(self):
        self.assertEqual(self.shut(), ["inner_seal", "nave_hatch"])
        self.assertEqual(len(R.relic_pieces("hollow")), 1)
        self.assertFalse(R.relic_repair_fixed("hollow", "coupling"))
        self.assertEqual(R.relic_contents_state("hollow", "hollow_niche"), "waiting")
        self.assertEqual(R.relic_ledger(), {})
        self.assertEqual(R.relic_ledger_count(), 0)

    def test_leaving_and_returning_changes_nothing_either(self):
        self.leave()
        self.build("hollow")
        self.assertEqual(self.shut(), ["inner_seal", "nave_hatch"])
        self.assertEqual(len(R.relic_pieces("hollow")), 1)
        self.assertEqual(self.quest, [], "tearing a ruin down is not news")
        self.assertEqual(P.persist_providers_snapshot(), {})


class TheSameEvening(_Base):
    def test_the_ledger_says_what_happened(self):
        self.play_the_ruin()
        self.assertEqual(R.relic_ledger("hollow"), {
            "opened": ["inner_seal", "nave_hatch"], "repaired": ["coupling"],
            "taken": ["hollow_cradle"], "placed": ["hollow_niche"]})
        self.assertEqual(R.relic_ledger("cyst"), {})

    def test_leave_and_come_back_and_it_is_as_it_was_left(self):
        self.play_the_ruin()
        self.leave()
        self.assertEqual(R.relic_ledger("hollow")["taken"], ["hollow_cradle"],
                         "the ledger outlives the ruin being let go")
        self.build("hollow")
        self.assert_as_it_was_left()

    def test_coming_back_sends_no_quest_signal(self):
        self.play_the_ruin()
        sent = list(self.quest)
        self.leave()
        self.build("hollow")
        self.tick()
        self.assertEqual(self.quest, sent)

    def test_the_other_ruin_is_not_touched(self):
        self.play_the_ruin()
        self.leave()
        self.build("hollow")
        self.assertEqual(self.shut("cyst"), ["membrane"])

    def test_a_ruin_can_be_made_to_forget(self):
        self.play_the_ruin()
        self.leave()
        R.relic_ledger_forget("hollow")
        self.build("hollow")
        self.assertEqual(self.shut(), ["inner_seal", "nave_hatch"])
        self.assertEqual(len(R.relic_pieces("hollow")), 1)


class Continue(_Base):
    def stop_and_continue(self):
        """The file a mission would write; a new process as far as the library can tell;
        the file handed back BEFORE the ruin is built."""
        saved = P.persist_providers_snapshot()
        signal_unobserve(self._watch)
        reset_mock(sbs)
        sbs.resume_sim()
        DeleteQueue.clear()
        self.quest.clear()
        signal_observe(self._watch)
        self.assertEqual(R.relic_ledger(), {}, "a reset forgets")
        P.persist_providers_restore(saved)
        self.load()
        return saved

    def test_what_is_written_down(self):
        self.play_the_ruin()
        saved = P.persist_providers_snapshot()
        self.assertEqual(saved["relics"], {
            "ruins": {"hollow": {"opened": ["inner_seal", "nave_hatch"],
                                 "repaired": ["coupling"], "taken": ["hollow_cradle"],
                                 "placed": ["hollow_niche"]}},
            "sent": ["coupling_repaired", "hollow_taken", "inner_seal_opened",
                     "nave_hatch_opened"]})

    def test_a_change_asks_to_be_saved(self):
        self.assertFalse(P.persist_providers_dirty())
        R.relic_open_barrier("hollow", "nave_hatch")
        self.assertTrue(P.persist_providers_dirty())

    def test_the_restore_is_lazy_and_the_ruin_reads_it_when_it_is_built(self):
        self.play_the_ruin()
        self.stop_and_continue()
        self.assertEqual(len(role("relic_barrier")), 0, "nothing is built by a restore")
        self.build()
        self.assert_as_it_was_left()
        self.assertEqual(self.shut("cyst"), ["membrane"])

    def test_restored_state_is_not_news(self):
        self.play_the_ruin()
        self.stop_and_continue()
        self.build()
        self.tick()
        self.assertEqual(self.quest, [], "nothing is sent by a ruin coming back")
        # ...and nothing the crew can still do sends an old one again.
        self.assertFalse(R.relic_open_barrier("hollow", "nave_hatch"))
        self.assertFalse(R.relic_repair_done("hollow", "coupling"))
        self.assertFalse(R.relic_quest_signal("hollow_taken"))
        signal_emit("seal_released")
        signal_emit("niche_found")
        self.tick()
        self.assertEqual(self.quest, [])

    def test_a_second_save_is_the_same_save(self):
        self.play_the_ruin()
        saved = self.stop_and_continue()
        self.build()
        self.assertEqual(P.persist_providers_snapshot(), saved)

    def test_a_ruin_not_visited_tonight_keeps_what_it_remembered(self):
        """Continue, never fly to the ruin, save: the ledger is still in the file."""
        self.play_the_ruin()
        saved = self.stop_and_continue()
        self.assertEqual(P.persist_providers_snapshot(), saved)

    def test_a_new_game_starts_every_ruin_from_its_file(self):
        self.play_the_ruin()
        self.leave()
        P.persist_providers_restore({})
        self.build("hollow")
        self.assertEqual(self.shut(), ["inner_seal", "nave_hatch"])
        self.assertEqual(len(R.relic_pieces("hollow")), 1)

    def test_nothing_is_left_on_the_reset_ledger(self):
        self.play_the_ruin()
        self.assertGreater(R.relic_ledger_count(), 0)
        reset_mission_state()
        self.assertEqual(R.relic_ledger_count(), 0)
        left = {k: v for k, v in reset_mission_audit().items() if not k.startswith("mock.")}
        self.assertEqual(left, {})


if __name__ == "__main__":
    unittest.main()
