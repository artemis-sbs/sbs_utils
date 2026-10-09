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


# --- Sides that value deeds ------------------------------------------------------
#
# What a side VALUES, by key. `Values: honest 40, generous 30` on a side record is the
# whole declaration; `sides_declare` files it here, and this is what lets `standing` in a
# line or a choice mean something in a mission that is not Open Universe.
#
# PER MISSION, so it is on the reset ledger (see handlerhooks): a side one mission
# declared must not answer for a side of the same name in the next.
_SIDES = {}


def _rep_norm(word):
    """A POLE as it is keyed: `By-the-Book` -> `by_the_book` (what `amd_norm` does)."""
    return str(word).strip().lower().replace("-", "_").replace(" ", "_")


def _rep_key(key):
    """A SIDE key as reputation files it: trimmed and lower-case, nothing else - the
    spelling a quest's `earns` clause already stores."""
    return str(key).strip().lower()


def reputation_side_register(key, leans=None):
    """Declare a side reputation is kept with: its key, and the poles it values.

    `leans` is `{pole: weight}` (what `Values:` parses to); a side that values nothing
    in particular is still worth declaring, since its standing is then the plain average
    of what a ship has earned with it. Registering a key again replaces its record, so
    re-declaring a document is safe. Returns the record `{key, leans}`."""
    if key is None or not str(key).strip():
        return None
    k = _rep_key(key)
    record = {"key": k, "leans": {_rep_norm(p): w for p, w in dict(leans or {}).items()}}
    _SIDES[k] = record
    return record


def reputation_side(key):
    """The registered record `{key, leans}` for a side key, or None."""
    if key is None:
        return None
    return _SIDES.get(_rep_key(key))


def reputation_sides_clear():
    """Forget every registered side - the per-mission reset."""
    _SIDES.clear()


def reputation_sides_count():
    """Reset-ledger probe: how many sides are registered."""
    return len(_SIDES)


def reputation_holder(agent_id):
    """Whose reputation a deed is filed under: THE SHIP's.

    A console, and a person on a boarding party, act for the ship they came from - a
    reputation filed on either is one nothing reads. Anything else (a ship, the shared
    story agent) is itself. The same rule a quest's reward follows (`quest_payee`)."""
    if agent_id is None:
        return None
    try:
        from .quest_driver import quest_payee
        return quest_payee(agent_id)
    except Exception:                                    # noqa: BLE001
        return agent_id


def reputation_grant(agent_id, rep_block):
    """Apply a rep block `{side: {pole: delta}}` to whoever `agent_id` stands for.

    A ship is paid as itself. The SHARED story agent stands for the whole table: the
    block is applied to it AND to every player ship flying at that moment, because a
    guard reads the acting SHIP - a deed filed only on the shared agent is one no line
    and no choice can ever see. A ship spawned later starts at nothing.

    Returns the ids the block was applied to."""
    if not isinstance(rep_block, dict) or not rep_block:
        return []
    holder = reputation_holder(agent_id)
    if holder is None:
        return []
    targets = [holder]
    try:
        from sbs_utils.agent import Agent
        from .query import to_id, to_id_list
        from .roles import role
        if to_id(holder) == Agent.SHARED_ID:
            for ship_id in sorted(to_id_list(role("__player__"))):
                if ship_id not in targets:
                    targets.append(ship_id)
    except Exception:                                    # noqa: BLE001
        pass
    for target in targets:
        reputation_apply(target, rep_block)
    return targets


def _rep_card_get(speaker, name):
    try:
        return speaker.get(name)
    except Exception:                                    # noqa: BLE001
        return None


