# Grav-tether

A tractor beam: **lock / tow / reel** a load, or **swing** a fighter around an anchor.
Thin wrappers over the engine-native tractor (`sim.AddTractorConnection`) plus the
mission-facing behavior the raw API doesn't provide — mode presets, a reel ramp, the
canonical **impulse-only** enforcement (cap / snap), and a moving circle-point swing.

Key facts (engine-confirmed): a static tether reels the target fully in, so holding a
load *at* a distance uses a per-tick rope-toggle; a player hull can be tractor-pulled.
Pair with [`closest_in_front`](space_objects.md) for nose-aim acquisition (the engine has
no raycast).

!!! warning "Ask `grav_tether_has`, not `grav_tether_get`, for *is this tethered?*"
    `grav_tether_get` returns the live **engine connection**, and a Tow is a rope-toggle:
    it deletes that connection whenever the load is inside the rope length and re-adds it
    when the load drifts out. So `get` reads `None` for most of a perfectly good tow. A
    menu gated on it offers *Tow* to something already under tow and never offers
    *Release* — which is exactly what the shipped Weapons hold-click did. Use `get` only
    when you want the connection object itself (to read `.offset`).

!!! note "The offset point is not world-fixed - this module just never passes one"
    Older notes here said the tractor's offset point is world-fixed. It is measurably
    **source-relative**: `AddTractorConnection(host, target, vec3(0,0,200), 0)` held a
    target at exactly 200u and exactly 0 deg off the host's nose while the host's heading
    swung 51 deg. A load tethered *here* always reels to the source's own position because
    this module passes **no** offset - which is what a tow wants. To bolt something ON to
    a hull instead of dragging it behind one, use [mount](mount.md).

!!! warning "Reach is opt-in, and so is the snap"
    `grav_tether_set_range_limit(distance)` sets how far a beam can reach to open; without
    one there is no limit, which is what the library shipped with and what a mission that
    says nothing still gets. An attach out of range is refused and emits
    `grav_tether_out_of_reach`.

    A live tether also **snaps** past `SNAP_RANGE_FACTOR` (1.5) times its hold distance,
    emitting `grav_tether_snapped`. The hold distance is the longer of the beam's rope and
    the engage range - **not the rope alone**, which is the tempting reading and is wrong:
    a rope-toggle tow is *supposed* to sit beyond its rope, since that is the state in
    which the pull engages, so a 500u tow reeling a load in from 2000 would snap itself on
    the first tick.

!!! danger "A rigid lock across a gap is a teleport"
    Rigid means stiffness **0**, and stiffness 0 has **no rate limit** - the engine puts
    the load on the source point the same tick the connection is made. Close up, which is
    the case `grav_tether_lock` was written for (a hangar recovery), that is exactly
    right. At range it is a teleport, and once `grav_tether_set_range_limit` made a lock
    from thousands of units away legal it became reachable from the shipped Weapons
    hold-click.

    It reads worst in the case the mass rule flips. Grav-lock a **starbase** and the
    station is the puller, so the end snapped across the gap is the **player** - reported
    from a bridge as "grav-lock a station from 7000u and you are instantly beside it".
    Measured: 7000u closed to 120u in a single 0.1s tick.

    So a lock opened beyond `LOCK_GRAB_DISTANCE` (100u) engages at `LOCK_WINCH_STIFFNESS`
    instead - a lagged, rate-limited pull - and hardens to rigid only once the load is
    genuinely in reach, emitting **`grav_tether_locked`**. Same end state, arrived at
    rather than jumped to. `grav_tether_set_lock_grab_distance(d)` retunes it.

    The rule reads the **live separation**, not a ramped rope length: `pull_distance` is
    not honored as a rest length, so a countdown would be a timer pretending to be a
    measurement.

