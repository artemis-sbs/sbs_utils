"""Combat time-to-kill (TTK) regression guard.

Locks the calibrated combat model (beam / shield / hull / steering) to the engine
ballpark so it can't silently drift. Exact engine TTK is NOT reproducible - the
engine maneuvers (beams miss), while the mock is a stationary face-off, so mock
fights run a bit faster. The engine reference (data_capture battle matrix, recorded
in mkdocs api/engine/events.md) is: cruiser duels resolve in ~40-70s, players win a
1v1 in ~37-44s, stations survive a lone attacker for 2 min.

These tests therefore assert WIDE bands: a duel must resolve (someone dies) within a
sane window - not instantly (combat values inflated) and not never (over-tanky) -
and a starbase must tank a single attacker. A change that breaks the beam/shield/
hull calibration will push TTK out of band and trip the guard.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.space_objects import target
from sbs_utils.procedural.sides import side_set_relations

# Sane resolve window (sim seconds) for a ship-vs-ship duel. The mock runs ~35-45s;
# the engine reference is ~40-70s. Below MIN => combat far too deadly; above MAX =>
# far too tanky / fights not resolving.
_TTK_MIN = 15.0
_TTK_MAX = 110.0


class TestCombatTTK(unittest.TestCase):
    def setUp(self):
        Agent.clear()
        clear_shared()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.sim = sbs.sim

    def _fight(self, a_hull, b_hull, a_station=False, secs=130.0):
        """Spawn A (tsn) vs B (raider) 800 apart, both shooting; tick physics until
        one dies. Returns (ttk_seconds_or_None, dead_side 'A'/'B'/None)."""
        side_set_relations("tsn", "raider", sbs.DIPLOMACY.HOSTILE)
        a_side = "tsn, station" if a_station else "tsn"
        a_behav = "behav_station" if a_station else "behav_npcship"
        a = npc_spawn(0, 0, 0, "A", a_side, a_hull, a_behav)
        b = npc_spawn(0, 0, 800, "B", "raider", b_hull, "behav_npcship")
        aid, bid = to_id(a), to_id(b)
        target(aid, bid, True, 0.0, stop_dist=700)
        target(bid, aid, True, 0.0, stop_dist=700)
        sbs.resume_sim()
        for k in range(int(secs / 0.5)):
            sbs.physics_tick(dt=0.5)
            if aid not in self.sim.space_objects:
                return (k + 1) * 0.5, "A"
            if bid not in self.sim.space_objects:
                return (k + 1) * 0.5, "B"
        return None, None

    def test_cruiser_duel_resolves_in_band(self):
        ttk, _ = self._fight("tsn_battle_cruiser", "kralien_dreadnought")
        self.assertIsNotNone(ttk, "cruiser duel should resolve, not stalemate")
        self.assertGreater(ttk, _TTK_MIN, "duel resolved too fast - combat values inflated?")
        self.assertLess(ttk, _TTK_MAX, "duel too slow - shields/hull over-tanky?")

    def test_light_vs_elite_resolves_in_band(self):
        ttk, _ = self._fight("tsn_light_cruiser", "skaraan_defiler")
        self.assertIsNotNone(ttk, "duel should resolve")
        self.assertGreater(ttk, _TTK_MIN)
        self.assertLess(ttk, _TTK_MAX)

    def test_station_far_tankier_than_a_cruiser(self):
        # A starbase should take much longer to kill than a cruiser duel takes to
        # resolve - stations are tanky. Asserted relative to a cruiser duel so it's
        # robust to absolute tuning. (The mock's stationary perfect-aim slugfest does
        # eventually crack a starbase ~2 min; the engine's maneuvering lets it survive
        # outright - either way it far outlasts a ship.)
        duel, _ = self._fight("tsn_battle_cruiser", "kralien_dreadnought")
        stn, _ = self._fight("starbase_command", "skaraan_executor", a_station=True, secs=130.0)
        self.assertIsNotNone(duel, "cruiser duel should resolve")
        stn_life = stn if stn is not None else 130.0
        self.assertGreater(stn_life, 2.0 * duel,
                           "a starbase should be far tankier than a cruiser")


if __name__ == '__main__':
    unittest.main()
