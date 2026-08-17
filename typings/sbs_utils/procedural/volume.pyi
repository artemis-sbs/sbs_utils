def _vol_anchor_drop (ship_id):
    """Release one ship's tractor and delete its anchor. The unit `_vol_anchors_clear`
    repeats for every ship - shared so the two paths cannot drift apart."""
def _vol_anchor_object (ship_id):
    """The invisible object a ship's containment tractor pulls against.
    
    One per ship, kept alive for the duration of the watch - spawning and deleting one
    per breach would churn objects, and `delete_object` frees the C++ side
    synchronously.
    
    `behav_station` on purpose: it is the object type grav_tether_spike uses as its
    anchor, and a station does not steer - an AI behavior here would be the
    `exclusion_radius`-zero NaN hazard. The radius is 1 rather than 0 for the same
    reason: it keeps the ship from ever reaching the anchor's exact center."""
def _vol_anchors_clear ():
    """Release every tractor and delete every anchor object.
    
    Deletion is `space_objects.delete_object`, NOT `sim.delete_object` - the simulation
    has no such method, so the old call raised AttributeError straight into the `except`
    below and every anchor survived: invisible (nothing draws them), unowned, and one
    more per watched ship on every unwatch and every mission reload.
    
    The `except` stays, because releasing a tractor on a ship that has since been
    destroyed is a legitimate no-op, but it no longer covers the delete."""
def _vol_bleed_throttle (so, keep=0.75, floor=0.0):
    """Take way off a ship that is in the wall. Only ever lowers, like the governor.
    
    Hitting something should COST you speed. The helm can open the throttle again the
    moment the hull is clear - this is drag while in contact, not a confiscation."""
def _vol_block_jump (so):
    """Try to hold the jump/warp drives inactive.
    
    ENGINE-VERIFIED (2026-08-12, from the helm seat): writing these DOES stop the drive
    engaging, so a volume can genuinely forbid jumping out. Still opt-in, because
    confiscating a drive is a gameplay decision rather than a containment necessity."""
def _vol_box_surface (prim, count, rng, out):
    """FACES, not a shell. A box dressed as a sphere of props reads as a cave again and
    hides the corners that are the whole reason it is a box.
    
    Each face is a JITTERED GRID, for the reason `_vol_even_sphere` exists: uniform
    random over a face clumps, and a clumped wall has holes you can see straight out
    through. A flat face is where that shows worst - the eye reads a plane and finds the
    gaps. The grid is proportioned to the face (a long thin wall gets a long thin
    lattice, not a square one), and each point is jittered inside its own cell so the
    lattice never reads as wallpaper."""
def _vol_capsule_args (args):
    """Accept a capsule as either two POINTS plus a radius, or seven FLAT numbers.
    
    The Python API reads better as points - `volume_solid(v, "capsule", (0,-800,0),
    (0,800,0), 60)` - but a declarative source has no tuples: an authored
    `Solid: capsule, 0, -800, 0, 0, 800, 0, 60` arrives as a flat row. Supporting both
    here means the AMD reader needs no special case and neither does the caller."""
def _vol_capsule_surface (prim, count, rng, out, per_ring=6):
    ...
def _vol_default_agents ():
    """Players and fighters, minus anything docked.
    
    The candidate set LM's black-hole lethal ticker uses: LM strips `__player__`
    from fighters so they carry `cockpit`, and docked craft carry `standby` - which
    are excluded so a carrier's own bay is not a hazard."""
def _vol_dist (p, q):
    ...
def _vol_even_sphere (n):
    """`n` roughly-even directions on the unit sphere - a golden-angle spiral.
    
    Even beats random here, and the difference is visible: uniform sampling clumps, and a
    clumped shell has holes you can see straight out through. `scatter.sphere` already
    samples a shell but draws pitch as `uniform(-pi, pi)`, which piles points at the poles
    and covers the equator twice - this is the sampler that defect calls for."""
def _vol_frame (u):
    """Two unit vectors perpendicular to `u`, and to each other.
    
    The helper axis is swapped when `u` is near vertical, because the cross product of two
    parallel vectors is zero and the frame collapses. Getting this wrong is why a vertical
    capsule can end up dressed as a flat disc - the axis-naive version assumes a corridor
    is never a shaft."""
