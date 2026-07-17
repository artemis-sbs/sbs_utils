"""Multi-axis faction reputation - how a faction sees an individual agent (a captain/ship),
distinct from side-wide diplomacy ("are we at war?").

Stored on the agent (inventory key "reputation") so every read/write keys the same way and
it persists with the agent. Model: signed axes -100..+100, authored by POLE name; a pole
maps to a canonical axis + sign, so gating on either pole works (honest>40 == liar<-40). The
axis set and standing tuning are declarative - a mission passes a `reputation:` config dict to
reputation_configure (or uses the built-in seven axes).

Promoted out of Open Universe (Epic F). Generic: a "faction record" here is any dict with a
`key` and optional `leans` weights - OU passes its clan records; another mission passes its
own. Pairs with amd_dialogue (guards read reputation) and declarative sides.
"""
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value

# Built-in default axes (pole -> (canonical axis, sign); +pole raises the axis, -pole lowers
# it). A mission can REPLACE the set via a `reputation: axes:` config block; with no block
# these seven stand.
_DEFAULT_POLES = {
    "honest": ("honesty", 1),        "liar": ("honesty", -1),
    "fearsome": ("nerve", 1),        "cowardly": ("nerve", -1),
    "peaceful": ("temperament", 1),  "violent": ("temperament", -1),
    "generous": ("generosity", 1),   "selfish": ("generosity", -1),
    "kind": ("kindness", 1),         "cruel": ("kindness", -1),
    "resourceful": ("method", 1),    "by_the_book": ("method", -1),
    "intellectual": ("intellect", 1), "foolish": ("intellect", -1),
}

# Built-in default standing tuning. Each knob is overridable per config.
_DEFAULT_TUNING = {
    "min": -100, "max": 100,
    "tier2": 20, "tier3": 50,    # standing to unlock offer tiers 2 / 3
    "foe_deal": 20,              # standing a foe faction needs before it deals
    "reward_mult_max": 2.0,      # reward multiplier at standing +100
    "ceasefire_free_at": 30,     # ceasefire free at/above this standing
    "ceasefire_per_point": 20,   # cr per standing-point below the free line
    "alliance_standing": 60,     # standing to propose an alliance
    "ransom_base": 400,          # cr floor to ransom a captured officer
    "ransom_per_point": 15,      # cr markup per standing-point below the ceasefire line
}

# Live config - module globals rebuilt per load by reputation_configure(). Seeded with the
# defaults so a mission with no reputation: block is unchanged.
_REP_POLES = dict(_DEFAULT_POLES)
_TUNING = dict(_DEFAULT_TUNING)


def reputation_configure(cfg):
    """Configure the reputation axes + standing tuning from a `reputation:` config dict.

    Always resets to the built-in defaults first (module globals persist for the process, so
    re-loading must not inherit the previous config). cfg None or missing keys -> defaults.

    cfg shape (all optional):
        axes: [ { axis: honesty, pos: honest, neg: liar }, ... ]  # REPLACES the set
        min / max / foe_deal / reward_mult_max / ceasefire_free_at /
        ceasefire_per_point / alliance_standing / ransom_base / ransom_per_point: <number>
        tiers: { t2: 20, t3: 50 }
    """
    global _REP_POLES, _TUNING
    _REP_POLES = dict(_DEFAULT_POLES)
    _TUNING = dict(_DEFAULT_TUNING)
    if not isinstance(cfg, dict):
        return
    axes = cfg.get("axes")
    if isinstance(axes, list) and axes:
        poles = {}
        for a in axes:
            if not isinstance(a, dict):
                continue
            axis, pos, neg = a.get("axis"), a.get("pos"), a.get("neg")
            if axis is None or pos is None:
                continue
            poles[pos] = (axis, 1)
            if neg is not None:
                poles[neg] = (axis, -1)
        if poles:
            _REP_POLES = poles
    for key in ("min", "max", "foe_deal", "reward_mult_max",
                "ceasefire_free_at", "ceasefire_per_point", "alliance_standing",
                "ransom_base", "ransom_per_point"):
        if key in cfg:
            _TUNING[key] = cfg[key]
    tiers = cfg.get("tiers")
    if isinstance(tiers, dict):
        if "t2" in tiers:
            _TUNING["tier2"] = tiers["t2"]
        if "t3" in tiers:
            _TUNING["tier3"] = tiers["t3"]


