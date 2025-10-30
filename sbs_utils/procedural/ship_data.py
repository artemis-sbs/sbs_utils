from ..fs import load_json_data, get_artemis_data_dir, get_mission_dir, get_mod_dir
import os


ship_data_cache = None
def get_ship_data():
    """
    Load the ship data, store it to the cache, and return it.
    If the ship data is already in cache, returns it the cache contents instead of loading the file again.
    Includes ship data from `extraShipData.json` for the current mission directory, if present.
    Returns:
        dict: The ship data dictionary.
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
    """
    Get the ship data for the current mission, then adds the contents of `extraShipData.json` for the specified mission folder, if present, and adds it to the cache.
    Returns:
        dict: The ship data.
    """
    global ship_data_cache

    ship_data_cache = get_ship_data()
    
    script_ship_data = load_json_data( os.path.join(get_mod_dir(mod), "extraShipData.json"))
    if script_ship_data is not None:
        ship_data_cache["#ship-list"] = script_ship_data["#ship-list"] + ship_data_cache["#ship-list"]

    return ship_data_cache


def reset_ship_data_caches():
    """
    Clear the ship data cache. Use to remove mission ship data for other mission folders, or possibly to just clear out some memory usage if it won't be used.
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
    """
    Get the ship data information and index it as a dictionary. 
    Keys include:
    * individual ship keys
    * default sides
    Returns:
        dict: The indexed ship data information.
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
        this_ship_index = ship_index.get(ship['side'])
        if not this_ship_index:
            this_ship_index = set()
            ship_index[ship['side']] = this_ship_index
        this_ship_index.add(i)
        ship_index[ship['key']] = ship
    return ship_index

def get_ship_name(ship_key):
    """
    Get the name of the ship with the specified key.
    Args:
        ship_key (str): The key for the ship.
    Returns:
        str | None: The name of the ship, or None.
    """
    ship = get_ship_index().get(ship_key)
    if ship:
        return ship['name']
    return None

def get_ship_data_for(ship_key):
    """
    Get the ship data information for the ship with the given key.
    Args:
        ship_key (str): The key for the ship.
    Returns:
        dict: The ship data contents.
    """
    return get_ship_index().get(ship_key)


def filter_ship_data_by_side(test_ship_key, sides, role=None, ret_key_only=False):
    """
    Get a list of all ships with the given sides.
    Args:
        test_ship_key (str | None): Only include ship data for which the key includes this substring.
        sides (str): The comma-separated list of sides by which the ship data should be filtered.
        role (str, optional): An optional role by which the list may also be filtered. Must be a single role.
        ret_key_only (bool, optional): Should the returned list be a list of keys (if True), or a list of ship data entries (if False)?
    Returns:
        list[str | dict]: The list of keys or list of ship data entries.
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
    """
    Get all asteroid keys in the ship data.
    Returns:
        list[str]: The list of keys.
    """
    global asteroid_keys_cache
    if asteroid_keys_cache is None:
        asteroid_keys_cache= filter_ship_data_by_side(None, "asteroid", None, True)
    return asteroid_keys_cache

crystal_asteroid_keys_cache=None
def crystal_asteroid_keys():
    """
    Get all crystal asteroid keys (excludes plain) in the ship data.
    Returns:
        list[str]: The list of keys.
    """
    global crystal_asteroid_keys_cache
    if crystal_asteroid_keys_cache is None:
        crystal_asteroid_keys_cache= filter_ship_data_by_side("crystal", "asteroid", None, True)
    return crystal_asteroid_keys_cache

plain_asteroid_keys_cache=None
def plain_asteroid_keys():
    """
    Get all plain asteroid keys (excludes crystal) in the ship data.
    Returns:
        list[str]: The list of keys.
    """
    global plain_asteroid_keys_cache
    if plain_asteroid_keys_cache is None:
        plain_asteroid_keys_cache= filter_ship_data_by_side("plain", "asteroid", None, True)
    return plain_asteroid_keys_cache

    
danger_keys_cache = None
def danger_keys():
    """
    Get all keys in the ship data that contain "danger" in the key.
    Returns:
        list[str]: The list of keys.
    """
    global danger_keys_cache
    if danger_keys_cache is None:
        danger_keys_cache =  filter_ship_data_by_side("danger", "pickup", None, True)
    return danger_keys_cache

container_keys_cache = None
def container_keys():
    """
    Get all keys in the ship data that contian "container" in the key.
    Returns:
        list[str]: The list of keys.
    """
    global container_keys_cache
    if container_keys_cache is None:
        container_keys_cache =  filter_ship_data_by_side("container", "pickup", None, True)
    return container_keys_cache

alien_keys_cache =  None
def alien_keys():
    """
    Get all keys in the ship data that contain "alien" in the key.
    Returns:
        list[str]: The list of keys.
    """
    global alien_keys_cache
    if alien_keys_cache is None:
        alien_keys_cache =  filter_ship_data_by_side("alien", "pickup", None, True)
    return alien_keys_cache

terran_starbase_keys_cache = None
def terran_starbase_keys():
    """
    Get all keys in the ship data for terran starbases.
    Returns:
        list[str]: The list of keys.
    """
    global terran_starbase_keys_cache
    if terran_starbase_keys_cache is None:
        terran_starbase_keys_cache =  filter_ship_data_by_side(None, "USPF", "station", True) #NOTE The 'side' argument used to be "port"? Changed to match shipData
    return terran_starbase_keys_cache

