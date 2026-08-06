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
from sbs_utils.procedural.amd import (amd_parse_facts, amd_norm, amd_num, amd_coords,
                                      amd_signal_name, amd_duration_parts)

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


# Triggers that read as an instruction to the crew, so they can stand in for a missing
# `Objective:`. A signal or a timer is a mechanism, not something anyone can go and do.
_INSTRUCTION_TRIGGERS = ("on_kill", "on_collect", "on_scan", "on_dock", "on_reach")


def _is_duration(text):
    """`5 minutes` / `30 seconds` - a time is a trigger like any other."""
    t = str(text).lower()
    return any(u in t for u in ("second", "minute", "min", "hour"))


def _resolve_role(target, aliases=None):
    """A friendly role name -> its real role: apply an alias, else singularize
    ('raiders' -> 'raider') but keep 'ss' words ('boss' stays 'boss')."""
    aliases = aliases or {}
    role = aliases.get(target.lower())
    if role is None:
        role = target.lower()
        if role.endswith("s") and not role.endswith("ss"):
            role = role[:-1]
    return role


def _signal_name(value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).
    Kept as a local alias; the rule itself lives in `amd.amd_signal_name` so the
    editor's signal join matches exactly what the driver matches."""
    return amd_signal_name(value)


def amd_trigger(value, aliases=None):
    """'destroy 4 raiders' -> ('on_kill', {role: raider, count: 4}); 'reach 6, 4' ->
    ('on_reach', {sector: [6,4]}); 'signal x' -> ('on_signal', {name: x}). Returns
    None if the leading word isn't a known verb. ``aliases`` optionally maps a
    friendly role name to its real role (e.g. {'derelict': 'universe_derelict'})."""
    aliases = aliases or {}
    toks = str(value).split()
    if not toks:
        return None
    # Forms that are not verb-led, so that ONE grammar answers all three life-cycle
    # questions (`Starts when:` / `Done when:` / `Fails when:`) instead of the seven
    # differently-shaped fields this replaces.
    low = " ".join(toks).strip().lower()
    if low in ("at once", "immediately", "now", "start", "at start"):
        return "at_once", {}
    if low in ("accepted", "on accept", "when accepted"):
        return "accepted", {}
    if low in ("revealed", "when revealed"):
        return "revealed", {}
    if toks[0].lower() == "all" and len(toks) > 2 and toks[1].lower() == "dead":
        return "all_dead", {"role": _resolve_role(" ".join(toks[2:]), aliases)}
    if toks[0].isdigit() and _is_duration(low):
        n, unit = amd_duration_parts(low)
        return "after", {unit: n or 0}
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
        # reach/travel is either a SECTOR (`reach 6, 4` - Open Universe) or a LANDMARK
        # role with an optional radius (`reach relay 5000` - the 2.8 "fly within R of
        # <object>" objective; absolute 2.8 coords do not map to sectors). A role form is
        # completed by the quest_driver's quest_tick_reach proximity watcher.
        toks = str(target).replace(",", " ").split()
        nums = [int(t) for t in toks if t.lstrip("-").isdigit()]
        words = [t for t in toks if not t.lstrip("-").isdigit()]
        if words:
            data["role"] = _resolve_role(" ".join(words), aliases)
            if nums:
                data["radius"] = nums[-1]
        elif len(nums) >= 2:
            data["sector"] = nums[:2]
        else:
            data["sector"] = amd_coords(target)
    elif kind == "name":
        # single-token signal name; lowercase + underscores so `signal Eliminated Foe`
        # and `signal eliminated_foe` agree (quest_on_signal matches exactly).
        if target:
            data["name"] = _signal_name(target)
        if count is not None:
            data["count"] = count
    elif kind == "key":
        if target:
            data["key"] = amd_norm(target)
        if count is not None:
            data["count"] = count
    else:  # role
        # A kill goal worded against "enemies"/"hostiles" scores by DIPLOMACY rather
        # than a specific faction role: general, faction-agnostic, and ceasefire-safe
        # (a neutral/ceasefired ship does not count). "destroy 4 raiders" still binds
        # to the raider role as before.
        if trig == "on_kill" and target.lower().strip() in ("enemy", "enemies", "hostile", "hostiles"):
            data["hostile"] = True
        else:
            data["role"] = _resolve_role(target, aliases)
        data["count"] = count if count is not None else 1
    return trig, data


