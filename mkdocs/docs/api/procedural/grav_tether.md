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
