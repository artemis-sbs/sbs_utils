def _dress_art (art, spec):
    """The art keys to use: whatever was asked for, else the style's, else asteroids.
    
    A KIT IGNORES `Art:`. Its pieces come from the kit, and a relic written for the art
    pack keeps its old `Art:` as what the FALLBACK style wears (`Walls: cave, rock` with
    `Art: plain_asteroid_6`): the pack present, carved stone; absent, the same rocks as
    before. An asked-for key the ship index does not know is dropped with one line - the
    engine would draw it as the `unknown` question mark rather than fail."""
def _dress_bars (rng, spec, prim, roles, normal, centre, u, v, wide, tall, thick, vol=None):
    """Ring frames laid across a panelled wall.
    
    ON TOP of the panel, never instead of it: bars alone are stripes with the room
    showing between them, which is a texture on a solid wall and a hole on nothing."""
def _dress_box_faces (rng, spec, art_keys, prim, roles, depth, vol=None, plate=0.0, gaps=0.0, grow=1.0):
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
    navigable is simply not laid, which is the doorway."""
def _dress_finish (p):
    """The two things EVERY piece of scenery needs, in one place.
    
    `exclusion_radius = 0` because a wall you can collide with is a wall that shoves the
    ship off itself, and `unselectable` because scenery is not a contact: a relic lays
    hundreds of pieces, and every one of them was arriving in the science list and under
    the weapons cursor. NOT `elite_main_scn_invis` - a wall has to stay VISIBLE, it just
    must not be targetable. The contents layer sets `unselectable, 0` on a marker it
    means you to click (amd_relics), so it keeps its own behaviour."""
def _dress_kit_box (rng, kit, prim, roles, depth, vol=None, plate=0.0, gaps=0.0, grow=1.0, flip=False):
    """A box as a room built from a kit: floor, ceiling and walls, each face tiled with
    its own kind of piece, upright, plus trims along the floor and ceiling edges and
    pillars up the corners. `flip` dresses a SOLID - looked at from outside."""
def _dress_kit_edges (rng, kit, prim, roles, vol, scale):
    """Trims where the walls meet the floor and ceiling, and pillars up the corners.
    Skipped wherever the room opens into the next one - a trim across a doorway is a bar
    across a doorway."""
def _dress_kit_tile (rng, kit, point, roles, flip=False, depth_min=0.0):
    """One kit piece on a CURVED surface (a chamber, a passage): the tiled path.
    
    Floor, wall or ceiling by where on the surface it is - the inward normal pointing up
    is a floor - so a round cave reads as a room with a floor rather than a ball of
    identical tiles."""
def _dress_orient (p, toward, roll):
    """Point the prop's local +Z down `toward`.
    
    Quietly does nothing where quaternions are unavailable, because a shell that is
    merely unrotated still reads as a wall, while a shell that failed to spawn does not."""
def _dress_prop (rng, spec, art_keys, point, roles, flip=False, depth_min=0.0):
    """One prop: spawned, sized to its spacing, and turned to face its wall."""
def _dress_report_unknown (art, part_art):
    """Say, once each, which asked-for art keys the game does not have.
    
    `_dress_art` drops such a key so the engine does not draw its `unknown` question
    mark - and it dropped it in silence. `Art: plain_astroid_9` on one room built the
    ruin, passed the run, left the log empty, and that room wore the ordinary rock. From
    the command line lint cannot say it either: the art catalog is the engine's."""
def _dress_solid (rng, spec, art_keys, prim, roles):
    """A subtracted mass as ONE primitive at its own size, seen from outside.
    
    The mirror of a wall piece, and the same reasoning: a pillar is a thing you look AT
    rather than fly inside, so there is nothing to cut and nothing to face - it is the
    shape, at its size. Wrapping a crate in fifty little plates was the tiling habit
    showing through; a box is a cube, a sphere is a sphere, a fallen span is a cylinder.
    
    Returns how many were made - 0 for a shape with no primitive, so the caller can fall
    back to a tiled shell for it."""
def _dress_solid_at (roles, art, centre, half, axis):
    """Spawn one primitive at `centre`, scaled to `half` extents, its local +Z on `axis`."""
