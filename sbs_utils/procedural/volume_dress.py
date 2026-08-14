"""Turning a volume into something you can see - the props, and what they look like.

`volume.py` says where space IS and samples its boundary; it deliberately knows nothing
about art. This is the layer above: it takes those samples and makes objects out of them,
with a named STYLE deciding the mesh, the size and which way each piece faces.

It lives in the library because it had already been written twice - `universe_relics.py`
and VisualTestRange's `relic_layout.py` held the same fifteen-line prop factory with the
same constants - and because the three things that make a wall read as a wall are each
easy to get wrong in the same way:

* **Size follows the SPACING, not the room.** A prop scaled to its chamber puts
  400-unit boulders 385 units apart: every rock bigger than the gap beside it, each one
  protruding half a corridor into the lane you fly down. Sized to the spacing instead,
  the same count tiles a surface.
* **The normal is used.** The sampler returns one per point and the old dressers threw
  it away, so every prop was a boulder floating near a wall rather than a piece of it.
  The flat meshes are thin in local +Z, so aligning +Z to the INWARD normal turns the
  face toward the crew.
* **Nothing is solid.** Props are terrain with `exclusion_radius = 0`. A `behav_*` AI
  object with radius 0 NaNs the engine and asserts; terrain WITH a radius shoves the
  ship away from the wall it is supposed to be.

The meshes are the game's own generic primitives - no mod, no media pack, no new art.
Their world size at scale 1 is the OBJ extent times shipData `meshscale`, which is why
the sizes below are written down rather than guessed: `rectangle` is a 100 x 100 x 1.25
slab, `cube` is 40 a side (meshscale 20), `cylinder` is a 100-long tube.
"""
import math
import random

from .spawn import terrain_spawn
from .volume import (volume_get, volume_surface_points, volume_solid_points,
                     volume_inside_points, volume_align_quat, _vol_prim_area, _vol_frame,
                     _VOL_BURIED)


# Nominal world size of one prop mesh at scale 1, as (across, across, through). The
# third number is the axis a flat mesh is thin in - local +Z for every flat generic.
_MESH = {
    "generic-rectangle": (100.0, 100.0, 1.25),
    "generic-hexagon": (86.6, 100.0, 1.0),
    "generic-disk": (100.0, 100.0, 1.0),
    "generic-cube": (40.0, 40.0, 40.0),
    "generic-cylinder": (100.0, 100.0, 100.0),
    "generic-sphere": (200.0, 200.0, 200.0),
    "generic-torus": (210.0, 210.0, 10.0),
}

# An asteroid mesh is about this across the middle. The old dressers spelled it as a
# bare 90.0 and divided by it; same number, named.
_ROCK_RADIUS = 90.0


class _Style:
    """How one look places a prop: which mesh, how big for the spacing it has, and
    whether it turns to face the wall it sits on."""

    __slots__ = ("art", "across", "through", "orient", "roll", "jitter", "tangent",
                 "panel", "bars")

    def __init__(self, art, across, through, orient=True, roll=False, jitter=0.0,
                 tangent=False, panel=False, bars=None):
        self.art = art              # default art keys
        self.across = across        # width, as a multiple of the spacing
        self.through = through      # depth into the wall, as a multiple of the spacing
        self.orient = orient        # align the mesh to the surface?
        self.roll = roll            # random spin about the normal
        self.jitter = jitter        # random size variation, +/- this fraction
        self.tangent = tangent      # align ALONG the wall instead of into it
        self.panel = panel          # a box face is a SLAB, not a field of tiles
        self.bars = bars            # art laid across a panelled wall, on top of it


