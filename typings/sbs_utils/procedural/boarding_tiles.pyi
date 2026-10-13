def _discover_outcome (agent_id, speaker, tokens):
    """`discover caves` - the party now knows an area exists (a map, a survivor's word)."""
def _on_signal (name, data):
    """A crew member who changes area leaves the conversation they were in: a side scene
    happens SOMEWHERE."""
def boarding_tile_area_of (client_id):
    """The tile area this console is in, or None."""
def boarding_tile_clear ():
    ...
def boarding_tile_click (client_id, area, x, y):
    """One map click, as policy. What ``gui_tilemap(on_click=...)`` should be given.
    
    Order: an armed device fires; then anything registered with
    ``boarding_tile_click_handler`` may claim the cell (a prop to use, somebody to talk
    to); otherwise the character walks there."""
def boarding_tile_click_handler (fn):
    """Let something else claim a map click first (a prop, a hostile). Idempotent."""
def boarding_tile_leave (client_id):
    """Take this console's character off the tile world."""
def boarding_tile_on (client_id):
    """Whether this console's body is standing on a tile world."""
def boarding_tile_put (client_id, area, at=None):
    """Stand this console's character in a tile area. Returns its actor record."""
def boarding_tile_style (sprite=None, colors=None):
    """How crew bodies are drawn: an atlas key, and a color per crew member in turn."""
def boarding_tile_where (client_id):
    """``(area, x, y)`` for this console's body, or None."""
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
