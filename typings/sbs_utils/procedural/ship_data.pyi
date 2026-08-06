def _tag_mod_entries (entries, mod):
    """Stamp every entry (in place) with its source mod so spawns can post-process it."""
def add_ship_data (entry, mod=None, prepend=True):
    """Add a single entry to the in-memory ship data.
    
    Inserts ``entry`` into the ``#ship-list`` so it is returned by
    :func:`get_ship_data`, :func:`get_ship_index`, :func:`get_ship_data_for`,
    :func:`filter_ship_data_by_side`, and the ``*_keys`` helpers -- letting a
    script register a ship/terrain/pickup type at runtime without editing
    ``shipData`` or shipping an ``extraShipData.json``.
    
    The entry is **prepended** by default, matching how ``extraShipData.json`` is
    merged (script data ahead of built-in data). The derived caches
    (``ship_index`` and every ``*_keys`` cache) are cleared so the new entry shows
    up on the next lookup; the loaded ``ship_data_cache`` itself is preserved.
    
    Args:
        entry (dict): A ship data dict. Must include a ``"key"`` (used to index
            it); typically also ``"name"``, ``"side"``, ``"roles"``, and
            ``"artfileroot"``.
        mod (str, optional): Name of the mod/addon this entry comes from; stamped on
            the entry as ``#mod`` so the low-level spawn post-processes it (see
            :func:`mod_ship_data_process`). Defaults to None (untagged).
        prepend (bool, optional): Insert at the front of the list (script
            priority) when ``True`` (default); append to the end when ``False``.
    
    Returns:
        dict | None: The updated ship data cache, or ``None`` if ship data could
            not be loaded."""
def alien_keys ():
    """Return all pickup keys containing ``"alien"`` (cached).
    
    Returns:
        list[str]: Alien pickup type keys."""
def arvonian_ship_keys ():
    """Return all Arvonian ship keys (cached).
    
    Returns:
        list[str]: Arvonian ship type keys."""
def arvonian_starbase_keys ():
    """Return all Arvonian starbase keys (cached).
    
    Returns:
        list[str]: Arvonian starbase type keys."""
def asteroid_keys ():
    """Return all asteroid ship keys from the ship data (cached).
    
    Returns:
        list[str]: Asteroid type keys."""
def container_keys ():
    """Return all pickup keys containing ``"container"`` (cached).
    
    Returns:
        list[str]: Container pickup type keys."""
def crystal_asteroid_keys ():
    """Return all crystal asteroid keys, excluding plain asteroids (cached).
    
    Returns:
        list[str]: Crystal asteroid type keys."""
def danger_keys ():
    """Return all pickup keys containing ``"danger"`` (cached).
    
    Returns:
        list[str]: Danger pickup type keys."""
def filter_ship_data_by_side (test_ship_key, sides, role=None, ret_key_only=False):
    """Return ship data entries matching a key substring, side filter, and optional role.
    
    Args:
        test_ship_key (str | None): Substring that must appear in the ship key,
            or ``None`` to match all keys.
        sides (str): Comma-separated side names to include (case-insensitive).
        role (str, optional): Single role that must be in the ship's role list.
            Defaults to None (no role filter).
        ret_key_only (bool, optional): Return a list of key strings instead of
            full data dicts. Defaults to False.
    
    Returns:
        list[str | dict]: Matching ship keys or data entries."""
def get_artemis_data_dir ():
    """Get the path to the Artemis Cosmos data directory.
    
    Returns:
        str: The data folder path (executable directory + "/data")."""
def get_mission_dir ():
    """Get the directory of the current mission.
    
    Returns:
        str: The script directory path."""
def get_mod (key_or_entry):
    """Return the source mod of a ship data entry, or ``None`` if it is engine-known.
    
    Exposed to MAST as ``ship_data_get_mod`` (the ``ship_data_`` prelude prefix); named
    ``get_mod`` here so it doesn't double-prefix to ``ship_data_ship_data_get_mod``.
    
    Args:
        key_or_entry (str | dict): A ship key, or a ship data entry dict.
    
    Returns:
        str | None: The mod name stamped at merge time, or ``None`` for built-in data."""
def get_mod_dir (mod):
    """Get the directory path for a mission module.
    
    Args:
        mod (str): The module/mission name.
    
    Returns:
        str: The full directory path for the module."""
def get_ship_data ():
    """Load and cache the full ship data, merging ``extraShipData.json`` if present.
    
    Results are cached after the first call. The mission-directory
    ``extraShipData.json`` is prepended to the ``#ship-list`` so mission ships
    take priority over built-in data.
    
    Returns:
        dict: The merged ship data dictionary."""