# `across` is well over 1.0 on purpose, and the number is not a taste call: props sit on
# a grid of one SPACING, a cell-corner is 0.707 spacings from the nearest centre, the
# jitter adds up to 0.15 more, and a piece is only guaranteed to cover its own INSCRIBED
# circle once it can be rolled. Half-width must therefore beat 0.86 spacings, so `across`
# must beat 1.72 - anything less leaves holes at the cell corners, which is exactly what
# flying through a wall feels like. Rock is the exception: it is meant to look eroded, it
# is a lump rather than a tile, and it is deep enough to plug its own gaps.
STYLES = {
    # The two WALL PRIMITIVES. `plates` is the plane - one flat quad scaled to the
    # surface. `blocks` is the same placement with a cube, so a doorway shows a reveal at
    # the cut edge instead of a paper edge. `across`/`jitter`/`roll` below apply only to
    # the tiled path (spheres and capsules); a wall piece is sized by its surface.
    "plates": _Style(("generic-rectangle",), across=1.80, through=0.06,
                     orient=True, roll=True, jitter=0.08, panel=True),
    "blocks": _Style(("generic-cube",), across=1.75, through=0.35,
                     orient=True, roll=False, jitter=0.10, panel=True),
    # A rib's `across` is its DIAMETER across the wall, so neighbouring bars touch at
    # 1.15 and a ribbed wall corrugates instead of striping. Its length comes from the
    # same figure, 1.6x longer again, so the bars read as frames rather than sausages.
    "ribs": _Style(("generic-rectangle",), across=1.15, through=0.30,
                   orient=True, roll=False, jitter=0.08, tangent=True, panel=True,
                   bars="generic-cylinder"),
    "rock": _Style(None, across=1.30, through=1.30,
                   orient=False, roll=False, jitter=0.25),
    "none": None,
}

DEFAULT_STYLE = "rock"


def volume_style_names():
    """Every style an author may name - for lint, and for the editor's dropdown."""
    return tuple(sorted(STYLES.keys()))