!!! tip "You can drag a starbase. It has to cost you."
    A **Lock** and a **Reel** mass-reverse; a **Tow** deliberately does not. Grabbing a
    station rigidly means going where the station goes; hauling one means straining
    against it. Two different verbs, and a crew that picked *Tow* asked to be the one
    pulling - so a tow never flips, however outmatched, and pays for it instead.

    It used to pay in one place only. `_enforce_drag` and `_spend_tow_energy` billed the
    **tug**, while `_tick_rope` set a flat `con.offset`, so a 200-mass starbase reeled to
    the rope at exactly the rate of a 1-mass fighter. The load was free; only the ship
    holding it felt anything. Three changes, each on an axis a crew can act on:

    **The beam pulls slower under weight.** `_tow_lag` divides the offset dial by
    `grav_tether_load_ratio(source, target) ** TOW_LAG_CURVE` - a **square root** - with a
    floor at `TOW_LAG_MIN_SCALE` (an eighth).

    !!! danger "`.offset` is a SPEED, and it was documented backwards"
        Engine-measured on a controlled sweep (`LM_TestRange` map
        `test_tractor_calibrate`: one source, identical targets at 30000u, raw
        `AddTractorConnection`, offsets 1-80 read at 10s and 20s): the target closes at
        **`offset x 30.2` units per second**, linear in offset *and* linear in time. 20s
        closes exactly twice what 10s closes at every value, so it is constant velocity -
        not the first-order lag both this page and the mock assumed. 30.2 against a
        30-tick second means the engine is almost certainly moving the target `offset`
        units per tick.

        So **higher offset pulls FASTER.** The engine API calls the field "stiffness" and
        the notes here called higher values "looser and laggier"; that was never measured
        and is the reverse of the truth. The first version of this feature therefore
        *multiplied* the dial for heavy loads and reeled a starbase in **four times faster
        than a fighter** - the exact opposite of its stated intent. Measured before and
        after on a real bridge, a light cruiser hauling a science station: **240 u/s
        before, 26 u/s after.**

        It was invisible because the mock modelled the pull as `tau = offset x 1.2`,
        fitted qualitatively to a single point. A kinder-than-the-engine mock does not
        merely miss bugs; here it confidently reported the inverse of the truth and every
        test agreed with it.

    Pull speeds at the base stiffness of 5: **151 u/s** evenly matched, ~75 u/s on a
    freighter, ~26 u/s for a lone cruiser on a science station - which four cruisers lift
    back to ~52.

    A square root because linear would put a 66:1 starbase grab at a fifteenth of base
    speed, slow enough that the power bill cuts the beam before the load has gone
    anywhere, so "you can drag a starbase" stops being true. The floor has to be strictly
    **above zero**: offset 0 is the rigid case, which puts the load on the source point in
    a single tick, so a mass table holding 100000 for a planet would otherwise divide the
    gentlest possible tow into a teleport.

    A ratio of 1 or less returns the nominal offset untouched, and the whole thing
    short-circuits when no mass provider is installed, so every existing tow - and every
    mission with no mass table - is unchanged. It applies to `MODE_TOW` only: a swing's
    anchor is a rock, and a lock on something heavy is *reversed*.

    **A second hull is worth bringing.** `grav_tether_pull_mass(target)` is the combined
    mass of everyone **hauling** it - `grav_tether_pullers_of` excludes a swing's anchor
    and a reversed tether's registered source, neither of which is pulling anything, and
    counting either would make the haul look lighter than it is.
    `grav_tether_load_ratio(source, target)` is what the load is measured against. Pull
    speed and drag both read it, and the **energy bill is shared** - each puller pays in
    proportion to its own mass. Billing every ship the full amount, which
    is what it did, means four hulls each drain at the solo rate and all cut out at the
    same moment: four times the fleet's power for not one extra second of haul.

    **And it says so.** `grav_tether_strain(target)` returns `none` / `light` / `heavy` /
    `overloaded`, and crossing a band emits **`grav_tether_strain`**
    (`SOURCE_ID, TARGET_ID, STRAIN, RATIO, PULLERS`). Edge-triggered - the tether tick
    runs several times a sim-second and a signal at that rate is a flood, not feedback.
    `grav_tether_status` carries `strain` and `pullers` for a readout. The band, not the
    ratio, is the published number precisely because a console keyed on a per-tick value
    repaints itself to pieces.

    The bands sit where the mechanics change, not on round numbers: `light` ends where
    drag stops growing (past there extra mass costs no extra drive - only lag and power),
    and `overloaded` is where the beam's sluggishness rather than the drive penalty is
    what is beating the crew.

    **A ship can be better at hauling than its hull says.**
    `grav_tether_set_pull_bonus_fn(fn)` installs `fn(id) -> multiplier` on what a ship
    counts for **when pulling**. Deliberately *not* folded into the mass provider even
    though the arithmetic is identical: mass also decides whether a Grav Lock reverses onto
    you, what you cost somebody else to tow, and - for a mission pricing salvage by mass -
    what your own wreck pays. Better towing gear that quietly raised the price of your hulk
    would be a bug nobody would trace back to the rig.

    LM ships two tiers of it. The **Heavy Tug Rig** is 4x, permanent, and bought at a
    station; the **Tug Rig Mk I** is 2.5x for ten minutes and is found in the world. They
    **stack**, and that is a fix rather than generosity: an item is decremented before its
    effect runs, so under a best-one-wins rule a crew that already owns the permanent rig
    would destroy any Mk I they activated for no benefit at all, with nothing able to
    refuse the press in time.

    Two numbers worth the explanation. 4x means a rigged hull reads the same as a
    four-ship team on every figure the beam computes - though **not** on endurance, since
    the power bill is split between the ships actually on the beam and one rigged hull pays
    all of it. And the Mk I is 2.5x rather than the obvious 2x because tow drag saturates
    at a ratio of `DRAG_FLOOR / DRAG_AT_EQUAL_MASS` = 2.14: on the standard haul, a mass-3
    cruiser dragging a mass-16 liner, a 2x rig only moves the ratio from 5.33 to 2.67 and
    the drag penalty does not shift at all. 2.5x lands at 2.13, just under the floor, so
    the penalty eases and the strain word drops a band.