def get_ship_data_for (ship_key):
    """Return the full ship data entry for a given key.
    
    Args:
        ship_key (str): The ship type key.
    
    Returns:
        dict | None: Ship data dict, or ``None`` if not found."""
def get_ship_index ():
    """Return ship data indexed by ship key for fast O(1) lookup.
    
    Returns:
        dict[str, dict]: Mapping of ship key → ship data entry."""
def get_ship_name (ship_key):
    """Return the display name of a ship type by key.
    
    Args:
        ship_key (str): The ship type key.
    
    Returns:
        str | None: Ship display name, or ``None`` if the key is not found."""
def kralien_ship_keys ():
    """Return all Kralien ship keys (cached).
    
    Returns:
        list[str]: Kralien ship type keys."""
def kralien_starbase_keys ():
    """Return all Kralien starbase keys (cached).
    
    Returns:
        list[str]: Kralien starbase type keys."""
def load_data (file):
    """Load a data file as YAML or JSON, dispatching on the extension.
    
    ``.yaml``/``.yml`` are parsed as YAML; ``.json`` as JSON (comment- and
    trailing-comma-tolerant). When ``file`` has no recognised extension it is
    treated as a BASE path and the ``.yaml``, ``.yml`` then ``.json`` siblings are
    tried in turn -- so a caller can pass ``"shipData"`` (no extension) and get
    whichever form is present, YAML preferred.
    
    Args:
        file (str): Path to the data file, with or without a
            ``.yaml``/``.yml``/``.json`` extension.
    
    Returns:
        dict | list | None: The parsed data, or ``None`` if nothing loaded."""
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
def merge_mod_ship_data (mod, file=None):
    """Merge a mod folder's extra ship data (YAML or JSON) into the ship data cache.
    
    Args:
        mod (str): Mod directory name (resolved via ``get_mod_dir``).
        file (str, optional): The data file within the mod folder. Defaults to
            the base name ``"extraShipData"``, which loads ``extraShipData.yaml``
            or ``extraShipData.json`` (YAML preferred). Pass a name WITH a
            ``.yaml``/``.yml``/``.json`` extension to force a specific format.
    
    Returns:
        dict: The updated ship data cache."""
def merge_mod_ship_yaml (content, mod=None):
    """Merge ship data supplied as a YAML/JSON string into the ship data cache.
    
    Companion to :func:`sbs_utils.procedural.media.media_read_relative_file`, which
    returns a data file's CONTENTS relative to the current addon -- working whether
    the addon is a loose folder (dev) or a packaged ``.mastlib`` zip, where a plain
    filesystem path can't reach the file. So an addon can ship its own ship/terrain
    data next to its prefabs and load it in one line:
    
        merge_mod_ship_yaml(media_read_relative_file("shipData_monsters.yaml"), "MyMod")
    
    The parsed ``#ship-list`` is **prepended** (addon data ahead of built-in). Each entry
    is stamped with ``mod`` (the ``#mod`` key) so the low-level spawn can tell these
    engine-unknown entries apart and post-process them (see :func:`mod_ship_data_process`).
    The derived caches (``ship_index`` and the ``*_keys`` caches) are cleared so the new
    entries are visible on the next lookup.
    
    Args:
        content (str): YAML or JSON text (YAML is a JSON superset, so both parse).
        mod (str, optional): Name of the mod/addon these entries come from; stamped on
            each entry as ``#mod``. Defaults to None (untagged).
    
    Returns:
        dict | None: The updated ship data cache, or ``None`` if ``content`` was
            empty or carried no ``#ship-list``."""