def volume_dress(volume, n=600, seed=7, style=DEFAULT_STYLE, art=None, roles="",
                 part_styles=None, part_art=None, out=1.06, solids=True,
                 wall_depth=0.0, debris=0, debris_art=None, plate=0.0, gaps=0.0):
    """Build the props for a volume. Returns how many were made.

    `style` names one of `STYLES`; `part_styles` overrides it per named part, which is
    how a plated hall opens into a rock cave. `art` (and `part_art`) force explicit
    shipData keys and always beat the style's own - an author who names a mesh means it.

    The budget is split by AREA across every part first, so a part dressed in a different
    style still gets the density its size earns and the total stays near `n` whatever the
    mix. `roles` go on every prop, and are how the caller tears the whole shell down.

    `wall_depth` is the least THICKNESS, in world units, the wall may have - pass the
    containment tolerance (scrape band + margin) and the wall covers every position the
    ship is allowed to reach. Without it a thin style is a skin: a ship pushing into the
    scrape band crosses the plating and ends up outside looking back in, which reads as
    flying through the wall, because it is.

    `debris` scatters that many small rocks INSIDE the rooms. A panelled room is a clean
    empty box, which is right for the walls and wrong for a ruin - the sense of scale and
    of age comes from the loose things drifting in it.

    `plate` is how big one piece of wall is, in world units (0 = pick from the room), and
    `gaps` is the fraction of plates left out. Both are about ruins: the engine dislikes
    big planes overlapping, and a wall with nothing missing from it is a wall rather than
    a wreck.
    """
    vol = volume_get(volume) if isinstance(volume, str) else volume
    if vol is None or n <= 0:
        return 0
    parts = vol.named_primitives()
    if not parts:
        return 0
    part_styles = part_styles or {}
    part_art = part_art or {}

    # Group the parts by the (style, art) they will wear, so each group is sampled in one
    # pass and every prop in it shares a look.
    groups = {}
    for name, prim in parts:
        key = (part_styles.get(name, style), part_art.get(name) or art)
        groups.setdefault(key, []).append((name, prim))

    total_area = sum(_vol_prim_area(prim) for _n, prim in parts) or 1.0
    rng = random.Random(seed)
    made = 0
    for (group_style, group_art), members in groups.items():
        spec = _dress_style(group_style)
        if spec is None:                      # "none", or a name nobody defined
            continue
        keys = _dress_art(group_art, spec)
        share = sum(_vol_prim_area(prim) for _n, prim in members) / total_area
        count = int(round(n * share))
        if count <= 0:
            continue
        # A BOX IS A ROOM: six walls, not a mosaic of tiles pretending to be six walls.
        # A built style panels each face with as few slabs as keep the texture square,
        # which is what "floor, ceiling, four walls" means and is what a box was for.
        # Curved surfaces cannot be panelled, so spheres and capsules keep the tiling.
        tiled = []
        for name, prim in members:
            if spec.orient and spec.panel and prim[0] == "box":
                made += _dress_box_faces(rng, spec, keys, prim, roles, wall_depth,
                                        vol, plate=plate, gaps=gaps)
            else:
                tiled.append(name)
        if not tiled:
            continue
        # An oriented prop is placed by its INNER FACE, so it is sampled ON the boundary
        # (out=1.0) and pushed out by its own half-thickness below. An unoriented rock is
        # a lump with no faces, and keeps the old nudge clear of the wall.
        for pt in volume_surface_points(vol, count, seed=seed,
                                        out=1.0 if spec.orient else out,
                                        names=tiled, with_spacing=True):
            _dress_prop(rng, spec, keys, pt, roles, depth_min=wall_depth)
            made += 1

    # A subtracted mass MUST be dressed or it is an invisible obstacle: containment stops
    # the ship dead at something with nothing there to see. A pillar is looked at from
    # outside, so a BOX one is simply the cube primitive at its own size - the same build
    # step as a wall, and 50 little plates wrapped around a crate was never it. Curved
    # masses keep the tiled shell until they get their own primitive.
    if solids and vol.solids:
        spec = _dress_style(style)
        if spec is not None:
            keys = _dress_art(art, spec)
            curved = []
            for prim in vol.solids:
                built = _dress_solid(rng, spec, keys, prim, roles) if spec.panel else 0
                if built:
                    made += built
                else:
                    curved.append(prim)
            if curved:
                solid_n = max(8, n // 12)
                for pt in volume_solid_points(vol, solid_n, seed=seed, with_spacing=True,
                                              only=curved):
                    _dress_prop(rng, spec, keys, pt, roles, flip=True,
                                depth_min=wall_depth)
                    made += 1

    # Loose stuff drifting in the rooms. Small, unoriented and well clear of the walls:
    # it is there for scale and for age, not to be flown around.
    if debris > 0:
        keys = _dress_art(debris_art, STYLES["rock"])
        for (x, y, z) in volume_inside_points(vol, int(debris), seed=seed, margin=200.0,
                                             tries=200):
            size = rng.uniform(40.0, 140.0)
            p = terrain_spawn(x, y, z, "", ("#," + roles) if roles else "#",
                              keys[rng.randrange(len(keys))], "behav_asteroid")
            if p is None:
                continue
            for axis in "xyz":
                p.blob.set("local_scale_" + axis + "_coeff",
                           size / _ROCK_RADIUS * rng.uniform(0.8, 1.2), 0)
            _dress_finish(p)
            made += 1
    return made


def _dress_box_faces(rng, spec, art_keys, prim, roles, depth, vol=None,
                     plate=0.0, gaps=0.0):
    """Build a box out of wall pieces: one primitive per surface, scaled to it.

    This is the build pass over a blockout, and it follows the same order anyone would in
    Blender or Unreal: the volume says where the space is, and then a WALL PRIMITIVE - a
    plane, or a cube with some thickness - is placed and scaled to each wall, floor and
    ceiling. A plain room is therefore SIX pieces. Not six hundred tiles arranged to look
    like six pieces, which is what this was and which read from outside as a starburst.

    Each surface is laid up out of PLATES on a regular grid rather than as one huge quad.
    Two reasons, and neither is decoration:

    * the engine does not cope with big planes overlapping - one enormous quad meeting
      another is where z-fighting lives, and small pieces that only ever touch avoid it;
    * a ruin should be missing some. `gaps` drops a fraction of the plates, which is a
      hole you can see through and the difference between a wall and a wreck.

    Plates are coplanar, axis-aligned and exactly adjacent - they tile the surface, they
    never overlap. That is the whole distinction from the confetti this replaced, which
    was randomly rolled, jittered and deliberately overlapping.

    Where one room opens into another there is no wall at all: a plate whose place is
    navigable is simply not laid, which is the doorway.
    """
    c, h = prim[1], prim[2]
    art = art_keys[rng.randrange(len(art_keys))]
    mesh = _MESH.get(art, (100.0, 100.0, 1.25))
    thick = max(float(depth or 0.0), 40.0)
    made = 0
    for axis in range(3):
        u, v = [i for i in range(3) if i != axis]
        hu, hv = h[u], h[v]
        # Plate size is judged PER FACE, off its shorter side: about three plates across
        # it. Taken from the room instead, a wall came out one plate tall and read as one
        # huge slab, which is what it looked like. Clamped at both ends - under ~250 a
        # wall is gravel again and the object count runs away, over ~900 the big-plane
        # overlap the engine dislikes comes back.
        size = float(plate) if plate else             min(max(min(2.0 * hu, 2.0 * hv) / 3.0, 250.0), 900.0)
        cols = max(1, int(round(2.0 * hu / size)))
        rows = max(1, int(round(2.0 * hv / size)))
        wide, tall = 2.0 * hu / cols, 2.0 * hv / rows
        for sign in (1.0, -1.0):
            normal = [0.0, 0.0, 0.0]
            normal[axis] = sign
            laid = 0
            for k in range(cols):
                for r in range(rows):
                    pos = [0.0, 0.0, 0.0]
                    pos[axis] = c[axis] + sign * h[axis]
                    pos[u] = c[u] + (2.0 * (k + 0.5) / cols - 1.0) * hu
                    pos[v] = c[v] + (2.0 * (r + 0.5) / rows - 1.0) * hv
                    # THE DOORWAY: the room next door is here, so no wall is.
                    if vol is not None and vol.depth(tuple(pos)) < -_VOL_BURIED:
                        continue
                    # A MISSING PLATE. Drawn before the spawn either way so the pattern
                    # stays deterministic in the seed.
                    if gaps > 0.0 and rng.random() < gaps:
                        continue
                    p = terrain_spawn(pos[0], pos[1], pos[2], "",
                                      ("#," + roles) if roles else "#", art,
                                      "behav_asteroid")
                    if p is None:
                        continue
                    # No roll: a plate is placed, not scattered. A quarter turn would swap
                    # a non-square plate's width and height, and the scale is applied
                    # after the rotation, so it would come out the wrong shape.
                    _dress_orient(p, [-n for n in normal], 0.0)
                    p.blob.set("local_scale_x_coeff", wide / mesh[0], 0)
                    p.blob.set("local_scale_y_coeff", tall / mesh[1], 0)
                    p.blob.set("local_scale_z_coeff", thick / mesh[2], 0)
                    _dress_finish(p)
                    made += 1
                    laid += 1
            # FRAMES ONLY WHERE THERE IS A WALL. A face that laid no plates is a doorway,
            # and bars were being hung across it regardless - the shaft's ends open into
            # the concourse and the bay, so its ribs floated in mid-air in two rooms that
            # are not even ribbed.
            if spec.bars and laid:
                # Frames across the whole surface, not per plate.
                centre = [0.0, 0.0, 0.0]
                centre[axis] = c[axis] + sign * h[axis]
                centre[u], centre[v] = c[u], c[v]
                made += _dress_bars(rng, spec, prim, roles, normal, centre,
                                    u, v, 2.0 * hu, 2.0 * hv, thick, vol)
    return made


def _dress_solid(rng, spec, art_keys, prim, roles):
    """A subtracted mass as ONE primitive at its own size, seen from outside.

    The mirror of a wall piece, and the same reasoning: a pillar is a thing you look AT
    rather than fly inside, so there is nothing to cut and nothing to face - it is the
    shape, at its size. Wrapping a crate in fifty little plates was the tiling habit
    showing through; a box is a cube, a sphere is a sphere, a fallen span is a cylinder.

    Returns how many were made - 0 for a shape with no primitive, so the caller can fall
    back to a tiled shell for it.
    """
    kind = prim[0]
    if kind == "sphere":
        c, r = prim[1], prim[2]
        return _dress_solid_at(roles, "generic-sphere", c, (r, r, r), None)
    if kind == "capsule":
        a, b, r = prim[1], prim[2], prim[3]
        mid = tuple((a[i] + b[i]) * 0.5 for i in range(3))
        axis = tuple(b[i] - a[i] for i in range(3))
        length = math.sqrt(sum(v * v for v in axis)) or 1.0
        # Half-extents in the cylinder's own frame: radius across, half the length plus
        # the caps along it.
        return _dress_solid_at(roles, "generic-cylinder", mid,
                               (r, r, (length + 2.0 * r) * 0.5), axis)
    if kind == "box":
        c, h = prim[1], prim[2]
        return _dress_solid_at(roles, "generic-cube", c, h, None)
    return 0


def _dress_solid_at(roles, art, centre, half, axis):
    """Spawn one primitive at `centre`, scaled to `half` extents, its local +Z on `axis`."""
    mesh = _MESH.get(art, (100.0, 100.0, 100.0))
    p = terrain_spawn(centre[0], centre[1], centre[2], "",
                      ("#," + roles) if roles else "#", art, "behav_asteroid")
    if p is None:
        return 0
    if axis is not None:
        _dress_orient(p, axis, 0.0)
    p.blob.set("local_scale_x_coeff", 2.0 * half[0] / mesh[0], 0)
    p.blob.set("local_scale_y_coeff", 2.0 * half[1] / mesh[1], 0)
    p.blob.set("local_scale_z_coeff", 2.0 * half[2] / mesh[2], 0)
    _dress_finish(p)
    return 1


def _dress_bars(rng, spec, prim, roles, normal, centre, u, v, wide, tall, thick,
                vol=None):
    """Ring frames laid across a panelled wall.

    ON TOP of the panel, never instead of it: bars alone are stripes with the room
    showing between them, which is a texture on a solid wall and a hole on nothing.
    """
    art = spec.bars
    mesh = _MESH.get(art, (100.0, 100.0, 100.0))
    # Along the SHORT axis of the face, so the frames read as ribs of a tube.
    along, across_axis = (u, v) if wide >= tall else (v, u)
    span = max(wide, tall)
    count = max(2, int(span / max(1.0, min(wide, tall) * 0.55)))
    radius = thick * 0.45
    made = 0
    for i in range(count):
        pos = list(centre)
        t = (i + 0.5) / count - 0.5
        pos[along] += t * span
        # And not across a hole in an otherwise walled face: a corner bite is still a way
        # through, and a frame hanging in it is the same bug at a smaller scale.
        if vol is not None and vol.depth(tuple(pos)) < -_VOL_BURIED:
            continue
        p = terrain_spawn(pos[0], pos[1], pos[2], "",
                          ("#," + roles) if roles else "#", art, "behav_asteroid")
        if p is None:
            continue
        axis_dir = [0.0, 0.0, 0.0]
        axis_dir[across_axis] = 1.0
        _dress_orient(p, axis_dir, 0.0)
        p.blob.set("local_scale_x_coeff", radius * 2.0 / mesh[0], 0)
        p.blob.set("local_scale_y_coeff", radius * 2.0 / mesh[1], 0)
        p.blob.set("local_scale_z_coeff", min(wide, tall) / mesh[2], 0)
        _dress_finish(p)
        made += 1
    return made


def _dress_finish(p):
    """The two things EVERY piece of scenery needs, in one place.

    `exclusion_radius = 0` because a wall you can collide with is a wall that shoves the
    ship off itself, and `unselectable` because scenery is not a contact: a relic lays
    hundreds of pieces, and every one of them was arriving in the science list and under
    the weapons cursor. NOT `elite_main_scn_invis` - a wall has to stay VISIBLE, it just
    must not be targetable. The contents layer sets `unselectable, 0` on a marker it
    means you to click (amd_relics), so it keeps its own behaviour.
    """
    p.blob.set("unselectable", 1, 0)
    p.engine_object.exclusion_radius = 0
    return p


def _dress_style(name):
    """The style spec for a name. An unknown name falls back to the default rather than
    failing: a typo should be a plain wall, not a mission that will not start."""
    return STYLES.get(str(name or DEFAULT_STYLE).strip().lower(), STYLES[DEFAULT_STYLE])


def _dress_art(art, spec):
    """The art keys to use: whatever was asked for, else the style's, else asteroids."""
    if art:
        keys = [k.strip() for k in (art.split(",") if isinstance(art, str) else art)]
        keys = [k for k in keys if k]
        if keys:
            return tuple(keys)
    if spec.art:
        return spec.art
    try:
        from .ship_data import plain_asteroid_keys
        got = tuple(plain_asteroid_keys() or ())
        if got:
            return got
    except Exception:                                   # noqa: BLE001
        pass
    return ("plain_asteroid_6", "plain_asteroid_7", "plain_asteroid_8")


def _dress_prop(rng, spec, art_keys, point, roles, flip=False, depth_min=0.0):
    """One prop: spawned, sized to its spacing, and turned to face its wall."""
    x, y, z, nx, ny, nz, spacing = point
    art = art_keys[rng.randrange(len(art_keys))]

    wobble = 1.0 + rng.uniform(-spec.jitter, spec.jitter) if spec.jitter else 1.0
    across = spec.across * spacing * wobble
    # DEEP ENOUGH TO BE A WALL. Containment lets a ship push a whole scrape band past the
    # boundary before it is held, so a wall thinner than that band is a skin the ship
    # crosses and comes out the far side of.
    through = max(spec.through * spacing * wobble, float(depth_min or 0.0), 1.0)
    mesh = _MESH.get(art, (_ROCK_RADIUS * 2.0,) * 3)

    if spec.orient:
        # Placed by its INNER FACE: the sample sits on the boundary, so the body goes
        # away from the space you fly through and nothing juts into it. On a SOLID that
        # is the other way round - the rock is on the normal's near side, and pushing
        # outward would stand the pillar's plating in the room.
        push = through * 0.5 * (-1.0 if flip else 1.0)
        x, y, z = x + nx * push, y + ny * push, z + nz * push

    p = terrain_spawn(x, y, z, "", ("#," + roles) if roles else "#", art, "behav_asteroid")
    if p is None:
        return None

    if spec.orient:
        # The face looks INWARD, at the crew - except on a pillar, which is looked at
        # from outside.
        toward = (nx, ny, nz) if flip else (-nx, -ny, -nz)
        if spec.tangent:
            # A rib lies ALONG the wall: its long axis is a tangent, so align to the
            # frame's first perpendicular rather than to the normal itself.
            toward = _vol_frame(toward)[0]
        # Quarter turns only. A square's FOOTPRINT is unchanged by a 90-degree roll, so
        # the plating stays gap-free while the texture and normal map still vary piece to
        # piece; a free roll rotates the square off the grid and opens the corners.
        roll = (math.pi * 0.5) * rng.randrange(4) if spec.roll else 0.0
        _dress_orient(p, toward, roll)
        if spec.tangent:
            # A BAR, not a drum. The mesh's long axis is local +Z, and for a tangent
            # style that axis lies ALONG the wall - so the length is the `across` figure
            # and the wall depth is the bar's THICKNESS. Feeding depth into the length
            # (the obvious reading of the same two numbers) produces a squat disc, and a
            # wall of discs has a gap between every one of them.
            radius = max(across * 0.5, through * 0.5)
            sx, sy = radius * 2.0 / mesh[0], radius * 2.0 / mesh[1]
            sz = (spec.across * spacing * 1.6) / mesh[2]
        else:
            sx, sy, sz = across / mesh[0], across / mesh[1], through / mesh[2]
    else:
        # Unoriented: the mesh has no meaningful axes, so vary all three and let it read
        # as rubble rather than as masonry.
        base = across / mesh[0]
        sx = base
        sy = base * rng.uniform(0.8, 1.2)
        sz = base * rng.uniform(0.8, 1.2)

    # All THREE, always: terrain_spawn sets none of them, and a reader that expects them
    # (resource_gather multiplies the three together) gets None and takes the mission
    # down with it.
    p.blob.set("local_scale_x_coeff", sx, 0)
    p.blob.set("local_scale_y_coeff", sy, 0)
    p.blob.set("local_scale_z_coeff", sz, 0)
    _dress_finish(p)
    return p


def _dress_orient(p, toward, roll):
    """Point the prop's local +Z down `toward`.

    Quietly does nothing where quaternions are unavailable, because a shell that is
    merely unrotated still reads as a wall, while a shell that failed to spawn does not.
    """
    try:
        import sbs
        w, qx, qy, qz = volume_align_quat(toward, roll)
        p.engine_object.rot_quat = sbs.quaternion(w, qx, qy, qz)
    except Exception:                                   # noqa: BLE001
        pass
