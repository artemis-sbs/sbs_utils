from sbs_utils.vec import Vec3
def _plan_points (count, start, end=None, radius=0, random_range=0):
    """Generate ``count`` Cosmos-space points (``start``/``end`` already in Cosmos).
    
    end given -> along the line; else radius>0 -> sphere cloud; else -> all at start.
    Then apply isotropic ``random_range`` jitter. Deterministic given the RNG state,
    so wrap with :func:`_with_seed` for reproducibility."""
def _to_cosmos (start, end):
    """Convert (x,y,z)-or-Vec3 ``start``/``end`` from 2.8 to Cosmos coords."""
def _with_seed (seed, fn):
    """Run ``fn`` with the global RNG seeded to ``seed`` (state restored after).
    
    Seeds the planning *and* the spawner's own internal randomness (y-scatter, type
    choice, etc.), then restores so other code is undisturbed. ``seed=None`` -> no-op."""
def create_asteroids (count, start, end=None, radius=0, random_range=0, seed=None, height=1000, selectable=False):
    """Spawn ``count`` asteroids (2.8 ``create type="asteroids"``). See
    :func:`create_nebulas` for the shared argument meanings."""
def create_mines (count, start, end=None, radius=0, random_range=0, seed=None, damage=5, blast_radius=1000):
    """Spawn ``count`` mines (2.8 ``create type="mines"``).
    
    Cosmos has no bulk-mine helper, so this places each mine with ``terrain_spawn``
    and sets ``damage_done`` / ``blast_radius`` on its data_set."""
def create_nebulas (count, start, end=None, radius=0, random_range=0, seed=None, neb_type=1, height=1000, selectable=False):
    """Spawn ``count`` nebula clusters (2.8 ``create type="nebulas"``).
    
    Args:
        count (int): number of clusters.
        start (Vec3 | tuple): origin in 2.8 coords.
        end (Vec3 | tuple, optional): if given, distribute start->end (line mode).
        radius (float, optional): sphere-cloud radius when ``end`` is None.
        random_range (float, optional): isotropic per-cluster jitter.
        seed (int, optional): reproducible placement (2.8 randomSeed).
        neb_type (int, optional): 2.8 nebType 1..3 -> colour.
        height (int, optional): vertical scatter passed to the spawner.
        selectable (bool, optional): selectable on 2D radar.
    
    Returns:
        list: the spawned nebula objects."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
def set_nebula_opaque_all (opaque):
    """2.8 global ``nebulaIsOpaque`` (a nameless set_object_property) -> set every nebula's
    throttle limit. Non-zero (opaque) keeps the Cosmos default limit (2.0, which slows
    ships); 0 = no limit. Returns the number of nebulae updated."""
def set_skybox_index (index):
    """2.8 ``set_skybox_index`` (SB00..SB29) -> schedule a Cosmos skybox.
    
    Cosmos has no SB## skyboxes; map the 2.8 index across the skyboxes the LM
    ``basic_random_skybox`` addon registers (``@media/skybox/*``), so each 2.8 index picks a
    stable Cosmos skybox. A negative / non-integer index schedules a random skybox. Returns
    the scheduled skybox label, or ``None`` when a random one was scheduled."""
