from sbs_utils.mast.mast_node import MastDataObject
def amd_lifeform_data (text):
    """Parse one lifeform fence into a data dict (default coercion - all fields are strings).
    Use as the ``data_parser`` for a cast-only .amd; a consolidated mission file uses
    ``amd_mission_data`` and its lifeform fences fall through to the same default coercion."""
def amd_parse_facts (text, handler=None, default=<function amd_num at 0x0000011CF6E5F4C0>, archetype=None, errors=None):
    """Parse one fact-sheet fence into a dict.
    
    Per label, in order: the caller's `handler` gets first refusal (returns truthy to
    consume it); then the FIELD REGISTRY, when the field is declared for `archetype` -
    which resolves the alias, coerces by the declared type and stores under the runtime
    key; then `default` (historically `amd_num`) for anything undeclared, so an unknown
    field behaves exactly as it does today.
    
    `errors` may be a list - parse problems are appended to it in a writer's terms
    rather than raised, so a typo never takes a mission down; the linter is what makes
    them loud. Returns `data`, carrying the kind line (when present) under `KIND_KEY`."""
def face_resolve (spec):
    """Resolve a declarative face spec to a face string. A KEYWORD (terran / male / female /
    fluid) -> a fresh random face of that kind; a literal face string -> itself unchanged;
    None/empty -> a random terran. Lets AMD/data author a face as a simple word instead of a
    raw face string. (Promoted from Open Universe's lifeform_face.)"""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def lifeform_from_record (record, host_id=None):
    """Spawn one authored lifeform: name + ``face_resolve(Face)`` + Roles, optionally hosted on
    ``host_id``, with the record's ``Path`` as its comms voice and ``Color`` as its card colour.
    A ``Scene`` (if any) and the record ``key`` are stored on the lifeform for a dialogue bridge.
    Returns the spawned lifeform Agent.
    
    Idempotent on (record ``key``, ``host_id``): a character already cast on that host is
    returned as-is, so re-running a section - a map body that runs twice, a re-emitted
    setup signal - does not create a second copy of the same person. The same section cast
    onto a DIFFERENT host still produces its own character."""
def lifeform_key_role (key, host_id=None):
    """The role marking the lifeform spawned for AMD ``key`` on ``host_id``.
    
    Keyed on key AND host: `lifeforms_spawn(section, host_id)` legitimately casts the same
    section onto several hosts (one crew roster, many stations), and keying on the record
    alone would make the second host silently resolve to the first host's character."""
def lifeform_of_key (key, host_id=None):
    """The live lifeform already spawned for ``key`` on ``host_id``, or None."""
def lifeform_spawn (name, face, roles, host=None, comms_id=None, path=None, title_color='green', message_color='white'):
    """Create a new Agent and initialise it as a lifeform.
    
    Args:
        name (str): Display name of the lifeform.
        face (str): Face image key.
        roles (str): Comma-separated roles to assign (e.g. ``"crew,medic"``).
        host (Agent | int, optional): Space object the lifeform boards.
            Defaults to None.
        comms_id (str, optional): Unused. Defaults to None.
        path (str, optional): Comms route path for this lifeform. Defaults to
            None.
        title_color (str, optional): Color of the comms title line. Defaults
            to ``"green"``.
        message_color (str, optional): Color of the comms message text.
            Defaults to ``"white"``.
    
    Returns:
        Agent: The newly created lifeform agent."""
def lifeform_speaker (records, key, default_color='#0cf'):
    """A dialogue voice record (key/name/color/leans) for a cast character, so a scene's
    ``Speaker: <key>`` resolves to that character's card. ``None`` if the key is not in the cast;
    cast NPCs carry no reputation, so leans is empty. ``records`` is ``lifeforms_from_section``'s
    list (or the ``.values()`` of a spawned map's records)."""
def lifeform_speaker_of (agent_id, default_color='#0cf'):
    """A dialogue speaker card (key/name/color/leans) built from a spawned lifeform Agent ITSELF -
    for the comms-cast route, where the hailed lifeform IS the speaker (its badge was selected).
    ``None`` if the id is not a live agent; cast NPCs carry no reputation, so leans is empty."""
def lifeforms_from_section (section):
    """Cast records (MastDataObject) from a section node's children (empty if None)."""
def lifeforms_spawn (section, host_id=None):
    """Spawn every character in a section (optionally all hosted on ``host_id``); returns a
    ``{key: lifeform}`` map. Convenience over ``lifeforms_from_section`` + ``lifeform_from_record``."""
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
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
