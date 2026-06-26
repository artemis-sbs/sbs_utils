"""Combat self-validation harness (//damage sub_float ledger).

Now that the mock reports each hit's amount on its //damage events (sub_float,
plus the weapon kind in sub_tag), the event STREAM can be reconciled against the
STATE it mutates: the total sub_float reported to a target must equal the damage
actually absorbed (shields drained + armor lost). This catches drift between what
apply_damage *does* and what it *reports* - exactly the bug that would silently
break a //damage mission counter while combat still "looked" right.

Per-hit amounts are also pinned to the calibrated engine bands recorded in
mkdocs/docs/api/engine/events.md (beam 5.5 NPC base, torpedo Homing 35, EMP 0
hull), so this doubles as a regression guard tying the event payload to the
capture reference.

These run headless in the unittest suite - no engine, no capture JSON needed
(the reference values live as the mock's calibrated constants).
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import Agent, clear_shared
from tests.reset_helper import reset_mock


def _drain_raw():
    out = []
    while True:
        try:
            out.append(sbs._pending_physics_events.get_nowait())
        except Exception:
            break
    return out


class TestDamageLedger(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)
        _drain_raw()

    def tearDown(self):
        sbs._beam_dmg_player = sbs._beam_dmg_npc = sbs._beam_dmg_station = None

    # --- helpers -----------------------------------------------------------
    def _station_target(self, armor=1000.0, shields=(0.0,), pos=(0, 0, 500)):
        """An armor (station) target with optional per-facing shields. Armor is a
        float, so shields_drained + armor_lost reconciles exactly with sub_float."""
        oid = self.sim.create_space_object("behav", "", 0x10)
        o = self.sim.space_objects[oid]
        o.data_set.set("armorMax", float(armor))
        o.data_set.set("armor", float(armor))
        o.data_set.set("shield_count", len(shields))
        for i, sv in enumerate(shields):
            o.data_set.set("shield_val", float(sv), i)
            o.data_set.set("shield_max_val", float(sv), i)
        o._pos = sbs.vec3(*pos)
        if Agent.get(oid) is None:
            ag = Agent(); ag.id = oid; ag.add()
        Agent.get(oid).add_role("station")
        return oid, o

    def _npc_beamer(self, target_id, per_shot=None, pos=(0, 0, 0)):
        """NPC firer aimed at target_id. With per_shot=None the beam coeff is 1.0 so
        each hit deals exactly the NPC base (_BEAM_DEFAULT_NPC); else beamDamage is
        scaled so each hit deals `per_shot`."""
        oid = self.sim.create_space_object("behav", "", 0x10)
        a = self.sim.space_objects[oid]
        a._pos = sbs.vec3(*pos)
        a.data_set.set("beamCount", 1)
        a.data_set.set("beamRange", 100000.0)
        a.data_set.set("beamCycleTime", 0.5)     # fire every dt=0.5 tick
        a.data_set.set("target_id", target_id)
        coeff = 1.0 if per_shot is None else per_shot / sbs._BEAM_DEFAULT_NPC
        a.data_set.set("beamDamage", coeff * sbs._BEAM_LOAD_BASE)
        return oid, a

    def _shield_total(self, o):
        n = int(o.data_set.get("shield_count") or 0)
        return sum((o.data_set.get("shield_val", i) or 0.0) for i in range(n))

    def _damage_amounts(self, events, target_id):
        """sub_float values from damage events landing on target_id."""
        return [ev[-1].get("sub_float")
                for ev in events
                if ev[0] == "damage" and ev[3] == target_id and isinstance(ev[-1], dict)]

    # --- the ledger invariant ---------------------------------------------
    def test_beam_sub_float_reconciles_with_damage_absorbed(self):
        # 6 beam volleys vs a shielded station: the reported sub_float must equal the
        # shields drained + armor lost. Per-shot is the calibrated NPC base.
        tid, t = self._station_target(armor=1000.0, shields=(10.0,))
        aid, a = self._npc_beamer(tid)            # coeff 1.0 -> 5.5 per shot
        sh0, ar0 = self._shield_total(t), t.data_set.get("armor")

        amounts = []
        for _ in range(12):           # beam re-arms every other tick (cycle 0.5, dt 0.5)
            sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
            amounts += self._damage_amounts(_drain_raw(), tid)

        self.assertEqual(len(amounts), 6, "12 ticks -> 6 hits (fires every other tick)")
        for amt in amounts:
            self.assertAlmostEqual(amt, sbs._BEAM_DEFAULT_NPC, delta=1e-6)  # capture band
        absorbed = (sh0 + ar0) - (self._shield_total(t) + t.data_set.get("armor"))
        self.assertAlmostEqual(sum(amounts), absorbed, delta=1e-6,
                               msg="reported sub_float must equal damage actually applied")

    def test_torpedo_homing_sub_float_reconciles(self):
        # A Homing torp's single hit reports the full warhead (35) and reconciles.
        tid, t = self._station_target(armor=1000.0, shields=(20.0,), pos=(100, 0, 0))
        sid, s = self._station_target(armor=1000.0, pos=(0, 0, 0))
        sh0, ar0 = self._shield_total(t), t.data_set.get("armor")
        _drain_raw()
        sbs.launch_missile(sid, tid, kind="Homing")
        sbs._physics_projectiles(self.sim, dt=0.5)         # straight-line impact
        amounts = self._damage_amounts(_drain_raw(), tid)
        self.assertEqual(amounts, [sbs._TORP_DAMAGE])
        absorbed = (sh0 + ar0) - (self._shield_total(t) + t.data_set.get("armor"))
        self.assertAlmostEqual(sum(amounts), absorbed, delta=1e-6)

    def test_emp_reports_zero_hull_but_halves_shields(self):
        # EMP is a shield/system pulse: it must report sub_float 0.0 (no hull) yet
        # halve each facing's shields and still fire //damage so routes run.
        tid, t = self._station_target(armor=1000.0, shields=(100.0, 80.0), pos=(100, 0, 0))
        sid, s = self._station_target(armor=1000.0, pos=(0, 0, 0))
        ar0 = t.data_set.get("armor")
        _drain_raw()
        sbs.launch_missile(sid, tid, kind="EMP")
        sbs._physics_projectiles(self.sim, dt=0.5)         # impact -> _apply_emp
        events = _drain_raw()
        amounts = self._damage_amounts(events, tid)
        self.assertTrue(amounts, "EMP should still emit a //damage event")
        self.assertTrue(all(a == 0.0 for a in amounts), "EMP reports no hull damage")
        # shields halved, hull untouched
        self.assertAlmostEqual(t.data_set.get("shield_val", 0), 50.0, delta=1e-6)
        self.assertAlmostEqual(t.data_set.get("shield_val", 1), 40.0, delta=1e-6)
        self.assertEqual(t.data_set.get("armor"), ar0)
        # the EMP event carries the weapon kind in sub_tag
        emp_evs = [ev for ev in events if ev[0] == "damage" and ev[3] == tid]
        self.assertTrue(all(ev[1] == "EMP" for ev in emp_evs))

    def test_weapon_kind_in_sub_tag(self):
        # Each weapon stamps its kind on sub_tag (the engine's //damage convention),
        # so a //damage/object route can branch on EVENT.sub_tag in the mock.
        tid, t = self._station_target(armor=1000.0)
        aid, a = self._npc_beamer(tid)
        _drain_raw()
        sbs._physics_beams(self.sim, [(aid, a), (tid, t)], dt=0.5)
        kinds = [ev[1] for ev in _drain_raw() if ev[0] == "damage" and ev[3] == tid]
        self.assertEqual(kinds, ["beam"])


if __name__ == '__main__':
    unittest.main()