def _rep_map(agent_id):
    return get_inventory_value(agent_id, "reputation", None) or {}


def _axis_sign(pole):
    return _REP_POLES.get(pole, (pole, 1))


def reputation_get(agent_id, faction, pole, default=0):
    """Reputation of an agent with a faction along a pole, oriented to the POLE asked for
    (reading "honest" gives honesty, "liar" gives its negation). Unset -> default."""
    axis, sign = _axis_sign(pole)
    cm = _rep_map(agent_id).get(faction)
    if not isinstance(cm, dict) or axis not in cm:
        return default
    return sign * cm[axis]


def reputation_adjust(agent_id, faction, pole, delta):
    """Shift an agent's reputation with a faction along a pole (clamped). delta is in the
    pole's direction (adjust "honest" +10 raises honesty; "liar" +10 lowers it). Returns the
    new canonical axis value."""
    axis, sign = _axis_sign(pole)
    reps = _rep_map(agent_id)
    cm = reps.get(faction)
    if not isinstance(cm, dict):
        cm = {}
        reps[faction] = cm
    val = max(_TUNING["min"], min(_TUNING["max"], cm.get(axis, 0) + sign * delta))
    cm[axis] = val
    set_inventory_value(agent_id, "reputation", reps)
    return val


def reputation_apply(agent_id, rep_block):
    """Apply a declarative rep block: { faction: { pole: delta, ... }, ... }."""
    if not isinstance(rep_block, dict):
        return
    for faction, poles in rep_block.items():
        if isinstance(poles, dict):
            for pole, delta in poles.items():
                reputation_adjust(agent_id, faction, pole, delta)


# --- Standing: a single "how much this faction likes you" scalar ----------------
def reputation_standing(agent_id, faction):
    """A -100..100 standing for a faction RECORD (a dict with `key` + optional `leans`):
    the agent's reputation along the poles the faction values, weighted by how strongly it
    holds each. 0 if the faction has no leans and the agent has no recorded reputation."""
    if faction is None:
        return 0
    leans = faction.get("leans") or {}
    key = faction.get("key")
    if not leans:
        cm = _rep_map(agent_id).get(key) or {}
        vals = list(cm.values())
        return int(sum(vals) / len(vals)) if vals else 0
    total = 0.0
    wsum = 0.0
    for pole, weight in leans.items():
        w = abs(weight)
        total += w * reputation_get(agent_id, key, pole)
        wsum += w
    return int(total / wsum) if wsum else 0


def reputation_offer_tier(standing):
    """Highest offer tier a standing unlocks: 1 always, 2 at >=tier2, 3 at >=tier3
    (defaults 20 / 50; per config via reputation: tiers)."""
    if standing >= _TUNING["tier3"]:
        return 3
    if standing >= _TUNING["tier2"]:
        return 2
    return 1


def reputation_foe_deal_standing():
    """Standing a foe faction needs before it offers any work (default 20)."""
    return _TUNING["foe_deal"]


def reputation_reward_mult(standing):
    """Reward multiplier from standing: 1.0 at <=0, up to reward_mult_max at +100
    (default 2.0; per config via reputation: reward_mult_max)."""
    return 1.0 + max(0, standing) / 100.0 * (_TUNING["reward_mult_max"] - 1.0)


# --- Standing -> diplomacy-economy pricing (formulas over the tuning knobs) ------
def reputation_ceasefire_cost(standing):
    """Tribute (credits) to buy a ceasefire: 0 at standing>=ceasefire_free_at, scaling by
    ceasefire_per_point below it (defaults 30 / 20 cr -> 600 at 0)."""
    return max(0, _TUNING["ceasefire_free_at"] - max(0, standing)) * _TUNING["ceasefire_per_point"]


def reputation_alliance_standing():
    """Standing needed to propose an alliance (default 60)."""
    return _TUNING["alliance_standing"]


def reputation_ransom_cost(standing):
    """Credits to ransom a captured officer: a base price plus a markup per standing-point
    below the ceasefire line (defaults 400 + 15/pt -> 850 at 0, 400 at/above the line)."""
    markup = max(0, _TUNING["ceasefire_free_at"] - max(0, standing)) * _TUNING["ransom_per_point"]
    return _TUNING["ransom_base"] + markup
