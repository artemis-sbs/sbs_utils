from random import choice, choices
from ..agent import Agent, CloseData, SpawnData
from ..helpers import FrameContext
from ..delete_queue import DeleteQueue

###################
# Set functions
# Get the set of IDS of a broad test
def to_py_object_list(the_set):
    """Convert a set of raw agent IDs to a list of Agent objects.

    The odd one out of the list resolvers, and kept that way for compatibility:

    * **IDs only.** It indexes ``Agent.all`` directly, so an ``Agent`` / ``CloseData`` /
      ``SpawnData`` in the set resolves to ``None``, not to itself.
    * **``None`` is kept, not dropped**, so positions line up with the input - every
      other list resolver filters instead.
    * **No liveness check**, so a deleted agent's id yields ``None`` (it is out of
      ``Agent.all``) while a stale ``Agent`` object yields ``None`` too, for the other
      reason.
    * id ``0`` resolves to the SERVER console, as ``Agent.get`` always has.

    Prefer :func:`to_object_list` (space objects, drops what it cannot resolve) or
    :func:`to_agent_list` (the write side, keeps the server). See the resolver table in
    :func:`to_object_list`.

    Args:
        the_set (set[int]): A set of agent IDs.

    Returns:
        list[Agent | None]: Agents resolved from the set, ``None`` where an id is not in
            ``Agent.all``.
    """
    return [Agent.get(id) for id in the_set]



def to_object_list(the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).

    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.

    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded.
    """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    # to_object, NOT Agent.resolve_py_object. resolve_py_object does not consult
    # `_alive`, so the list form used to hand back agents the singular form had already
    # refused - `to_object(x)` None while `to_object_list([x])` returned it. Every guard
    # written as "resolve it, then use it" is only as good as the resolve, and a caller
    # has no reason to want the one dead entry the list quietly kept.
    #
    # Not the source of a crash today: a dead agent's `data_set` is already None, so a
    # write through one raises rather than reaching freed memory. This closes the
    # inconsistency, not a use-after-free.
    #
    # THE OTHER HALF, and the reason that change had a sequel: to_object also refuses id
    # 0, which is the SERVER's own agent. That is correct HERE - this is the space-object
    # resolver, and for a space object 0 means "no object" - but it is wrong for anything
    # resolving in order to WRITE, and this list used to be that path too. Timers and
    # counters ride set_inventory_value, so `start_counter(0, name)` silently wrote
    # nothing (LM #719). Writers use `to_agent_list`; both halves are pinned together in
    # tests/test_stale_handle.py.
    # THE FOUR LIST RESOLVERS, measured - pick by what the caller DOES with the answer:
    #
    #   resolver               id 0 (server)   dead agent   use for
    #   to_object_list         dropped         dropped      space objects (this one)
    #   to_space_object_list   dropped         dropped      space objects, said out loud
    #   to_agent_list          KEPT            dropped      writes: roles, links, inventory
    #   to_id_list             KEPT            KEPT         ids; no liveness check
    #   to_py_object_list      kept            None entry   raw id sets only; keeps None
    #
    # Both columns are load-bearing here and neither is an oversight. See to_agent_list
    # for why 0 is a holder but not an object, and tests/test_stale_handle.py, which pins
    # both halves together - the id-0 half was missing once, and that is how LM #719 got
    # in through a change whose stated purpose was to strengthen the liveness half.
    return [y for x in the_list if (y := to_object(x)) is not None]

def to_space_object_list(the_set):
    """Convert a set or list of IDs/agents to a list of SpaceObject agents (excluding None).

    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.

    Returns:
        list[Agent]: Space-object agents only; grid/client IDs are excluded.
    """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y := to_space_object(x)) is not None]


def to_id_list(the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.

    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.

    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded.
    """
    if the_set is None:
        return []
    the_list = to_list(the_set)
    return [y for x in the_list if (y:=Agent.resolve_id(x)) is not None]

