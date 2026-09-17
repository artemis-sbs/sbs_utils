from sbs_utils.tickdispatcher import DripQueue
from sbs_utils.vec import Vec3
def _asteroid_scatter_now (cluster_spawn_points, height, selectable=False):
    ...
def _mix32 (x):
    """A stable integer hash -- the point is that it DRAWS NOTHING.
    
    Per-object jitter has to come from a value the object already has, not from
    `random`. The sower draws every per-object value up front so a queued chunk carries
    no randomness of its own (see _nebula_plan); a draw down here would break that and
    shift every later spawn. `random_seed` is already per nebula, so hashing it gives
    variety for free and a sown cluster stays identical to an inline one."""
def _neb_icon_jitter (scaled, seed):
    """Nudge saturation and value, hold hue exactly.
    
    Hue is the thing that carries the name -- purple has to stay purple -- so it is not
    touched at all. Saturation and value are what make a cluster look like cloud rather
    than a stencil, which is what the old color_noise() was reaching for and never
    delivered: it ran once at import, so every purple nebula in a session shared one
    value and only the NEXT session looked different."""
def _nebula_chunk_now (specs, density, selectable):
    """Pure creation: the mirror of terrain_nebula_spawn with the draws removed."""
def _nebula_marker_spawn (x, y, z, name, color):
    """Spawn one nebula cluster marker and return its space object.
    
    Extracted from ``terrain_spawn_nebula_common`` so the cluster merge can place
    markers itself, once it knows which ones survive."""
def _nebula_markers_place (cluster_pos, cluster_color, name, merge_dist=15000):
    """Merge nebula clusters and place ONE marker per merged group.
    
    The merge is decided before anything is spawned, so a marker that would be
    merged away is never created.
    
    **Why it works this way.** The markers used to be spawned one per cluster and
    the redundant ones deleted immediately afterwards, in the same frame. The
    engine defers adding a new object (``Simulation::objectToAddList``), so an
    object freed before that add-pass runs can land in ``SuperContainer::allList``
    as a dangling pointer -- which the per-object slow tick then dereferences.
    That is the ObjectDataBlob crash-to-desktop. Never create and free a
    SpaceObject in one frame.
    
    A marker left over from an EARLIER frame is still folded in the old way,
    deletion included: it has been through a tick, so freeing it is the safe case.
    
    Args:
        cluster_pos (list[Vec3]): Cluster origins, in spawn order.
        cluster_color (list[str]): Each cluster's color display name.
        name (str): Marker display name.
        merge_dist (float, optional): Markers closer than this merge. Defaults to
            15 000."""
def _nebula_plan (points, cluster_color, rainbow, color_is_set, height, neb_size):
    """Draw every per-object value now, in the same order the inline spawn draws
    them -- so the caller's RNG stream advances exactly as it would have, and the
    sown cluster is identical to the inline one."""
def _nebula_scatter_now (points, height, cluster_color, neb_size, density, selectable, rainbow, color_is_set):
    ...
def _sowing ():
    ...
def _unit (seed, salt):
    """`seed` mixed with `salt`, as a float in [0, 1)."""
def art_key_for (ship_key):
    """The hull key to DRAW in place of `ship_key`. ART ONLY.
    
    The companion to :func:`art_faction_for`, for the OTHER way a hull gets chosen. Some
    callers do not look a ship up by faction at all - they name the key outright:
    
      * stations (``station_type``), and
      * fleet ladders, which list their hulls class by class so a wave keeps its shape.
    
    A faction map cannot help those, so they get a key map instead - ``ART_KEYS``, keyed by
    the STOCK key being replaced. Mapping per key also PRESERVES THE LADDER'S CHOICES: a
    battleship is replaced by a specific hull rather than by a random ship of some faction.
    
    Returns `ship_key` unchanged when unset, or when the replacement is not in the ship
    table - a half-written map should degrade to stock art, never to nothing spawning."""
def awaitable (func):
    ...