def _dress_style (name):
    """The style spec for a name. An unknown name falls back to the default rather than
    failing: a typo should be a plain wall, not a mission that will not start.
    
    A comma list is a FALLBACK CHAIN - `torgoth, plates` is the art pack's kit when the
    mission loaded it, and plates when it did not - so the first name that is registered
    wins. `none` is a real answer (no walls), not a miss."""
def _kit_face_axes (axis):
    """For a face across `axis`: (horizontal axis, vertical axis) of its pieces - which
    world axis a piece's local X and local Y run along."""
def _kit_face_kind (axis, sign, flip=False):
    """What a box face is: the -Y face of a room is its floor, the +Y its ceiling. On a
    solid it is the other way round - you stand on its TOP."""
def _kit_grow (kit, prims, budget, plate=0.0):
    """The smallest growth at which these boxes fit `budget` pieces."""
def _kit_plan (kit, prim, grow, plate=0.0):
    """How many pieces a box takes at this growth: (faces, trims, pillars)."""
def _kit_spawn (art, pos, facing, up, scale, roles):
    """Spawn one kit piece: upright, facing `facing`, scaled per axis. None on failure."""
def _known_art (keys):
    """The keys the ship index knows. Every key when there is no index to ask (a tool, a
    test), so this can only ever REMOVE a key it is sure about."""
def _mesh_size (art, default):
    """A mesh's world size at scale 1: a generic primitive's from `_MESH`, an art pack's
    piece from its kit manifest, else `default`."""
def _vol_frame (u):
    """Two unit vectors perpendicular to `u`, and to each other.
    
    The helper axis is swapped when `u` is near vertical, because the cross product of two
    parallel vectors is zero and the frame collapses. Getting this wrong is why a vertical
    capsule can end up dressed as a flat disc - the axis-naive version assumes a corridor
    is never a shaft."""
def _vol_prim_area (prim):
    """Rough surface area of a primitive, for splitting a budget between them.
    
    Rough is the point: it decides how many props each room gets, so a chamber twice the
    size gets about twice as many. Exactness would buy nothing a author would notice."""
def terrain_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a passive terrain object into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the object belongs to, or ``None``.
        ship_key (str): Object template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new terrain object."""
def volume_align_quat (direction, roll=0.0):
    """A quaternion `(w, x, y, z)` rotating local **+Z** onto `direction`.
    
    This is what turns a sampled normal into an oriented prop. The flat generic meshes -
    `rectangle`, `disk`, `hexagon` - are thin in local +Z, so aligning +Z to a wall's
    INWARD normal turns the face towards the crew and the slab lies on the wall.
    
    `roll` spins the prop about that axis, in radians. A shell of panels all rolled
    identically reads as printed wallpaper; a random roll per prop reads as plating.
    
    Geometry, not decoration: it converts a direction into a rotation and knows nothing
    about art, which is why it belongs beside the sampler rather than in the dresser."""
def volume_dress (volume, n=600, seed=7, style='rock', art=None, roles='', part_styles=None, part_art=None, out=1.06, solids=True, wall_depth=0.0, debris=0, debris_art=None, plate=0.0, gaps=0.0, solid_skip=()):
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
    
    A KIT style (`volume_kit`) builds the same rooms from an art pack's pieces - floor,
    ceiling, walls, trims and corner pillars, each upright - and, unlike the plates,
    honours `n`: its pieces grow together until the relic fits.
    
    `solid_skip` names solids (by index in `vol.solids`) that something else dresses - a
    set piece standing in for the generic primitive (`amd_relics.relic_dress`)."""
def volume_get (name):
    """The named volume, or None."""
def volume_inside_points (volume, n, seed=None, margin=0.0, tries=40):
    """`n` points INSIDE the volume - the fill, for debris, cargo, anything floating.
    
    Rejection sampled in the bounding sphere against `depth(p) < -margin`, which is
    wasteful in principle and exact in practice: it is the only test that respects
    subtracted solids, so nothing lands inside a pillar. A relic is mostly empty bounding
    sphere, so `tries` caps the work rather than looping forever on a layout with no room
    in it; a short return means the volume could not hold that many.
    
    Deterministic in `(seed, n)`, like the shell."""