def mod_ship_data_process (so, entry):
    """Apply a runtime-merged (mod) ship data entry to a freshly spawned object.
    
    The engine's built-in shipData table doesn't contain entries merged at runtime
    (:func:`merge_mod_ship_yaml` / :func:`merge_mod_ship_data` / :func:`add_ship_data`),
    so ``create_space_object`` returns a bare object that never got the values the engine
    normally derives from a KNOWN shipData entry. The low-level spawn (``spawn_common``)
    calls this for such objects to reproduce that derivation.
    
    The shipData-field -> object mapping mirrors ``cosmos_dev.mock.sbs``'s reverse-engineered
    ``_apply_ship_data_to_object`` (the engine's data_set names are NOT the shipData spellings):
    
    * **Art** via ``set_ship_data_key(artfileroot)`` when the modded key differs from its art
      (the engine picks the mesh from ``data_tag``, not a data_set field). ``meshscale`` /
      ``radarscale`` are engine-internal render props with NO data_set key -- not applied.
    * **``exclusionradius``** -> the physics attribute ``engine_object.exclusion_radius``
      (not a data_set field).
    * **1-to-1 float scalars** (``turn_rate``, ``speed_coeff``, ``interactionradius``, ...).
    * **``hullpoints``** -> ``armor`` / ``armorMax`` (stations only; ships use another system).
    * **``baycount``** -> ``bay_count``; **``tubecount``** -> ``torpedo_tube_count``.
    * **``shields``** array -> ``shield_count`` + ``shield_val`` / ``shield_max_val`` per facing.
    * **``hull_port_sets``** beams -> ``beamCount`` + ``beamRange`` / ``beamDamage`` (coeff *
      6.0) / ``beamCycleTime`` / ``beamArcWidth`` / ``beamBarrelAngle`` per port.
    * **``torpedostart``** -> ``{Type}_NUM`` / ``_MAX`` / ``_VAL`` + ``torpedo_types_available``.
    
    Fields with no known engine mapping (and the meta key/name/side/roles/#mod) are skipped;
    a prefab may still set anything extra afterwards (it runs after spawn, so it wins).
    
    Args:
        so: The spawned SpaceObject (exposes ``.data_set`` and ``.set_ship_data_key``).
        entry (dict): The ship data entry (as merged, carrying ``#mod``)."""
def pirate_ship_keys ():
    """Return all pirate ship keys (cached).
    
    Returns:
        list[str]: Pirate ship type keys."""
def pirate_starbase_keys ():
    """Return all pirate starbase keys (cached).
    
    As of v1.2.2 no pirate starbases exist in ``shipData``; this returns an
    empty list.
    
    Returns:
        list[str]: Pirate starbase type keys."""
def plain_asteroid_keys ():
    """Return all plain asteroid keys, excluding crystal asteroids (cached).
    
    Returns:
        list[str]: Plain asteroid type keys."""
def reset_ship_data_caches ():
    """Clear the DERIVED ship data caches (index and key lists), not the data itself.
    
    Called by the merge/add functions after they change the ``#ship-list`` so the next
    lookup sees the new entries. For the mission-boundary reset that also drops the
    loaded data, use :func:`ship_data_reset_for_mission`."""
def ship_data_is_loaded () -> int:
    """Reset-ledger probe: 1 while ship data (possibly mod-merged) is held, else 0."""
def ship_data_reset_for_mission ():
    """Drop the loaded ship data ENTIRELY, including any merged mod entries.
    
    Deliberately NOT the same as :func:`reset_ship_data_caches`, which clears only the
    DERIVED caches and is called by the merge functions themselves - clearing
    ``ship_data_cache`` there would throw away the entries just merged.
    
    This is the MISSION-BOUNDARY reset. The next mission has its own mission directory
    (its own ``extraShipData``) and its own set of mods, so a ``#ship-list`` carrying the
    previous mission's merged entries must not survive into it. The engine forks a fresh
    process per mission and hides this; ``cosmos_dev`` reuses one interpreter and does
    not. Registered in the reset ledger as ``ship_data_cache``."""
def skaraan_ship_keys ():
    """Return all Skaraan ship keys (cached).
    
    Returns:
        list[str]: Skaraan ship type keys."""
def skaraan_starbase_keys ():
    """Return all Skaraan starbase keys (cached).
    
    Returns:
        list[str]: Skaraan starbase type keys."""
def terran_ship_keys ():
    """Return all TSN ship keys (cached).
    
    Returns:
        list[str]: Terran ship type keys."""
def terran_starbase_keys ():
    """Return all USPF station (Terran starbase) keys (cached).
    
    Returns:
        list[str]: Terran starbase type keys."""
def torgoth_ship_keys ():
    """Return all Torgoth ship keys (cached).
    
    Returns:
        list[str]: Torgoth ship type keys."""
def torgoth_starbase_keys ():
    """Return all Torgoth starbase keys (cached).
    
    Returns:
        list[str]: Torgoth starbase type keys."""
def ximni_ship_keys ():
    """Return all Ximni ship keys (cached).
    
    Returns:
        list[str]: Ximni ship type keys."""
def ximni_starbase_keys ():
    """Return all Ximni starbase keys (cached).
    
    Returns:
        list[str]: Ximni starbase type keys."""