def closest_list (source: int | sbs_utils.agent.CloseData | sbs_utils.agent.SpawnData | sbs_utils.agent.Agent | sbs_utils.vec.Vec3, the_set, max_dist=None, filter_func=None) -> list[sbs_utils.agent.CloseData]:
    """Return all objects in a set within optional distance and filter criteria.
    
    Args:
        source (Agent | int | CloseData | SpawnData | Vec3): The reference
            agent ID, object, or position.
        the_set (set[int]): IDs of candidates to test.
        max_dist (float, optional): Maximum distance to include. Defaults to
            None (no limit).
        filter_func (Callable, optional): Extra predicate ``f(agent) -> bool``
            applied to each candidate. Defaults to None.
    
    Returns:
        list[CloseData]: All qualifying candidates with their distances."""
def color_noise (r_min, r_max, g_min, g_max, b_min, b_max, a_min=255, a_max=255):
    ...
def npc_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a non-player (NPC) ship into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new NPC."""
def plain_asteroid_keys ():
    """Return all plain asteroid keys, excluding crystal asteroids (cached).
    
    Returns:
        list[str]: Plain asteroid type keys."""
def prefab_spawn (label, data=None, OFFSET_X=None, OFFSET_Y=None, OFFSET_Z=None):
    """Spawn a prefab label as an independent task and return it.
    
    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.
    
    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).
    
    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid."""
def random_terran (face=None, civilian=None):
    """Create a random terran face.
    
    Args:
        face (int | None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian (boolean | None): The force this to be a civilian=True, For non-civilian=False or None= random
    
    Returns:
        (str):   A Face string"""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Reaches the server console, for the same reason :func:`add_role` does - and it has
    to be the same set, or a console that could gain a role could never lose it.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def scatter_ring (ca, cr, x, y, z, outer_r, inner_r=0, start=0.0, end=90.0, random=False) -> collections.abc.Generator:
    """Calculate the points on rings with each ring has same count.
    
    Args:
        ca (int): The number of points to generate on each ring
        cr (int): The number of rings
        x (float): The start point/origin
        y (float): The start point/origin
        z (float): The start point/origin
        outer_r (float): The radius
        inner_r (float, optional): The inner radius. Default is 0.
        start (float): degrees start angle. Default is 0.
        end (float): degrees start angle. Default is 90.0.
        random (bool): When True, points will be randomly placed. When False, points will be evenly placed.
    
    Returns:
        points (Generator): A generator of Vec3"""
def set_face (ship_id, face):
    """Sets a face string for a specified ID.
    
    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string"""
def terrain_asteroid_clusters (terrain_value, center=None, selectable=False, points=None):
    """Scatter random asteroid clusters across the map.
    
    Args:
        terrain_value (int): 0–4 scale controlling cluster count and density.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False.
        points (list[Vec3], optional): Explicit cluster origins instead of
            random positions. Defaults to None.
    
    Returns:
        list[Vec3]: The cluster centre positions used."""
def terrain_field_plan_keyed (key, cell, x_min, z_min, x_max, z_max, nebula_chance, asteroid_chance, exclude=None, exclude_radius=0, y_min=-375, y_max=375):
    """Decide what the keyed terrain field contains, without spawning.
    
    Walks the global lattice (``scatter.grid_keyed``) and, per cell, uses
    ``scatter.cell_roll`` to pick nebula / asteroid / empty. Pure and
    deterministic: the same ``(key, cell)`` yields the same plan for any cell, so
    a smaller region is the centered subset of a larger one. ``exclude`` points
    (e.g. stations) within ``exclude_radius`` are skipped.
    
    Args:
        key (int): World/map seed (concrete; caller maps "random" to a random int).
        cell (float): Lattice cell size.
        x_min, z_min, x_max, z_max (float): World bounds.
        nebula_chance, asteroid_chance (float): Per-cell probabilities (0..1).
        exclude (list, optional): Points/objects to keep clear of.
        exclude_radius (float): Clearance radius around ``exclude``.
        y_min, y_max (float): Height range for the points.
    
    Returns:
        list[tuple[Vec3, str]]: ``(position, "nebula"|"asteroid")`` entries."""
def terrain_nebula_color (cluster_color):
    ...
def terrain_nebula_icon_color (color, peak=204, seed=None):
    """The radar tint for a nebula, computed FROM that nebula's own emission.
    
    A nebula used to carry two unrelated descriptions of itself: a hand-written
    "radar_color_override" hex for the 2D icon, and the emission/scattering/absorption
    levers the engine actually draws the cloud with. Nothing tied them together, so
    retuning either side desynced them silently -- which is how "red" ended up with a
    magenta icon over a red cloud (the icon line survived 0ae545ea byte-identical while
    the cloud was rewritten), and how every icon ended up ~3x too dark to read.
    
    Deriving the icon here removes the second copy: there is one color, and the icon is
    a view of it.
    
    EMISSION ONLY, and that is not a guess. Running the engine shader's own raymarch
    (data/graphics/shader-emissivenebula.ps:152-180) over each entry shows the rendered
    hue tracks NORMALIZED EMISSION almost exactly -- purple [0.70,0.00,1.00] renders
    [0.69,0.00,1.00], red [1.00,0.30,0.10] renders [1.00,0.29,0.10]. Absorption and
    scattering largely cancel: they form `ext`, which appears both inside `trans` and as
    the divisor of the integral, so they set how BRIGHT and how thick the cloud is far
    more than what color it is.
    
    The lit term (`light * phase * (1-absorption) * scattering * p`) is deliberately not
    used. It swings the hue by 0.3-0.8 per channel across plausible light intensities and
    goes NEGATIVE wherever absorption exceeds 1.0 (red absorbs green/blue at 1.5), so it
    is not a stable thing to name a color from.
    
    Args:
        color (dict | str): a _neb_colors entry, a color name, or any dict carrying
            emission_red/green/blue.
        peak (int, optional): value the largest channel is scaled to. Defaults to
            ``NEB_ICON_PEAK``.
        seed (int, optional): the nebula's own ``random_seed``. Given one, the HUE is
            kept exactly and saturation/value are nudged per object, so a cluster reads
            as a drift of one color rather than a block of identical dots. Defaults to
            None -- the canonical, unjittered color of that entry.
    
    Returns:
        str: ``"#rrggbb"``."""
def terrain_nebula_spawn (v2, height, cluster_color, diameter, density, selectable):
    ...
def terrain_random_point_box (all_points, left, top, front, right, bottom, back, inside=True, count=1):
    """wraps a set of points in a generator returning unique points inside (or outside) a box
    
    
    Args:
        all_points (_type_): The source set of points
        left (_type_): left (x)
        top (_type_): top (y)
        front (_type_): front (z)
        right (_type_): right (x)
        bottom (_type_): bottom (y)
        back (_type_): back (z)
        inside (bool, optional): Within the box or out side it. Defaults to True.
        count (int, optional): Number of points each iteration. Defaults to True.
    
    Yields:
        Vec3 | list[Vec3]: A random point"""
def terrain_remove_points_near (all_points, test_points, radius):
    """Return only the points that are outside a given radius of every test point.
    
    Filters ``all_points`` by removing any point within ``radius`` of at least
    one entry in ``test_points``. Useful for clearing spawn candidates around
    existing objects.
    
    Args:
        all_points (list[Vec3]): Candidate spawn positions.
        test_points (list[Vec3 | Agent | int]): Exclusion reference points.
            Non-``Vec3`` items are resolved to their space-object position.
        radius (float): Exclusion radius in simulation units.
    
    Returns:
        list[Vec3]: Subset of ``all_points`` farther than ``radius`` from every
            test point."""
def terrain_set_nebula_object_size (size=2500):
    """OPT-IN (experimental): raise the per-object nebula size so clusters spawn
    FEWER, BIGGER objects.
    
    A cluster's object count is ``cluster_size // NEB_SIZE_LARGE``, so raising this
    makes the existing generator produce fewer/bigger objects (a 10000 cluster:
    ~36 -> ~16 at 2500 = ~55% less overdraw) while keeping all its scatter/drift/
    jitter - no re-tuning. Default behavior is UNCHANGED unless a mission calls this.
    
    Pairs with the projection depth shader fix (NEB_DEPTH_PROJECTION in
    shader-emissivenebula.ps): sizes above ~3000 need it to avoid the "sphere at
    origin" artifact. 2500 is clean even without it. Call once before spawning
    nebulae; pass 1500 to restore the default."""
def terrain_setup_nebula (nebula, diameter=4000, density_coef=1.0, color='yellow', seed=None):
    """Apply visual and physical properties to an existing nebula space object.
    
    Args:
        nebula (SpaceObject | Agent): The nebula to configure.
        diameter (int, optional): Nebula diameter (capped at ``NEB_MAX_SIZE``).
            Defaults to 4000.
        density_coef (float, optional): Visual nebula density multiplier (3D
            view). Defaults to 1.0.
        color (str | dict, optional): Colour name or a full colour dict.
            Defaults to ``"yellow"``.
        seed (int, optional): The shader's ``random_seed``. Defaults to None --
            drawn here, as always. The sower passes one in because it draws every
            per-object value up front, so a queued chunk contains no randomness."""
def terrain_sow_begin (over=6, focus=None):
    """Start sowing: terrain fill queued and spread over ``over`` sim-seconds.
    
    What this guarantees: each queued call creates exactly what it would have
    created inline -- it carries the RNG state it was queued under, so deferring a
    cluster never changes that cluster.
    
    NEBULA is identical either way, cluster for cluster: its whole plan (colour,
    height, size, shader seed per object) is drawn at queue time in the same order
    the inline spawn draws it, so the caller's stream advances exactly as it would
    have. The same is true of ``terrain_spawn_field_keyed``, which already isolates
    its RNG per cell.
    
    ASTEROID clusters do shift the stream: their spawn loop's randomness is
    interleaved with reads of the spawned object (a rock's exclusion radius sets
    where its satellites go), so it cannot be drawn up front the same way. Deferring
    it moves that consumption, which changes what a LATER cluster draws. Cluster
    centres come from one up-front scatter, so the macro layout is unchanged; what
    differs is rock counts and scales per cluster. Across seeds this is a different
    sample of the same distribution, not a thinner field (measured: +2% net, both
    directions). The result is fully deterministic -- the same seed sows the same
    field every time -- just not the same field as not sowing. Since sowing is
    opt-in per map, a map is only ever played one way.
    
    Args:
        over (float, optional): Seconds to spread the work across. Defaults to 6.
        focus (Vec3 | tuple, optional): Work runs nearest-first from here, so the
            space around it is correct first. Defaults to the map origin.
    
    Returns:
        DripQueue: the queue, for callers that want to inspect it."""
def terrain_sow_complete ():
    """Promise that resolves once the sown terrain has all been created.
    
    Example:
        terrain_sow_begin(over=6)
        terrain_asteroid_clusters(terrain_value)
        await terrain_sow_complete()"""
def terrain_sow_end ():
    """Stop queueing; terrain_* calls spawn inline again. Anything already queued
    keeps draining -- use ``terrain_sow_flush()`` to force it out now."""
def terrain_sow_flush ():
    """Run all queued terrain work immediately. Returns how many units ran.
    
    For code that must see the whole field right now -- a test, a headless
    conformance run, or a query that cannot wait for the drip."""
def terrain_sow_pending ():
    """How many queued units of terrain work are still to run."""
def terrain_sow_reset ():
    """Drop queued work and leave sowing off (mission reset)."""
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
def terrain_spawn_asteroid_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, selectable=False, is_tiled=False):
    """Spawn asteroids scattered inside a box volume; density is per 1000 units.
    
    Args:
        x (float): Box origin X.
        y (float): Box origin Y (unused for placement; passed through).
        z (float): Box origin Z.
        size_x (int, optional): Box width along X. Defaults to 10000.
        size_z (int | None, optional): Box depth along Z. Defaults to
            ``size_x``.
        density_scale (float, optional): Multiplier for asteroid count.
            Defaults to 1.0.
        density (int, optional): Base density per 1000 units. Defaults to 1.
        height (int, optional): Box height (Y spread). Defaults to 1000.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False.
        is_tiled (bool, optional): Adjust origin for map-editor tile coordinates.
            Defaults to False."""
def terrain_spawn_asteroid_points (x, y, z, points, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """Spawn asteroids along a polyline defined by a list of 2D points.
    
    Offsets each point by ``(x, z)`` and scatters asteroids along the
    resulting line segments.
    
    Args:
        x (float): X offset applied to all points.
        y (float): Unused.
        z (float): Z offset applied to all points.
        points (list[tuple]): 2D ``(x, z)`` vertices defining the polyline.
        radius (int, optional): Unused. Defaults to 10000.
        density_scale (float, optional): Multiplier for per-segment density.
            Defaults to 1.0.
        density (int, optional): Base density. Defaults to 1.
        height (int, optional): Y spread of each asteroid. Defaults to 1000.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False."""
def terrain_spawn_asteroid_scatter (cluster_spawn_points, height, selectable=False):
    """Spawn a randomised asteroid (with possible satellite cluster) at each given point.
    
    Every asteroid path in this module funnels through here, so this is where
    sowing intercepts: inside a sow scope the whole cluster is queued as one unit
    of work and created later, identically. See ``terrain_sow_begin``.
    
    Args:
        cluster_spawn_points (Iterable[Vec3]): Spawn positions.
        height (int): Controls Y scatter range around each point.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False."""
def terrain_spawn_asteroid_sphere (x, y, z, radius=10000, density_scale=1.0, density=1, height=1000, selectable=False):
    """Spawn asteroids scattered inside a sphere volume; density is per 1000 units.
    
    Args:
        x (float): Sphere centre X.
        y (float): Sphere centre Y.
        z (float): Sphere centre Z.
        radius (int, optional): Sphere radius. Defaults to 10000.
        density_scale (float, optional): Multiplier for asteroid count.
            Defaults to 1.0.
        density (int, optional): Base density per 1000 units. Defaults to 1.
        height (int, optional): Y spread of each asteroid. Defaults to 1000.
        selectable (bool, optional): Make asteroids selectable on 2D radar.
            Defaults to False."""
def terrain_spawn_black_hole (x, y, z, gravity_radius=1500, gravity_strength=1.0, turbulence_strength=1.0, collision_damage=200):
    """Spawn a black hole (maelstrom) terrain object at the given position.
    
    Args:
        x (float): X position.
        y (float): Y position.
        z (float): Z position.
        gravity_radius (int, optional): Radius within which objects are pulled
            in. Defaults to 1500.
        gravity_strength (float, optional): Pull speed multiplier. Defaults to
            1.0.
        turbulence_strength (float, optional): Turbulence intensity. Defaults
            to 1.0.
        collision_damage (int, optional): Damage on entry into the event
            horizon. Defaults to 200.
    
    Returns:
        SpaceObject: The spawned black hole object."""
def terrain_spawn_black_holes (lethal_value, center=None, points=None):
    """Spawn multiple black holes based on the game's lethal terrain value.
    
    Args:
        lethal_value (int): Number of black holes to spawn.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        points (list[Vec3], optional): Explicit spawn positions. Defaults to
            None (random within 75 000 units of centre).
    
    Returns:
        list[SpaceObject]: The spawned black hole objects."""
def terrain_spawn_field_keyed (key, cell, x_min, z_min, x_max, z_max, terrain_value, nebula_chance, asteroid_chance, y_min=-375, y_max=375, exclude=None, exclude_radius=0, selectable=False, marker=True):
    """Spawn a position-keyed asteroid / nebula field over the given bounds.
    
    The field is a pure function of ``(key, position)``: the same seed produces
    the same field, and a small map is the centered subset of a large one. Each
    cluster's contents come from a per-cell RNG (the global RNG is re-seeded per
    cell from the cell's coords and restored afterward), so the existing
    cluster-spawn code is reused and stays deterministic. ``terrain_value``
    (0-4) controls cluster richness; ``nebula_chance`` / ``asteroid_chance`` are
    per-cell probabilities.
    
    Returns:
        list[tuple[Vec3, str]]: the plan that was spawned."""
def terrain_spawn_monsters (monster_value, center=None, points=None):
    """Spawn monster-bestiary prefabs based on the monster difficulty value.
    
    Each monster is rolled from ``monster_species_weights`` (Typhon-dominant), so
    the field is a mix of hostile, tame and helpful creatures. Reassign that list
    to change the mix.
    
    Args:
        monster_value (int): Number of monsters to spawn.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        points (list[Vec3], optional): Explicit spawn positions. Defaults to
            None (random within 75 000 units of centre).
    
    Returns:
        list[Vec3]: The spawn positions used."""
def terrain_spawn_nebula_box (x, y, z, size_x=10000, size_z=None, density_scale=1.0, density=1, height=1000, cluster_color=None, selectable=False, marker=True, name=''):
    """Spawn nebulae scattered inside a box volume.
    
    Delegates to ``terrain_spawn_nebula_common`` with box geometry.
    
    Args:
        x (float): Box origin X.
        y (float): Unused.
        z (float): Box origin Z.
        size_x (int, optional): Box width along X. Defaults to 10000.
        size_z (int | None, optional): Box depth; defaults to ``size_x``.
        density_scale (float, optional): Nebula count multiplier. Defaults to
            1.0.
        density (int, optional): Visual density per nebula (3D view). Defaults
            to 1.
        height (int, optional): Y spread. Defaults to 1000.
        cluster_color (str | int | dict | None, optional): Colour override;
            see ``terrain_spawn_nebula_common``. Defaults to None (random).
        selectable (bool, optional): Make nebulae selectable. Defaults to
            False.
        marker (bool, optional): Place a radar marker. Defaults to True.
        name (str, optional): Marker name. Defaults to ``""``.
    
    Returns:
        list[SpaceObject]: Spawned nebula objects."""
def terrain_spawn_nebula_clusters (terrain_value, center=None, selectable=False, points=None, marker=True, name=''):
    """Scatter random nebula clusters across the map and merge nearby markers.
    
    After spawning, neighbouring ``nebula_marker`` objects within 15 000 units
    are merged into a single marker that represents the combined cluster.
    
    Args:
        terrain_value (int): 0–4 scale controlling cluster count and density.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        selectable (bool, optional): Make nebulae selectable on 2D radar.
            Defaults to False.
        points (list[Vec3], optional): Explicit cluster origins. Defaults to
            None (random positions).
        marker (bool, optional): Place a radar marker at each cluster origin.
            Defaults to True.
        name (str, optional): Name assigned to each radar marker. Defaults to
            ``""``.
    
    Returns:
        list[SpaceObject]: All spawned nebula objects."""
def terrain_spawn_nebula_common (x, y, z, size_x=10000, size_z=None, radius=None, density_scale=1.0, density=1, height=1000, cluster_color=None, selectable=False, marker=True, name='', color_out=None):
    """Spawn a nebula cluster using either box or sphere geometry.
    
    Shared implementation called by ``terrain_spawn_nebula_box`` and
    ``terrain_spawn_nebula_sphere``. Distributes nebulae with noise-based
    scatter and optionally places a radar marker at the cluster centre.
    
    Args:
        x (float): Centre X position.
        y (float): Centre Y position.
        z (float): Centre Z position.
        size_x (int, optional): Box width or sphere radius X. Defaults to
            10000.
        size_z (int | None, optional): Box depth; if None uses ``size_x``.
            Defaults to None.
        radius (float | None, optional): Override for sphere scatter radius.
            Defaults to None (uses box geometry).
        density_scale (float, optional): Multiplier for cluster density.
            Defaults to 1.0.
        density (float, optional): Visual density of each nebula (3D view).
            Defaults to 1.
        height (int, optional): Vertical spread in simulation units. Defaults
            to 1000.
        cluster_color (str | int | dict | None, optional): Nebula colour — a
            colour name string (e.g. ``"purple"``), an integer index into the
            colour table, a full colour dict, or ``None`` for a random colour.
            Defaults to None.
        selectable (bool, optional): Make nebulae selectable on 2D radar.
            Defaults to False.
        marker (bool, optional): Place a radar marker at the cluster origin.
            Defaults to True.
        name (str, optional): Name assigned to the radar marker. Defaults to
            ``""``.
    
    Returns:
        list[SpaceObject]: Spawned nebula objects."""
def terrain_spawn_nebula_scatter (cluster_spawn_points, height, cluster_color=None, diameter=1500, density=1.0, selectable=False):
    """Spawn a nebula at each given point with randomised Y scatter.
    
    Args:
        cluster_spawn_points (Iterable[Vec3]): Spawn positions.
        height (int): Controls Y scatter range around each point.
        cluster_color (str | int | dict | None, optional): Colour name, index
            (0=purple, 1=red, 2=blue, 3=yellow), dict, or ``None`` for random.
            Defaults to None.
        diameter (int, optional): Max nebula diameter. Defaults to
            ``NEB_MAX_SIZE``.
        density (float, optional): Visual nebula density (3D view). Defaults
            to 1.0.
        selectable (bool, optional): Make nebulae selectable on 2D radar.
            Defaults to False.
    
    Returns:
        list[SpaceObject]: The spawned nebula objects."""
def terrain_spawn_nebula_sphere (x, y, z, radius=1500, density_scale=1.0, density=1.0, height=1000, cluster_color=None, selectable=False, marker=True, name='', color_out=None):
    """Spawn nebulae scattered inside a sphere volume.
    
    Delegates to ``terrain_spawn_nebula_common`` with sphere geometry.
    
    Args:
        x (float): Sphere centre X.
        y (float): Sphere centre Y.
        z (float): Sphere centre Z.
        radius (int, optional): Sphere radius. Defaults to ``NEB_MAX_SIZE``.
        density_scale (float, optional): Nebula count multiplier. Defaults to
            1.0.
        density (float, optional): Visual density per nebula. Defaults to 1.0.
        height (int, optional): Y spread. Defaults to 1000.
        cluster_color (str | int | dict | None, optional): Colour override;
            see ``terrain_spawn_nebula_common``. Defaults to None (random).
        selectable (bool, optional): Make nebulae selectable. Defaults to
            False.
        marker (bool, optional): Place a radar marker. Defaults to True.
        name (str, optional): Marker name. Defaults to ``""``.
    
    Returns:
        list[SpaceObject]: Spawned nebula objects."""
def terrain_spawn_stations (DIFFICULTY, lethal_value, x_min=-32500, x_max=32500, center=None, min_num=0, points=None):
    """Spawn starbases weighted by difficulty and optionally surround them with minefields.
    
    Args:
        DIFFICULTY (int): Game difficulty (affects station count and type mix).
        lethal_value (int): Lethal terrain level; ``> 0`` wraps minefields
            around each station.
        x_min (int, optional): Minimum X spawn bound. Defaults to -32500.
        x_max (int, optional): Maximum X spawn bound. Defaults to 32500.
        center (Vec3, optional): Map centre. Defaults to ``(0, 0, 0)``.
        min_num (int, optional): Minimum station count. Defaults to 0.
        points (list[Vec3], optional): Explicit spawn positions. If provided,
            stations are sampled from this list. Defaults to None.
    
    Returns:
        list[SpaceObject]: The spawned station objects."""
def terrain_to_value (dropdown_select, default=0):
    """Convert a terrain density string to an integer level (0–4).
    
    Args:
        dropdown_select (str): Density string: ``"few"`` → 1, ``"some"`` → 2,
            ``"lots"`` → 3, ``"max"``/``"many"`` → 4.
        default (int, optional): Value returned for unrecognised strings.
            Defaults to 0.
    
    Returns:
        int: Terrain density level 0–4."""
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
