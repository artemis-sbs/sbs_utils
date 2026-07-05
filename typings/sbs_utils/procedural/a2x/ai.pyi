def add_ai (agent, ai_type, data=None):
    """Attach a brain to ``agent`` matching a 2.8 ``add_ai`` block ``type``.
    
    Args:
        agent: the ship handle (id, object, or the value from a2x_create_*).
        ai_type (str): the 2.8 AI block type (e.g. ``"CHASE_PLAYER"``).
        data (dict, optional): variables passed to the brain label.
    
    Returns:
        str | None: the brain name added, or ``None`` if the type has no mapping."""
def ai_brain_for (ai_type):
    """2.8 AI block type -> a Cosmos brain label name, or ``None`` if unmapped."""
def clear_ai (agent):
    """2.8 ``clear_ai``: remove the agent's brain stack."""
