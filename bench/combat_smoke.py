"""
Combat smoke test for the mock physics weapon model.

LegendaryMissions games run 30-45 minutes, so they're a poor harness for a
seconds-long combat check. This sets up a small synthetic battle directly
against the working-tree mock and drives physics_tick() (the real integrated
path: beams + launchers + projectiles + heat) until it resolves, then reports
and asserts that combat actually happened (damage dealt + ships killed).

Run from the sbs_utils repo root:
    python -m bench.combat_smoke
    python bench/combat_smoke.py
Exit code 0 = combat resolved (kills occurred); 1 = nothing died (regression).

Dev-only; bench/ is tracked but never packaged.
"""
from __future__ import annotations

import os
import sys

# Force working-tree precedence (see project_smoke_run_sbslib_shadow).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
elif sys.path[0] != _REPO_ROOT:
    sys.path.remove(_REPO_ROOT)
    sys.path.insert(0, _REPO_ROOT)

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from cosmos_dev.mock import sbs


def _drain():
    out = []
    while True:
        try:
            out.append(sbs._pending_physics_events.get_nowait())
        except Exception:
            break
    return out


def _ship(sim, x, hull=120.0, torps=False, heat_seek=False):
    """A stationary combat ship: hull + beams, optionally a torpedo tube."""
    oid = sim.create_space_object("combat_dummy", "", 0x10)  # no behavior -> stays put
    o = sim.space_objects[oid]
    o._pos = sbs.vec3(float(x), 0.0, 0.0)
    o._exclusion_radius = 0.0           # don't collide; we're testing weapons
    ds = o.data_set
    ds.set("armorMax", hull)
    ds.set("armor", hull)
    ds.set("beamCount", 1)
    ds.set("beamRange", 4000.0)
    ds.set("beamDamage", 12.0)
    ds.set("beamCycleTime", 3.0)
    if torps:
        ds.set("torpedo_tube_count", 1)
        ds.set("torpedo_launch_max_range", 6000.0)
        if heat_seek:
            ds.set("torpedo_heat_seek", 1)
    return oid, o


def main():
    import argparse
    ap = argparse.ArgumentParser(description="mock combat smoke")
    ap.add_argument("--per-side", type=int, default=3, help="ships per side")
    ap.add_argument("--ticks", type=int, default=400, help="max physics ticks")
    ap.add_argument("--dt", type=float, default=0.5, help="seconds per tick")
    args = ap.parse_args()

    import cosmos_dev.mock.sbs as _m
    print(f"sbs loaded from: {_m.__file__}")
    if ".sbslib" in _m.__file__:
        print("  !! PACKAGED sbslib, not the working tree !!")

    sbs.create_new_sim()
    sim = sbs.sim
    sbs.resume_sim()

    # Two facing lines ~1000 apart (within beamRange). One torpedo boat per side,
    # the red one heat-seeking.
    reds, blues = [], []
    for i in range(args.per_side):
        reds.append(_ship(sim, -500 - i * 50, torps=(i == 0), heat_seek=True))
        blues.append(_ship(sim,  500 + i * 50, torps=(i == 0)))

    # Each ship targets the opposite-index enemy (weapon_target_UID).
    for i in range(args.per_side):
        reds[i][1].data_set.set("weapon_target_UID", blues[i][0])
        blues[i][1].data_set.set("weapon_target_UID", reds[i][0])

    red_ids = {oid for oid, _ in reds}
    blue_ids = {oid for oid, _ in blues}

    n_damage = n_missile = n_drone = n_killed = 0
    first_kill_tick = None
    _drain()

    for t in range(args.ticks):
        sbs.physics_tick(dt=args.dt)
        for ev in _drain():
            tag = ev[0]
            if tag == "damage":
                n_damage += 1
            elif tag == "player_launches_missile":
                n_missile += 1
            elif tag == "ship_launches_drone":
                n_drone += 1
            elif tag in ("npc_killed", "station_killed"):
                n_killed += 1
                if first_kill_tick is None:
                    first_kill_tick = t
        reds_alive = sum(1 for oid in red_ids if oid in sim.space_objects)
        blues_alive = sum(1 for oid in blue_ids if oid in sim.space_objects)
        if reds_alive == 0 or blues_alive == 0:
            break

    reds_alive = sum(1 for oid in red_ids if oid in sim.space_objects)
    blues_alive = sum(1 for oid in blue_ids if oid in sim.space_objects)

    print(f"scale: {args.per_side} per side, dt={args.dt}")
    print(f"damage events:   {n_damage}")
    print(f"missiles fired:  {n_missile}")
    print(f"drones fired:    {n_drone}")
    print(f"ships killed:    {n_killed}  (first at tick {first_kill_tick})")
    print(f"survivors:       red={reds_alive} blue={blues_alive}")

    if n_damage > 0 and n_killed > 0:
        print("RESULT: OK - combat resolves (damage dealt and ships destroyed)")
        return 0
    print("RESULT: FAIL - combat did not resolve")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
