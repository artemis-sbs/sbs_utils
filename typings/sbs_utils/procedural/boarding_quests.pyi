from sbs_utils.agent import Agent
def _matches (lifeform, want):
    """Is `want` this person: a job of theirs, their name, or who the ROSTER says they are.
    
    The roster half matters. A body is named after whatever is on the console, and a
    player may have saved a name of their own: `For: Hale` then matched nobody on the one
    machine at the table that had done so. The seat's roster member - its key, its name,
    its last name - is who the author meant, whatever the player is called."""
def _norm (s):
    ...
def boarding_quest_holder (client_id):
    """Point this console's quest screens at its crew member."""
def boarding_quest_is_open (key):
    """True when a personal quest went to the whole party for want of its owner."""
def boarding_quest_owner (key):
    """The lifeform a personal quest went to, ``"party"``, or None."""
def boarding_quests_clear ():
    ...
def boarding_quests_count ():
    """Reset-ledger probe."""
def boarding_quests_grant (section, team=None):
    """Grant every ``For:`` quest in a section to the crew member it names.
    
    Idempotent: a quest already granted is left where it went, so this can be called
    each time somebody beams down and only the newly arrived pick theirs up.
    
    Returns:
        dict: ``{quest key: lifeform id, or "party"}`` for what was granted this call."""
def boarding_quests_of (lifeform):
    """The keys of the personal quests handed to this person, sorted. Empty for nobody."""
def boarding_quests_open_unclaimed (section):
    """Give the whole party every ``For:`` quest nobody has claimed. Call it once the
    party is settled (not on the first beam-down, or the late arrival loses theirs)."""
def boarding_transport (client_id, area):
    """Beam this console's crew member to another area. Returns ``(ok, text)``."""
def boarding_transport_jam (on=True, why='Transporter jammed'):
    """Nobody beams anywhere while this is on."""
def boarding_transport_jammed ():
    ...
def boarding_transport_targets (client_id=None):
    """Tile areas the transporter can put someone: known, and beamable."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
