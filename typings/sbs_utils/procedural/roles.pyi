from sbs_utils.agent import Agent
def _role_expr_match (so, toks):
    ...
def _role_expr_tokenize (expr):
    ...
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    THE SERVER CONSOLE COUNTS. `to_object(0)` returns None by design, so this used to
    be a silent no-op for client id 0 - and LM's main screen adds `console, mainscreen`
    to its own client id. On the server window that role was never added, so every
    audience narrowed with `any_role("mainscreen")` - a hail placed on the main screen,
    a hero card, a lower third - resolved to nobody and drew nothing, with no error.
    `to_agent_list` resolves the server the same way `get_inventory_value` always has.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def all_roles (roles: str):
    """Return the set of agent IDs that hold every one of the given roles.
    
    Args:
        roles (str): A comma-separated list of role names.
    
    Returns:
        set[int]: IDs of agents that have all specified roles."""
def any_role (roles: str):
    """Return the set of agent IDs that hold at least one of the given roles.
    
    Args:
        roles (str): A single role name or a comma-separated list.
    
    Returns:
        set[int]: IDs of agents with any of the specified roles."""
def get_role_list (id_or_obj):
    """Return the list of role names held by an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        list[str]: Role names, or an empty list if the agent does not exist."""
def get_role_string (id_or_obj):
    """Return a comma-separated string of role names held by an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
    
    Returns:
        str: Comma-separated role names, or ``""`` if the agent does not exist."""
def has_any_role (so, roles):
    """Return whether an agent holds at least one of the given roles.
    
    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.
    
    Returns:
        bool: ``True`` if the agent has one or more of the roles."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Answers for the SERVER console too. It used to always say False for client id 0,
    which reads exactly like "the role is not there" - so a check on the server was
    indistinguishable from a real negative and passed silently for years.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def has_roles (so, roles):
    """Return whether an agent holds all of the given roles.
    
    Args:
        so (Agent | int): Agent ID or object.
        roles (str): A comma-separated list of role names.
    
    Returns:
        bool: ``True`` if the agent has every role in the list."""
def remove_role (agents, role):
    """Remove a role from one or more agents.
    
    Reaches the server console, for the same reason :func:`add_role` does - and it has
    to be the same set, or a console that could gain a role could never lose it.
    
    Args:
        agents (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to remove."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def role_allies (id_or_obj):
    """Return the set of agent IDs allied with the specified object.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object.
    
    Returns:
        set[int]: IDs of all agents on allied sides."""
def role_ally_add (id_or_obj, side):
    """Add a side to an agent's ally list.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object to update.
        side (str): The side name to add as an ally."""
def role_ally_remove (id_or_obj, side):
    """Remove a side from an agent's ally list.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): The agent ID or object to update.
        side (str): The side name to remove from the ally list."""
def role_are_allies (id_or_obj, other_id_or_obj):
    """Return whether two objects share any allied side.
    
    Deprecated as of v1.3.0. Prefer the Sides system.
    
    Args:
        id_or_obj (Agent | int): First agent ID or object.
        other_id_or_obj (Agent | int): Second agent ID or object.
    
    Returns:
        bool: ``True`` if both objects have at least one allied side in common."""
def role_matches (so, expr):
    """Return whether an agent satisfies a role EXPRESSION.
    
    The expression combines role names (a ship's side counts as a role) with set-style
    operators, evaluated for the single agent ``so``:
    
    * ``|`` OR       -- ``"__player__ | tsn"``     (a player OR a tsn ship)
    * ``&`` AND      -- ``"__player__ & tsn"``     (a tsn player)
    * ``-`` AND-NOT  -- ``"__player__ - cockpit"`` (a player that is not a fighter)
    * ``!`` NOT      -- ``"!tsn"``                 (anything not tsn); ``-`` is BINARY
    * ``( )`` group  -- ``"(tsn | raider) & !__player__"``
    
    Precedence high->low: ``!``, then ``&``/``-`` (left to right), then ``|`` -- use
    parentheses for other groupings. An empty/None expression matches nothing.
    
    Args:
        so (Agent | int): Agent ID or object to test.
        expr (str): The role expression.
    
    Returns:
        bool: ``True`` if the agent satisfies the expression."""
def roles_matching (expr):
    """Return the set of agent IDs that satisfy a role expression (see :func:`role_matches`).
    
    Args:
        expr (str): The role expression (``| & - !`` and parentheses).
    
    Returns:
        set[int]: IDs of all agents matching the expression."""
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
def to_client_object (other: sbs_utils.agent.Agent | int):
    """Resolve a client/console ID or Agent to its Agent object.
    
    Returns ``None`` when the ID is not a valid client ID or the agent no
    longer exists.
    
    Args:
        other (Agent | int): Client ID or agent to resolve.
    
    Returns:
        Agent | None: The client agent, or ``None``."""
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
