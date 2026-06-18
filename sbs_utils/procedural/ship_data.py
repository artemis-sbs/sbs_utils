from ..fs import load_json_data, get_artemis_data_dir, get_mission_dir, get_mod_dir
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
    
    ship_data_cache = load_json_data( os.path.join(get_artemis_data_dir(), "shipData.yaml"))
    if ship_data_cache is None:
        ship_data_cache = load_json_data( os.path.join(get_artemis_data_dir(), "shipData.json"))
    
    script_ship_data = load_json_data( os.path.join(get_mission_dir(), "extraShipData.json"))
    if script_ship_data is not None:
        ship_data_cache["#ship-list"] = script_ship_data["#ship-list"] + ship_data_cache["#ship-list"]
        # ship_data_cache |= script_ship_data

    return ship_data_cache

def merge_mod_ship_data(mod):
    """Merge a mod folder's ``extraShipData.json`` into the ship data cache.

    Args:
        mod (str): Mod directory name (resolved via ``get_mod_dir``).

    Returns:
        dict: The updated ship data cache.
    """
    global ship_data_cache

    ship_data_cache = get_ship_data()
    
    script_ship_data = load_json_data( os.path.join(get_mod_dir(mod), "extraShipData.json"))
    if script_ship_data is not None:
        ship_data_cache["#ship-list"] = script_ship_data["#ship-list"] + ship_data_cache["#ship-list"]

    return ship_data_cache


def reset_ship_data_caches():
    """Clear all ship data and key-list caches.

    Use when switching missions to ensure stale ship data from a previous
    mission directory is not used.
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

