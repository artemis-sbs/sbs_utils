"""Shared AMD quest vocabulary.

The generic quest/objective fact-sheet grammar - the English verbs and labels an
author writes inside an ``.amd`` fence: ``Goal: destroy 3 raiders``,
``When: signal x``, ``Then: reveal y``, ``Pays: 300 credits``, ``Scope: shared``,
``State: secret``, ``Win: true``. Promoted out of Open Universe so a mission (e.g.
the LegendaryMissions siege map) and Open Universe share ONE parser - siege AMD is
then a strict SUBSET of universe AMD, and the two cannot drift.

Generic value coercion lives in ``amd.py``; this module is the quest LAYER on top:
the trigger-verb table and the label->quest-data interpretation, exposed as an
``amd_parse_facts`` handler. Map / economy / clan vocabulary is intentionally NOT
here - a richer mission (Open Universe) keeps its own labels and composes this
handler underneath them.
"""
from sbs_utils.procedural.amd import amd_parse_facts, amd_norm, amd_num, amd_coords

# verb -> (quest-data trigger key, target field). The trigger keys are what the LM
# quest_driver dispatchers read (quest_on_kill / on_collect / on_scan / on_dock /
# on_arrive / on_signal). "signal" is the escape hatch for game-state milestones
# (a quest completes when signal_emit("quest_signal", {"SIGNAL_NAME": <name>}) fires).
TRIGGER_VERBS = {
    "destroy": ("on_kill", "role"),   "kill": ("on_kill", "role"),
    "recover": ("on_collect", "key"), "collect": ("on_collect", "key"),
    "gather": ("on_collect", "key"),
    "scan": ("on_scan", "role"),      "survey": ("on_scan", "role"),
    "dock": ("on_dock", "role"),
    "reach": ("on_reach", "sector"),  "travel": ("on_reach", "sector"),
    "signal": ("on_signal", "name"),
}


def amd_trigger(value, aliases=None):
    """'destroy 4 raiders' -> ('on_kill', {role: raider, count: 4}); 'reach 6, 4' ->
    ('on_reach', {sector: [6,4]}); 'signal x' -> ('on_signal', {name: x}). Returns
    None if the leading word isn't a known verb. ``aliases`` optionally maps a
    friendly role name to its real role (e.g. {'derelict': 'universe_derelict'})."""
    aliases = aliases or {}
    toks = str(value).split()
    if not toks:
        return None
    spec = TRIGGER_VERBS.get(toks[0].lower())
    if spec is None:
        return None
    trig, kind = spec
    rest = toks[1:]
    count = None
    if rest and rest[0].isdigit():
        count = int(rest[0])
        rest = rest[1:]
    target = " ".join(rest).strip()
    data = {}
    if kind == "sector":
        data["sector"] = amd_coords(target)
    elif kind == "name":
        # single-token signal name; lowercase + underscores so `signal Eliminated Foe`
        # and `signal eliminated_foe` agree (quest_on_signal matches exactly).
        if target:
            data["name"] = target.strip().lower().replace(" ", "_")
        if count is not None:
            data["count"] = count
    elif kind == "key":
        if target:
            data["key"] = amd_norm(target)
        if count is not None:
            data["count"] = count
    else:  # role
        role = aliases.get(target.lower())
        if role is None:
            role = target.lower()
            # singularize "raiders" -> "raider", but keep "ss" words ("boss", "class")
            if role.endswith("s") and not role.endswith("ss"):
                role = role[:-1]
        data["role"] = role
        data["count"] = count if count is not None else 1
    return trig, data


def amd_reward(value):
    """'300 credits' -> {credits: 300}."""
    for t in str(value).split():
        if t.isdigit():
            return {"credits": int(t)}
    return {"credits": 0}


def amd_quest_facts(aliases=None):
    """Return an ``amd_parse_facts`` handler for the shared quest vocabulary:
    Scope / State / Goal / When / Then / Pays / Win / Lose / Tier / Display.

    Unknown labels return None, so a mission with extra vocabulary chains its own
    handler after this one (or falls to amd_parse_facts's default coercion). Win/Lose
    set ``end_win`` / ``end_lose`` - the keys the LM quest end-game driver reads to end
    the game on a mission quest's terminal transition. ``aliases`` is forwarded to
    ``amd_trigger``."""
    def handler(data, label, value):
        if label in ("scope", "state"):
            data[label] = value
        elif label == "display":
            data["display"] = value
        elif label == "tier":
            data["tier"] = amd_num(value)
        elif label in ("goal", "when"):
            trig = amd_trigger(value, aliases)
            if trig is not None:
                data[trig[0]] = trig[1]
            if label == "goal":
                data["objective"] = value[:1].upper() + value[1:]
            elif label == "when" and trig is None:
                data["when"] = value
        elif label == "then":
            toks = str(value).split()
            if len(toks) >= 2 and toks[0].lower() in ("reveal", "signal"):
                data[toks[0].lower()] = toks[1]
            else:
                data["reveal"] = value
        elif label == "pays":
            data["reward"] = amd_reward(value)
        elif label in ("win", "lose"):
            data["end_" + label] = str(value).strip().lower() in ("true", "yes", "1", "")
        else:
            return None
        return True
    return handler


def amd_quest_data(text, aliases=None):
    """Parse one quest fact-sheet fence into a quest-data dict using the shared
    vocabulary only. A mission with extra labels should compose ``amd_quest_facts``
    with its own handler and call ``amd_parse_facts`` directly instead."""
    return amd_parse_facts(text, amd_quest_facts(aliases))