def _vol_govern_throttle (so, cap=1.0):
    """Cap a player's throttle. Only ever lowers it, never raises.
    
    Engine-measured: ONE write is enough, because `playerThrottle` stays where it is
    put until a helm changes it - and `max_throttle` does NOT do this (measured, it
    made no difference at all).
    
    A cap of 1.0 forbids WARP for free, since warp simply is `playerThrottle > 1.0`.
    Below 1.0 it is a genuine speed limit - a relic interior at 0.5 flies like a tight
    space rather than open sky, which also shrinks the tunneling budget."""
def _vol_hold_stiffness (depth, scrape_band):
    """The engine's pull dial for a breach this deep: soft at the wall, locked past it.
    
    `offset` is inverted - 0 is an INFINITE pull. So this walks from a taut-tow 5.0 at
    the scrape band down to 0 at twice the band, which is where a ship is no longer
    scraping along a wall but leaving through it."""
def _vol_prim_area (prim):
    """Rough surface area of a primitive, for splitting a budget between them.
    
    Rough is the point: it decides how many props each room gets, so a chamber twice the
    size gets about twice as many. Exactness would buy nothing a author would notice."""
def _vol_project (prim, p, margin=0.0):
    """The nearest point INSIDE the primitive by at least `margin`.
    
    Per-kind on purpose. A box cannot be projected by pushing towards a centre - that
    would collapse a rectangular hall to its inscribed sphere and make the corners
    unreachable. Clamping per axis is both exact and cheaper."""
def _vol_push_out (p, anchor, radius):
    """A point on the sphere of `radius` about `anchor`, in the direction of p.
    
    When p IS the anchor there is no direction to preserve, so +x is chosen - an
    arbitrary but finite answer. Returning the anchor itself would leave a ship at
    a primitive's exact center, which is the zero-distance case that NaNs AI
    objects."""
def _vol_push_solid_out (prim, p, margin=0.0):
    """The nearest point at least `margin` OUTSIDE a solid - how you leave a pillar."""
def _vol_resolve (volume):
    ...
def _vol_resolve_agents (agents):
    ...
def _vol_rope (prim, p, margin=0.0):
    """``(anchor, rope_len)`` for a tractor hold against this primitive.
    
    Sphere and capsule return the MEDIAL AXIS point and the primitive's radius, so a
    rope of that length about that point IS the containment constraint - the shape the
    engine run validated, kept exactly.
    
    A box has no such single sphere, so it returns the projected interior point with a
    short rope: while breached the ship is outside anyway, and the tether is released
    the moment it is back inside, so pulling it to the nearest safe point is the same
    behavior expressed for a shape that has no centre-and-radius."""
def _vol_sdf (prim, p):
    """Signed distance from p to the primitive's surface. Negative inside."""
def _vol_seg_closest (p, a, b):
    """Closest point on segment AB to P. Returns (distance, (cx, cy, cz)).
    
    Clamped to the segment - that is what makes a capsule a capsule rather than an
    infinite cylinder."""
def _vol_share (prims, n):
    """Split `n` points between primitives by area, giving every one at least 1."""
def _vol_shift (point, origin):
    """Translate an (x, y, z) by the origin. Identity when there is no origin."""
def _vol_shift_solid (kind, args, origin):
    """Translate a solid's POSITION arguments, leaving its size arguments alone.
    
    Each kind carries a different arg shape, which is why this cannot be one generic
    slice: sphere is (x, y, z, r), box is (x, y, z, hx, hy, hz), and capsule is two
    POINTS plus a radius."""
def _vol_ship_radius (so):
    """A ship's own radius, so containment can treat it as a hull rather than a dot."""
def _vol_sphere_surface (prim, count, rng, out):
    ...
def _vol_tractor_hold (vol, ship_id, pos, margin, scrape_band=120.0, radius=0.0):
    """Hold a ship inside the volume with an engine-side tractor.
    
    Why not `set_pos`: measured from the helm seat, a per-tick teleport clamp is
    correct on the server and looks WRONG on the client - the client predicts its own
    position, so the ship visibly leaves the volume and snaps back. A tractor moves
    the ship inside the engine's own physics, so client prediction follows it.
    
    THE ENGINE CALL DIRECTLY, not `grav_tether`. That library is a TOWING model, and
    containment inherited three of its rules by reusing it:
    
      * it REFUSES a target moving faster than a grab-speed limit, and LegendaryMissions
        installs that limit at half impulse. A ship flying at a wall is above half
        impulse by definition, so the hold was declined every tick - emitting
        `grav_tether_too_fast` instead of holding anything. That is the whole of "the
        tractor is not strong enough": there was usually no tractor.
      * its impulse enforcement caps the SOURCE, which here is our own invisible anchor;
      * it keeps a shared registry, so a mission towing something and a wall holding a
        ship would argue over one entry.
    
    `orbit.py` reached the same conclusion for the same reasons and calls the engine
    directly; this is that decision applied to the other user of the tractor.
    
    STRENGTH SCALES WITH DEPTH. `tractor_connection.offset` is the engine's only dial -
    "how much the target is pulled towards the offset every tick", where 0 is an
    infinite pull that locks the target. So a ship a hair past the wall gets a soft
    nudge and one driving hard at it gets something immovable, instead of one constant
    that is wrong at both ends."""
