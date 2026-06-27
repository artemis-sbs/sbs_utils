"""Legacy-style AI: 2.8 ``add_ai`` / ``clear_ai`` -> Cosmos brain behaviours.

2.8 ships have a "brain stack" of AI blocks (CHASE_PLAYER, CHASE_STATION, ...).
Cosmos uses behaviour-tree brains attached with the core ``brain_add``. This maps the
common 2.8 block types to the LegendaryMissions ``ai`` brain labels (referenced by
name -- ``brain_add`` resolves strings at runtime, so ``a2x`` carries no import
dependency on LegendaryMissions; the mission feature-detects the ``ai`` addon).

Unmapped 2.8 block types (POINT_THROTTLE, PROCEED_TO_EXIT, DEFEND, GUARD_STATION,
elite SPCL_AI, monster-only blocks, ...) return ``None`` so the caller can leave a
TODO -- "close enough" rather than a wrong brain.
"""

# 2.8 add_ai 'type' -> LegendaryMissions ai brain label name.
_AI_BRAIN = {
    "CHASE_PLAYER": "ai_chase_player",
    "CHASE_STATION": "ai_chase_station",
    "CHASE_AI_SHIP": "ai_chase_npc",
    "CHASE_NEUTRAL": "ai_chase_npc",
    "ATTACK": "ai_chase_current",
    "TARGET_THROTTLE": "ai_chase_current",
}


def ai_brain_for(ai_type):
    """2.8 AI block type -> a Cosmos brain label name, or ``None`` if unmapped."""
    return _AI_BRAIN.get((ai_type or "").strip().upper())


def add_ai(agent, ai_type, data=None):
    """Attach a brain to ``agent`` matching a 2.8 ``add_ai`` block ``type``.

    Args:
        agent: the ship handle (id, object, or the value from a2x_create_*).
        ai_type (str): the 2.8 AI block type (e.g. ``"CHASE_PLAYER"``).
        data (dict, optional): variables passed to the brain label.

    Returns:
        str | None: the brain name added, or ``None`` if the type has no mapping.
    """
    from sbs_utils.procedural.brain import brain_add

    name = ai_brain_for(ai_type)
    if name is None:
        return None
    brain_add(agent, name, data=data)
    return name


def clear_ai(agent):
    """2.8 ``clear_ai``: remove the agent's brain stack."""
    from sbs_utils.procedural.brain import brain_clear

    brain_clear(agent)
