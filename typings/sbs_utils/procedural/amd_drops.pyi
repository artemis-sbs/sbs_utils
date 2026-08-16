from sbs_utils.agent import Agent
def amd_drop_table (s):
    """'salvage x2-4, contraband 20%' -> [{key, low, high, chance}, ...].
    
    What a kill leaves behind. A richer shopping list than `amd_counted`, because loot
    has a RANGE and a CHANCE as well as a name:
    
        key            one, always
        key xN         N, always
        key xN-M       between N and M
        key P%         one, P of the time
        key xN-M P%    both
        none           nothing at all - an EMPTY table, which is NOT the same as having
                       no table (see `amd_drops.drops_table_for`)
    
    Lives here rather than in `amd_drops` so the stdlib-only half of the toolchain can
    read it too: the parser turns these keys into references and the linter checks them,
    and neither may import the runtime module. An already-parsed list passes through, so
    parsing twice is harmless."""
def amd_drops (section):
    """Register every record in a `## [Drops]` section. The record key is the role.
    
    `children` comes back as a LIST from some readers and a DICT from others, so both are
    accepted rather than assuming whichever one this caller happens to hold."""
def drop_table_parse (value):
    """`salvage x2-4, contraband 20%` -> [{key, low, high, chance}].
    
    The grammar itself lives in `amd.amd_drop_table`, alongside the other authored value
    types and reachable from the stdlib-only half of the toolchain - the parser turns
    these keys into references and `sbs lint` checks them, and neither may import this
    module. This name stays because it is what the mission-facing code calls."""
def drops_clear ():
    """Forget every authored table. Part of the per-mission reset."""
def drops_register (role, value):
    """Register one role's table. Re-registering a role REPLACES it."""
def drops_roll (agent_or_id):
    """(key, count) pairs this object's table actually yields on THIS kill - chances
    rolled, counts picked. Empty when the table is empty or absent."""
def drops_size ():
    ...
def drops_spawn (agent_or_id, x=None, y=None, z=None):
    """Spawn this object's authored drops at its position (or an explicit point).
    
    Returns the number of pickups spawned. Read the position BEFORE the caller deletes
    the object, or pass the point in - a destroyed object cannot be asked where it was."""
def drops_table_for (agent_or_id):
    """The authored table for this object, or None when nothing was authored.
    
    None and [] are DIFFERENT and the difference is the whole feature: None means "no
    author had an opinion, do whatever you did before", [] means "this one drops nothing"
    (`Drops: none`). Collapsing them would make `Drops: none` a no-op."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