def _vol_tractor_release (ship_id):
    """Drop this ship's containment tractor. The engine call directly, to match the hold -
    going through `grav_tether_release` would look up a registry entry we never made."""
def _vol_xyz (p):
    """Coerce a position: Vec3, tuple/list, engine vec3, Agent, or agent id."""
def volume_align_quat (direction, roll=0.0):
    """A quaternion `(w, x, y, z)` rotating local **+Z** onto `direction`.
    
    This is what turns a sampled normal into an oriented prop. The flat generic meshes -
    `rectangle`, `disk`, `hexagon` - are thin in local +Z, so aligning +Z to a wall's
    INWARD normal turns the face towards the crew and the slab lies on the wall.
    
    `roll` spins the prop about that axis, in radians. A shell of panels all rolled
    identically reads as printed wallpaper; a random roll per prop reads as plating.
    
    Geometry, not decoration: it converts a direction into a rotation and knows nothing
    about art, which is why it belongs beside the sampler rather than in the dresser."""
def volume_anchor (volume, pos):
    """``(depth, anchor, radius)`` of the nearest primitive - the local containment
    sphere. Exposed because a tractor hold needs the anchor, not just the projection."""
def volume_anchor_count ():
    """Live tractor anchor objects. The reset-ledger probe."""
def volume_box (volume, name, x, y, z, hx, hy, hz):
    """Add an axis-aligned rectangular space. Half-extents, not widths."""
def volume_chamber (volume, name, x, y, z, radius):
    """Add one chamber to a volume (by object or by name)."""
def volume_clear ():
    """Drop every volume and stop every watcher. Called by reset_mission_state()."""
def volume_containment_tick (t=None):
    """One containment pass over every watched volume. Also directly callable."""
def volume_contains (volume, pos):
    """True if the position is inside any chamber or passage."""
def volume_count ():
    """Number of defined volumes. The reset-ledger probe."""
def volume_define (name, chambers=None, passages=None, boxes=None, solids=None, origin=None):
    """Create (or replace) a named volume.
    
    Declarative form - `chambers` maps a name to (x, y, z, radius), `passages` is a
    sequence of (a, b, radius) where a and b are chamber names or explicit points:
    
        volume_define("relic",
                      chambers={"hub": (0, 0, 0, 1200)},
                      passages=[("hub", "spine", 300)])
    
    `origin` PLACES the whole layout: every coordinate is treated as relative to it.
    That is what lets one authored layout be dropped at two different points in a
    system - without it a layout is welded to the absolute coordinates it was written
    at, and a second copy means editing every number. Radii and half-extents are
    sizes, not positions, so they are never shifted; a passage naming a chamber needs
    no shift either, since the chamber it names has already moved."""
def volume_depth (volume, pos):
    """Signed distance to the wall: NEGATIVE inside, positive outside.
    
    The number the graded response is built on - scrape near zero, govern the
    throttle further out, clamp as the backstop."""
def volume_engaged (volume):
    """The ids containment is currently applying to - the ships that are IN this relic.
    
    Also the answer to a question missions ask for their own reasons: is the crew inside
    the ruin yet? A quest that starts when they arrive, a door that closes behind them, an
    ambush that waits until they are committed - all of them want this set, and computing
    it from depth per tick would duplicate the latch the watcher already keeps.
    
    Empty for an unwatched volume, and for `engage="always"`, where the question does not
    apply because containment is not gated on having been inside."""
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
def volume_load (name, data, origin=None):
    """Define a volume from one parsed block - a MAST `metadata:` yaml section, or a
    mission yaml file.
    
    Takes the shape yaml actually parses to (lists, not tuples), so a relic can be
    authored declaratively rather than as a wall of calls::
    
        metadata: ``` yaml
        chambers:
            hub:   [0, 0, 0, 1200]
            spine: [4000, 0, 0, 900]
        passages:
            - [hub, spine, 300]
        ```
    
    then ``volume_load("relic", {"chambers": chambers, "passages": passages})`` - or
    pass the whole parsed mapping straight in.
    
    Two more keys, both optional::
    
        boxes:                             # axis-aligned, x y z then HALF-extents
            vault: [4000, 0, 0, 900, 400, 900]
        solids:                            # SUBTRACTED - pillars, spires, solid hubs
            - [sphere, 4000, 0, 0, 250]
            - [box, 0, 0, 0, 100, 800, 100]"""
