def _near_any (x, y, z, pts, r2):
    ...
def _player_points ():
    """(x,y,z) of every player, or None if there are no players."""
def brain_pause (agent_id_or_set, paused=True):
    """Pause (or resume) one or more agents' brains without removing them.
    
    A paused brain is skipped by ``brains_run_all`` until resumed - used when an
    object is parked on the standby list so its brain doesn't act on a
    non-simulated object. The brain tree is preserved (unlike ``brain_clear``).
    
    Args:
        agent_id_or_set: Agent ID, object, or set/list of either.
        paused (bool, optional): True to pause, False to resume. Defaults True."""
def brain_resume (agent_id_or_set):
    """Resume one or more agents' brains (see ``brain_pause``)."""
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
def standby_cull_clear ():
    """Retrieve everything parked and forget it - call before clearing a system
    on a jump, so parked terrain returns to normal space and gets despawned with
    the rest (delete-by-box only sees objects in normal space, not standby)."""
def standby_cull_count ():
    """How many objects are currently parked (diagnostics): loose objects + fleet
    ships."""
def standby_cull_fleets (fleet_role, radius):
    """Park/retrieve whole fleets by proximity. A fleet (an agent with `fleet_role`
    whose ships are linked under "ship_list") is parked when no player is within
    `radius` of ANY of its ships: every ship goes to standby and the fleet's brain
    is paused (it lives on the fleet agent). It is retrieved the moment a player
    comes near. Treating the formation as one unit keeps the fleet brain from
    steering non-simulated ships."""
def standby_cull_step (candidates, radius):
    """Park candidates with no player within `radius` (out of the engine
    network); retrieve parked ones once a player comes near. `candidates` is an
    iterable of Agents (e.g. a role set); non-space agents that share a role are
    skipped. A parked self-brained NPC has its brain paused while parked."""
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
