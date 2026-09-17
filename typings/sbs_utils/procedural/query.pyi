from sbs_utils.agent import Agent
from sbs_utils.agent import CloseData
from sbs_utils.agent import SpawnData
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.helpers import FrameContext
def _agent_id_or_raise (value):
    """One agent id, or a TypeError that says what was actually passed.
    
    :func:`to_id` and :meth:`Agent.resolve_id` are pass-throughs with no ``else`` branch -
    an ``Agent`` / ``CloseData`` / ``SpawnData`` is unwrapped to its ``.id`` and EVERYTHING
    ELSE is returned untouched. So a dict, a Vec3, a nested list or a ``dict_keys`` view
    reaches the set construction in :func:`to_set` unchanged, and Python raises
    ``unhashable type: 'dict'`` against a set literal in this file. That message names
    neither the resolver nor the argument, and the frame it is reported against is the
    least useful one in the stack - the mission author is told about query.py, not about
    the ``link()`` / ``add_role()`` call their script made.
    
    RAISING, NOT DROPPING. The list resolvers next door legitimately drop what they cannot
    resolve, but every :func:`to_set` caller is a WRITE - link, add_role, target, brain_add,
    modifier_add - so swallowing a bad argument turns the write into a no-op with nothing
    logged. That is the LM #719 failure mode, where a silently skipped write cost far more
    to find than a crash would have. Bad data should be loud; it just has to say what it is.
    
    Only genuinely unusable values are rejected, tested by hashability rather than by an
    allowlist of accepted types. Every value that works today still works - this converts
    an opaque crash into an explained one and changes nothing else."""
def all_objects_exists (the_set):
    """Return whether every object in a collection exists in the simulation.
    
    Args:
        the_set (Agent | int | set[Agent | int] | list[Agent | int]): One or
            more agent IDs or objects.
    
    Returns:
        bool: ``True`` if all objects exist; ``False`` if any is missing."""
def are_variables_defined (keys):
    """Return whether all named variables are defined in the current MAST task.
    
    Args:
        keys (str): Comma-separated variable names to check.
    
    Returns:
        bool: ``True`` if every key is defined in the current task scope."""
def dec_disable_client_comms_selection (client_id):
    ...
def dec_disable_client_grid_selection (client_id):
    ...
def dec_disable_client_science_selection (client_id):
    ...
def dec_disable_client_selection (client_id, console_selected_UID):
    """Reverse an :func:`inc_disable_client_selection` call.
    
    Args:
        client_id (Agent | int): The console (client) to restore.
        console_selected_UID (str): The blob key for the console."""
def dec_disable_client_weapons_selection (client_id):
    ...
def dec_disable_grid_selection (id_or_obj):
    ...
def dec_disable_science_selection (id_or_obj):
    ...
def dec_disable_selection (id_or_obj, console_selected_UID):
    """Decrement the disable-count for a console selection.
    
    Reverses an ``inc_disable_selection`` call. When the counter reaches zero
    the console is no longer suppressed.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"weapon_target_UID"``)."""
def dec_disable_weapons_selection (id_or_obj):
    ...
def get_comms_selection (id_or_not):
    """Return the ID of the object currently selected on the comms console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_crew (id_or_obj):
    """Get the crew string of a space object (defaults to the side from shipData).
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The crew string, or ``""`` if the object does not exist."""
def get_data_set_value (id_or_obj, key, index=0, default=None):
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
        any: The stored value, ``default`` if the object or key is not found."""
def get_engine_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID, object, or SpawnData.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if not found."""
def get_grid_selection (id_or_not):
    """Return the ID of the object currently selected on the engineering grid console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_origin (id_or_obj):
    """Get the origin string of a space object (defaults to the side from shipData).
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The origin string, or ``""`` if the object does not exist."""
def get_race (id_or_obj):
    """Return the race string of a space object (defaults to side from shipData).
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The race string, or ``""`` if the object does not exist."""
def get_science_selection (id_or_not):
    """Return the ID of the object currently selected on the science console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_side (id_or_obj):
    """Return the side string of an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The side string, or ``""`` if the object does not exist."""
def get_side_display (id_or_obj):
    """Return the display name of an agent's side.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: The side display string, or ``""`` if the object does not exist."""
def get_weapons_selection (id_or_not):
    """Return the ID of the object currently selected on the weapons console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def inc_disable_client_comms_selection (client_id):
    ...
def inc_disable_client_grid_selection (client_id):
    ...
def inc_disable_client_science_selection (client_id):
    ...
def inc_disable_client_selection (client_id, console_selected_UID):
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
    
    KNOWN LIMITATION: this does not fully hold for a ship's INTERIOR view. On a real
    console a display-only second view still moves the grid highlight - the engine owns
    that selection and the write-back does not stick. Gate `//point/grid` on the client's
    role as well, which is what actually stops a display console driving anybody. The
    other surfaces are untested in the engine.
    
    Pair with :func:`dec_disable_client_selection`; the count nests.
    
    Args:
        client_id (Agent | int): The console (client) that must not select.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"grid_selected_UID"``)."""