def volume_names ():
    """Every defined volume name."""
def volume_nearest_inside (volume, pos, margin=0.0):
    """Closest point inside by at least `margin`; the position itself if already so."""
def volume_passage (volume, a, b, radius):
    """Join two chambers (or two points) with a capsule."""
def volume_path (volume, start, goal):
    """Chamber names from start to goal inclusive, or [] if unreachable."""
def volume_remove (name):
    """Drop ONE volume: stop its watcher, let go of anything it held, forget the geometry.
    
    `volume_clear()` drops every volume, which is right for a mission reset and wrong for a
    galaxy. An Open Universe cell is torn down while the next one is already being built,
    so clearing everything there would delete the relic the crew is standing in. Returns
    True if there was something to remove."""
def volume_solid (volume, kind, *args):
    """SUBTRACT a shape from the navigable space.
    
    Three forms - a pillar, a bar, a block::
    
        volume_solid(v, "sphere",  x, y, z, radius)
        volume_solid(v, "capsule", (ax, ay, az), (bx, by, bz), radius)
        volume_solid(v, "box",     x, y, z, hx, hy, hz)
    
    Union alone can only ADD space, so this is what buys a column in the middle of a
    chamber, a spire, or a torus with a genuinely solid hub."""
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
def volume_tier (volume, pos, scrape_band=120.0, radius=0.0):
    """Which response tier a position falls in. Pure - the testable seam.
    
    `scrape_band` defaults to 120u: two ticks of warp travel at the measured 60
    u/tick, so a glancing clip scrapes while a determined exit breaches.
    
    `radius` is the SHIP, not a point. A hull is a sphere of its `exclusion_radius`,
    and testing only its centre lets half the ship stand in the wall before anything
    reacts - 50 units of light cruiser against a 60-unit scrape band, so the hull is
    110 units through the plating at the moment the centre first counts as breaching.
    That is the difference between scraping a wall and visibly passing through it."""
def volume_unwatch (name):
    """Stop enforcing containment for a volume.
    
    Anything this watcher was HOLDING is let go first. A tractor hold is an anchor object
    plus a live engine connection, and neither belongs to the watcher's task - so dropping
    the task alone leaves a ship roped to an invisible post that nothing will ever release,
    which reads in play as a ship that cannot fly after the ruin around it is gone."""
def volume_watch (volume, agents=None, scrape_band=120.0, margin=0.0, govern=True, clamp=True, seconds=0, hold='tractor', speed_limit=None, block_jump=False, engage='entered'):
    """Start enforcing containment for a volume. Replaces any existing watch.
    
    ENGAGEMENT - who this applies to, which is not the same question as who is watched.
    
    A tier is a pure depth test, so a ship that has never been near the relic reads
    BREACH exactly like one that just punched through a wall: measured, a ship 80,000
    units away came back BREACH and, under the default agent set of every player, was
    tractored toward the relic. That is not containment, it is a fishing net.
    
    So a ship is contained ONCE IT HAS BEEN INSIDE, and released when it leaves the
    bounding sphere. Fly in through a mouth - a chamber or passage that reaches out past
    the hull - and you are inside the volume before you are deep in it, so the latch
    catches without a breach ever happening. Fly out and away and it lets go. A ship that
    never entered is never touched, which is what makes an entrance possible at all and
    what stops a relic in one corner of a system grabbing everything in it.
    
    `engage="always"` restores the old behaviour for a volume that IS the playfield.
    
    Args:
        volume: Volume or its name.
        agents: None for players+fighters (the default set), a CALLABLE returning a
            set - re-evaluated every tick, so arrivals and departures need no
            wiring - or a static set.
        scrape_band (float): how far past the wall a scrape becomes a breach.
        margin (float): how far inside the wall the clamp puts a breached ship.
        govern (bool): cap `playerThrottle` to impulse while breached.
        clamp (bool): project a breached ship back inside.
        seconds (int): tick interval; 0 = every tick, which is what containment
            wants - it is a handful of float ops per agent.
    
    Signals fire on tier CHANGE only, never per tick, each carrying
    ``{"volume": name, "id": agent_id, "depth": float}``:
        ``volume_scrape``    - entered the wall
        ``volume_breach``    - went past the scrape band
        ``volume_recovered`` - back inside
    
    Route the consequences: ``//shared/signal/volume_scrape`` for damage or scoring
    (server-once), ``//signal/volume_scrape`` only for per-console display."""