def reputation_speaker_side(speaker):
    """The side record `{key, leans}` a speaker's opinion is read against, or None.

    In order:

    1. a record that carries its own non-empty `leans` - an Open Universe clan or
       captain, who is regarded personally. Returned as it is.
    2. the speaker's `side`: a character's `Side:`, or the speaking object's own side.
       The registered record when the side declared `Values:`, else a record with no
       leans (standing is then the plain average of what was earned with it).
    3. a speaker whose own key IS a registered side (`Speaker: guild`).
    4. None.

    `speaker` may be a card (anything with `.get`), a key, or a live agent / its id.
    """
    if speaker is None:
        return None
    side = None
    key = None
    from sbs_utils.agent import Agent
    if isinstance(speaker, (int, Agent)):
        from .query import to_object, to_id
        obj = to_object(speaker)
        if obj is None:
            return None
        agent_id = to_id(obj)
        side = get_inventory_value(agent_id, "lf_side", None) or getattr(obj, "side", None)
        key = get_inventory_value(agent_id, "lf_key", None)
    elif isinstance(speaker, str):
        key = speaker
        try:
            from .amd_lifeforms import lifeform_side_of_key
            side = lifeform_side_of_key(key)
        except Exception:                                # noqa: BLE001
            side = None
    else:
        if _rep_card_get(speaker, "leans"):
            return speaker
        side = _rep_card_get(speaker, "side")
        key = _rep_card_get(speaker, "key")
    if side is not None and str(side).strip():
        k = _rep_key(side)
        return _SIDES.get(k) or {"key": k, "leans": {}}
    if key is not None and _rep_key(key) in _SIDES:
        return _SIDES[_rep_key(key)]
    return None


#: The guard words that ask for the one-number answer.
_STANDING_WORDS = ("standing", "rep", "reputation")


def reputation_pole_names():
    """Every pole of the configured axes, sorted - for lint and completion."""
    return sorted(_REP_POLES)


def reputation_metric(name, agent_id, speaker, any_pole=False):
    """A guard's left side, where it is about reputation: `if standing >= 30`,
    `%{fearsome > 20}`.

    `standing` (or `rep` / `reputation`) is the acting SHIP's standing with the
    SPEAKER's side (`reputation_speaker_side`); a pole name is that ship's reading on
    one pole with the same side. Anything else is 0 - unless `any_pole` is set, which
    reads ANY name as a pole (Open Universe's habit, kept for it).

    This is the BASE of the guard resolver chain: it answers when no mission resolver
    is installed, and after the away resolver has had its say. A resolver a mission
    installs itself still wins.
    """
    word = _rep_norm(name)
    standing = word in _STANDING_WORDS
    if not (standing or any_pole or word in _REP_POLES):
        return 0
    agent = reputation_holder(agent_id)
    if agent is None:
        return 0
    side = reputation_speaker_side(speaker)
    if side is None and not isinstance(speaker, (int, str)) and speaker is not None:
        # A record with a key and nothing else to go on is regarded as ITSELF: what was
        # earned under its own key. Open Universe's captains and cast have always read
        # this way.
        if _rep_card_get(speaker, "key") is not None:
            side = speaker
    if standing:
        return reputation_standing(agent, side)
    return reputation_get(agent, (side.get("key") if side is not None else None), word)


def reputation_earns_outcome(agent_id, speaker, tokens):
    """The `earns` outcome verb: `- [Pay the levy](paid) ; earns guild honest 20`.

    `earns <side> <pole...> <+-n>` - the number last, the pole possibly several words.
    The same shape a quest's `Reward:` takes. It moves the standing of the ship that
    answered (a console or a boarding party member answers for their ship; the shared
    story agent for every player ship - see `reputation_grant`).

    Anything that does not fit the shape changes nothing; `sbs lint` is what says so.
    """
    toks = [str(t) for t in (tokens or ())]
    if len(toks) < 3 or not toks[-1].lstrip("+-").isdigit():
        return None
    side = _rep_key(toks[0])
    pole = _rep_norm(" ".join(toks[1:-1]))
    reputation_grant(agent_id, {side: {pole: int(toks[-1])}})
    return None


# Registered AT IMPORT, the way every library outcome verb is: `sbs lint` asks the
# registry which verbs exist, and the linter does not run a mission. At the BOTTOM of the
# module because `amd_dialogue` imports this module at its own bottom - each finds the
# other complete whichever is imported first.
from .amd_dialogue import dialogue_register_outcome  # noqa: E402

dialogue_register_outcome("earns", reputation_earns_outcome)
