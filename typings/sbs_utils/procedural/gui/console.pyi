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
