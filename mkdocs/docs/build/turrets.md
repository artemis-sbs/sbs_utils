# Turrets

A turret is an object whose only job is to **acquire a target and shoot it, and never
move**. Two things fall out of one idea:

- a **deployable tower** - bought or earned as a kit, towed into position with the grav
  tether, and unfolded into an autonomous emplacement;
- an **autonomous mount** - the same object welded into a ship's or station's body frame,
  firing independently of where the pilot is looking.

They share all of their combat code and differ only in where position comes from.

## Placing one from a mission

```
prefab_spawn(prefab_lm_turret_tower, {"START_X": x, "START_Y": y, "START_Z": z, "side_value": "tsn"})
```

Three kinds ship: `prefab_lm_turret_tower` (beam), `_heavy` (longer reach, harder hitting,
slower), and `_drone` (launches attack drones). All carry `type: prefab/turret`, so a GM
menu enumerates them with no hardcoded list.

## Bolting turrets onto a ship or station

```
lm_turret_bolt_ring(ship_id, 4)
```

The **same call** for a station and a hard-maneuvering ship: offsets are body-frame and
the engine's tractor holds them there, so neither needs a per-tick reposition.

## The deploy ritual

A kit is a physical crate, not an inventory row, so deploying is a crew job:

1. **Buy or earn** `turret_kit_beam` / `_heavy` / `_drone`. A `price:` is all it takes to
   appear in the station Market - `market_purchasable()` collects every item that has one.
2. **Activate** it from Weapons or Engineering; a crate ejects ahead of the ship.
3. **Tow** it - Weapons hold-click gives *Grav Tow Kit*.
4. **Release** where you want it, then hold-click again for *Deploy Turret*.

## Balance

| lever | default | what it does |
|---|---|---|
| per-side cap | `LM_TURRET_CAP` = 8 | deploying past it is refused, server-side |
| lifetime | `LM_TURRET_LIFETIME` = 1200s | the tower powers down and is removed |
| magazine | `LM_TURRET_CHARGE` = 60 shots | charged **per shot**, then dormant until resupplied |

A mission overrides any of them with a shared of the same name. Upkeep is per *shot*
rather than per second because `//damage/object` carries the shooter in
`DAMAGE_ORIGIN_ID` - a timer would punish a turret nothing ever flew past.

## Adding a new tower kind

No code. Add a hull to `turrets/shipData_turrets.yaml`, a `type: prefab/turret` prefab,
and (if it should be buyable) an item whose `turret_prefab` names the prefab. The GM menu,
the market and the deploy route all discover it.

## Engine facts worth knowing

Measured on 1.3.5 by `LM_TestRange/maps/test_turret_probe.mast` and friends.

!!! warning "A turret must use a hull the mission ships itself"
    A `behav_station` fires **only** from a hull the mission declared to the engine.
    Stock starbase art produces a turret that never shoots.

    The turret hulls live in `media/turrets/extraShipData_turrets.yaml` and are
    registered with `ship_data_add_extra`, which points the engine and the library at
    the same file. They ride the **media pack** rather than the turrets mastlib
    because a mastlib is a zip and the engine cannot read inside one; a media pack is
    unpacked to disk once, so the engine can be handed a real folder.

    Do **not** use `ship_data_merge_mod` for this. It reaches the engine by generating
    `extraShipData.json`, which `get_ship_data()` then loads back on the next run
    while the addon declares the same entries again - 51 hulls became 102 from run 2.

!!! warning "Beam stats are fixed at the hull"
    `beamRange` / `beamCount` / `beamDamage` are not readable or writable on a live object
    - they live in the engine's ship table. A variant with different beams needs its own
    shipData entry, and its prefab's `range:` must be kept in step by hand.

!!! note "A drone tower is the one kind that is not a `behav_station`"
    `drone_launch_timer` launches drones only under `behav_npcship`; a `behav_station`
    launches nothing whatever its hull says. The drone tower therefore rides
    `behav_npcship` with throttle 0 and `target_pos` pinned to its spawn point (0.0u drift
    measured over 90s). Stock `starbase_torgoth` already carries a timer, so it needs no
    new art. Note also that a `//launch/drone` event reports the **drone** as `origin`;
    the launcher is `parent_id`.

!!! note "Turrets are targets"
    A turret carries `turret` and neither `ship` nor `station`, so `turret` is named
    explicitly in `ai_chase_npc`'s candidate set - that is what makes enemy NPCs engage
    one. Feral monsters still hunt players only. A fleet ordered against emplacements
    needs `test_roles: station,turret`.