def volume_watch_count ():
    """Number of live watchers. The reset-ledger probe."""
def volume_watching (name):
    """True if a volume is currently enforced."""
class Volume(object):
    """A navigable space built from primitives, minus any solids carved out of it.
    
    Navigable: `chambers` (spheres), `passages` (capsules), `boxes` (axis-aligned).
    `solids` are SUBTRACTED - the pillar in the middle of the room."""
    def __init__ (self, name):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _endpoint (self, e):
        """Resolve a passage endpoint: a chamber name, or an explicit point."""
    def add_box (self, name, x, y, z, hx, hy, hz):
        """An axis-aligned rectangular space. Half-extents, so hx is HALF the width.
        
        A box reads as BUILT rather than eroded - a vault with flat walls and real
        corners, which spheres and capsules cannot express at all. Not rotatable:
        arbitrary orientation needs a quaternion in the SDF, and every relic so far
        wanted axis-aligned rooms."""
    def add_chamber (self, name, x, y, z, radius):
        ...
    def add_passage (self, a, b, radius):
        """Join two chambers by name, or two explicit points, with a capsule."""
    def add_solid (self, prim):
        """SUBTRACT a shape from the navigable space - a pillar, a spire, a solid hub.
        
        Union alone can only ever ADD space, so without this a chamber with a column
        in the middle has to be faked by routing capsules around where the column
        goes. Takes any primitive tuple; see `volume_solid` for the friendly form."""
    def bound (self):
        """Bounding sphere of the whole volume.
        
        Used to size a relic's nebula. NOT wired into `nearest` as an early-out - at
        tens of primitives the walk is already noise, and a stale claim that it was
        would be worse than none. If a volume ever reaches thousands, this is the hook."""
    def depth (self, pos):
        """Signed distance to the boundary. NEGATIVE inside, positive outside.
        
        An empty volume is all wall, reporting +inf rather than pretending everything
        is contained."""
    def named_primitives (self):
        """Every navigable primitive as `(name, prim)`.
        
        `primitives()` drops the names, which is right for sampling and wrong for
        dressing: a relic wants THIS hall plated and THAT cave left as rock, and the
        only handle an author has on a room is the name they gave it. A passage is
        named for the two rooms it joins, since it never had a name of its own."""
    def nearest (self, pos):
        """``(depth, anchor, rope)`` - signed depth plus a tractor hold target.
        
        Depth is the SDF of the whole volume: the union of the navigable primitives,
        with every solid subtracted. In SDF algebra, subtracting S is
        ``max(d_union, -d_S)`` - so a point inside a pillar reports positive (outside
        the navigable space), and a point near one correctly measures its distance to
        the pillar as its distance to the nearest wall.
        
        A point inside a solid is anchored AGAINST THE SOLID, not the room it sits in:
        the way out of a pillar is away from the pillar."""
    def nearest_inside (self, pos, margin=0.0):
        """The closest point that is inside by at least `margin`.
        
        Returns the position unchanged when it already satisfies that, so this is safe
        to call every tick. A HARD geometric projection, deliberately - not a
        proportional pull. `orbit.py` measured a proportional-only controller
        spiralling against real engine 1.3.5 rather than settling."""
    def neighbors (self, chamber):
        ...
    def path (self, start, goal):
        """Chamber names from `start` to `goal` inclusive, or [] if unreachable.
        
        Breadth-first: passages have no meaningful cost yet, and with a dozen
        chambers a weighted search would be ceremony."""
    def primitives (self):
        """Every NAVIGABLE primitive, uniformly tagged."""
class _Watcher(object):
    """class _Watcher"""
    def __init__ (self, volume, agents, scrape_band, margin, govern, clamp, hold, speed_limit, block_jump, engage='entered'):
        """Initialize self.  See help(type(self)) for accurate signature."""
