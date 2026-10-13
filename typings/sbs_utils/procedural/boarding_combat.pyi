def _calm_outcome (agent_id, speaker, tokens):
    ...
def _cells (value):
    ...
def _dismiss_outcome (agent_id, speaker, tokens):
    ...
def _face (spec):
    """A person's `Face:` - a face string as written, or a keyword (`female`, `male`,
    `terran`) resolved ONCE, here, so they keep one face all mission. None: no face,
    which is right for anyone the face art cannot draw."""
def _hostile_hit (rec, setting, by=None):
    """What a shot does to a hostile, by setting."""
def _hostile_step (rec, now):
    ...
def _hostiles_restore (blob):
    """REPLACE the ledger with what a save says, and bring anybody already declared (and
    not standing on a map) into line with it. Announces nothing."""
def _hostiles_snapshot ():
    ...
def _in_parley (area):
    """Whether some crew member in this area is mid-conversation with someone here.
    Nobody fights while that is going on - a parley that gets you shot is not one."""
def _name (who):
    ...
def _norm (s):
    ...
def _now ():
    ...
def _num (v, default):
    ...
def _on_ground_signal (name, data):
    """Every emit, as it happens: anybody `Hidden until:` this signal arrives."""
def _party_in (area):
    ...
def _persist_provider_register (name, snapshot_fn, restore_fn, library=False):
    """Register a state provider under `name`. Re-registering a name replaces it.
    
    If a save was already restored this mission and it held a blob under this name,
    the new provider is handed it at once - so a provider that registers late (an
    addon that loads after the campaign was opened) is not left empty.
    
    `library=True` is for sbs_utils' own modules, which register once as they
    import: the per-mission reset keeps those and drops the rest."""
def _rouse_outcome (agent_id, speaker, tokens):
    ...
def _saved_apply (rec):
    ...
def _saved_touch ():
    ...
def _summon_outcome (agent_id, speaker, tokens):
    ...
def _tell (lifeform, text):
    ...
def _walking (rec):
    ...
def amd_yes (value, default=False):
    """Read one authored yes/no. THE parser: the schema, the props and the people on a
    boarding party's ground all read a flag through this, so `Blocks: yes` cannot mean
    one thing to the reader and another to the map.
    
    A real bool passes through (the reader has already coerced a declared field); nothing
    written is `default`; anything that is not a yes word is no - which is why a typo
    needs the linter to say so."""
def boarding_can_act (lifeform):
    """Up, and not stunned."""
def boarding_combat_clear ():
    ...
def boarding_combat_count ():
    """Reset-ledger probe."""
def boarding_combat_install ():
    """Make map clicks reach talkable hostiles. Idempotent."""
def boarding_crew_stunned (lifeform):
    ...
def boarding_drop_sprite (sprite):
    """The atlas key a dropped item is drawn with."""
def boarding_heal (lifeform, amount=1):
    ...
def boarding_hostile (key):
    ...
def boarding_hostile_calm (key, calm=True):
    """Stand a hostile down (a parley worked) - or set it off again."""
def boarding_hostile_click (client_id, area, x, y):
    """Tile-click handler: a person with a ``Talk scene`` is TALKED to when clicked -
    from close up. Further off, the crew member walks over and talks on arrival."""
def boarding_hostile_dismiss (key):
    """Take an actor off the map without a fight - an NPC who leaves, a youngster who
    goes with the party."""
def boarding_hostile_forget (key):
    """Take somebody off the map AND forget them - the twin of ``boarding_prop_forget``,
    for a crowd that was only ever there for one visit. No signal, no drop, nothing
    saved."""
def boarding_hostile_of (actor_id):
    ...
def boarding_hostile_records (section):
    ...
def boarding_hostile_remove (key):
    """Take somebody off the map and KEEP the record, so ``boarding_hostiles_place`` can
    stand them somewhere again - the twin of ``boarding_prop_remove``. Nobody is hurt:
    somebody up is back to how they were declared (calm or not), somebody down stays
    down. False when they were not on a map."""
def boarding_hostile_reveal (key):
    ...
def boarding_hostile_state (key):
    ...
def boarding_hostiles (area=None, alive=True):
    ...
def boarding_hostiles_declare (section, generated=False):
    """Remember everybody in a section. Returns the keys. Nobody is placed yet.
    
    ``generated`` marks a crowd made by code for one visit (a boarded ship's own crew):
    a saved game neither keeps nor restores who among them is down."""
def boarding_hostiles_place (area=None):
    """Put declared hostiles on their areas. Safe to call again."""
def boarding_hostiles_saved_count ():
    """Reset-ledger probe: how many people a saved game is still speaking for."""
def boarding_hostiles_tick (t=None):
    """One pass over every hostile. Guarded per hostile - one bad record must not stop
    the tick, which would pause the mission."""
def boarding_hostiles_unwatch ():
    ...
def boarding_hostiles_watch (seconds=0.5):
    ...
def boarding_hp (lifeform):
    ...
def boarding_hurt (lifeform, amount=1, by=None):
    """Wound a crew member. Returns the HP left."""
def boarding_is_down (lifeform):
    ...
def boarding_revive (lifeform, hp=None, by=None):
    """Bring a downed crew member back to their feet (default: half health)."""
def boarding_strike (area, x, y, radius=2, setting='full'):
    """Fire support from orbit: everything hostile within ``radius`` of a cell.
    
    Crew caught in it are hurt too - the bridge is firing blind at a point on a map.
    Somebody CALM is not harmed, as with any shot, and no prop is touched.
    Returns the hostile keys that went down."""
def boarding_stun_crew (lifeform, seconds):
    ...
def boarding_talk (client_id, key):
    """Open this person's talk scene for this console. True when it opened."""
def boarding_tile_fire (client_id, x, y):
    """Shoot the cell this console clicked. A shot disarms, whatever happens.
    
    WHAT A SHOT DOES, one rule for every setting and every thing:
    
    - **a hostile** is shot: STUN holds them still, CUT takes a hit point, FULL puts
      them down whatever their health;
    - **somebody CALM** (`Calm: yes`, or calmed by an answer) is NOT HARMED, by any
      setting - the shot is refused and says ``calm``;
    - **a prop is NEVER REMOVED.** A shut prop whose `Opens with:` lists ``cut`` is
      OPENED by CUT or by FULL, exactly as cutting it always did. Every other prop - a
      terminal, a beacon, a door that only a key or a signal opens, a pickup, a bunk -
      is ``scorched`` and stays where it is, as shut as it was. STUN does ``nothing``;
    - a cell holding a hostile AND a prop: the hostile is the one hit, wherever each
      was put down first. People before things.
    
    Returns True when something was hit, and always reports through ``xess_fired``
    (``XESS_EFFECT``: ``stunned`` / ``wounded`` / ``down`` / ``opened`` / ``scorched`` /
    ``nothing``; ``XESS_DESTROYED`` is never true of a prop)."""
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
