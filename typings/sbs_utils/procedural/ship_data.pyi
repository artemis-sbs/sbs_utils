def alien_keys ():
    """Get all keys in the ship data that contain "alien" in the key.
    Returns:
        list[str]: The list of keys."""
def arvonian_ship_keys ():
    """Get all keys in the ship data for Arvonian ships.
    Returns:
        list[str]: The list of keys."""
def arvonian_starbase_keys ():
    """Get all keys in the ship data for Arvonian starbases.
    Returns:
        list[str]: The list of keys."""
def asteroid_keys ():
    """Get all asteroid keys in the ship data.
    Returns:
        list[str]: The list of keys."""
def container_keys ():
    """Get all keys in the ship data that contian "container" in the key.
    Returns:
        list[str]: The list of keys."""
def crystal_asteroid_keys ():
    """Get all crystal asteroid keys (excludes plain) in the ship data.
    Returns:
        list[str]: The list of keys."""
def danger_keys ():
    """Get all keys in the ship data that contain "danger" in the key.
    Returns:
        list[str]: The list of keys."""
def filter_ship_data_by_side (test_ship_key, sides, role=None, ret_key_only=False):
    """Get a list of all ships with the given sides.
    Args:
        test_ship_key (str | None): Only include ship data for which the key includes this substring.
        sides (str): The comma-separated list of sides by which the ship data should be filtered.
        role (str, optional): An optional role by which the list may also be filtered. Must be a single role.
        ret_key_only (bool, optional): Should the returned list be a list of keys (if True), or a list of ship data entries (if False)?
    Returns:
        list[str | dict]: The list of keys or list of ship data entries."""
def get_artemis_data_dir ():
    """Get the path to the Artemis Cosmos data directory.
    
    Returns:
        str: The data folder path (executable directory + "/data")."""
def get_mission_dir ():
    """Get the directory of the current mission.
    
    Returns:
        str: The script directory path."""
def get_mod_dir (mod):
    """Get the directory path for a mission module.
    
    Args:
        mod (str): The module/mission name.
    
    Returns:
        str: The full directory path for the module."""
def get_ship_data ():
    """Load the ship data, store it to the cache, and return it.
    If the ship data is already in cache, returns it the cache contents instead of loading the file again.
    Includes ship data from `extraShipData.json` for the current mission directory, if present.
    Returns:
        dict: The ship data dictionary."""
def get_ship_data_for (ship_key):
    """Get the ship data information for the ship with the given key.
    Args:
        ship_key (str): The key for the ship.
    Returns:
        dict: The ship data contents."""
def get_ship_index ():
    """Get the ship data information and index it as a dictionary.
    Keys include:
    * individual ship keys
    Returns:
        dict: The indexed ship data information."""
def get_ship_name (ship_key):
    """Get the name of the ship with the specified key.
    Args:
        ship_key (str): The key for the ship.
    Returns:
        str | None: The name of the ship, or None."""
def kralien_ship_keys ():
    """Get all keys in the ship data for Kralien ships.
    Returns:
        list[str]: The list of keys."""
def kralien_starbase_keys ():
    """Get all keys in the ship data for Kralien starbases.
    Returns:
        list[str]: The list of keys."""
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def merge_mod_ship_data (mod):
    """Get the ship data for the current mission, then adds the contents of `extraShipData.json` for the specified mission folder, if present, and adds it to the cache.
    Returns:
        dict: The ship data."""
def pirate_ship_keys ():
    """Get all keys in the ship data for pirate ships.
    Returns:
        list[str]: The list of keys."""
def pirate_starbase_keys ():
    """Get all keys in the ship data for pirate starbases. (As of 1.2.2, there were none.)
    Returns:
        list[str]: The list of keys."""
def plain_asteroid_keys ():
    """Get all plain asteroid keys (excludes crystal) in the ship data.
    Returns:
        list[str]: The list of keys."""
def reset_ship_data_caches ():
    """Clear the ship data cache. Use to remove mission ship data for other mission folders, or possibly to just clear out some memory usage if it won't be used."""
def skaraan_ship_keys ():
    """Get all keys in the ship data for Skaraan ships.
    Returns:
        list[str]: The list of keys."""
def skaraan_starbase_keys ():
    """Get all keys in the ship data for Skaraan starbases.
    Returns:
        list[str]: The list of keys."""
def terran_ship_keys ():
    """Get all keys in the ship data for terran ships.
    Returns:
        list[str]: The list of keys."""
def terran_starbase_keys ():
    """Get all keys in the ship data for terran starbases.
    Returns:
        list[str]: The list of keys."""
def torgoth_ship_keys ():
    """Get all keys in the ship data for Torgoth ships.
    Returns:
        list[str]: The list of keys."""
def torgoth_starbase_keys ():
    """Get all keys in the ship data for Torgoth starbases.
    Returns:
        list[str]: The list of keys."""
def ximni_ship_keys ():
    """Get all keys in the ship data for Ximni ships.
    Returns:
        list[str]: The list of keys."""
def ximni_starbase_keys ():
    """Get all keys in the ship data for Ximni starbases.
    Returns:
        list[str]: The list of keys."""
