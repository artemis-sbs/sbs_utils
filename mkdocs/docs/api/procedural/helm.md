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

## Energy has a floor, and that is the useful part

The tank drains **only while the throttle is up** —
`min(thr,1) * ship_energy_cost + max(0, thr-1) * warp_energy_cost`, warp weighted about
double — and the auxiliary power unit trickles it back **unconditionally** whenever energy
is below `ship_apu_ceiling`. Docking refills it fast on top of that.

> **There is no unrecoverable energy state. A ship that strands is a ship that never stopped
> burning.**

That is why `helm_throttle` consults a reserve before allowing warp, and why
`helm_energy_reserve` exists at all. Three rules follow, and together they make stranding
impossible rather than unlikely:

1. **Never enter warp without the reserve to reach help.** Warp is the only thing that
   outruns the APU.
2. **Below the reserve, drop to impulse or stop.** The APU then refills with certainty.
3. **Dock when a station is in reach**, because it is faster than waiting.

`helm_energy_reserve(ship, target)` asks the question a flat threshold cannot: *can I afford
to get there and still have something left?* "Dock below 300 energy" says nothing about
whether the station is 2,000 units away or 40,000.

This is what let LegendaryMissions' autoplay delete its energy **refill cheat** rather than
keep hiding real energy bugs behind it. A cheat put there so an unattended run would not
stall also guarantees the run can never find an energy bug.

!!! tip "Prove it, because a plain run does not"
    Neither the old nor the new autoplayer dropped below ~730 energy in 300 sim-seconds on
    siege — the cheat never fired, so the run proved nothing either way. Draining the tank
    to 20 (below the old threshold) and watching it climb back to 596 unaided is the test
    that means something.

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