def volume_look_quat (forward, up=(0.0, 1.0, 0.0), fallback_up=(0.0, 0.0, 1.0)):
    """A quaternion `(w, x, y, z)` turning local **+Z** onto `forward` with local **+Y**
    as close to `up` as it can get.
    
    The difference from `volume_align_quat` is the second axis, and it is the whole of
    why a kit piece can be placed at all. `volume_align_quat` spins a piece about its
    facing by whatever `_vol_frame` happens to pick, which is harmless for a square plate
    and wrong for anything with a top: on every side wall it puts local +Y at world -Y, so
    a wall panel with a skirting board, a door, a statue would all stand on their heads.
    
    `fallback_up` is used when `forward` is (nearly) parallel to `up` - a floor or a
    ceiling, whose facing IS the up direction - and decides which way the tile's own +Y
    runs across it. Deterministic, so a floor's tiles all line up."""
def volume_solid_points (volume, n, seed=None, inward=0.94, with_spacing=False, only=None):
    """`n` points on the surface of the SUBTRACTED masses, facing outward.
    
    A solid that is not dressed is an invisible obstacle: containment stops you at
    something with nothing there to see, which reads as the relic being broken rather than
    as a pillar. `inward` keeps the props just inside the solid's own surface, because you
    look at a pillar from outside it - the opposite of the shell, where they sit just
    outside the space you fly in.
    
    `only` narrows to particular solid primitives. A caller that can build some masses
    from a single primitive - a box mass is just the cube - uses it to ask for a shell
    over the rest rather than over everything."""
def volume_style_add_kit (name):
    """Make a registered wall kit nameable as a style (`Walls: torgoth`). What
    `volume_kit_register` calls; a built-in style of the same name is never replaced."""
def volume_style_names ():
    """Every style an author may name - for lint, and for the editor's dropdown."""
def volume_style_remove_kits (names):
    """Forget kit styles - the per-mission reset."""
def volume_surface_points (volume, n, seed=None, out=1.06, kinds=None, clip=True, with_spacing=False, names=None):
    """`n` points spread over the volume's BOUNDARY, with an outward normal each.
    
    Returns `[(x, y, z, nx, ny, nz)]` in world coordinates. This is the shell: what a
    mission scatters props over to turn a described space into a visible one.
    
    The budget is split between primitives BY AREA, so a chamber twice the size gets about
    twice the props and density reads as uniform across the whole relic rather than per
    part. `out` pushes points just clear of the true surface - props belong outside the
    space you fly in, or they are obstacles you cannot see coming.
    
    Deterministic in `(seed, n)`: the same call gives the same shell, so a relic looks the
    same every time a mission runs, and a rebuild after an edit only changes what the edit
    changed.
    
    `kinds` narrows to some of `"sphere"`, `"capsule"`, `"box"` - the chambers alone, say.
    `names` narrows to particular PARTS, which is how one room is dressed differently
    from the next. Clipping still sees the whole volume, so a wall sampled for one room
    is still dropped where the room next door has opened it up.
    
    `with_spacing=True` appends how far apart the points are on that primitive, giving
    `(x, y, z, nx, ny, nz, spacing)`. That is what a prop sizes itself to: sized to the
    ROOM instead, a shell puts 400-unit boulders 385 units apart and the wall becomes a
    gravel field you fly through rather than past.
    
    `clip` drops points that are BURIED - inside the union rather than on the outside of
    it. Each primitive is sampled on its own surface, so where two overlap, one shape's
    wall runs through the other's open space: the ring where a passage meets a chamber puts
    rock in the middle of the corridor. The shell wanted is the outside of the union, not
    the union of the surfaces. Costs one depth() per point and returns fewer than `n`,
    which is the honest trade - ask for more if a count matters."""
class _Style(object):
    """How one look places a prop: which mesh, how big for the spacing it has, and
    whether it turns to face the wall it sits on."""
    def __init__ (self, art, across, through, orient=True, roll=False, jitter=0.0, tangent=False, panel=False, bars=None, kit=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
