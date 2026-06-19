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
def load_json_data (file):
    """Load and parse a JSON file with comment support.
    
    Strips comments (# and //) and trailing commas before parsing.
    Attempts to load using ryaml first, falls back to json.loads with preprocessing.
    
    Args:
        file (str): Path to the JSON file to load.
    
    Returns:
        dict or None: Parsed JSON data, or None if loading fails."""
def merge_mod_ship_data (mod):
    """Merge a mod folder's ``extraShipData.json`` into the ship data cache.
    
    Args:
        mod (str): Mod directory name (resolved via ``get_mod_dir``).
    
    Returns:
        dict: The updated ship data cache."""
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
    """Clear all ship data and key-list caches.
    
    Use when switching missions to ensure stale ship data from a previous
    mission directory is not used."""
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
