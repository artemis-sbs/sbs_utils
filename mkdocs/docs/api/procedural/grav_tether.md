# Grav-tether

A tractor beam: **lock / tow / reel** a load, or **swing** a fighter around an anchor.
Thin wrappers over the engine-native tractor (`sim.AddTractorConnection`) plus the
mission-facing behavior the raw API doesn't provide — mode presets, a reel ramp, the
canonical **impulse-only** enforcement (cap / snap), and a moving circle-point swing.

Key facts (engine-confirmed): a static tether reels the target fully in, so holding a
load *at* a distance uses a per-tick rope-toggle; the offset point is world-fixed; a
player hull can be tractor-pulled. Pair with [`closest_in_front`](space_objects.md) for
nose-aim acquisition (the engine has no raycast).

## API

::: sbs_utils.procedural.grav_tether
