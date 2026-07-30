from ..objects import Terrain, PlayerShip, Npc
from ..gridobject import GridObject

def npc_spawn(x,y,z,name, side, ship_key, behave_id):
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
        SpawnData: Spawn data for the new NPC.
    """
    # TODO: Modify such that a Vec3 can be provided?
    so = Npc()
    return so.spawn(x,y,z,name, side, ship_key, behave_id)
    
def player_spawn(x,y,z,name, side, ship_key):
    """Spawn a player ship into the simulation.

    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.

    Returns:
        SpawnData: Spawn data for the new player ship.
    """
    so = PlayerShip()
    return so.spawn(x,y,z,name, side, ship_key)


# ---------------------------------------------------------------------------
# Player slot identity
#
# A player ship has no stable identity of its own: player_spawn mints a new hull
# on every call, and every consumer re-derives "slot N" from id ORDER (sorted by
# id, or an unordered role set). Two consequences, and the second is the nastier:
#
#   1. Creation is not idempotent. An init route emitted twice - a double Start
#      press, two addons emitting the same signal, a copy-pasted emit, an emit
#      inside a loop - duplicates the whole roster.
#   2. A re-created ship gets a NEW (higher) id, so it moves to the END of every
#      id-sorted list. It can fall past `player_list_all[:PLAYER_COUNT]` and become
#      unpickable at ship select while still counting toward all-players-dead.
#
# Stamping the slot ON the ship fixes both: creation becomes idempotent against
# the CURRENT world instead of against "did I already run". That distinction is
# what keeps the LEGITIMATE re-runs working - after a sim_create() wipe the ships
# are gone and ensure recreates them; a destroyed ship can be remade; a late
# joining crew's slot is filled without touching the others; a route that failed
# halfway completes the set rather than adding a second one. A boolean did-I-run
# flag is wrong for every one of those. See SIGNAL_ROUTING.md.
# ---------------------------------------------------------------------------
PLAYER_SLOT_KEY = "player_slot"


def player_slot_role(slot):
    """The role marking the ship that holds ``slot`` (e.g. ``player_slot_3``).

    A role, because role sets are the only O(1) keyed lookup available and they
    self-clean when the object is deleted (``Agent._remove`` purges the registries),
    so a slot is freed by deleting its ship with no bookkeeping.
    """
    return f"{PLAYER_SLOT_KEY}_{int(slot)}"


def player_slot_id(slot):
    """The live player ship holding ``slot``, or ``None``.

    Args:
        slot (int): The player slot.

    Returns:
        int|None: The ship's ID, or None if the slot is empty.
    """
    from .roles import role
    from .query import to_id_list, object_exists
    for so_id in to_id_list(role(player_slot_role(slot)) & role("__player__")):
        if object_exists(so_id):
            return so_id
    return None


def player_slots():
    """Every filled player slot as ``{slot: id}``.

    Returns:
        dict: Slot number -> ship ID, for live player ships carrying a slot.
    """
    from .roles import role
    from .query import to_id_list, object_exists
    from .inventory import get_inventory_value
    found = {}
    for so_id in to_id_list(role("__player__")):
        if not object_exists(so_id):
            continue
        slot = get_inventory_value(so_id, PLAYER_SLOT_KEY, None)
        if slot is not None:
            found[slot] = so_id
    return found


def player_ensure(slot, x, y, z, ship_key, name=None, side="tsn"):
    """Ensure a player ship occupies ``slot``, spawning one only if it is empty.

    Idempotent: returns the existing ship's ID if the slot is already filled, so an
    initialization route that gets emitted more than once creates nothing extra.
    Because the check is against the live world and not a did-I-run flag, a slot
    emptied by ``sim_create()``, a deletion or a destroyed ship is refilled on the
    next call - which is what makes reset, respawn and late-joining crew work.

    An existing ship is returned UNTOUCHED (not repositioned or renamed); use
    ``a2x_place_player`` to converge one in place. This mirrors ``side_ensure`` /
    ``side_create``.

    Args:
        slot (int): Player slot, stable across re-runs.
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        ship_key (str): Ship template key from shipData.
        name (str, optional): Display name.
        side (str, optional): Side the ship belongs to. Comma tokens become roles.

    Returns:
        int|None: The ship's ID, or None if the spawn failed.
    """
    from .roles import role, add_role, remove_role
    from .query import to_id, to_id_list
    from .inventory import set_inventory_value
    from .execution import log

    slot = int(slot)
    existing = player_slot_id(slot)
    if existing is not None:
        # Loud on purpose. Nothing is broken - that is the point of ensure - but
        # reaching here means the init ran twice, which is worth chasing.
        log(f"player slot {slot} already filled by {existing}; not spawning again",
            "spawn")
        return existing

    # A husk can keep the marker: spawn_players strips __player__ from unused hulls
    # before deleting them, and player_slot_id skips those. Free the marker so one
    # slot is never claimed by two objects.
    marker = player_slot_role(slot)
    for stale in to_id_list(role(marker)):
        remove_role(stale, marker)

    so_id = to_id(player_spawn(x, y, z, name, side, ship_key))
    if so_id is None:
        return None
    add_role(so_id, marker)
    set_inventory_value(so_id, PLAYER_SLOT_KEY, slot)
    return so_id


def players_reset():
    """Delete every player ship, freeing all slots.

    The explicit path for an INTENTIONAL re-initialization (reset the scenario
    without reloading the mission): wipe, then re-emit the create signal and let
    ``player_ensure`` rebuild the roster. Slot roles are purged by the delete, so
    nothing else needs clearing.

    Returns:
        int: How many ships were deleted.
    """
    from .roles import role
    from .query import to_id_list
    from .space_objects import delete_object
    ids = to_id_list(role("__player__"))
    for so_id in ids:
        delete_object(so_id)
    return len(ids)


def terrain_spawn(x,y,z,name, side, ship_key, behave_id):
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
        SpawnData: Spawn data for the new terrain object.
    """
    so = Terrain()
    return so.spawn(x,y,z,name, side, ship_key, behave_id)

from .query import to_id
def grid_spawn(id, name, tag, x,y, icon_index, color, roles):
    """Spawn a grid object (engineering component) onto a ship's grid.

    Args:
        id (Agent | int): The ship agent ID or object to attach the grid object
            to.
        name (str): Display name of the grid object.
        tag (str): Tag identifying the grid object's side or type.
        x (int): Column position on the engineering grid.
        y (int): Row position on the engineering grid.
        icon_index (int): Icon index for the grid display.
        color (str): Display color string.
        roles (str): Comma-separated roles to assign to the grid object.

    Returns:
        GridObject: The newly created grid object.
    """
    # TODO: The docs for 'tag' imply that this is the side of the grid object? Clarify.
    so = GridObject()
    id = to_id(id)
    return so.spawn(id, name, tag, x,y, icon_index, color, roles)
