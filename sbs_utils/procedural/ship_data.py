from ..fs import load_data, load_yaml_string, get_artemis_data_dir, get_mission_dir, get_mod_dir
import os


ship_data_cache = None
def get_ship_data():
    """Load and cache the full ship data, merging ``extraShipData.json`` if present.

    Results are cached after the first call. The mission-directory
    ``extraShipData.json`` is prepended to the ``#ship-list`` so mission ships
    take priority over built-in data.

    Returns:
        dict: The merged ship data dictionary.
    """
    global ship_data_cache
    if ship_data_cache is not None:
        return ship_data_cache
    
    # Base name (no extension) so load_data picks shipData.yaml or shipData.json.
    ship_data_cache = load_data( os.path.join(get_artemis_data_dir(), "shipData"))

    # extraShipData may be supplied as .yaml or .json.
    script_ship_data = load_data( os.path.join(get_mission_dir(), "extraShipData"))
    if script_ship_data is not None:
        ship_data_cache["#ship-list"] = script_ship_data["#ship-list"] + ship_data_cache["#ship-list"]
        # ship_data_cache |= script_ship_data

    return ship_data_cache

# Runtime-merged ("mod") ship data entries are stamped with this key naming their source, so
# the low-level spawn can tell them from engine-known shipData and post-process them.
SHIP_DATA_MOD_KEY = "#mod"

# shipData scalar fields the engine copies 1-to-1 onto the data_set (same name), as floats.
# (Mirrors cosmos_dev.mock.sbs._apply_ship_data_to_object, the reverse-engineered mapping.)
_MOD_SCALAR_FLOAT_SAME = (
    "interactionradius", "turn_rate", "speed_coeff", "scan_strength_coeff",
    "ship_energy_cost", "warp_energy_cost", "jump_energy_cost", "drone_launch_timer",
    "repair_rate_shields", "repair_rate_systems", "repair_rate_armor",
)

# beamDamage = port damage_coeff * the engine beam-load base.
_MOD_BEAM_LOAD_BASE = 6.0


def _tag_mod_entries(entries, mod):
    """Stamp every entry (in place) with its source mod so spawns can post-process it."""
    if mod is not None:
        for e in entries:
            if isinstance(e, dict):
                e[SHIP_DATA_MOD_KEY] = mod
    return entries


def get_mod(key_or_entry):
    """Return the source mod of a ship data entry, or ``None`` if it is engine-known.

    Exposed to MAST as ``ship_data_get_mod`` (the ``ship_data_`` prelude prefix); named
    ``get_mod`` here so it doesn't double-prefix to ``ship_data_ship_data_get_mod``.

    Args:
        key_or_entry (str | dict): A ship key, or a ship data entry dict.

    Returns:
        str | None: The mod name stamped at merge time, or ``None`` for built-in data.
    """
    entry = key_or_entry
    if isinstance(key_or_entry, str):
        entry = get_ship_data_for(key_or_entry)
    if not isinstance(entry, dict):
        return None
    return entry.get(SHIP_DATA_MOD_KEY)