def to_list(other: Agent | CloseData | int):
    """Normalize any agent-like value or collection into a list.

    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.

    Returns:
        list: A list containing whatever was passed in; ``None`` becomes ``[]``.
    """
    if isinstance(other, set):
        return list(other)
    elif isinstance(other, str):
        return [other]
    elif isinstance(other, list):
        return other
    elif other is None:
        return []
    return [other]

def to_set(other: Agent | CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.

    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.

    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set.
    """
    if isinstance(other, list):
        # Convert to a list of IDs
        other = [y for x in other if (y:=Agent.resolve_id(x)) is not None]
        return set(other)
    elif isinstance(other, set):
        return other
    elif other is None:
        return set()
    return {to_id(other)}


def to_id(other: Agent | CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.

    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.

    Returns:
        int: The integer agent ID.
    """
    other_id = other
    if isinstance(other, Agent):
        other_id = other.id
    elif isinstance(other, CloseData):
        other_id = other.id
    elif isinstance(other, SpawnData):
        other_id = other.id
   
    return other_id

def to_object(other: Agent | CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.

    Returns ``None`` when the agent no longer exists.

    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.

    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved.
    """
    py_object = other
    if isinstance(other, Agent):
        py_object = other
    elif isinstance(other, CloseData):
        py_object = other.py_object
    elif isinstance(other, SpawnData):
        py_object = other.py_object
    elif other==0:
        return None
    else:
        # should return space object or grid object
        py_object = Agent.get(other)
    # An Agent instance -- or one cached inside a CloseData / SpawnData -- can
    # outlive the engine object it describes: a route's SPAWNED, a console task's
    # roster snapshot and a Modifier's target all hold one across ticks. Handing
    # a dead one back is what made every `->END if to_object(x) is None` guard
    # inert for object arguments, and let writes land on freed memory.
    # Agent.get() above already consults Agent.all; this covers the three paths
    # that never did. See Agent._alive.
    if py_object is not None and not py_object._alive:
        return None
    return py_object


def to_agent_list(the_set):
    """Resolve to Agent objects for a WRITE, the SERVER CONSOLE included.

    `to_object` refuses id 0 by design - 0 means "no object" for a space object - so
    every write built on :func:`to_object_list` silently skipped the server console.
    That is not a corner case: the server window is a console like any other, and
    `add_role(client_id, "console, mainscreen")` on it was a no-op, which is why an
    overlay narrowed with `consoles="mainscreen"` never reached the main screen when
    the main screen WAS the server.

    The reads already knew better - `get_inventory_value` has carried an explicit
    `Agent.get(0)` branch for exactly this. This is that branch generalized, so a write
    can reach everything a read can see.

    Space-object callers keep using `to_object_list`: id 0 there really does mean "no
    object", and this must not resurrect it for them.

    Args:
        the_set (set[Agent | int] | list[Agent | int] | Agent | int): what to resolve.

    Returns:
        list[Agent]: resolved agents; unresolvable entries are dropped.
    """
    if the_set is None:
        return []
    out = []
    for x in to_list(the_set):
        y = to_object(x)
        if y is None:
            y = to_client_object(x)
        if y is not None:
            out.append(y)
    return out


def to_client_object(other: Agent | int):
    """Resolve a client/console ID or Agent to its Agent object.

    Returns ``None`` when the ID is not a valid client ID or the agent no
    longer exists.

    Args:
        other (Agent | int): Client ID or agent to resolve.

    Returns:
        Agent | None: The client agent, or ``None``.
    """
    if isinstance(other, Agent):
        py_object = other
        if is_client_id(other.get_id()):
            return py_object
    else:
        if is_client_id(other) or other == 0:
            # should return space object or grid object
            return Agent.get(other)
    return None

def to_space_object(other: Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).

    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.

    Args:
        other (Agent | CloseData | int): ID or agent to resolve.

    Returns:
        Agent | None: The space-object agent, or ``None``.
    """
    other = to_object(other)
    if is_space_object_id(other):
            # should return space object or grid object
            return other
    return None

def to_grid_object(other: Agent | int):
    """Resolve an ID or Agent to a GridObject agent.

    Returns ``None`` when the ID is not a grid-object ID or the object no
    longer exists.

    Args:
        other (Agent | CloseData | int): ID or agent to resolve.

    Returns:
        Agent | None: The grid-object agent, or ``None``.
    """
    other = to_object(other)
    if is_grid_object_id(other):
            # should return space object or grid object
            return other
    return None


def object_exists(so_id):
    """Return whether an object currently exists in the simulation.

    Args:
        so_id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the engine reports the object present.
    """
    so_id = to_id(so_id)
    if so_id is None:
        return False
    # A tombstoned (deferred-delete) object is logically gone the instant
    # delete_object() is called, even though its native memory is freed later at
    # the end-of-handler drain. Report it gone now to preserve the pre-deferral
    # contract. object_exists is a hot per-tick path, so read the set directly and
    # short-circuit on empty (the common case: nothing pending) rather than pay a
    # method call every time. See delete_queue.DeleteQueue.
    pending = DeleteQueue._pending
    if pending and so_id in pending:
        return False
    # space_object_exists only validly answers for SPACE-object ids. The engine
    # asserts (0 == uID || VALID_SPACE_OBJ(uID)) on an id it doesn't recognise as a
    # space object: a Fleet / side / task / grid id is script-only - the engine never
    # created it - so passing it would crash-to-desktop. Such an id is, by definition,
    # not an existing space object, so answer False without asking the engine. (A
    # dead-but-well-formed space id IS still a space-object id, so it still goes to the
    # engine, which returns 0.)
    if not is_space_object_id(so_id):
        return False
    return FrameContext.context.sim.space_object_exists(so_id) != 0
    #return eo is not None

def all_objects_exists(the_set):
    """Return whether every object in a collection exists in the simulation.

    Args:
        the_set (Agent | int | set[Agent | int] | list[Agent | int]): One or
            more agent IDs or objects.

    Returns:
        bool: ``True`` if all objects exist; ``False`` if any is missing.
    """
    so_ids = to_id_list(the_set)
    for so_id in so_ids:
        # object_exists (not the raw engine call) so a non-space id in the set can't
        # assert the engine (VALID_SPACE_OBJ) and a tombstoned object counts as gone.
        if not object_exists(so_id):
            return False
    return True

def get_data_set_value(id_or_obj, key, index=0, default=None):
    """Get a value from the engine data-set (blob) of a space or grid object.

    Args:
        id_or_obj (Agent | int): The agent ID or object.
        key (str): The data-set key.
        index (int, optional): The slot index within that key. Defaults to 0.
            **This is an INDEX, not a fallback** - the third positional argument is
            which slot to read (shield 0 vs shield 1), and passing a "default" there
            reads the wrong slot or fails outright.
        default (any, optional): what to return when the field has never been set.
            The engine answers ``None`` for such a field, and a mission that then
            compares it (``if fuel < 1000``) raises on a real bridge while running
            clean against the mock's typed defaults - the bug behind LM's Florbin
            cargo-hold watcher and an earlier helm crash. Pass ``default=0`` (or
            ``default=""``) and the caller gets something it can use. ``sbs lint``
            flags the unguarded shape as ``blob-unguarded-none``.

    Returns:
        any: The stored value, ``default`` if the object or key is not found.
    """
    # Initialize so an id that is NEITHER a space nor a grid object (e.g. a side id,
    # a story id, or the server id 0) returns None instead of raising UnboundLocalError
    # on the `object is not None` check below. This unblocks callers like side-level
    # modifier_add, whose is_key_for_blob probes get_data_set_value on the side id.
    object = None
    if is_space_object_id(id_or_obj):
        object = to_space_object(id_or_obj)
    elif is_grid_object_id(id_or_obj):
        object = to_grid_object(id_or_obj)
    if object is not None:
        try:
            value = object.data_set.get(key, index)
            return default if value is None else value
        except ValueError:
            # A grid object's Agent can OUTLIVE its host ship: to_grid_object still
            # returns it, but its blob lives in the host's hull map. Once the host is
            # freed, the engine raises ValueError ("invalid space object while accessing
            # blob of gridobject"). Its data is gone, so honour this function's contract
            # and report not-found rather than let the throw propagate. (A deleted SPACE
            # object already resolves to None above, so only grid objects reach here.)
            return default
    return default

def set_data_set_value(to_update, key, value, index=0):
    """Set a value in the engine data-set (blob) for one or more space or grid objects.

    If ``to_update`` is a set or list, the value is applied to each member.

    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The
            agent(s) to update.
        key (str): The data-set key.
        value (any): The value to store.
        index (int, optional): The slot index within that key. Defaults to 0.
    """
    objects = to_object_list(to_set(to_update))
    for object in objects:
        if is_space_object_id(object) or is_grid_object_id(object):
            object.data_set.set(key, value, index)

def get_engine_data_set(id_or_obj):
    """Return the engine data-set (blob) for an agent.

    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID, object, or SpawnData.

    Returns:
        data_set | None: The engine data-set, or ``None`` if not found.
    """
    if isinstance(id_or_obj, SpawnData):
        # SpawnData caches the raw blob handed out at spawn. It is the same blob
        # the agent holds, so resolve through the agent rather than returning the
        # cached pointer blind -- otherwise this path stays a use-after-free even
        # once every other one is guarded.
        spawned = to_object(id_or_obj)
        return None if spawned is None else id_or_obj.blob
    object = to_object(id_or_obj)
    if object is not None:
        return object.data_set
    return None

# easier to remember function names
def to_blob(id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.

    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.

    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist.
    """
    return get_engine_data_set(id_or_obj)

def to_data_set(id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.

    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.

    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist.
    """
    return get_engine_data_set(id_or_obj)

def is_client_id(id):
    """Return whether an ID belongs to a client (player console) agent.

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the client-console bit (0x8000…) is set.
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x8000000000000000)!=0

def is_space_object_id(id):
    """Return whether an ID belongs to a space object.

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set.
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x4000000000000000)!=0

def is_alt_ship_target(id):
    """Return whether an ID is safe to hand to ``assign_client_to_alt_ship``.

    ``0`` means "clear the focus" and is always allowed. Anything else must be a
    SPACE-object id. A Fleet, side, task or grid id is script-only - the engine never
    created it - and pointing a console at one crashes the client: measured 5 runs out of
    5 as either a modal ``vertexIndex < numVerts`` assert out of ``DX11PAXVertList.cpp``
    or an access violation reading off the end of a vertex list. The engine takes the id
    as a ship, indexes a mesh it does not have, and reads whatever is there.

    A dead-but-well-formed space id is deliberately still allowed: the engine handles a
    deleted ship cleanly (measured), and rejecting it here would drop legitimate focus
    changes on a target that is merely mid-teardown. This guards the class the engine
    cannot survive, not staleness. ``object_exists`` already applies the same reasoning
    before calling ``space_object_exists``.

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the id is 0 or a space-object id.
    """
    id = to_id(id)
    if id is None:
        return False
    if id == 0:
        return True
    return is_space_object_id(id)


def is_grid_object_id(id):
    """Return whether an ID belongs to an engineering-grid object.

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the grid-object bit (0x2000…) is set.
    """
    id = to_id(id)
    if id is None:
        return False
    return (id & 0x2000000000000000)!=0

def is_task_id(id):
    """Return whether an ID belongs to a MAST task.

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the task-id bit (0x0080…) is set.
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x0080000000000000)!=0

def is_story_id(id):
    """Return whether an ID belongs to a story agent (not an engine object, e.g. Fleets).

    Args:
        id (Agent | int): Agent ID or object.

    Returns:
        bool: ``True`` if the ID has the story-object bit set.
    """

    id = to_id(id)
    if id is None:
        return False
    return (id & 0x0040000000000000)!=0


def to_engine_object(id_or_obj):
    """Return the C++ engine-object pointer for an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        pointer | None: The underlying C++ engine-object, or ``None`` if the
            agent does not exist.
    """
    object = to_object(id_or_obj)
    if object is not None:
        eo = object.engine_object
        return eo
    return None


def get_comms_selection(id_or_not):
    """Return the ID of the object currently selected on the comms console.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.

    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable.
    """
    # Guard existence first: to_blob can hand back a dangling engine data-set for a
    # deleted/tombstoned object (to_object returns the still-registered Python Agent),
    # and blob.get(...) then throws in the engine. object_exists consults the delete
    # queue and the engine, so a gone ship returns None instead of crashing.
    if not object_exists(id_or_not):
        return None
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("comms_target_UID",0)
    return None

def get_science_selection(id_or_not):
    """Return the ID of the object currently selected on the science console.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.

    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable.
    """
    if not object_exists(id_or_not):
        return None
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("science_target_UID",0)
    return None

def get_grid_selection(id_or_not):
    """Return the ID of the object currently selected on the engineering grid console.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.

    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable.
    """
    if not object_exists(id_or_not):
        return None
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("grid_selected_UID",0)
    return None

def get_weapons_selection(id_or_not):
    """Return the ID of the object currently selected on the weapons console.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.

    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable.
    """
    if not object_exists(id_or_not):
        return None
    blob = to_blob(id_or_not)
    if blob is not None:
        return blob.get("weapon_target_UID",0)
    return None


def set_console_selection(id_or_not, other_id_or_obj, console):
    """Set the selected object for a named console on a player ship.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select, or ``0`` to clear.
        console (str): The blob key for the console (e.g. ``"comms_target_UID"``).
    """
    if not object_exists(id_or_not):
        return
    blob = to_blob(id_or_not)
    other = to_id(other_id_or_obj)
    if not isinstance(other, int):
        # to_id passes through anything that isn't an Agent/CloseData/SpawnData
        # (None, a raw engine space_object, etc.). Only an int id may be stored -
        # a non-int would poison the selection blob and crash every later reader.
        other = 0
    if blob is not None:
        blob.set(console, other, 0)
        # Keep the roll-back value in step. A display-only console's click is undone by
        # restoring `approved_<console>` (see ConsoleDispatcher.do_select); without this
        # a selection the SCRIPT made would be rolled back to whatever a console last
        # picked the moment anyone clicked a read-only view.
        _obj = to_object(id_or_not)
        if _obj is not None:
            _obj.set_inventory_value(f"approved_{console}", other)


def set_comms_selection(id_or_not, other_id_or_obj):
    """Set the selected object on the comms console of a player ship.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select.
    """
    set_console_selection(id_or_not, other_id_or_obj, "comms_target_UID")

def set_science_selection(id_or_not, other_id_or_obj):
    """Set the selected object on the science console of a player ship.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select.
    """

    set_console_selection(id_or_not, other_id_or_obj, "science_target_UID")

def set_grid_selection(id_or_not, other_id_or_obj):
    """Set the selected object on the engineering grid console of a player ship.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select.
    """
    set_console_selection(id_or_not, other_id_or_obj, "grid_selected_UID")

def set_weapons_selection(id_or_not, other_id_or_obj):
    """Set the selected object on the weapons console of a player ship.

    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select.
    """
    set_console_selection(id_or_not, other_id_or_obj, "weapon_target_UID")

# TODO: What is the purpose of these functions? Docstrings are based on what they do, but the purpose is unclear.
def inc_disable_selection(id_or_obj, console_selected_UID):
    """Increment the disable-count for a console selection and clear it.

    Increments an internal counter tracking how many callers have suppressed
    the selection for this console, then zeroes the console's selected UID
    in the blob so the console has no active target.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"weapon_target_UID"``).
    """
    _obj = to_object(id_or_obj)
    if _obj is None: return
    cur = _obj.get_inventory_value(console_selected_UID, 0)
    cur += 1
    _obj.set_inventory_value(console_selected_UID,cur)
    blob = to_blob(id_or_obj)
    blob.set(console_selected_UID,0,0)

def inc_disable_weapons_selection(id_or_obj): inc_disable_selection(id_or_obj, "weapon_target_UID")
def inc_disable_science_selection(id_or_obj): inc_disable_selection(id_or_obj, "science_target_UID")
def inc_disable_grid_selection(id_or_obj): inc_disable_selection(id_or_obj, "grid_selected_UID")

def dec_disable_selection(id_or_obj, console_selected_UID):
    """Decrement the disable-count for a console selection.

    Reverses an ``inc_disable_selection`` call. When the counter reaches zero
    the console is no longer suppressed.

    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"weapon_target_UID"``).
    """
    _obj = to_object(id_or_obj)
    if _obj is None: return
    cur = _obj.get_inventory_value(console_selected_UID, 0)
    cur -= 1
    _obj.set_inventory_value(console_selected_UID,cur)
    
def dec_disable_weapons_selection(id_or_obj): dec_disable_selection(id_or_obj, "weapon_target_UID")
def dec_disable_science_selection(id_or_obj): dec_disable_selection(id_or_obj, "science_target_UID")
def dec_disable_grid_selection(id_or_obj): dec_disable_selection(id_or_obj, "grid_selected_UID")

def inc_disable_client_selection(client_id, console_selected_UID):
    """Make ONE console take no part in a selection, without affecting the others.

    The selection itself lives on the SHIP, so `inc_disable_selection` is all-or-nothing
    for every console looking at that ship: disable it so a second, display-only view
    cannot click and the console that is meant to be driving stops selecting too. This
    is the per-console form: the shared value is left exactly as it was, which is what a
    read-only second view of an interior needs.

    It RESTORES rather than refuses, because refusing is too late. The ENGINE writes the
    ship's selection into the blob before the event reaches the script - measured by
    instrumenting ``do_select`` in a real run, where the blob already held the new value
    on entry - so declining to write leaves the engine's change standing. The dispatcher
    puts back ``approved_<console>``, the last selection the library allowed.

    Pair with :func:`dec_disable_client_selection`; the count nests.

    Args:
        client_id (Agent | int): The console (client) that must not select.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"grid_selected_UID"``).
    """
    # Deliberately the inventory helpers, NOT Agent.get: the SERVER console is client
    # id 0, `to_object(0)` is None by design, and a bare `Agent.get` write silently does
    # nothing for it. `set_inventory_value` resolves through `to_agent_list`, which has
    # the explicit server branch. The main screen IS the server window in an ordinary
    # setup, so getting this wrong means the one console this exists for is the one it
    # does not work on - and it fails without a word.
    from .inventory import get_inventory_value, set_inventory_value
    key = f"disable_{console_selected_UID}"
    set_inventory_value(client_id, key, get_inventory_value(client_id, key, 0) + 1)

def dec_disable_client_selection(client_id, console_selected_UID):
    """Reverse an :func:`inc_disable_client_selection` call.

    Args:
        client_id (Agent | int): The console (client) to restore.
        console_selected_UID (str): The blob key for the console.
    """
    from .inventory import get_inventory_value, set_inventory_value
    key = f"disable_{console_selected_UID}"
    set_inventory_value(client_id, key, max(0, get_inventory_value(client_id, key, 0) - 1))

def inc_disable_client_grid_selection(client_id): inc_disable_client_selection(client_id, "grid_selected_UID")
def dec_disable_client_grid_selection(client_id): dec_disable_client_selection(client_id, "grid_selected_UID")
def inc_disable_client_science_selection(client_id): inc_disable_client_selection(client_id, "science_target_UID")
def dec_disable_client_science_selection(client_id): dec_disable_client_selection(client_id, "science_target_UID")
def inc_disable_client_weapons_selection(client_id): inc_disable_client_selection(client_id, "weapon_target_UID")
def dec_disable_client_weapons_selection(client_id): dec_disable_client_selection(client_id, "weapon_target_UID")
def inc_disable_client_comms_selection(client_id): inc_disable_client_selection(client_id, "comms_target_UID")
def dec_disable_client_comms_selection(client_id): dec_disable_client_selection(client_id, "comms_target_UID")

def get_side(id_or_obj):
    """Return the side string of an agent.

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        str: The side string, or ``""`` if the object does not exist.
    """
    so = to_object(id_or_obj)
    if so is not None:
        return so.side
    return ""

def get_side_display(id_or_obj):
    """Return the display name of an agent's side.

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        str: The side display string, or ``""`` if the object does not exist.
    """
    so = to_object(id_or_obj)
    if so is not None:
        return so.side_display
    return ""


def get_race(id_or_obj):
    """Return the race string of a space object (defaults to side from shipData).

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        str: The race string, or ``""`` if the object does not exist.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    
    return obj.race
    

