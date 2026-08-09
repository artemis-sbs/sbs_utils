# Mount

Weld an object into another object's **body frame** and let the engine hold it there - a
weapon turret on a hull, a sensor pod, a parasite craft. Pair with
[turret](turret.md) and you have an autonomous weapon mount: turret decides what to
shoot, mount decides where it rides.

Engine-measured (1.3.5): `sim.AddTractorConnection(host, mount, vec3(0,0,200), 0)` held a
mount at **exactly 200.0u and exactly 0.0 deg off the host's nose while the host's heading
swung 51 deg** - the separation vector rotated with the hull. So the engine does the work
every frame: **no per-tick reposition, no tick task, and no frame lag.**

!!! note "Do not infer this from grav_tether's docs"
    [grav_tether](grav_tether.md) describes the offset point as world-fixed, which is true
    only of the case it uses - it never *passes* an offset, so its load reels to the
    source's own position. The two modules want opposite things: grav_tether drags a load
    **behind** a ship, mount bolts one **onto** it.

## Lifecycle

`+z` local is forward, `+x` right, `+y` up. A mount spawns at the host's position and the
weld pulls it into place.

- A host killed in **combat** takes its mounts with it, honoring each mount's
  `delete_with_host` - pass `False` for a blown-off turret that survives as salvage.
- A host removed by a **script** fires no destroy event, so `mount_host_of()` reads `None`
  for a vanished host and `mount_prune_orphans()` cleans up that path.
- There is **no module-level registry**: the engine owns the connection, the host/mount
  relationship is an Agent link, and per-mount settings live in the mount's inventory - so
  nothing here can outlive its objects, and nothing needs a reset-ledger entry.

## API

::: sbs_utils.procedural.mount
