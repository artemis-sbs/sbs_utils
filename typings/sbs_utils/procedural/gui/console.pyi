from sbs_utils.helpers import FrameContext
def all_roles (roles: str):
    """Return the set of agent IDs that hold every one of the given roles.
    
    Args:
        roles (str): A comma-separated list of role names.
    
    Returns:
        set[int]: IDs of agents that have all specified roles."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_activate_console (console):
    """Set the current page's active console name.
    
    Marks the page as running a specific console type, which affects which
    console-specific routes and widgets respond to this client.
    
    Args:
        console (str): Console name, e.g. ``"helm"``, ``"weapons"``,
            ``"science"``.
    
    Example:
        gui_activate_console("helm")"""
def gui_console (console, is_jump=False):
    """Activate a standard console with its default engine widget layout.
    
    Sets the engine widget list for the named console using the built-in
    configuration. Supported values: ``"helm"``, ``"weapons"``,
    ``"science"``, ``"engineering"``, ``"comms"``, ``"cinematic"``,
    ``"mainscreen"``, ``"cockpit"``.
    
    Args:
        console (str): Console name (case-insensitive).
        is_jump (bool, optional): For ``"helm"`` only — include jump-drive
            controls in the widget list. Defaults to ``False``.
    
    Example:
        gui_console("helm")
        gui_console("helm", is_jump=True)"""
def gui_console_clients (path, for_ships=None):
    """Return the set of client IDs that have a specific console type.
    
    Searches all player ships (or the given ship set) for linked console
    clients whose role matches ``console,{path}``.
    
    Args:
        path (str): Console path to match, e.g. ``"helm"`` or ``"science"``.
        for_ships (object | None, optional): Agent ID, object, or set of ships
            to search. Defaults to all ``__player__`` ships.
    
    Returns:
        set: Client IDs that have a console matching ``path``.
    
    Example:
        helm_clients = gui_console_clients("helm")"""
def gui_console_enter (client_id, console_type, ship=None):
    """THE ONE DOOR. Call this FIRST whenever a console becomes something else.
    
    A console that arrives somewhere carrying the last screen's furniture is the
    single most common transition bug in this codebase, and every mission used to
    have to remember seven separate pieces of trivia to avoid it. This is those
    seven, in the order that works.
    
    **It fires on a CHANGE of console type, not on a repaint.** A screen is
    re-entered every time it repaints - LegendaryMissions' main screen jumps back
    to itself on the viewscreen signal - so clearing on every reroute would tear
    down the furniture the screen just raised. Passing the type it already is
    is a no-op, so putting this at the top of a console label costs nothing.
    
    In order, and each step is here because it bit somebody:
    
    1. **Overlays.** They belong to the CONSOLE, not the page, and the page object
       survives a reroute - so ``present_all`` re-draws whatever the slots still
       hold, and the catch-up ticker re-delivers any live record it finds an empty
       slot for. ``overlay_clear_console`` defeats both.
    2. **The viewscreen claim.** A console that was driving its ship's main screen
       gives it back rather than holding it from a station that no longer has the
       control. Leaving a story claim held by a console nobody is sitting at parks
       every later crew request forever.
    3. **The camera.** A shot ASSIGNS its console to the object the lens rides, so
       a console leaving mid-shot is still riding an enemy ship.
    4. **Every console role, stripped** - or a screen that used to be a main screen
       keeps answering as one.
    5. **The role AND ``CONSOLE_TYPE``, both.** Role without ``CONSOLE_TYPE`` means
       main-screen view routes never find it; ``CONSOLE_TYPE`` without the role
       means overlays, ``announce()`` and comms drop the message in SILENCE,
       because every audience narrows through ``any_role``.
    6. **The crew seat.** A seat is believed only while the client's own
       ``CONSOLE_TYPE`` still agrees with it, so changing console frees it as a side
       effect and the player's name and face vanish. Re-asserted with an explicit
       pick, which is deterministic where letting it re-resolve is not.
    7. **The engine widget list.** A console leaves its native widgets behind and
       the page underneath draws through them.
    
    Args:
        client_id (int): the console.
        console_type (str): what it is becoming - ``"helm"``, ``"mainscreen"``, a
            mission's own console name.
        ship (optional): the ship it belongs to. Defaults to its home ship.
    
    Returns:
        bool: True if the console actually changed, False if it already was this."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