def get_origin(id_or_obj):
    """Get the origin string of a space object (defaults to the side from shipData).

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        str: The origin string, or ``""`` if the object does not exist.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    
    return obj.origin

def get_crew(id_or_obj):
    """Get the crew string of a space object (defaults to the side from shipData).

    Args:
        id_or_obj (Agent | int): Agent ID or object.

    Returns:
        str: The crew string, or ``""`` if the object does not exist.
    """
    obj = to_object(id_or_obj)
    if obj is None:
        return ""
    
    return obj.crew

def random_id(the_set):
    """Return the ID of a randomly chosen element from a collection.

    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.

    Returns:
        int | None: A random agent ID, or ``None`` if the collection is empty.
    """
    if len(the_set)==0:
        return None
    return to_id(choice(tuple(the_set)))



def random_object(the_set):
    """Return a randomly chosen agent object from a collection.

    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.

    Returns:
        Agent | None: A random agent, or ``None`` if the collection is empty.
    """
    if len(the_set)==0:
        return None
    return to_object(choice(tuple(the_set)))



def random_object_list(the_set, count=1):
    """Return a list of randomly chosen agent objects from a collection.

    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
        count (int, optional): Number of objects to pick. Defaults to 1.

    Returns:
        list[Agent]: Randomly selected agents (may contain duplicates).
    """
    rand_id_list = choices(tuple(the_set), count)
    return [Agent.get(x) for x in rand_id_list]

def safe_int(s, defa=0):
    """Convert a value to an integer, returning a default on failure.

    Accepts strings (GUI typeins / loaded game codes arrive as strings) as well
    as values that are already ``int``/``float`` - a GUI property can be either
    depending on whether it was typed, defaulted, or loaded from settings, so
    callers must not assume a string. Non-numeric input yields ``defa``.

    A prefixed literal is also accepted: ``"0x1F"`` -> 31 (and ``0o``/``0b``).
    Decimal is tried first so leading-zero decimals still parse as base 10
    (``"007"`` -> 7). Bare hex without the ``0x`` prefix is intentionally NOT
    accepted - ``"42"`` is valid hex too, so it would silently reinterpret
    ordinary decimal input.

    Args:
        s (str | int | float | any): The value to convert.
        defa (int, optional): Value returned if ``s`` is not a valid integer.
            Defaults to 0.

    Returns:
        int: The converted integer, or ``defa``.
    """
    if s is None:
        return defa
    if isinstance(s, (int, float)):
        return int(s)
    s = str(s).strip()
    try:
        return int(s)          # decimal (keeps leading-zero decimals: "007" -> 7)
    except (ValueError, TypeError):
        pass
    try:
        return int(s, 0)       # prefixed literal: "0x1F" -> 31, "0o17", "0b101"
    except (ValueError, TypeError):
        return defa

def are_variables_defined(keys):
    """Return whether all named variables are defined in the current MAST task.

    Args:
        keys (str): Comma-separated variable names to check.

    Returns:
        bool: ``True`` if every key is defined in the current task scope.
    """
    task = FrameContext.task
    if task is None:
        return False
    return task.are_variables_defined(keys)