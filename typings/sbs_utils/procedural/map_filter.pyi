def _console (console):
    ...
def _last_key (console):
    ...
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def map_filter_clear (ship_id, console='comms'):
    """Remove one console's map filter from this ship: the map shows everything again."""
def map_filter_get (ship_id, console='comms'):
    """The ids one console's map is filtered to, or [] when it shows everything."""
def map_filter_set (ship_id, ids, console='comms'):
    """Show only `ids` - and the ship itself - on this ship's 2D map for one console.
    
    Only ids the engine knows are written - live space objects. A lifeform, grid object,
    fleet or dead id is dropped. The ship's own id is always in the list, so the crew
    never loses their own ship from the map, and a lens that matches nothing still writes
    a non-empty list (empty would mean "no filter"). Skips the write when the list has not
    changed since the last one, since every write goes over the network.
    
    Terrain in `ids` is drawn only while its flag is on - see map_show_terrain.
    
    Args:
        ship_id (Agent | int): The player ship whose map is filtered.
        ids (iterable): Agent ids or objects to show.
        console (str): "comms", "sci", "helm" or "weapon".
    
    Returns:
        list: The ids shown (the ship included), sorted."""
def map_show_terrain (ship_id, console, nebulas=None, asteroids=None):
    """Show or hide nebulas and asteroids on one console's 2D map, for the whole ship.
    
    None leaves that flag alone. The flags work with or without a filter.
    
    Args:
        ship_id (Agent | int): The player ship.
        console (str): "sci", "helm" or "weapon". Comms has no terrain flags.
        nebulas (bool | None): Draw nebulas.
        asteroids (bool | None): Draw asteroids.
    
    Returns:
        tuple: (nebulas, asteroids) as they now stand; None for one that cannot be read."""
def map_terrain_shown (ship_id, console):
    """(nebulas, asteroids) for one console's 2D map. The engine's default is both on."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
