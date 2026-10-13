def _axis_sign (pole):
    ...
def _rep_card_get (speaker, name):
    ...
def _rep_key (key):
    """A SIDE key as reputation files it: trimmed and lower-case, nothing else - the
    spelling a quest's `earns` clause already stores."""
def _rep_map (agent_id):
    ...
def _rep_norm (word):
    """A POLE as it is keyed: `By-the-Book` -> `by_the_book` (what `amd_norm` does)."""
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
def reputation_adjust (agent_id, faction, pole, delta):
    """Shift an agent's reputation with a faction along a pole (clamped). delta is in the
    pole's direction (adjust "honest" +10 raises honesty; "liar" +10 lowers it). Returns the
    new canonical axis value."""
def reputation_alliance_standing ():
    """Standing needed to propose an alliance (default 60)."""
def reputation_apply (agent_id, rep_block):
    """Apply a declarative rep block: { faction: { pole: delta, ... }, ... }."""
def reputation_axis_names ():
    """Every configured AXIS by its own name (`honesty`, `nerve`...), sorted.
    
    A deed may be written against the axis as well as against a pole: `_axis_sign` reads
    a word that is no pole as an axis of that name, plus direction, so `earns guild
    honesty 30` and `earns guild honest 30` land in the same place. A GUARD is
    different - `if honesty >= 30` is not a pole and reads 0."""
def reputation_ceasefire_cost (standing):
    """Tribute (credits) to buy a ceasefire: 0 at standing>=ceasefire_free_at, scaling by
    ceasefire_per_point below it (defaults 30 / 20 cr -> 600 at 0)."""
def reputation_configure (cfg):
    """Configure the reputation axes + standing tuning from a `reputation:` config dict.
    
    Always resets to the built-in defaults first (module globals persist for the process, so
    re-loading must not inherit the previous config). cfg None or missing keys -> defaults.
    
    cfg shape (all optional):
        axes: [ { axis: honesty, pos: honest, neg: liar }, ... ]  # REPLACES the set
        min / max / foe_deal / reward_mult_max / ceasefire_free_at /
        ceasefire_per_point / alliance_standing / ransom_base / ransom_per_point: <number>
        tiers: { t2: 20, t3: 50 }"""
def reputation_earns_outcome (agent_id, speaker, tokens):
    """The `earns` outcome verb: `- [Pay the levy](paid) ; earns guild honest 20`.
    
    `earns <side> <pole...> <+-n>` - the number last, the pole possibly several words.
    The same shape a quest's `Reward:` takes. It moves the standing of the ship that
    answered (a console or a boarding party member answers for their ship; the shared
    story agent for every player ship - see `reputation_grant`).
    
    Anything that does not fit the shape changes nothing; `sbs lint` is what says so."""
def reputation_foe_deal_standing ():
    """Standing a foe faction needs before it offers any work (default 20)."""
def reputation_get (agent_id, faction, pole, default=0):
    """Reputation of an agent with a faction along a pole, oriented to the POLE asked for
    (reading "honest" gives honesty, "liar" gives its negation). Unset -> default."""
def reputation_grant (agent_id, rep_block):
    """Apply a rep block `{side: {pole: delta}}` to whoever `agent_id` stands for.
    
    A ship is paid as itself. The SHARED story agent stands for the whole table: the
    block is applied to it AND to every player ship flying at that moment, because a
    guard reads the acting SHIP - a deed filed only on the shared agent is one no line
    and no choice can ever see. A ship spawned later starts at nothing.
    
    Returns the ids the block was applied to."""
def reputation_holder (agent_id):
    """Whose reputation a deed is filed under: THE SHIP's.
    
    A console, and a person on a boarding party, act for the ship they came from - a
    reputation filed on either is one nothing reads. Anything else (a ship, the shared
    story agent) is itself. The same rule a quest's reward follows (`quest_payee`)."""
def reputation_metric (name, agent_id, speaker, any_pole=False):
    """A guard's left side, where it is about reputation: `if standing >= 30`,
    `%{fearsome > 20}`.
    
    `standing` (or `rep` / `reputation`) is the acting SHIP's standing with the
    SPEAKER's side (`reputation_speaker_side`); a pole name is that ship's reading on
    one pole with the same side. Anything else is 0 - unless `any_pole` is set, which
    reads ANY name as a pole (Open Universe's habit, kept for it).
    
    This is the BASE of the guard resolver chain: it answers when no mission resolver
    is installed, and after the away resolver has had its say. A resolver a mission
    installs itself still wins."""
def reputation_offer_tier (standing):
    """Highest offer tier a standing unlocks: 1 always, 2 at >=tier2, 3 at >=tier3
    (defaults 20 / 50; per config via reputation: tiers)."""
def reputation_pole_names ():
    """Every pole of the configured axes, sorted - for lint and completion."""
def reputation_ransom_cost (standing):
    """Credits to ransom a captured officer: a base price plus a markup per standing-point
    below the ceasefire line (defaults 400 + 15/pt -> 850 at 0, 400 at/above the line)."""
def reputation_reward_mult (standing):
    """Reward multiplier from standing: 1.0 at <=0, up to reward_mult_max at +100
    (default 2.0; per config via reputation: reward_mult_max)."""
def reputation_side (key):
    """The registered record `{key, leans}` for a side key, or None."""
def reputation_side_register (key, leans=None):
    """Declare a side reputation is kept with: its key, and the poles it values.
    
    `leans` is `{pole: weight}` (what `Values:` parses to); a side that values nothing
    in particular is still worth declaring, since its standing is then the plain average
    of what a ship has earned with it. Registering a key again replaces its record, so
    re-declaring a document is safe. Returns the record `{key, leans}`."""
def reputation_sides_clear ():
    """Forget every registered side - the per-mission reset."""
def reputation_sides_count ():
    """Reset-ledger probe: how many sides are registered."""
def reputation_speaker_side (speaker):
    """The side record `{key, leans}` a speaker's opinion is read against, or None.
    
    In order:
    
    1. a record that carries its own non-empty `leans` - an Open Universe clan or
       captain, who is regarded personally. Returned as it is.
    2. the speaker's `side`: a character's `Side:`, or the speaking object's own side.
       The registered record when the side declared `Values:`, else a record with no
       leans (standing is then the plain average of what was earned with it).
    3. a speaker whose own key IS a registered side (`Speaker: guild`).
    4. None.
    
    `speaker` may be a card (anything with `.get`), a key, or a live agent / its id."""
def reputation_standing (agent_id, faction):
    """A -100..100 standing for a faction RECORD (a dict with `key` + optional `leans`):
    the agent's reputation along the poles the faction values, weighted by how strongly it
    holds each. 0 if the faction has no leans and the agent has no recorded reputation."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
