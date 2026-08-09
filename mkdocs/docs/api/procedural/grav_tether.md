# Grav-tether

A tractor beam: **lock / tow / reel** a load, or **swing** a fighter around an anchor.
Thin wrappers over the engine-native tractor (`sim.AddTractorConnection`) plus the
mission-facing behavior the raw API doesn't provide — mode presets, a reel ramp, the
canonical **impulse-only** enforcement (cap / snap), and a moving circle-point swing.

Key facts (engine-confirmed): a static tether reels the target fully in, so holding a
load *at* a distance uses a per-tick rope-toggle; a player hull can be tractor-pulled.
Pair with [`closest_in_front`](space_objects.md) for nose-aim acquisition (the engine has
no raycast).

!!! note "The offset point is not world-fixed - this module just never passes one"
    Older notes here said the tractor's offset point is world-fixed. It is measurably
    **source-relative**: `AddTractorConnection(host, target, vec3(0,0,200), 0)` held a
    target at exactly 200u and exactly 0 deg off the host's nose while the host's heading
    swung 51 deg. A load tethered *here* always reels to the source's own position because
    this module passes **no** offset - which is what a tow wants. To bolt something ON to
    a hull instead of dragging it behind one, use [mount](mount.md).

## API

::: sbs_utils.procedural.grav_tether