def mod_ship_data_process(so, entry):
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
        entry (dict): The ship data entry (as merged, carrying ``#mod``).
    """
    if not isinstance(entry, dict):
        return
    blob = getattr(so, "data_set", None)
    if blob is None:
        return

    # Art (data_tag), only when the modded key names a different (engine-known) mesh.
    art = entry.get("artfileroot")
    if art and art != entry.get("key") and hasattr(so, "set_ship_data_key"):
        so.set_ship_data_key(art)

    # exclusionradius is a physics attribute, not a data_set field.
    er = entry.get("exclusionradius")
    if er is not None:
        eo = getattr(so, "engine_object", None)
        if eo is not None:
            eo.exclusion_radius = float(er)

    # 1-to-1 float scalars.
    for field in _MOD_SCALAR_FLOAT_SAME:
        val = entry.get(field)
        if val is not None:
            blob.set(field, float(val), 0)

    # Renamed scalars.
    bc = entry.get("baycount")
    if bc is not None:
        blob.set("bay_count", int(bc), 0)
    tc = entry.get("tubecount")
    if tc is not None:
        blob.set("torpedo_tube_count", int(tc), 0)

    # hullpoints -> station armor (ships use a different hull system in the engine).
    hp = entry.get("hullpoints")
    if hp is not None and hasattr(so, "has_role") and so.has_role("station"):
        blob.set("armor", float(hp), 0)
        blob.set("armorMax", float(hp), 0)

    # Shields (per-facing array).
    shields = entry.get("shields")
    if shields:
        blob.set("shield_count", len(shields), 0)
        for i, sv in enumerate(shields):
            blob.set("shield_val", float(sv), i)
            blob.set("shield_max_val", float(sv), i)

    # Beams from every "beam ..." hull_port_sets entry (monster arts name theirs "beam Bite",
    # "beam Maw", ...; standard ships use "beam Primary Beams").
    hps = entry.get("hull_port_sets")
    if isinstance(hps, dict):
        beams = []
        for pname, plist in hps.items():
            if isinstance(pname, str) and pname.startswith("beam") and isinstance(plist, list):
                beams.extend(plist)
        if beams:
            blob.set("beamCount", len(beams), 0)
            for i, b in enumerate(beams):
                blob.set("beamRange",       float(b.get("range", 1000)), i)
                blob.set("beamDamage",      float(b.get("damage_coeff", 1.0)) * _MOD_BEAM_LOAD_BASE, i)
                blob.set("beamCycleTime",   float(b.get("cycle_time", 6.0)), i)
                blob.set("beamArcWidth",    float(b.get("arcwidth", 360)), i)
                blob.set("beamBarrelAngle", float(b.get("barrel_angle", 0)), i)

    # Starting torpedoes: shipData "torpedostart" is a {type: count} dict or a list of them.
    torp_start = entry.get("torpedostart")
    if torp_start:
        if isinstance(torp_start, dict):
            items = list(torp_start.items())
        else:
            items = [kv for e in torp_start if isinstance(e, dict) for kv in e.items()]
        names = []
        for tname, count in items:
            names.append(tname)
            blob.set(f"{tname}_NUM", int(count), 0)
            blob.set(f"{tname}_MAX", int(count), 0)
            blob.set(f"{tname}_VAL", int(count), 0)
        if names:
            blob.set("torpedo_types_available", ",".join(names), 0)


def merge_mod_ship_data(mod, file=None):
    """Merge a mod folder's extra ship data (YAML or JSON) into the ship data cache.

    Args:
        mod (str): Mod directory name (resolved via ``get_mod_dir``).
        file (str, optional): The data file within the mod folder. Defaults to
            the base name ``"extraShipData"``, which loads ``extraShipData.yaml``
            or ``extraShipData.json`` (YAML preferred). Pass a name WITH a
            ``.yaml``/``.yml``/``.json`` extension to force a specific format.

    Returns:
        dict: The updated ship data cache.
    """
    global ship_data_cache

    ship_data_cache = get_ship_data()
    if file is None:
        file = "extraShipData"

    script_ship_data = load_data( os.path.join(get_mod_dir(mod), file))
    if script_ship_data is not None:
        entries = _tag_mod_entries(script_ship_data["#ship-list"], mod)
        ship_data_cache["#ship-list"] = entries + ship_data_cache["#ship-list"]

    return ship_data_cache


def merge_mod_ship_yaml(content, mod=None):
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
            empty or carried no ``#ship-list``.
    """
    if content is None:
        return None
    global ship_data_cache
    data = load_yaml_string(content)
    if data is None or "#ship-list" not in data:
        return None
    ship_data_cache = get_ship_data()
    entries = _tag_mod_entries(data["#ship-list"], mod)
    ship_data_cache["#ship-list"] = entries + ship_data_cache["#ship-list"]
    reset_ship_data_caches()
    return ship_data_cache


def add_ship_data(entry, mod=None, prepend=True):
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
            not be loaded.
    """
    global ship_data_cache
    data = get_ship_data()
    if data is None:
        return None
    if mod is not None and isinstance(entry, dict):
        entry[SHIP_DATA_MOD_KEY] = mod
    ship_list = data.setdefault("#ship-list", [])
    if prepend:
        ship_list.insert(0, entry)
    else:
        ship_list.append(entry)
    # Rebuild the key index and the cached key lists so the new entry is visible;
    # the loaded ship_data_cache (which we just mutated) is intentionally kept.
    reset_ship_data_caches()
    return data


def ship_data_reset_for_mission():
    """Drop the loaded ship data ENTIRELY, including any merged mod entries.

    Deliberately NOT the same as :func:`reset_ship_data_caches`, which clears only the
    DERIVED caches and is called by the merge functions themselves - clearing
    ``ship_data_cache`` there would throw away the entries just merged.

    This is the MISSION-BOUNDARY reset. The next mission has its own mission directory
    (its own ``extraShipData``) and its own set of mods, so a ``#ship-list`` carrying the
    previous mission's merged entries must not survive into it. The engine forks a fresh
    process per mission and hides this; ``cosmos_dev`` reuses one interpreter and does
    not. Registered in the reset ledger as ``ship_data_cache``.
    """
    global ship_data_cache
    ship_data_cache = None
    reset_ship_data_caches()
    # The record of which extra files were loaded belongs to the mission that
    # loaded them; carried over, a soak run reports the previous mission's.
    extra_reset()


def ship_data_is_loaded() -> int:
    """Reset-ledger probe: 1 while ship data (possibly mod-merged) is held, else 0."""
    return 0 if ship_data_cache is None else 1


def reset_ship_data_caches():
    """Clear the DERIVED ship data caches (index and key lists), not the data itself.

    Called by the merge/add functions after they change the ``#ship-list`` so the next
    lookup sees the new entries. For the mission-boundary reset that also drops the
    loaded data, use :func:`ship_data_reset_for_mission`.
    """
    global ship_index
    ship_index = None
    global asteroid_keys_cache
    asteroid_keys_cache = None
    global crystal_asteroid_keys_cache
    crystal_asteroid_keys_cache = None
    global plain_asteroid_keys_cache
    plain_asteroid_keys_cache=None
    global danger_keys_cache
    danger_keys_cache = None
    global container_keys_cache
    container_keys_cache = None
    global terran_starbase_keys_cache
    terran_starbase_keys_cache = None
    global pirate_starbase_keys_cache
    pirate_starbase_keys_cache=None
    global pirate_ship_keys_cache
    pirate_ship_keys_cache=None
    global ximni_starbase_keys_cache
    ximni_starbase_keys_cache=None
    global ximni_ship_keys_cache
    ximni_ship_keys_cache=None
    global arvonian_starbase_keys_cache
    arvonian_starbase_keys_cache=None
    global arvonian_ship_keys_cache
    arvonian_ship_keys_cache=None
    global skaraan_starbase_keys_cache
    skaraan_starbase_keys_cache=None
    global skaraan_ship_keys_cache
    skaraan_ship_keys_cache=None
    global kralien_starbase_keys_cache
    kralien_starbase_keys_cache=None
    global kralien_ship_keys_cache
    kralien_ship_keys_cache=None
    global torgoth_starbase_keys_cache
    torgoth_starbase_keys_cache=None
    global torgoth_ship_keys_cache
    torgoth_ship_keys_cache=None




ship_index = None
def get_ship_index():
    """Return ship data indexed by ship key for fast O(1) lookup.

    Returns:
        dict[str, dict]: Mapping of ship key → ship data entry.
    """
    global ship_index
    if ship_index is not None:
        return ship_index
    
    data = get_ship_data()
    ship_index = {

    }
    if data is None:
        return ship_index
    
    for i,ship in enumerate(data["#ship-list"]):
        # this_ship_index = ship_index.get(ship['side'])
        # if not this_ship_index:
        #     this_ship_index = set()
        #     ship_index[ship['side']] = this_ship_index
        # # Sometimes it gets a dict instead of a set
        # # When side == key?
        # if isinstance(this_ship_index, set):
        #     this_ship_index.add(i)
        ship_index[ship['key']] = ship
    return ship_index

def get_ship_name(ship_key):
    """Return the display name of a ship type by key.

    Args:
        ship_key (str): The ship type key.

    Returns:
        str | None: Ship display name, or ``None`` if the key is not found.
    """
    ship = get_ship_index().get(ship_key)
    if ship:
        return ship['name']
    return None

def get_ship_data_for(ship_key):
    """Return the full ship data entry for a given key.

    Args:
        ship_key (str): The ship type key.

    Returns:
        dict | None: Ship data dict, or ``None`` if not found.
    """
    return get_ship_index().get(ship_key)


def filter_ship_data_by_side(test_ship_key, sides, role=None, ret_key_only=False):
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
        list[str | dict]: Matching ship keys or data entries.
    """
    data = get_ship_data()

    ret = []
    if data is None:
        return ret
    
    if sides is not None:
        if isinstance(sides, str):
            sides=sides.replace(" ","").lower()
            sides_list = sides.split(",")
            sides = set(sides_list)
            
    
    for ship in data["#ship-list"]:
        if role:
            roles = ship.get("roles", None)
            if roles is None:
                continue
            roles = roles.replace(" ","").lower()
            roles = set(roles.split(","))
            role = role.lower().strip()
            if not (role in roles):
                continue

        key = ship["key"]
        if len(key)==0:
            ship["artfileroot"]

        key_met = test_ship_key is None 
        if test_ship_key is not None:
            key_met =  test_ship_key in ship["key"]
        
        side_met = sides is None
        if sides is not None:
            side_met = ship["side"].lower() in sides

        if key_met and side_met:
            if ret_key_only:
                ret.append(ship["key"])
            else:
                ret.append(ship)
    return ret


asteroid_keys_cache=None
def asteroid_keys():
    """Return all asteroid ship keys from the ship data (cached).

    Returns:
        list[str]: Asteroid type keys.
    """
    global asteroid_keys_cache
    if asteroid_keys_cache is None:
        asteroid_keys_cache= filter_ship_data_by_side(None, "asteroid", None, True)
    return asteroid_keys_cache

crystal_asteroid_keys_cache=None
def crystal_asteroid_keys():
    """Return all crystal asteroid keys, excluding plain asteroids (cached).

    Returns:
        list[str]: Crystal asteroid type keys.
    """
    global crystal_asteroid_keys_cache
    if crystal_asteroid_keys_cache is None:
        crystal_asteroid_keys_cache= filter_ship_data_by_side("crystal", "asteroid", None, True)
    return crystal_asteroid_keys_cache

plain_asteroid_keys_cache=None
def plain_asteroid_keys():
    """Return all plain asteroid keys, excluding crystal asteroids (cached).

    Returns:
        list[str]: Plain asteroid type keys.
    """
    global plain_asteroid_keys_cache
    if plain_asteroid_keys_cache is None:
        plain_asteroid_keys_cache= filter_ship_data_by_side("plain", "asteroid", None, True)
    return plain_asteroid_keys_cache

    
danger_keys_cache = None
def danger_keys():
    """Return all pickup keys containing ``"danger"`` (cached).

    Returns:
        list[str]: Danger pickup type keys.
    """
    global danger_keys_cache
    if danger_keys_cache is None:
        danger_keys_cache =  filter_ship_data_by_side("danger", "pickup", None, True)
    return danger_keys_cache

container_keys_cache = None
def container_keys():
    """Return all pickup keys containing ``"container"`` (cached).

    Returns:
        list[str]: Container pickup type keys.
    """
    global container_keys_cache
    if container_keys_cache is None:
        container_keys_cache =  filter_ship_data_by_side("container", "pickup", None, True)
    return container_keys_cache

alien_keys_cache =  None
def alien_keys():
    """Return all pickup keys containing ``"alien"`` (cached).

    Returns:
        list[str]: Alien pickup type keys.
    """
    global alien_keys_cache
    if alien_keys_cache is None:
        alien_keys_cache =  filter_ship_data_by_side("alien", "pickup", None, True)
    return alien_keys_cache

terran_starbase_keys_cache = None
def terran_starbase_keys():
    """Return all USPF station (Terran starbase) keys (cached).

    Returns:
        list[str]: Terran starbase type keys.
    """
    global terran_starbase_keys_cache
    if terran_starbase_keys_cache is None:
        terran_starbase_keys_cache =  filter_ship_data_by_side(None, "USPF", "station", True) #NOTE The 'side' argument used to be "port"? Changed to match shipData
    return terran_starbase_keys_cache

terran_ship_keys_cache = None
def terran_ship_keys():
    """Return all TSN ship keys (cached).

    Returns:
        list[str]: Terran ship type keys.
    """
    global terran_ship_keys_cache
    if terran_ship_keys_cache is None:
        terran_ship_keys_cache =  filter_ship_data_by_side(None, "TSN", "ship", True)
    return terran_ship_keys_cache

pirate_starbase_keys_cache = None
def pirate_starbase_keys():
    """Return all pirate starbase keys (cached).

    As of v1.2.2 no pirate starbases exist in ``shipData``; this returns an
    empty list.

    Returns:
        list[str]: Pirate starbase type keys.
    """
    global pirate_starbase_keys_cache
    if pirate_starbase_keys_cache is None:
        pirate_starbase_keys_cache =  filter_ship_data_by_side(None, "port", None, True) #NOTE: There are no pirate starbases yet in shipData.
    return pirate_starbase_keys_cache

pirate_ship_keys_cache = None
def pirate_ship_keys():
    """Return all pirate ship keys (cached).

    Returns:
        list[str]: Pirate ship type keys.
    """
    global pirate_ship_keys_cache
    if pirate_ship_keys_cache is None:
        pirate_ship_keys_cache =  filter_ship_data_by_side(None, "pirate", "ship", True)
    return pirate_ship_keys_cache

ximni_starbase_keys_cache = None
def ximni_starbase_keys():
    """Return all Ximni starbase keys (cached).

    Returns:
        list[str]: Ximni starbase type keys.
    """
    global ximni_starbase_keys_cache
    if ximni_starbase_keys_cache is None:
        ximni_starbase_keys_cache =  filter_ship_data_by_side(None, "ximni", "station", True)
    return ximni_starbase_keys_cache

ximni_ship_keys_cache = None
def ximni_ship_keys():
    """Return all Ximni ship keys (cached).

    Returns:
        list[str]: Ximni ship type keys.
    """
    global ximni_ship_keys_cache
    if ximni_ship_keys_cache is None:
        ximni_ship_keys_cache =  filter_ship_data_by_side(None, "Ximni", "ship", True)
    return ximni_ship_keys_cache

arvonian_starbase_keys_cache = None
def arvonian_starbase_keys():
    """Return all Arvonian starbase keys (cached).

    Returns:
        list[str]: Arvonian starbase type keys.
    """
    global arvonian_starbase_keys_cache
    if arvonian_starbase_keys_cache is None:
        arvonian_starbase_keys_cache =  filter_ship_data_by_side(None, "arvonian", "station", True)
    return arvonian_starbase_keys_cache

arvonian_ship_keys_cache =  None
def arvonian_ship_keys():
    """Return all Arvonian ship keys (cached).

    Returns:
        list[str]: Arvonian ship type keys.
    """
    global arvonian_ship_keys_cache
    if arvonian_ship_keys_cache is None:
        arvonian_ship_keys_cache =  filter_ship_data_by_side(None, "Arvonian", "ship", True)
    return arvonian_ship_keys_cache

skaraan_starbase_keys_cache = None
def skaraan_starbase_keys():
    """Return all Skaraan starbase keys (cached).

    Returns:
        list[str]: Skaraan starbase type keys.
    """
    global skaraan_starbase_keys_cache
    if skaraan_starbase_keys_cache is None:
        skaraan_starbase_keys_cache = filter_ship_data_by_side(None, "skaraan", "station", True)
    return skaraan_starbase_keys_cache

skaraan_ship_keys_cache = None
def skaraan_ship_keys():
    """Return all Skaraan ship keys (cached).

    Returns:
        list[str]: Skaraan ship type keys.
    """
    global skaraan_ship_keys_cache
    if skaraan_ship_keys_cache is None:
        skaraan_ship_keys_cache =  filter_ship_data_by_side(None, "Skaraan", "ship", True)
    return skaraan_ship_keys_cache

kralien_starbase_keys_cache = None
def kralien_starbase_keys():
    """Return all Kralien starbase keys (cached).

    Returns:
        list[str]: Kralien starbase type keys.
    """
    global kralien_starbase_keys_cache
    if kralien_starbase_keys_cache is None:
        kralien_starbase_keys_cache =  filter_ship_data_by_side(None, "kralien", "station", True)
    return kralien_starbase_keys_cache

kralien_ship_keys_cache = None
def kralien_ship_keys():
    """Return all Kralien ship keys (cached).

    Returns:
        list[str]: Kralien ship type keys.
    """
    global kralien_ship_keys_cache
    if  kralien_ship_keys_cache is None:
        kralien_ship_keys_cache =  filter_ship_data_by_side(None, "Kralien", "ship", True)
    return kralien_ship_keys_cache

torgoth_starbase_keys_cache =  None
def torgoth_starbase_keys():
    """Return all Torgoth starbase keys (cached).

    Returns:
        list[str]: Torgoth starbase type keys.
    """
    global torgoth_starbase_keys_cache
    if torgoth_starbase_keys_cache is None:
        torgoth_starbase_keys_cache =  filter_ship_data_by_side(None, "torgoth", "station", True)
    return torgoth_starbase_keys_cache

torgoth_ship_keys_cache = None
def torgoth_ship_keys():
    """Return all Torgoth ship keys (cached).

    Returns:
        list[str]: Torgoth ship type keys.
    """
    global torgoth_ship_keys_cache
    if torgoth_ship_keys_cache is None:
        torgoth_ship_keys_cache =filter_ship_data_by_side(None, "Torgoth", "ship", True)
    return torgoth_ship_keys_cache



# --- the engine's extra-ship-data hook, wrapped ------------------------------
# `sbs.add_extra_ship_data(filename, path)` (engine 1.3.5) points the engine at a
# second ship-data file for this mission. It was being called RAW from mission
# code, which left three problems with nowhere to live:
#
#   * it is newer than some engines a mission may meet, so a bare call is an
#     AttributeError on an older one;
#   * it is not fully landed, and there is no way to stop using it without
#     editing every caller;
#   * the ENGINE learning about the ships and SBS_UTILS learning about them are
#     two different things, and a mission needs both - the library is what
#     answers `get_ship_data_for`, drives the mock, and fills in stats headless.
#
# So this always merges into the library's own list, and gates only the engine
# call. Turning it off therefore costs you the engine-side effects (art, and
# anything the engine resolves itself) and keeps the stats - which is the same
# split the runtime-mod work already measured: stats travel through the library,
# artfileroot does not.

_EXTRA_SHIP_DATA_ENGINE = True      # is the engine call allowed?
_extra_ship_data_loaded = []        # (filename, path, reached_engine) per call


def extra_enable(enabled=True):
    """Allow or forbid the ENGINE side of `add_extra`.

    Off, the ships are still merged into sbs_utils, so headless runs and every
    library lookup behave the same; only the engine is not told. Use it to take
    the engine path out of play without touching any caller."""
    global _EXTRA_SHIP_DATA_ENGINE
    _EXTRA_SHIP_DATA_ENGINE = bool(enabled)
    return _EXTRA_SHIP_DATA_ENGINE


def extra_enabled():
    """Is the engine call currently allowed?"""
    return _EXTRA_SHIP_DATA_ENGINE


def extra_loaded():
    """`[(filename, path, reached_engine)]` for every call so far, so a report can
    say what was loaded and whether the engine actually heard about it."""
    return list(_extra_ship_data_loaded)


def extra_reset():
    """Forget the record. Called by the per-mission reset, not by missions."""
    _extra_ship_data_loaded.clear()


def _looks_like_hjson(text):
    """Is this extra ship data in a shape the ENGINE can read?

    The engine parses these files as **HJSON**, not YAML - its own
    `data/shipData.yaml` says so in the header. HJSON is JSON with comments, so
    a key cannot contain whitespace and there are no block sequences: a perfectly
    valid `- key: thing` list, or a `"beam Primary Beams":` block mapping, is a
    parse error.

    And it fails in SILENCE. `add_extra_ship_data` raises, we carry on, and the
    library still merges the file with PyYAML - which accepts both shapes - so
    every headless run, every unit test and every library lookup sees the ships.
    Only the engine does not, and the bill arrives later as a hull it was never
    given: LegendaryMissions' turrets spawned and never fired for exactly this
    reason (found 2026-08-14).

    So check the shape at load, where the file is in front of us."""
    for line in str(text).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped.startswith("{")
    return True                 # empty file - a different complaint


def add_extra(name, path=None, mod=None):
    """Load another ship-data file for this mission.

    `name` has **no extension** - the engine tries `.yaml` then `.json` itself,
    which is the more useful form because a mod can change format without the
    caller changing. It may include a logical folder
    (`"turrets/extraShipData_turrets"`).

    With no `path`, the file is looked for where the media system already looks:
    this mission's folder first, then each media pack it pinned. That matters
    because an ADD-ON cannot put a file where the engine can read it - a mastlib
    is a zip - while a media pack is unpacked to disk once. So an addon ships its
    hulls in its media pack and names them here, and neither it nor the library
    has to write anything.

    Returns True when the engine was told, False when only the library was.
    Missing files are not fatal, matching the engine's habit: a mod with a broken
    path should be a ship with no stats, not a dead mission."""
    folder, _, stem = str(name).replace(chr(92), "/").rpartition("/")
    filename = stem or str(name)
    if path is None:
        path = _find_extra_root(folder, filename)
    elif folder:
        path = os.path.join(path, *folder.split("/"))
    reached = False
    why = ""

    text = _read_extra_ship_data(filename, path)
    if text is not None:
        merge_mod_ship_yaml(text, mod or "add_extra_ship_data")
        if not _looks_like_hjson(text):
            why = "block YAML - the engine reads HJSON and will reject this file"
            from .execution import log
            log(f"{filename} is block YAML. The engine parses extra ship data as HJSON "
                f"(JSON with comments): no `- item` sequences, no whitespace in a key. "
                f"sbs_utils reads it fine, so the ships work everywhere EXCEPT the engine "
                f"- where spawning one fails. Write it as JSON.", "ship_data", "warning")
    else:
        # SAY SO. A missing file is not fatal - but silence here costs a whole
        # afternoon, because the failure surfaces far away and looks like something
        # else entirely: every ship in the file spawns with no stats, so a monster
        # has beamCount 0 and reads as "combat is broken" rather than "the hulls
        # were never loaded". The usual cause is a mission that loads the ADDON but
        # not the media pack the addon keeps its hulls in, so name that too.
        from .execution import log
        log(f"extra ship data not found: {filename} (looked in {path}). "
            f"Ships from this file will have no stats. If it belongs to an add-on, "
            f"the mission's story.json probably needs that add-on's shared_media zip.",
            "ship_data", "warning")

    if _EXTRA_SHIP_DATA_ENGINE:
        try:
            import sbs
            sbs.add_extra_ship_data(str(filename), _engine_path(path))
            reached = True
        except AttributeError as e:
            why = "AttributeError: %s" % e
            # Older engine. The library merge above already happened, so the ships exist
            # as far as sbs_utils is concerned - but SAY SO. "engine told: False" with no
            # reason is the same silence that hid the path bug above: the hulls are in
            # the library, the mission looks fine, and the engine kills a spawn minutes
            # later for a ship type it was never given.
            from .execution import log
            log(f"add_extra_ship_data({filename}) unavailable on this engine: {e}. "
                f"Ships from this file exist in sbs_utils but NOT in the engine, so "
                f"spawning one will fail inside the engine.", "ship_data", "warning")
        except Exception as e:                  # noqa: BLE001
            why = "%s: %s" % (type(e).__name__, e)
            from .execution import log
            log(f"add_extra_ship_data({filename}) failed: {e}", "ship_data", "warning")

    _extra_ship_data_loaded.append((str(filename), str(path), reached))
    # SAY WHAT HAPPENED, to debug.log - the one channel that survives an engine session.
    # Everything about this call is invisible from inside the game: whether the file was
    # found, what path the ENGINE was handed, and whether it accepted the call. When the
    # hulls do not arrive, the symptom is a spawn dying inside the engine several minutes
    # later with `bad allocation`, and nothing connects the two.
    try:
        from ..mast.mast import DEBUG
        DEBUG("add_extra(%s): file %s in %r -> engine path %r, engine told: %s%s"
              % (filename, "FOUND" if text is not None else "MISSING", path,
                 _engine_path(path), reached, why and (" (%s)" % why) or ""))
    except Exception:                                   # noqa: BLE001
        pass
    return reached


def _find_extra_root(folder, filename):
    """The folder holding a logical ship-data path: the mission, then each media
    root, in the order `media_paths` already searches.

    Chosen by whether the FILE is there, not whether the folder is. An addon's
    logical folder name usually matches its own source folder - `turrets/` is both
    the mastlib's name and a real directory in the mission - so picking the first
    directory that exists silently picks the addon folder, which is exactly where
    the file no longer is.

    THE UNPACKED MEDIA PACK WINS. An addon developed in place has the same file twice -
    once in its source `media/` folder and once in the pack unpacked under `__lib__` -
    and the engine can only read the second. ENGINE-MEASURED 1.3.5, the whole of a
    morning:

        add_extra_ship_data("extraShipData_monsters",
                            "data/missions/__lib__/media/<pack>/prefabs")  -> works
        add_extra_ship_data("extraShipData_monsters",
                            "data/missions/LegendaryMissions/media/prefabs") -> silently
                            loads NOTHING

    The call does not fail either way, and the LIBRARY reads the file fine from both, so
    everything looks correct: the mission runs, the mock is happy, `sbs lint` is happy.
    The bill arrives when something spawns one of those hulls and the ENGINE is asked for
    a ship type it never received - `MemoryError: bad allocation` from
    `create_space_object`, minutes later, in a mission that never mentions ship data.
    (Measured harder still: asking the engine to build one directly is an access
    violation, not an exception.)

    Falls back to the mission folder, so a genuinely missing file still reports
    against somewhere a person can go and look."""
    mission = get_mission_dir()
    roots = [mission]
    try:
        from .media_paths import media_roots
        roots += [r for r in (media_roots() or []) if r]
    except Exception:
        pass
    found = []
    for root in roots:
        cand = os.path.join(root, *folder.split("/")) if folder else root
        if not os.path.isabs(cand):
            cand = os.path.normpath(os.path.join(mission, cand))
        stem = os.path.join(cand, filename)
        if any(os.path.isfile(stem + e) for e in ("", ".yaml", ".json")):
            found.append(cand)
    for cand in found:
        norm = cand.replace(chr(92), "/")
        if "/__lib__/media/" in norm:
            return cand
    if found:
        return found[0]
    return os.path.join(mission, *folder.split("/")) if folder else mission


def _engine_path(path):
    """A path in the form the ENGINE wants: relative to the Cosmos root.

    Their own example is `add_extra_ship_data("extraShipDataAAA",
    "data/missions/BeamArcTest")` - root-relative, not absolute, and not relative
    to the mission. Every caller building that string by hand would get it wrong
    in a different way, and a wrong path is not an error here: the engine is
    forgiving about data it cannot find, so it fails as ships with no stats.

    An absolute path under the install is converted; anything else is passed
    through, since a caller who wrote a relative path already knew what it meant."""
    text = str(path)
    if not os.path.isabs(text):
        return text
    try:
        from ..fs import get_artemis_dir
        rel = os.path.relpath(text, get_artemis_dir())
    except Exception:
        return text
    if rel.startswith(".."):
        return text             # outside the install - leave it alone
    return rel.replace(os.sep, "/")


def _read_extra_ship_data(filename, path):
    """The file's text, trying the same extensions the engine tries, or None."""
    stem = os.path.join(str(path), str(filename))
    for candidate in (stem, stem + ".yaml", stem + ".json"):
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            continue
    return None