def _quest_log(message):
    """Warn about an authored line that did not parse (never raise - a bad reward must
    not take the mission down with it). Mirrors ``amd_action``'s ``_action_log``."""
    try:
        from .execution import log
        log(message, "quest", "warning")
    except Exception:
        pass


def _rep_clause(toks):
    """``earns <faction> <pole...> <n>`` -> ``(faction, pole, delta)``, else None.

    Deliberately the SAME shape as the dialogue outcome verb already in production
    (``earns ashfang selfish +5``, OU ``_ou_earns``): number last, pole possibly several
    words. One grammar for shifting standing, not two spellings of it.
    """
    if len(toks) >= 3 and str(toks[-1]).lstrip("+-").isdigit():
        return toks[0].lower(), amd_norm(" ".join(toks[1:-1])), int(toks[-1])
    return None


def amd_reward(value):
    """A reward/penalty block -> ``{credits, items, reputation}``. Clauses are
    comma-separated::

        Pays: 300 credits, 2 torpedoes, earns tsn honest +10
        Penalty: 200 credits, earns tsn diplomatic -15

    * ``<n> credits``  -> ``{"credits": n}``
    * ``<n> <item>``   -> ``{"items": {<amd_norm(item)>: n}}``, keyed exactly the way
      ``recover 2 torpedoes`` keys its goal, so a reward and the goal that collects it
      cannot disagree.
    * ``earns <faction> <pole...> <n>`` -> ``{"reputation": {faction: {pole: n}}}``.

    ``earns`` applies its delta **literally in both blocks** - a `Penalty:` does not
    silently flip the sign, so an author writing ``-15`` gets ``-15``. (Credits differ:
    a bare quantity takes its direction from the block, which is why the sign is written
    on the one that could be ambiguous and omitted on the one that cannot.)

    Prose carrying no number is a FLAVOR reward and stays ``{"credits": 0}`` silently -
    "a favor" is a legitimate thing to write. A clause that DOES carry a number but
    matches no form is logged: this used to be the ``Pays: 300 credits, 2 torpedoes``
    case, which returned the credits and dropped the torpedoes without telling anyone,
    while ``quest_grant_reward`` had supported ``items`` the whole time.

    ``items`` and ``reputation`` are present only when non-empty, so the common
    ``{"credits": n}`` shape is unchanged for every existing caller.
    """
    out = {"credits": 0}
    items = {}
    rep = {}
    for clause in str(value).split(","):
        toks = clause.split()
        if not toks:
            continue
        if toks[0].lower() == "earns":
            parsed = _rep_clause(toks[1:])
            if parsed is None:
                _quest_log(f"reward clause {clause.strip()!r} is not "
                           f"'earns <faction> <pole> <n>'")
            else:
                faction, pole, delta = parsed
                rep.setdefault(faction, {})[pole] = delta
            continue
        nums = [t for t in toks if t.lstrip("+-").isdigit()]
        words = [t for t in toks if not t.lstrip("+-").isdigit()]
        if not nums:
            continue        # flavor prose, silent - the pre-existing behavior
        n = int(nums[0])
        # "300 credits" and "300 credits bonus" are both money; anything else counted
        # is an item.
        if any(w.lower().startswith("credit") for w in words):
            out["credits"] = n
        elif words:
            key = amd_norm(" ".join(words))
            items[key] = items.get(key, 0) + n
        else:
            _quest_log(f"reward clause {clause.strip()!r} counts something, but does "
                       f"not say what")
    if items:
        out["items"] = items
    if rep:
        out["reputation"] = rep
    return out


def amd_console_list(value):
    """'comms, admiral' / 'comms admiral' -> ['comms', 'admiral'] (lowercased). Used by
    the Quests-tab `Accept On:` / `Engage On:` labels to restrict WHICH consoles may
    accept/abandon or engage this quest (a job specific to one station)."""
    raw = str(value).replace(",", " ").split()
    return [t.strip().lower() for t in raw if t.strip()]


def _norm(label):
    return str(label).strip().lower().replace("-", "_").replace(" ", "_")