!!! note "Tow drag is what *hauling* costs - a reversed tether pays none of it"
    `_enforce_drag` drops the puller's `impulse_upgrade_coeff` and `turn_upgrade_coeff` by
    the mass ratio. On a **mass-reversed** tether the caller is not hauling anything: they
    are the load, and the engine is already moving their hull. Charging them anyway
    stacked this module's two heaviest penalties on the one ship that had earned neither -
    capped to impulse by `_enforce_impulse` **and** cut to the `DRAG_FLOOR` (a starbase is
    20-60x a cruiser, which pins the amount at its 0.75 ceiling). That is what "the
    engines stopped working while tethered" was. A swing is exempt for the mirror reason.

    **Warp is still refused, and always intentionally**: impulse-only is canonical, so
    `_enforce_impulse` clamps `playerThrottle` back to 1.0 every tick while a tether is
    live. `grav_tether_set_overspeed_default("snap")` breaks the beam instead;
    `("off")` drops the rule.

!!! danger "An anchor is never a load"
    `ANCHOR_ROLES` (`black_hole,planet,nebula` by default) names the bodies that may only
    ever be the **source** end of a tether. Attaching one as the **target** is refused and
    emits `grav_tether_immovable`.

    This is not tidiness. A rigid `grav_tether_lock` on a black hole makes the hole the
    load: the beam reels it onto the hull, `_enforce_impulse` caps the puller to impulse
    so it cannot warp away, and a mission's lethal-proximity watch then explodes anything
    within the kill radius - after which the hole stays parked wherever it was dropped.
    One hold-click took whole games down that way.

    A **swing** is unaffected and is the point of the distinction: there the anchor is the
    source and the ship is what moves, so a black-hole slingshot still works. A mission
    that wants the old behavior calls `grav_tether_set_anchor_roles("")`; one that has
    other immovable bodies adds them.

!!! tip "For a readout, ask `grav_tether_status`"
    A display needs three facts at once: what is on the other end, what the beam is
    doing, and **which end this ship is on**. `grav_tether_status(obj)` answers all
    three (`partner` / `mode` / `role`), or `None` when the ship is free;
    `grav_tether_partner(obj)` is the id alone, for a route that wants something to hand
    straight to `to_object`.

    `role` is the part that is easy to skip and wrong to skip: a fighter on a **swing**
    is the tethered `target`, not the puller, and so is any ship caught in a hostile
    beam - or one that grabbed a load heavy enough for the mass rule to reverse the
    connection. A panel that assumes "I am the puller" is confidently backwards exactly
    when being tethered matters most. LM's Weapons readout
    (`consoles/tether_indicator.py`) is the worked example.

## API

::: sbs_utils.procedural.grav_tether
