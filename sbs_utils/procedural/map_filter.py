"""The 2D map filters and terrain flags: engine data sets on a player ship.

Each console family has its own filter on the SHIP's blob - a list of the ids its 2D map
shows - so every console of that kind on the ship shares it:

    comms   comms_map_filter     comms_2d_view
    sci     sci_map_filter       science_2d_view
    helm    helm_map_filter      2dview
    weapon  weapon_map_filter    weapon_2d_view

`comms` is engine 1.3.13; the other three arrived in 1.3.15, along with two flags each,
`<console>_show_nebulas` and `<console>_show_asteroids` (comms has none).

MEASURED ON ENGINE 1.3.15 (a raw-sbs probe, server screen and a real client agreeing):

* The flags default to 1 and act ON THEIR OWN: 0 hides that terrain with no filter set.
* A filter shows only the listed ids. Terrain in the list ALSO needs its flag on, and
  the flag on its own shows no terrain the list leaves out.
* An empty list means "no filter". `comms_map_filter` gets back there through
  clear_data_set_value. **The three new keys do not**: the server blob reads empty after
  the clear, but the view goes on drawing the last list, on the server's own screen and
  on a client alike. Until the engine fixes that, a sci/helm/weapon filter can be
  CHANGED but not REMOVED - map_filter_clear is correct and has no visible effect there.

Written as clear + set by index, the clear through clear_data_set_value so the clients'
copy goes too: a bare clear_data is not replicated.
"""
from .inventory import get_inventory_value, set_inventory_value

#: console -> the blob key of its filter.
MAP_FILTER_KEYS = {
    "comms": "comms_map_filter",
    "sci": "sci_map_filter",
    "helm": "helm_map_filter",
    "weapon": "weapon_map_filter",
}

#: The consoles that have `_show_nebulas` / `_show_asteroids`. Comms does not.
MAP_TERRAIN_CONSOLES = ("sci", "helm", "weapon")

_ALIASES = {"science": "sci", "weapons": "weapon", "weap": "weapon", "comm": "comms"}


def _console(console):
    console = str(console or "comms").strip().lower()
    console = _ALIASES.get(console, console)
    if console not in MAP_FILTER_KEYS:
        raise ValueError(f"map filter: unknown console {console!r}; "
                         f"expected one of {', '.join(MAP_FILTER_KEYS)}")
    return console


def _last_key(console):
    # The comms name predates the others and is read by missions' saved state.
    return MAP_FILTER_KEYS[console] + "_last"


def map_filter_set(ship_id, ids, console="comms"):
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
        list: The ids shown (the ship included), sorted.
    """
    from .query import to_id, to_data_set, object_exists, is_space_object_id, clear_data_set_value
    console = _console(console)
    key = MAP_FILTER_KEYS[console]
    ship_id = to_id(ship_id)
    keep = {ship_id}
    for i in ids or ():
        i = to_id(i)
        if i and is_space_object_id(i) and object_exists(i):
            keep.add(i)
    keep = sorted(keep)
    if get_inventory_value(ship_id, _last_key(console), None) == keep:
        return keep
    data_set = to_data_set(ship_id)
    if data_set is None:
        return keep
    clear_data_set_value(ship_id, key)
    for index, i in enumerate(keep):
        data_set.set(key, i, index)
    set_inventory_value(ship_id, _last_key(console), keep)
    return keep


def map_filter_clear(ship_id, console="comms"):
    """Remove one console's map filter from this ship: the map shows everything again.

    On engine 1.3.15 this is only visible for "comms" - see the module docstring.
    """
    from .query import to_id, to_data_set, clear_data_set_value
    console = _console(console)
    ship_id = to_id(ship_id)
    if get_inventory_value(ship_id, _last_key(console), None) == []:
        return
    data_set = to_data_set(ship_id)
    if data_set is None:
        return
    clear_data_set_value(ship_id, MAP_FILTER_KEYS[console])
    set_inventory_value(ship_id, _last_key(console), [])


def map_filter_get(ship_id, console="comms"):
    """The ids one console's map is filtered to, or [] when it shows everything."""
    from .query import to_id
    return list(get_inventory_value(to_id(ship_id), _last_key(_console(console)), None) or [])


def map_show_terrain(ship_id, console, nebulas=None, asteroids=None):
    """Show or hide nebulas and asteroids on one console's 2D map, for the whole ship.

    None leaves that flag alone. The flags work with or without a filter.

    Args:
        ship_id (Agent | int): The player ship.
        console (str): "sci", "helm" or "weapon". Comms has no terrain flags.
        nebulas (bool | None): Draw nebulas.
        asteroids (bool | None): Draw asteroids.

    Returns:
        tuple: (nebulas, asteroids) as they now stand; None for one that cannot be read.
    """
    from .query import to_id, to_data_set
    console = _console(console)
    if console not in MAP_TERRAIN_CONSOLES:
        raise ValueError(f"map terrain flags: {console!r} has none; "
                         f"expected one of {', '.join(MAP_TERRAIN_CONSOLES)}")
    data_set = to_data_set(to_id(ship_id))
    if data_set is None:
        return (None, None)
    for name, value in (("nebulas", nebulas), ("asteroids", asteroids)):
        if value is not None:
            data_set.set(f"{console}_show_{name}", 1 if value else 0, 0)
    return map_terrain_shown(ship_id, console)


def map_terrain_shown(ship_id, console):
    """(nebulas, asteroids) for one console's 2D map. The engine's default is both on."""
    from .query import to_id, to_data_set
    console = _console(console)
    if console not in MAP_TERRAIN_CONSOLES:
        return (None, None)
    data_set = to_data_set(to_id(ship_id))
    if data_set is None:
        return (None, None)
    out = []
    for name in ("nebulas", "asteroids"):
        value = data_set.get(f"{console}_show_{name}", 0)
        # An engine older than 1.3.15 answers None: it draws terrain and has no flag.
        out.append(True if value is None else bool(value))
    return tuple(out)