def inc_disable_client_weapons_selection (client_id):
    ...
def inc_disable_grid_selection (id_or_obj):
    ...
def inc_disable_science_selection (id_or_obj):
    ...
def inc_disable_selection (id_or_obj, console_selected_UID):
    """Increment the disable-count for a console selection and clear it.
    
    Increments an internal counter tracking how many callers have suppressed
    the selection for this console, then zeroes the console's selected UID
    in the blob so the console has no active target.
    
    Args:
        id_or_obj (Agent | int): The player ship agent ID or object.
        console_selected_UID (str): The blob key for the console (e.g.
            ``"weapon_target_UID"``)."""
def inc_disable_weapons_selection (id_or_obj):
    ...
def is_alt_ship_target (id):
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
        bool: ``True`` if the id is 0 or a space-object id."""
def is_client_id (id):
    """Return whether an ID belongs to a client (player console) agent.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the client-console bit (0x8000…) is set."""
def is_grid_object_id (id):
    """Return whether an ID belongs to an engineering-grid object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the grid-object bit (0x2000…) is set."""
def is_space_object_id (id):
    """Return whether an ID belongs to a space object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set."""
def is_story_id (id):
    """Return whether an ID belongs to a story agent (not an engine object, e.g. Fleets).
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the ID has the story-object bit set."""
def is_task_id (id):
    """Return whether an ID belongs to a MAST task.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the task-id bit (0x0080…) is set."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def random_id (the_set):
    """Return the ID of a randomly chosen element from a collection.
    
    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
    
    Returns:
        int | None: A random agent ID, or ``None`` if the collection is empty."""
def random_object (the_set):
    """Return a randomly chosen agent object from a collection.
    
    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
    
    Returns:
        Agent | None: A random agent, or ``None`` if the collection is empty."""
def random_object_list (the_set, count=1):
    """Return a list of randomly chosen agent objects from a collection.
    
    Args:
        the_set (set[Agent | int]): A set or list of agent IDs or objects.
        count (int, optional): Number of objects to pick. Defaults to 1.
    
    Returns:
        list[Agent]: Randomly selected agents (may contain duplicates)."""
def safe_int (s, defa=0):
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
        int: The converted integer, or ``defa``."""
def set_comms_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the comms console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_console_selection (id_or_not, other_id_or_obj, console):
    """Set the selected object for a named console on a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select, or ``0`` to clear.
        console (str): The blob key for the console (e.g. ``"comms_target_UID"``)."""
def set_data_set_value (to_update, key, value, index=0):
    """Set a value in the engine data-set (blob) for one or more space or grid objects.
    
    If ``to_update`` is a set or list, the value is applied to each member.
    
    Args:
        to_update (Agent | int | set[Agent | int] | list[Agent | int]): The
            agent(s) to update.
        key (str): The data-set key.
        value (any): The value to store.
        index (int, optional): The slot index within that key. Defaults to 0."""
def set_grid_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the engineering grid console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_science_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the science console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def set_weapons_selection (id_or_not, other_id_or_obj):
    """Set the selected object on the weapons console of a player ship.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
        other_id_or_obj (Agent | int): The object to select."""
def to_agent_list (the_set):
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
        list[Agent]: resolved agents; unresolvable entries are dropped."""
def to_blob (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_data_set``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_client_object (other: sbs_utils.agent.Agent | int):
    """Resolve a client/console ID or Agent to its Agent object.
    
    Returns ``None`` when the ID is not a valid client ID or the agent no
    longer exists.
    
    Args:
        other (Agent | int): Client ID or agent to resolve.
    
    Returns:
        Agent | None: The client agent, or ``None``."""
def to_data_set (id_or_obj):
    """Return the engine data-set (blob) for an agent. Same as ``to_blob``.
    
    Args:
        id_or_obj (Agent | int | SpawnData): Agent ID or object.
    
    Returns:
        data_set | None: The engine data-set, or ``None`` if the object does
            not exist."""
def to_engine_object (id_or_obj):
    """Return the C++ engine-object pointer for an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        pointer | None: The underlying C++ engine-object, or ``None`` if the
            agent does not exist."""
def to_grid_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a GridObject agent.
    
    Returns ``None`` when the ID is not a grid-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The grid-object agent, or ``None``."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_id_list (the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded."""
def to_list (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a list.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        list: A list containing whatever was passed in; ``None`` becomes ``[]``."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_py_object_list (the_set):
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
            ``Agent.all``."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def to_space_object (other: sbs_utils.agent.Agent | int):
    """Resolve an ID or Agent to a SpaceObject agent (NPC, player, or terrain).
    
    Returns ``None`` when the ID is not a space-object ID or the object no
    longer exists.
    
    Args:
        other (Agent | CloseData | int): ID or agent to resolve.
    
    Returns:
        Agent | None: The space-object agent, or ``None``."""
def to_space_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of SpaceObject agents (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Space-object agents only; grid/client IDs are excluded."""
