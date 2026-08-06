def _axis_sign (pole):
    ...
def _rep_map (agent_id):
    ...
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
def reputation_foe_deal_standing ():
    """Standing a foe faction needs before it offers any work (default 20)."""
def reputation_get (agent_id, faction, pole, default=0):
    """Reputation of an agent with a faction along a pole, oriented to the POLE asked for
    (reading "honest" gives honesty, "liar" gives its negation). Unset -> default."""
def reputation_offer_tier (standing):
    """Highest offer tier a standing unlocks: 1 always, 2 at >=tier2, 3 at >=tier3
    (defaults 20 / 50; per config via reputation: tiers)."""
def reputation_ransom_cost (standing):
    """Credits to ransom a captured officer: a base price plus a markup per standing-point
    below the ceasefire line (defaults 400 + 15/pt -> 850 at 0, 400 at/above the line)."""
def reputation_reward_mult (standing):
    """Reward multiplier from standing: 1.0 at <=0, up to reward_mult_max at +100
    (default 2.0; per config via reputation: reward_mult_max)."""
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
