from sbs_utils.mast.mast_node import MastDataObject
def _coords3 (value):
    """Parse `x, y, z` (comma or space separated) into [x, y, z] floats, or None."""
def _role_csv (record):
    """`side, roles` (side first, so npc_spawn reads it as the side); side defaults to `#`
    (no side, for terrain)."""
def amd_coords (s, n=2):
    """'6, 4' -> [6, 4] (the first `n` signed-integer tokens)."""
def amd_landmark_data (text):
    """Parse one landmark fence into a data dict."""
def amd_landmark_facts ():
    """amd_parse_facts handler for landmark fences: kind/side/roles/art/behavior (text),
    loc (3 floats), system (2 ints). Unknown labels return None (chain / default coercion)."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000028640FEBF60>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def landmark_key_role (key):
    """The role marking the object spawned for AMD landmark ``key``.
    
    A role, because role sets are the only O(1) keyed lookup and they self-clean when the
    object is deleted, so a landmark that is destroyed can be re-placed by re-running the
    section with no bookkeeping."""
def landmark_object (key):
    """The live object already spawned for landmark ``key``, or None."""
def landmark_pos (record):
    """Resolve a landmark's world [x, y, z]: explicit Loc; else the injected placer over its
    System (offset by Loc if both); else the origin."""
def landmark_record (key):
    """A registered landmark record by key, or None."""
def landmark_set_placer (fn):
    """Set the position placer for landmarks that name a System but no Loc:
    fn(system, record) -> [x, y, z]. A single-system mission needs no placer."""
def landmark_spawn (record):
    """Spawn one landmark; returns the spawned object (None if it has no Art, or an unknown
    kind maps to no spawner). Kind picks npc_spawn vs terrain_spawn + a behavior default.
    
    Idempotent on the record's ``key``: a landmark already placed is returned as-is, so
    re-running a section (a map body that runs twice, a re-emitted setup signal) does not
    litter the map with duplicates at the same coordinates. Because the check is against
    the live world rather than a did-I-run flag, a landmark that was destroyed or cleared
    IS re-placed - which is what makes a deliberate reset work."""
def landmarks_from_section (section):
    """Landmark records (MastDataObject) from a section node's children (empty if None)."""
def landmarks_register (section):
    """Remember every landmark record in ``section`` by key, without spawning any.
    
    Separate from ``landmarks_spawn`` on purpose: a mission places most of its landmarks
    at setup, but a story beat places one on cue, and both need the same record."""
def landmarks_registry_clear ():
    """Drop the declared-record registry - the per-mission reset."""
def landmarks_spawn (section):
    """Spawn every landmark in a section; returns the list of spawned objects (skips artless).
    Convenience over landmarks_from_section + landmark_spawn."""
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
