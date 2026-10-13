def _check_outcome (agent_id, speaker, tokens):
    """The ``check <skill> <dc> [else <target>]`` outcome verb."""
def _check_unreadable (tokens):
    """Say that a `check` could not be read - where the author will see it.
    
    Nothing was rolled, and the choice carried on as if the roll had worked: a locked
    door that is open, with no roll line in the transcript to say why. `sbs lint` reports
    the same line as `check-shape`; this is for the mission nobody linted."""
def _checks_metric (name):
    """``skill engineering`` for a guard: ``if skill engineering >= 3``."""
def _helpers (lifeform, skill):
    """Teammates standing next to this one who have the skill.
    
    On the ground that is the tile map's neighbours. In a relic nobody is on a tile, and
    `tilemap_actors_near` answers [] for a body with no cell - so a suit's check was
    always rolled alone however many of the crew were floating beside it. There the
    neighbours are the other SUITS within `EVA_HELP_RADIUS`."""
def _norm (s):
    ...
def _roll_note (lifeform, text):
    """Put the roll in the transcript of everyone in the actor's conversation - what the
    module docstring always said happened, and never did: `boarding_check` only emitted
    a signal, so a player saw the scene jump to the failure beat with no roll to explain
    why."""
def _suit_neighbours (lifeform):
    """The people in the other suits near this one's suit. [] when it is not in one."""
def _table_for (lifeform):
    ...
def boarding_check (lifeform, skill, dc, bonus=0, help=True):
    """Try something. Returns a dict: ``ok``, ``roll``, ``skill``, ``help``, ``total``,
    ``dc``, ``who``, and ``text`` - one line for a transcript.
    
    Emits ``boarding_checked`` with the same values as ``BOARDING_*`` keys."""
def boarding_checks_clear ():
    ...
def boarding_checks_count ():
    """Reset-ledger probe."""
def boarding_checks_mode (mode='dice'):
    """``"dice"`` (the default) or ``"flat"`` - no randomness."""
def boarding_checks_seed (seed):
    ...
def boarding_last_check (lifeform):
    """The last check this character made, or None."""
def boarding_skill (lifeform, name):
    """How good this character is at ``name``."""
def boarding_skills_declare (name, skills):
    """Skills for whoever is NAMED this - a crew member, before any body exists."""
def boarding_skills_from_amd (section):
    """Read ``Skills:`` off every record in an AMD section (a crew roster), by name.
    
    Nested sections are walked, so the roster file's own ``## [Watch]`` heading with its
    ``### [Person]`` children works as it is."""
def boarding_skills_parse (text):
    """``"engineering 3, science 1"`` (or a dict) -> ``{"engineering": 3, "science": 1}``."""
def boarding_skills_set (lifeform, skills):
    """Give a body its skills: ``{"engineering": 3, "athletics": 1}``."""
def dialogue_register_outcome (verb, fn, check=None):
    """Register an outcome handler: fn(agent_id, speaker, tokens) - tokens are the words
    after the verb. Returning False refuses the pick; returning ``OUTCOME_STOP`` accepts
    it but skips the outcomes after this one. (`signal` is built in.)
    
    ``check(tokens)`` may say the words after the verb cannot be read: it returns None
    when they can, or one sentence for the writer when they cannot. Every check of an
    answer runs BEFORE any of its outcomes is applied (``dialogue_apply``), so an answer
    with one bad outcome does nothing at all rather than half of what it says."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
