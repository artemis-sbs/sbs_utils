def _proceed_to_exit (agent):
    """2.8 add_ai PROCEED_TO_EXIT: leave the sector -- head for the ship's spawn point (the
    entry/exit edge), the same way a surrendered ship goes home (LM take_surrendered_home
    drives it to ``spawn_pos`` and removes it near the edge). One-shot ``target_pos`` at speed;
    a mission that wants the ship deleted on arrival can add that. Returns the type on success,
    or ``None`` if the ship / its spawn point can't be resolved."""
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
def default_enemy_ai (agent, enemies_only=True):
    """Attach 2.8's implicit default enemy behaviour to a freshly spawned NPC.
    
    ``brain_add``'s root is a Select: the children run in order and it stops at the
    first success, so this is a priority list, exactly like a 2.8 brain stack.
    ``ai_chase_current`` re-chases whatever last angered the ship (2.8 CHASE_ANGER) and
    fails harmlessly on a fresh spawn with no target, falling through to the station and
    then the player.
    
    Firing is NOT decided here: every LM chase brain gates its trigger on
    ``side_are_enemies(BRAIN_AGENT_ID, target)``, so a ship shoots only what diplomacy
    says is hostile -- and a ceasefire silently stops it. ``enemies_only`` likewise
    narrows target SELECTION to declared enemies, so an enemy will not shadow a neutral.
    
    The brain labels live in the LegendaryMissions ``ai`` addon and are resolved by NAME
    at runtime, so a2x keeps no import dependency on LM (the mission feature-detects the
    addon). Returns the brain list attached."""
def dir_throttle (agent, heading, throttle=1.0):
    """2.8 ``add_ai DIR_THROTTLE``: fly a compass heading at a throttle. Compute a far point
    along the heading from the ship and drive there with the ``goto_object_or_location`` brain
    (via ``blackboard:target_point``).
    
    HEADING CONVENTION -- VERIFY IN-ENGINE (same open question as the 2.8 ``angle`` property):
    2.8 heading is in degrees (0=N, 90=E, ...), and Cosmos mirrors X and Z about the map centre,
    so the 2.8 direction is negated here. If ships fly the wrong way, flip the ``dx``/``dz``
    signs. Returns the brain name, or ``None`` if the ship can't be resolved."""