# The renamed spellings, mapped back to the label this module's handler chain already
# matches. Declared in amd_schema (which owns the vocabulary); repeated here as the
# RUNTIME half, because the handler gets first refusal and matches literal labels.
_CANONICAL_TO_LEGACY = {
    "done_when": "goal",        # Goal: -> Done when:
    "starts_when": "when",      # When: -> Starts when:
    "part_of": "parent",        # Parent: -> Part of:
    "at_start": "state",        # State: -> At start:
    "fatal": "critical",        # Critical: -> Fatal:
    "reward": "pays",           # Pays: -> Reward:
    "fails_when": "fails_when",  # (matched directly; listed so the intent is visible)
}

# The authored word -> the word the DRIVER reads. `At start:` is written in story
# words (`hidden` / `offered` / `running`); QuestState is unchanged underneath, so a
# rename here never reaches the state machine.
_STATE_ALIASES = {"available": "idle", "offered": "idle",
                  "running": "active", "hidden": "secret", "done": "complete"}


def amd_quest_facts(aliases=None):
    """Return an ``amd_parse_facts`` handler for the shared quest vocabulary.

    Objective/flow labels: Scope / State / Goal / When / Then / Pays / Tier / Display.
    Quests-tab action gating: Accept On (consoles that may Accept/Abandon) and Engage On
    (consoles that may Engage) restrict a job to specific stations.
    End-game + mission-tree labels: Win / Lose (bare flag -> end_win/end_lose; prose ->
    also the win_text/lose_text reason), Parent, Required, Critical, and the fail
    triggers Fail on signal / Fail on all dead / Fail after, plus the timed-completion
    trigger Complete after (symmetric to Fail after; drives a reveal chain). These map to
    the data keys the LM quest end-game driver reads (parent aggregation, end_win/end_lose
    game-over, fail_on_signal/fail_on_all_dead/fail_after, complete_after).

    Unknown labels return None, so a mission with extra vocabulary chains its own
    handler after this one (or falls to amd_parse_facts's default coercion).
    ``aliases`` is forwarded to ``amd_trigger`` / role resolution."""
    def handler(data, label, value):
        # Resolve the AUTHORED spelling to the one this chain matches on, so a
        # renamed label works at RUNTIME and not only in the tooling. The registry
        # owns which spellings mean what; this keeps the chain below unchanged.
        label = _CANONICAL_TO_LEGACY.get(_norm(label), label)
        if label in ("scope", "state"):
            # `State: idle` was renamed to `State: available` (the word the player
            # already sees). Accept both; store what the driver reads.
            if label == "state":
                value = _STATE_ALIASES.get(str(value).strip().lower(), value)
            data[label] = value
        elif label in ("held by", "held_by"):
            # WHO owns this quest. `Scope: shared` already redirects the holder to the
            # shared story agent; this generalizes that to a NAMED actor, so a station's
            # resupply job or a side's war aim is held by the thing it is about rather
            # than by whichever ship happened to be passed in. Resolved at grant time
            # against landmarks then roles (the same resolution `Action:` verbs use).
            data["held_by"] = str(value).strip()
        elif label == "display":
            data["display"] = value
        elif label == "tier":
            data["tier"] = amd_num(value)
        elif label in ("goal", "when", "fails_when"):
            # ONE grammar, three questions. `Starts when:` / `Done when:` / `Fails when:`
            # all take the same trigger, and the label decides which of the driver's keys
            # it lands in - instead of `Fail on signal:` / `Fail on all dead:` /
            # `Fail after:` / `Complete after:` each having their own shape.
            trig = amd_trigger(value, aliases)
            kind, payload = trig if trig is not None else (None, None)
            if label == "fails_when":
                if kind == "on_signal":
                    data["fail_on_signal"] = {"name": payload.get("name")}
                elif kind == "all_dead":
                    data["fail_on_all_dead"] = payload
                elif kind == "after":
                    data["fail_after"] = payload
                # any other trigger has no failure watcher behind it; the linter says so
            elif label == "when":
                # A start is also WHEN THE PLAYER lets it start: an offered job starts
                # on Accept, a hidden step starts when something reveals it. Those were
                # `State: idle` / `State: secret` - a second field saying the same thing
                # in a different vocabulary.
                if kind == "at_once":
                    data["state"] = "active"
                elif kind == "accepted":
                    data["state"] = "idle"
                elif kind == "revealed":
                    data["state"] = "secret"
                elif trig is not None:
                    # A real START trigger: the quest is granted armed with THIS, and
                    # swaps in its own `Done when:` once it fires. It used to be stored
                    # as an advancement trigger - the identical key `Done when:` writes -
                    # so a quest with both completed on whichever fired first.
                    data["start_trigger"] = {"trigger": kind, "data": payload}
                else:
                    data["when"] = value
            else:                                   # goal / Done when
                if kind == "after":
                    data["complete_after"] = payload
                elif trig is not None:
                    data[kind] = payload
                # The objective is the SENTENCE THE PLAYER READS, so only a doable verb
                # can stand in for one - "Signal a2x_gate_11" never should have. And it
                # only ever FILLS A BLANK: an explicit `Objective:` used to be clobbered
                # when it happened to be written above `Done when:`, so the same two
                # lines meant different things depending on their order.
                if kind in _INSTRUCTION_TRIGGERS and not data.get("objective"):
                    data["objective"] = value[:1].upper() + value[1:]
        elif label == "then":
            toks = str(value).split()
            if len(toks) >= 2 and toks[0].lower() in ("reveal", "signal"):
                data[toks[0].lower()] = toks[1]
            else:
                data["reveal"] = value
        elif label == "pays":
            data["reward"] = amd_reward(value)
        elif label == "penalty":
            # Same grammar as the reward, and the driver wants the same shape - it was
            # storing the raw string, which quest_grant_penalty silently ignores.
            data["penalty"] = amd_reward(value)
        elif label in ("accept on", "accept_on", "manage on", "manage_on"):
            # Restrict WHICH consoles may Accept/Abandon this quest from the Quests tab
            # (else the mission default QUEST_ACCEPT_CONSOLES). A job specific to a station.
            data["accept_consoles"] = amd_console_list(value)
        elif label in ("engage on", "engage_on"):
            # Restrict WHICH consoles may Engage (travel to) this quest (else the mission
            # default QUEST_ENGAGE_CONSOLES). Only meaningful when QUEST_ENGAGE_ENABLED.
            data["engage_consoles"] = amd_console_list(value)
        elif label in ("reveals", "scan text"):
            # Declarative SCIENCE SCAN content: scanning this quest's on_scan target
            # shows this text (and the quest driver makes the target scannable). This is
            # the science analogue of attaching comms to an object - the quest carries
            # what the scan returns, so no hand-authored //science route is needed.
            data["reveal_scan"] = str(value).strip()
        elif label in ("win", "lose"):
            v = str(value).strip()
            lo = v.lower()
            if lo in ("false", "no", "0"):
                data["end_" + label] = False
            else:
                data["end_" + label] = True
                # prose after Win:/Lose: (not a bare flag) is the end-screen reason.
                if lo not in ("true", "yes", "1", ""):
                    data[label + "_text"] = v
        # --- mission tree (the LM quest end-game structure) ---
        elif label == "parent":
            data["parent"] = str(value).strip()
        elif label in ("required", "critical"):
            data[label] = str(value).strip().lower() in ("true", "yes", "1", "")
        elif label in ("fail on signal", "fail_on_signal"):
            data["fail_on_signal"] = {"name": _signal_name(value)}
        elif label in ("fail on all dead", "fail_on_all_dead"):
            data["fail_on_all_dead"] = {"role": _resolve_role(str(value).strip(), aliases)}
        elif label in ("fail after", "fail_after"):
            n, unit = amd_duration_parts(value)
            data["fail_after"] = {unit: n or 0}
        elif label in ("complete after", "complete_after"):
            # Symmetric to Fail after: COMPLETE the quest once a time elapses (anchored
            # lazily on the first ACTIVE tick, same as fail_after). Lets a purely timed
            # step - a narrative beat, a "hold for N seconds" objective - be a quest that
            # advances a reveal chain (pair with Then: reveal) with no hand-written timer
            # loop. Read by the LM quest_driver's quest_tick_complete_after watcher.
            n, unit = amd_duration_parts(value)
            data["complete_after"] = {unit: n or 0}
        else:
            return None
        return True
    return handler


def amd_quest_data(text, aliases=None):
    """Parse one quest fact-sheet fence into a quest-data dict using the shared
    vocabulary only. A mission with extra labels should compose ``amd_quest_facts``
    with its own handler and call ``amd_parse_facts`` directly instead."""
    return amd_parse_facts(text, amd_quest_facts(aliases))
