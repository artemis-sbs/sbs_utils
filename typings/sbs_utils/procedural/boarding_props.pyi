def _cell (rec):
    ...
def _give_outcome (agent_id, speaker, tokens):
    ...
def _holding_metric (rest, agent_id):
    ...
def _listen (rec):
    """Hear the signals this prop wrote: `Opens with: signal X`, `Hidden until: X`."""
def _needs_ok (needs, lf):
    ...
def _norm (s):
    ...
def _note (client_id, text):
    ...
def _on_ground_signal (name, data):
    """Every emit, as it happens. One set lookup for a name no prop wrote."""
def _open_outcome (agent_id, speaker, tokens):
    ...
def _opens (value):
    ...
def _pack_outcome_check (verb):
    """What `; give` / `; take` must look like - ``<item>`` or ``<item> <how many>`` -
    as a check that runs BEFORE any outcome of the answer is applied."""
def _party_metric (rest, agent_id):
    ...
def _persist_provider_register (name, snapshot_fn, restore_fn, library=False):
    """Register a state provider under `name`. Re-registering a name replaces it.
    
    If a save was already restored this mission and it held a blob under this name,
    the new provider is handed it at once - so a provider that registers late (an
    addon that loads after the campaign was opened) is not left empty.
    
    `library=True` is for sbs_utils' own modules, which register once as they
    import: the per-mission reset keeps those and drops the rest."""
def _pickup_note (client_id, lf, rec):
    """What was picked up, in this console's Act transcript - with its picture, which is
    the sprite it lay on the map with."""
def _props_restore (blob):
    """REPLACE the ledger with what a save says, and bring anything already declared
    into line with it. Announces nothing."""
def _props_snapshot ():
    """Every prop that is open or taken now - plus what the save said about props that
    have not been declared this session (a site the crew did not go back to)."""
def _relic_verb (verb, agent_id, name):
    """`open <barrier>` / `reveal <point>` against a relic. Never raises."""
def _reveal_outcome (agent_id, speaker, tokens):
    ...
def _saved_apply (rec):
    """Make one declared prop agree with the saved game. Silent, and only ever opens or
    takes: a save cannot shut a door the crew has opened since."""
def _saved_touch ():
    ...
def _take_outcome (agent_id, speaker, tokens):
    ...
def _try_open (rec, lf):
    """Try each way this door opens that the user can manage. The first that works."""
def _walk_beside (client_id, lf, area, x, y, reach, intent, cells=None):
    """Walk to the nearest open cell within ``reach`` of (x, y) - or of any of ``cells``,
    for something bigger than one - and run ``intent`` there."""
def _yes (v, default=False):
    """One authored yes/no - the schema's own parser, so there is one reading of it."""
def boarding_field_number (value, default, label, name, key, whole=False):
    """A number a writer typed in a fence, or ``default`` when it is not one - said ONCE,
    in a writer's words, in ``mast.runtime.log``. NEVER RAISES: `Qty: two` used to raise
    inside the load, and a mission with one bad number had no ground at all.
    
    Args:
        value: what was written (None or empty is simply "not written").
        default: what the game uses instead.
        label (str): the field as the writer spells it - ``Qty``.
        name, key: the record, for the sentence.
        whole (bool): a count of things or cells - a fraction is not one."""
def boarding_give (lifeform, item, n=1):
    """Put ``n`` of ``item`` in a character's pack. Returns the new count."""
def boarding_hand_over (giver, taker, item, n=1):
    """One crew member passes something to another."""
def boarding_holding (lifeform, item):
    ...
def boarding_interact (client_id, key):
    """Use a prop. Returns ``(result, text)``.
    
    Results: ``hidden``, ``refused``, ``opened``, ``failed``, ``locked``, ``picked``,
    ``scene``, ``looked``. Emits ``boarding_interacted`` with the result."""
def boarding_last_note (client_id):
    """The last thing this console was told by a prop - for the device to show."""
def boarding_metric_word (word, fn):
    """Answer guards of the form ``<word> <argument>`` - ``if holding medkit >= 1``.
    
    ``fn(argument, agent_id)`` returns a number. The word is the first token of the
    guard's left side; a guard that is only the word (no argument) is still a role."""
def boarding_pack (lifeform):
    """``{item: count}`` this character is carrying."""
def boarding_party_holding (item):
    """How many of ``item`` the whole party is carrying between them."""
def boarding_prop (key):
    """The prop record, or None."""
def boarding_prop_add (key, area, at, **fields):
    """Declare one prop from code. Fields as in the AMD (snake_case)."""
def boarding_prop_at (area, x, y):
    ...
def boarding_prop_click (client_id, area, x, y):
    """The tile-click handler: use a prop in reach, or walk up to one and use it there."""
def boarding_prop_forget (key):
    """Take a prop off the map AND forget it - for something that was only ever there
    for a while (rubble on a node that has been repaired). A removed prop keeps its
    record, so ``boarding_props_place`` would put it back."""
def boarding_prop_is_open (key):
    ...
def boarding_prop_is_scenery (rec):
    """True for a prop with nothing to it - no scene, item, lock, need or description.
    
    Scenery furnishes a map (a bunk, a console bank, a barrel) and blocks like any prop,
    but nothing lists it or offers to use it, and a click on it walks toward it."""
def boarding_prop_of (actor_id):
    """The prop key standing as this tile actor, or None."""
def boarding_prop_open (key, how='opened'):
    """Open a door or hatch: its cell can be walked and it draws open."""
def boarding_prop_records (section):
    """Prop records from an AMD section, as plain dicts."""
def boarding_prop_remove (key):
    """Take a prop off the map (picked up, destroyed)."""
def boarding_prop_reveal (key):
    """A hidden prop can now be found."""
def boarding_props (area=None):
    ...
def boarding_props_clear ():
    ...
def boarding_props_count ():
    """Reset-ledger probe."""
def boarding_props_declare (section):
    """Remember every prop in a section. Returns the keys. Nothing is placed yet."""
def boarding_props_install ():
    """Make map clicks reach props. Idempotent; a mission calls it once."""
def boarding_props_near (lifeform, reach=1):
    """Props within ``reach`` of this character, nearest first. Scenery is left out. A big
    prop is measured to its nearest cell, so the far end of a car is as near as the end
    you are standing by."""
def boarding_props_place (area=None):
    """Put declared props onto their tile areas. Returns how many were placed.
    
    Safe to call again: a prop already placed is left where it is."""
def boarding_props_saved_count ():
    """Reset-ledger probe: how many props a saved game is still speaking for."""
def boarding_props_scenes (scenes):
    """The dialogue scenes a prop's ``Scene:`` names (from ``dialogue_scenes``)."""
def boarding_props_signal (name):
    """Open every prop whose ``Opens with`` names ``signal <name>``. Returns the keys.
    
    What a bridge action is wired to: the ship powers the Lantern, the Lantern's doors
    open. The library calls this itself when the signal is emitted (see ``_listen``); a
    mission calls it only to open those doors WITHOUT the signal."""
def boarding_take_item (lifeform, item, n=1):
    """Take ``n`` of ``item`` out of a pack. False (and nothing taken) if short."""
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
