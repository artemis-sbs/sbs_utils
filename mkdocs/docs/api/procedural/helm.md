# Helm

Fly a **player** ship from script: throttle, direction steering, docking, shields, and the
engineering power/heat table.

Nothing in the library could do this before. [`target`](space_objects.md) and `target_pos`
write the **NPC** keys (`target_pos_x/y/z`, `throttle`), so every brain movement leaf is
unusable on a player ship and anything that wanted to fly one hand-rolled the `data_set`
writes — LegendaryMissions' autoplay did, and so did the headless quest pilot, in two
different styles.

Everything here is a real control write, the same one the crew's console makes. So the same
calls serve an attract bot and a conformance run; what differs is the policy above them.

!!! danger "An unset field is not a *no*"
    The engine returns `None` for a field nobody set, and the third argument of
    `data_set.get` is a **slot index**, not a default — so it does not save you. Coalescing
    that `None` to `0` is right for arithmetic and wrong for a *capability* question:
    "I have no information" silently becomes "you may never warp", for the whole mission,
    with no error, on a ship that flies perfectly well.

    `helm_warp_available` therefore refuses only on **positive** evidence of no drive — the
    flag says 0 **and** the hull costs nothing to warp — and the energy reserve is consulted
    only when the energy field actually says something. This shipped the wrong way round
    once and the symptom was simply that a bot never warped, with nothing anywhere to read.

!!! warning "Warp is gated, reverse is `-1`, and undock needs two writes"
    Three engine details from [`ENGINE_WIDGETS.md`](https://github.com/artemis-sbs/sbs_utils)
    that are easy to get subtly wrong:

    * **Warp is only available when `data_set warp == 1.0`.** A hull without a drive ignores
      a warp throttle — it just flies at impulse — so a bot that never checks believes it is
      travelling three times faster than it is. `helm_throttle` returns what it *actually*
      set, so the caller can tell.
    * **`playerThrottle` of `-1` is reverse.** The engine's own bar tops out at 5.
    * **Undocking must clear `dock_base_id`, not just `dock_state`.** The engine holds a
      docked ship with a *tractor*, so rewriting only the state leaves it attached to a base
      it believes it has left.

## Energy: waiting gets you to 200, docking gets you home

The engine's energy numbers are in `data/preferences.json`:

| key | value | meaning |
|---|---|---|
| `player-fuel-use-coeff` | 0.12 | drain, times the ship's speed |
| `player-base-energy-use-coeff` | 0.007 | drain, times the power on every engineering slider — a stopped ship still draws |
| `player-shields-raised-energy-coeff` | 2.0 | drain multiplier while shields are up |
| `energyCostOfOneBeamShot` | 1.0 | per beam shot |
| `ship_apu_assistance_per_tick` | 0.1 | APU refill, 3/s at 30 ticks |
| `ship_apu_assistance_ceiling` | 200 | **the APU stops here** |
| `player-no_energy-speed-coeff` | 0.1 | an empty ship still flies, at 10% |

`helm_apu_ceiling(ship)` returns that ceiling (the ship's `ship_apu_ceiling` when it carries
one). **Anything that parks a ship "until energy recovers" must aim below it**, or it waits
forever. Only docking refills the tank.

`helm_throttle` still refuses warp below `DEFAULT_ENERGY_RESERVE` (400), so a ship keeps
enough in hand to reach a station. That is a spending gate, not a recovery target.
`helm_energy_reserve(ship, target)` estimates whether a trip is affordable at a given
throttle. Because an empty ship still moves, "unaffordable" means "slow", not "impossible".

!!! danger "This page used to say energy has a floor"
    It claimed a stopped ship always recovers, because the mock's APU refilled to 1000. LM's
    brain autoplayer believed it: it parked ships below 400 to wait for 400, and in the
    engine every ship that ran low away from a station sat still for the rest of the run.
    The mock now uses the engine's ceiling and rate.

## The engineering table is many-to-one

`helm_eng_controls` walks `eng_control_label` once. That walk was previously written out by
hand in three places — autoplay's can-turn check, autoplay's power loop, and
`set_engineering_value`.

**`eng_control_type_index` is the ship system a control feeds, and several controls share
one.** On a `tsn_light_cruiser` the engine reports eight controls onto four systems:

| control | system |
|---|---|
| `BEAM`, `TORP` | 0 |
| `IMPULSE`, `WARP`, `MANEUVER` | 1 |
| `SENSORS` | 2 |
| `FRONT SHIELD`, `REAR SHIELD` | 3 |

So `helm_set_power` sets **every** matching control, where `set_engineering_value` stops at
the first — which on this hull means it sets FRONT SHIELD and silently leaves REAR alone.
Labels are the engine's display text in upper case, so matching folds case.

!!! note "`helm_can_turn` consults two things on purpose"
    A wrecked maneuver system stops a ship turning *before* `turn_damage_coeff` bottoms out,
    so the check is the coefficient **and** the maneuver system's damage. A ship that cannot
    turn must not burn straight ahead: that only commits it further, and a straight-line
    chase after a target it cannot aim at ends in deep space.

## API

::: sbs_utils.procedural.helm