terran_ship_keys_cache = None
def terran_ship_keys():
    """
    Get all keys in the ship data for terran ships.
    Returns:
        list[str]: The list of keys.
    """
    global terran_ship_keys_cache
    if terran_ship_keys_cache is None:
        terran_ship_keys_cache =  filter_ship_data_by_side(None, "TSN", "ship", True)
    return terran_ship_keys_cache

pirate_starbase_keys_cache = None
def pirate_starbase_keys():
    """
    Get all keys in the ship data for pirate starbases. (As of 1.2.2, there were none.)
    Returns:
        list[str]: The list of keys.
    """
    global pirate_starbase_keys_cache
    if pirate_starbase_keys_cache is None:
        pirate_starbase_keys_cache =  filter_ship_data_by_side(None, "port", None, True) #NOTE: There are no pirate starbases yet in shipData.
    return pirate_starbase_keys_cache

pirate_ship_keys_cache = None
def pirate_ship_keys():
    """
    Get all keys in the ship data for pirate ships.
    Returns:
        list[str]: The list of keys.
    """
    global pirate_ship_keys_cache
    if pirate_ship_keys_cache is None:
        pirate_ship_keys_cache =  filter_ship_data_by_side(None, "pirate", "ship", True)
    return pirate_ship_keys_cache

ximni_starbase_keys_cache = None
def ximni_starbase_keys():
    """
    Get all keys in the ship data for Ximni starbases.
    Returns:
        list[str]: The list of keys.
    """
    global ximni_starbase_keys_cache
    if ximni_starbase_keys_cache is None:
        ximni_starbase_keys_cache =  filter_ship_data_by_side(None, "ximni", "station", True)
    return ximni_starbase_keys_cache

ximni_ship_keys_cache = None
def ximni_ship_keys():
    """
    Get all keys in the ship data for Ximni ships.
    Returns:
        list[str]: The list of keys.
    """
    global ximni_ship_keys_cache
    if ximni_ship_keys_cache is None:
        ximni_ship_keys_cache =  filter_ship_data_by_side(None, "Ximni", "ship", True)
    return ximni_ship_keys_cache

arvonian_starbase_keys_cache = None
def arvonian_starbase_keys():
    """
    Get all keys in the ship data for Arvonian starbases.
    Returns:
        list[str]: The list of keys.
    """
    global arvonian_starbase_keys_cache
    if arvonian_starbase_keys_cache is None:
        arvonian_starbase_keys_cache =  filter_ship_data_by_side(None, "arvonian", "station", True)
    return arvonian_starbase_keys_cache

arvonian_ship_keys_cache =  None
def arvonian_ship_keys():
    """
    Get all keys in the ship data for Arvonian ships.
    Returns:
        list[str]: The list of keys.
    """
    global arvonian_ship_keys_cache
    if arvonian_ship_keys_cache is None:
        arvonian_ship_keys_cache =  filter_ship_data_by_side(None, "Arvonian", "ship", True)
    return arvonian_ship_keys_cache

skaraan_starbase_keys_cache = None
def skaraan_starbase_keys():
    """
    Get all keys in the ship data for Skaraan starbases.
    Returns:
        list[str]: The list of keys.
    """
    global skaraan_starbase_keys_cache
    if skaraan_starbase_keys_cache is None:
        skaraan_starbase_keys_cache = filter_ship_data_by_side(None, "skaraan", "station", True)
    return skaraan_starbase_keys_cache

skaraan_ship_keys_cache = None
def skaraan_ship_keys():
    """
    Get all keys in the ship data for Skaraan ships.
    Returns:
        list[str]: The list of keys.
    """
    global skaraan_ship_keys_cache
    if skaraan_ship_keys_cache is None:
        skaraan_ship_keys_cache =  filter_ship_data_by_side(None, "Skaraan", "ship", True)
    return skaraan_ship_keys_cache

kralien_starbase_keys_cache = None
def kralien_starbase_keys():
    """
    Get all keys in the ship data for Kralien starbases.
    Returns:
        list[str]: The list of keys.
    """
    global kralien_starbase_keys_cache
    if kralien_starbase_keys_cache is None:
        kralien_starbase_keys_cache =  filter_ship_data_by_side(None, "kralien", "station", True)
    return kralien_starbase_keys_cache

kralien_ship_keys_cache = None
def kralien_ship_keys():
    """
    Get all keys in the ship data for Kralien ships.
    Returns:
        list[str]: The list of keys.
    """
    global kralien_ship_keys_cache
    if  kralien_ship_keys_cache is None:
        kralien_ship_keys_cache =  filter_ship_data_by_side(None, "Kralien", "ship", True)
    return kralien_ship_keys_cache

torgoth_starbase_keys_cache =  None
def torgoth_starbase_keys():
    """
    Get all keys in the ship data for Torgoth starbases.
    Returns:
        list[str]: The list of keys.
    """
    global torgoth_starbase_keys_cache
    if torgoth_starbase_keys_cache is None:
        torgoth_starbase_keys_cache =  filter_ship_data_by_side(None, "torgoth", "station", True)
    return torgoth_starbase_keys_cache

torgoth_ship_keys_cache = None
def torgoth_ship_keys():
    """
    Get all keys in the ship data for Torgoth ships.
    Returns:
        list[str]: The list of keys.
    """
    global torgoth_ship_keys_cache
    if torgoth_ship_keys_cache is None:
        torgoth_ship_keys_cache =filter_ship_data_by_side(None, "Torgoth", "ship", True)
    return torgoth_ship_keys_cache

