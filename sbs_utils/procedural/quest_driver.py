"""Quest driver engine: advance active quests from game signals, apply rewards,
and gate the Quests-tab actions.

This is the generic quest *engine* — the "outside logic" that
``procedural.quest`` (the data model) defers to. ``procedural.quest``'s
``quest_set_state``/``activate``/``complete`` only *emit* signals; this module
writes state directly (idempotently) so progress is immediate and never
double-counts, and also handles the API's ``quest_activated``/``quest_completed``
signals so manual activation still updates state.

Declarative triggers live in each quest's AMD ``--- yaml ---`` data section
(``on_kill`` / ``on_collect`` / ...). The signal-route WIRING that feeds these
functions (which game event maps to which trigger, plus mission-policy teardown
like ``game_over``) lives in a mission library's ``.mast`` — in LegendaryMissions,
``quests/quest_driver.mast``. The hangar sortie board that reads the same quest
data lives with the hangar feature (LM ``quests/quest_driver.py``).

Runs server-side (called from signal routes).
"""
from sbs_utils.procedural.quest import (
    quest_agent_quests, quest_get, quest_get_state, quest_get_data,
    quest_get_key, quest_set_key, quest_get_display_name, quest_add, QuestState,
    quest_log_build_items, quest_run_action)
from sbs_utils.procedural.roles import has_role, role
from sbs_utils.procedural.query import (
    to_object, to_object_list, to_id, to_id_list, to_set, is_space_object_id)
from sbs_utils.procedural.gui.overlay import overlay_kind, consoles_of
from sbs_utils.procedural.amd_overlay import overlay_amd, _PRIMARY
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.sides import to_side_id, side_are_enemies, is_hostile_to_players
from sbs_utils.procedural.timers import (
    set_timer, is_timer_set, is_timer_finished, get_time_remaining,
    format_time_remaining)
from sbs_utils.procedural.comms import comms_broadcast
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.procedural.gui import gui_list_box_is_header
from sbs_utils.procedural.amd_schema import amd_kind_defaults
from sbs_utils.procedural.amd import KIND_KEY
from sbs_utils.agent import Agent


def _quest_audience(agent_id):
    """Who should see a quest's complete/fail line. A per-ship quest is owned by a
    real space object -> tell that ship. A shared-scope quest is owned by the
    non-space SHARED story agent (Agent.SHARED_ID), which is NOT a player ship, so
    tell every player instead - passing SHARED to send_message_to_player_ship
    raises "invalid space object"."""
    if is_space_object_id(agent_id):
        return agent_id
    return role("__player__")


def _quest_overlay_audience(agent_id):
    """The CONSOLE clients that should see a quest's overlays: the participant
    ships' linked consoles (overlays target consoles, not ships)."""
    return consoles_of(to_set(_quest_audience(agent_id)))


# How long an inline overlay directive stays up, by kind. Mirrors announce()'s
# _LEVEL_SECONDS so `On complete: toast ...` and an announce at status level agree.
# A kind with no entry gets 4s - transient, because an authored directive is a
# notification; anything that must persist belongs in the log or an info card.
_DIRECTIVE_SECONDS = {"hero": 5, "lower_third": 8, "banner": 6, "toast": 3}


def _fire_overlay_directive(directive, to):
    """Fire one inline overlay directive: ``<kind> <text>`` (e.g. ``hero CONVOY
    SAVED``) or ``overlay <key>`` to fire a declared amd_overlays record. The kind's
    primary field (title/text/line) receives the text."""
    directive = str(directive or "").strip()
    if not directive:
        return
    parts = directive.split(None, 1)
    kind = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""
    if kind == "overlay":
        overlay_amd(rest, to=to)
        return
    prim = _PRIMARY.get(kind, "title")
    # Pass a LIFETIME. overlay_kind only schedules a dismiss when it is given one, so
    # without this an authored `On accept: toast ...` was registered STICKY: the text sat
    # on every console for the rest of the mission, and restarting the mission script was
    # the only thing that cleared it. overlay_toast() has always expired; this path never
    # did, which is why the two behaved differently.
    #
    # The defaults match announce()'s _LEVEL_SECONDS for the same kinds, so a directive
    # and an announce of the same weight stay on screen for the same time.
    overlay_kind(kind, to=to, seconds=_DIRECTIVE_SECONDS.get(kind, 4), **{prim: rest})


def _quest_noun(data):
    """What to call this quest to the crew: "Mission" only when it IS the mission.

    The player already meets three words for one thing - the tab says Quests, an AMD
    author writes Job, and the library used to say Mission for every last step of every
    arc. "Mission" is reserved for a quest that ends the game (`end_win`/`end_lose`),
    where it is simply true; everything else is a Quest, which is the word on the tab
    the player clicks to find it.
    """
    if data and (data.get("end_win") or data.get("end_lose")):
        return "Mission"
    return "Quest"


def _quest_author_announces(data, ref_key, inline_key):
    """True when the quest carries its own completion/failure announcement.

    `on_complete` / `on_fail` are overlay DIRECTIVES (`<kind> <text>`), so a quest that
    has one is already telling the crew - and the library adding its own line made every
    such quest announce twice, in two different vocabularies ("Job complete: Mercy Run"
    then "Mission complete: Mercy Run"). Authored wording wins where an author wrote any.

    TRADE-OFF worth knowing: the overlay is the attention layer and the broadcast is the
    durable log, so suppressing the broadcast means an authored completion leaves no line
    in the waterfall. That is the intent here (the duplicate is what playtesters
    reported), but if a quest wants both, it should say so rather than getting it by
    accident.
    """
    if not data:
        return False
    for key in (ref_key, inline_key):
        # accept underscore or space authoring, same as _quest_fire_overlays
        if data.get(key) or data.get(key.replace("_", " ")):
            return True
    return False


def _quest_fire_overlays(agent_id, data, ref_key, inline_key):
    """Fire a quest lifecycle overlay to the quest's participant consoles. Supports
    BOTH forms: a declared-record reference (``ref_key`` -> ``overlay_amd(key)``) and
    an inline directive (``inline_key`` -> ``<kind> <text>``)."""
    if not data:
        return
    # accept underscore or space authoring: `complete_overlay` or `Complete Overlay`
    ref = data.get(ref_key) or data.get(ref_key.replace("_", " "))
    inline = data.get(inline_key) or data.get(inline_key.replace("_", " "))
    if not ref and not inline:
        return
    to = _quest_overlay_audience(agent_id)
    if ref:
        overlay_amd(str(ref).strip(), to=to)
    if inline:
        _fire_overlay_directive(inline, to)


def _quest_rep_holder(agent_id):
    """True where a reputation line MEANS something: a player ship, or the shared story
    agent standing in for the crew.

    A world-held quest (a station, a side) carries no reputation. ``reputation_adjust``
    shifts *this agent's* standing with a faction, so a rep penalty on DS1's resupply
    quest would move DS1's own opinion of TSN - which no player can perceive and no
    author means. World stakes are world state (``Then:`` / ``Action:``). Silently
    ignoring the line would hide the mistake, so ``sbs lint`` rejects it at author time;
    this is the runtime backstop. DESIGN_RECORD.md s4.
    """
    if agent_id == Agent.SHARED_ID:
        return True
    return has_role(agent_id, "__player__")


def _quest_grant_reputation(agent_id, block):
    """Apply a reward/penalty block's ``reputation`` map, if this holder can carry one.

    Deltas apply exactly as authored - a ``Penalty:`` never flips the sign for you (see
    ``amd_reward``).
    """
    rep = (block or {}).get("reputation")
    if not rep:
        return
    if not _quest_rep_holder(agent_id):
        return
    from sbs_utils.procedural.reputation import reputation_apply
    reputation_apply(agent_id, rep)


def quest_grant_reward(agent_id, reward):
    """Grant a quest reward: credits to the agent's side, items to the agent, and
    reputation to the agent (player/SHARED holders only - see ``_quest_rep_holder``)."""
    if not isinstance(reward, dict):
        return
    credits = reward.get("credits", 0)
    if credits:
        ship = to_object(agent_id)
        side = getattr(ship, "side", None)   # SHARED / console agents have no .side
        if side:
            sid = to_side_id(side)
            set_inventory_value(sid, "credits", get_inventory_value(sid, "credits", 0) + credits)
    for k, n in (reward.get("items") or {}).items():
        set_inventory_value(agent_id, k, get_inventory_value(agent_id, k, 0) + n)
    _quest_grant_reputation(agent_id, reward)


def quest_grant_penalty(agent_id, penalty):
    """Apply a quest penalty (mirror of quest_grant_reward): deduct credits from
    the agent's side, remove items from the agent, and apply any reputation block
    (player/SHARED holders only). Credits and items never go below zero; reputation
    applies as authored, so a penalty's ``earns`` carries its own sign."""
    if not isinstance(penalty, dict):
        return
    credits = penalty.get("credits", 0)
    if credits:
        ship = to_object(agent_id)
        side = getattr(ship, "side", None)   # SHARED / console agents have no .side
        if side:
            sid = to_side_id(side)
            set_inventory_value(sid, "credits", max(0, get_inventory_value(sid, "credits", 0) - credits))
    for k, n in (penalty.get("items") or {}).items():
        set_inventory_value(agent_id, k, max(0, get_inventory_value(agent_id, k, 0) - n))
    _quest_grant_reputation(agent_id, penalty)


def _quest_maybe_end_game(agent_id, quest_id, data, win):
    """Fire game_over once if this quest is a game-ending mission quest.

    A quest with end_win (on COMPLETE) or end_lose (on FAILED) ends the game;
    win_text/lose_text (falling back to the display name) is the end-screen reason.
    Guarding the actual teardown lives in the //signal/game_over route.
    """
    if not data.get("end_win" if win else "end_lose"):
        return
    text = data.get("win_text" if win else "lose_text") or quest_get_display_name(agent_id, quest_id) or quest_id
    signal_emit("game_over", {"WIN": bool(win), "TEXT": str(text),
                              "AGENT_ID": to_id(agent_id), "QUEST_ID": quest_id})


def quest_reeval_mission(agent_id, parent_qid):
    """Re-evaluate a mission (parent) quest from its children's states.

    Any `critical` child FAILED -> the mission FAILS; else once every `required`
    child is COMPLETE the mission COMPLETES. No-op unless the parent is ACTIVE, so
    it settles exactly once. Children link up via their data `parent: <parent_qid>`.
    """
    if not parent_qid or quest_get_state(agent_id, parent_qid) != QuestState.ACTIVE:
        return
    tree = quest_agent_quests(agent_id)
    if tree is None:
        return
    required_done = []
    # Walk the WHOLE tree, not just the top level. A child nested under an arc
    # (`group/step`) still declares `parent:` for the win/lose mission tree, and a
    # top-level-only scan simply never sees it - the parent then waits forever on
    # required children it cannot find.
    all_ids = []
    def _walk(children, prefix):
        for cid, q in (children or {}).items():
            path = f"{prefix}/{cid}" if prefix else cid
            all_ids.append(path)
            _walk(q.get("children"), path)
    _walk(tree.get("children", {}), "")
    for qid in all_ids:
        d = quest_get_data(agent_id, qid) or {}
        if d.get("parent") != parent_qid:
            continue
        st = quest_get_state(agent_id, qid)
        if d.get("critical") and st == QuestState.FAILED:
            quest_mark_failed(agent_id, parent_qid)
            return
        if d.get("required"):
            required_done.append(st == QuestState.COMPLETE)
    if required_done and all(required_done):
        quest_mark_complete(agent_id, parent_qid)


def _quest_tree_parent(quest_id):
    """The parent path of a nested quest key (`arc/step` -> `arc`); None for a top-level key."""
    return quest_id.rsplit("/", 1)[0] if "/" in quest_id else None


def quest_reeval_tree_parent(agent_id, quest_id):
    """A quest with CHILDREN completes when ALL its children are COMPLETE - the natural
    'the arc is done when its steps are done'. Called when a nested `arc/step` settles: it
    completes the tree parent, which recurses UP via quest_mark_complete. SECRET children
    are unrevealed future steps, so they block completion (the arc isn't finished). Only an
    ACTIVE parent is settled; idempotent (quest_mark_complete no-ops if already complete).

    Author a parent as a pure CONTAINER (no own When trigger) with leaf children as the
    objectives, so its completion is driven only by the children (unambiguous)."""
    parent = _quest_tree_parent(quest_id)
    if parent is None:
        return
    if quest_get_state(agent_id, parent) != QuestState.ACTIVE:
        return
    pnode = quest_get(agent_id, parent)
    kids = (pnode.get("children") if pnode is not None else None) or {}
    if not kids:
        return
    for c in kids.values():
        if int(c.get("state", 0) or 0) != int(QuestState.COMPLETE):
            return  # a child still to do -> parent stays active
    quest_mark_complete(agent_id, parent)


def quest_mark_active(agent_id, quest_id):
    """Set a quest ACTIVE (idempotent)."""
    if quest_get_state(agent_id, quest_id) == QuestState.ACTIVE:
        return
    quest_set_key(agent_id, quest_id, "state", QuestState.ACTIVE)
    # `Action:` fires when the beat STARTS. quest.quest_set_state runs it, but the
    # DRIVER writes state directly - so the block was dead on every path an author
    # actually uses: the Accept button, `Then: reveal`, a quest granted ACTIVE (the
    # default for Beat/Arc/Objective), and a `Starts when:` swap-in. The one documented
    # example in amd-format.md takes the swap-in path and never fired.
    # Ordering matches quest_set_state: act first, so a route hearing the signal sees a
    # world that has already changed rather than one it has to guess about.
    quest_run_action(agent_id, quest_id)
    data = quest_get_data(agent_id, quest_id) or {}
    _quest_fire_overlays(agent_id, data, "accept_overlay", "on_accept")
    # Activation announcement, completing the set. The idempotence guard above runs
    # BEFORE this, so the driver hearing its own signal back is a no-op.
    signal_emit("quest_started", {"AGENT_ID": agent_id, "QUEST_ID": quest_id,
                                  "DATA": data})


def quest_mark_complete(agent_id, quest_id):
    """Complete a quest (idempotent): set state, grant reward, announce.

    A quest waiting on a `Starts when:` trigger passes through here when that trigger
    fires - it is armed with it - and STARTS instead: its real advancement trigger is
    swapped in and nothing else happens (no reward, no announcement, no reveal)."""
    if quest_get_state(agent_id, quest_id) == QuestState.COMPLETE:
        return
    data = quest_get_data(agent_id, quest_id) or {}
    if _quest_swap_in_armed(agent_id, quest_id, data):
        return
    quest_set_key(agent_id, quest_id, "state", QuestState.COMPLETE)
    quest_grant_reward(agent_id, data.get("reward"))
    quest_reveal(agent_id, data.get("reveal"))
    # On-complete actions: emit an optional custom signal (e.g. to flip
    # diplomacy), and the generic SUCCESS announcement carrying the data so addons
    # can react (the universe applies the declarative rep: block from it).
    sig = data.get("signal")
    if sig:
        signal_emit(sig, {"AGENT_ID": agent_id, "QUEST_ID": quest_id})
    signal_emit("quest_succeeded", {"AGENT_ID": agent_id, "QUEST_ID": quest_id, "DATA": data})
    _quest_fire_overlays(agent_id, data, "complete_overlay", "on_complete")
    name = quest_get_display_name(agent_id, quest_id) or quest_id
    if not _quest_author_announces(data, "complete_overlay", "on_complete"):
        # Tagged at the SOURCE, so every mission's quest traffic lands in the log's
        # Mission tab without any mission being edited. `tip` gives a completion its
        # callout; failures below take `danger`.
        comms_broadcast(_quest_audience(agent_id),
                        f"{_quest_noun(data)} complete: {name}", "#0f0",
                        category="mission", severity="tip")
    # A game-ending mission quest wins the game; then bubble up to a parent mission.
    _quest_maybe_end_game(agent_id, quest_id, data, win=True)
    if data.get("parent"):
        quest_reeval_mission(agent_id, data.get("parent"))
    # A quest with children (a nested-key arc) completes when all its children complete:
    # settle this quest's TREE parent, recursing up.
    quest_reeval_tree_parent(agent_id, quest_id)


_STATE_NAMES = {
    "idle": QuestState.IDLE, "active": QuestState.ACTIVE, "secret": QuestState.SECRET,
    "complete": QuestState.COMPLETE, "failed": QuestState.FAILED,
    # `At start:` in the author's words. Accepted here as well as translated in
    # amd_quest, so a doc read WITHOUT the quest fact-handler still grants correctly.
    "offered": QuestState.IDLE, "available": QuestState.IDLE,
    "running": QuestState.ACTIVE, "hidden": QuestState.SECRET,
    "done": QuestState.COMPLETE,
}

# Goal keys whose `count` is a completion target a mission may want to scale by difficulty.
_COUNT_GOAL_KEYS = ("on_signal", "on_kill", "on_scan", "on_reach", "on_dock", "on_collect",
                    "on_tow")


def _arm_start_trigger(data):
    """A quest authored `Starts when: <trigger>` is granted armed with THAT trigger, its
    real advancement trigger set aside under `armed_trigger`.

    Doing it this way means a start trigger needs no matching code of its own: every
    on_kill / on_scan / on_dock / on_reach / on_signal matcher already knows how to
    recognize a trigger, so the start uses the same ones. `quest_mark_complete` swaps the
    real trigger back in instead of completing (see `_quest_swap_in_armed`).

    Before this, `Starts when:` wrote the SAME key `Done when:` writes, so a quest
    carrying both completed on whichever fired first - the gate could finish the job."""
    start = data.get("start_trigger")
    if not isinstance(start, dict) or not start.get("trigger"):
        return data
    out = dict(data)
    out["armed_trigger"] = {k: out.pop(k) for k in _COUNT_GOAL_KEYS if k in out}
    out.pop("start_trigger", None)
    out[start["trigger"]] = start.get("data") or {}
    return out


def _quest_swap_in_armed(agent_id, quest_id, data):
    """The start trigger fired: arm the real one instead of completing. True when this
    was a start (so the caller must not complete, reward or announce)."""
    armed = data.get("armed_trigger")
    if armed is None:
        return False
    for k in _COUNT_GOAL_KEYS:
        data.pop(k, None)
    data.update(armed)
    data.pop("armed_trigger", None)
    quest_set_key(agent_id, quest_id, "progress", 0)
    return True


def _scale_goal_counts(data, scale):
    """Return `data` with every explicit goal `count` scaled by `scale` (rounded, min 1),
    WITHOUT touching the shared doc (goal dicts are copied only when scaled). Goals with no
    authored count - singleton objectives like `reach the shuttle` - are left as-is. A scale
    of 1.0 (or falsy) returns `data` unchanged."""
    if not scale or scale == 1.0:
        return data
    out = None
    for gk in _COUNT_GOAL_KEYS:
        g = data.get(gk)
        if isinstance(g, dict) and "count" in g:
            if out is None:
                out = dict(data)
            g2 = dict(g)
            g2["count"] = max(1, int(g2["count"] * scale + 0.5))
            out[gk] = g2
    return out if out is not None else data


def _quest_held_by(name, qid):
    """Resolve a ``Held by:`` actor to the agent id that should hold the quest.

    Uses ``amd_action_actors`` - the SAME resolution a stage direction uses (a declared
    landmark key first, then a role), so "DS1" means the same thing in ``Held by:`` as it
    does in ``DS1 departs``. ``shared`` / ``game`` / ``story`` name the shared story agent.

    Returns None if nothing answers to the name, having LOGGED it. The caller skips the
    quest rather than falling back to the passed-in agent: quietly parking a station's
    resupply job on a player ship would put a world deadline in a crew's log and pay its
    penalty out of the crew's pocket. Most often this means the AMD was granted before the
    landmark spawned, which the message says.

    A name matching several agents grants to all of them - ``quest_add`` takes a list, and
    "every listening post wants a resupply" is a legitimate thing to author.
    """
    key = str(name).strip()
    if key.lower() in ("shared", "game", "story"):
        return [Agent.SHARED_ID]
    from sbs_utils.procedural.amd_action import amd_action_actors
    ids = amd_action_actors(key)
    if not ids:
        try:
            from sbs_utils.procedural.execution import log
            log(f"quest {qid!r} is 'Held by: {key}', but nothing answers to that name "
                f"- is it granted before the landmark spawns?", "quest", "warning")
        except Exception:
            pass
        return None
    return list(ids)


def quest_grant_amd(agent_id, doc, _prefix="", count_scale=1.0):
    """Grant all quests from a parsed AMD story doc to an agent at once.

    Each heading becomes a quest; its data `state` (active/secret/idle/...) sets
    the starting state, so a multi-step story is granted as parent ACTIVE + later
    steps SECRET, chained by each step's `reveal`. Idempotent per quest id.

    NESTED headings become NESTED quests: a deeper heading (`#### step` under a
    `### arc`) is granted with the '/'-path key `arc/step` (via quest_folder), so
    the arc renders as a collapsible tree in the Quests tab and its steps trigger /
    reveal by their full path. The parent is granted before its children so
    quest_folder can attach them.

    `count_scale` scales every explicit goal COUNT (on_signal/on_kill/on_scan/... `count`)
    by that factor, so a mission can size a scalable job board by difficulty WITHOUT editing
    the AMD - pair it with the same factor on the matching spawn counts. Singleton goals (no
    authored count) never scale; the default 1.0 leaves every existing caller unchanged.
    """
    if doc is None:
        return
    for n in doc.get("children", []):
        key = n.get("key")
        if not key:
            continue
        qid = _prefix + key
        data = n.get("data") or {}
        # A record that called itself `Beat` / `Arc` / `Cue` has already said it is the
        # whole crew's and already running; only a record that DIFFERS writes the field.
        implied = amd_kind_defaults(data.get(KIND_KEY) if hasattr(data, "get") else None)
        # WHO holds this quest. `Held by: <actor>` names it outright (a station's
        # resupply job belongs to the station); `scope: shared` grants to the game
        # (SHARED) agent so the whole crew shares the arc; otherwise the given agent.
        # A name can answer for several agents, so the holder is always a LIST.
        scope = data.get("scope") or implied.get("scope")
        held_by = data.get("held_by")
        if held_by:
            targets = _quest_held_by(held_by, qid)
            if not targets:
                continue    # already logged; never fall back to the player
        else:
            targets = [Agent.SHARED_ID if scope == "shared" else agent_id]
        for target in targets:
            # ABSENT, not IDLE. quest_get_state returns IDLE for a quest that does not
            # exist AND for one that exists and is merely OFFERED - so a re-grant ran
            # quest_add over every unaccepted quest, and quest_add builds a FRESH node
            # with "children": {}. Any nested arc step underneath it, however far along,
            # was silently discarded. (A re-grant happens on the OU Continue path and on
            # a map restart.) One behavior change: re-granting with a different
            # count_scale no longer re-scales an already-offered quest.
            if quest_get(target, qid) is None:
                st = _STATE_NAMES.get(
                    str(data.get("state") or implied.get("state") or "idle").lower(),
                    QuestState.IDLE)
                quest_add(target, qid, n.get("display_text"),
                          (n.get("description") or "").strip(), state=st,
                          data=_arm_start_trigger(_scale_goal_counts(data, count_scale)))
        # Recurse into nested headings, building the child path key `<qid>/<childkey>`.
        # The steps of a `Held by:` job belong to the SAME holder - a station's job does
        # not have its steps held by a passing ship. Without a `Held by:` the historical
        # behavior is kept exactly: children are granted against the passed-in agent and
        # re-resolve their own `scope`, so a `scope: shared` parent's plain children still
        # land on the ship as they always have.
        if n.get("children"):
            for child_agent in (targets if held_by else [agent_id]):
                quest_grant_amd(child_agent, n, _prefix=qid + "/", count_scale=count_scale)


def quest_reveal(agent_id, reveal):
    """Activate sub-quests revealed on completion (reveal: id, or [ids]).

    The revealed quests must already exist on the agent (added SECRET/IDLE when
    the parent story was granted); this flips them ACTIVE so their triggers go
    live - the next step(s) of a multi-step bridge story.
    """
    if not reveal:
        return
    ids = reveal if isinstance(reveal, list) else [reveal]
    for qid in ids:
        quest_mark_active(agent_id, qid)


def quest_shared_state(quest_id):
    """State of a game-level (SHARED) quest - convenience for narrative arcs."""
    return int(quest_get_state(Agent.SHARED_ID, quest_id) or 0)


def quest_mark_failed(agent_id, quest_id):
    """Fail an active quest (idempotent): set state, apply penalty, announce, then
    fire the lose (if end_lose) and bubble up to the parent mission."""
    if quest_get_state(agent_id, quest_id) != QuestState.ACTIVE:
        return
    quest_set_key(agent_id, quest_id, "state", QuestState.FAILED)
    data = quest_get_data(agent_id, quest_id) or {}
    quest_grant_penalty(agent_id, data.get("penalty"))
    _quest_fire_overlays(agent_id, data, "fail_overlay", "on_fail")
    name = quest_get_display_name(agent_id, quest_id) or quest_id
    if not _quest_author_announces(data, "fail_overlay", "on_fail"):
        comms_broadcast(_quest_audience(agent_id),
                        f"{_quest_noun(data)} failed: {name}", "#f33",
                        category="mission", severity="danger")
    _quest_maybe_end_game(agent_id, quest_id, data, win=False)
    # The FAILURE twin of quest_succeeded. There was no announcement for failure at
    # all, so anything reacting to a lost objective had nothing to listen to.
    signal_emit("quest_failed_done", {"AGENT_ID": agent_id, "QUEST_ID": quest_id,
                                      "DATA": data})
    if data.get("parent"):
        quest_reeval_mission(agent_id, data.get("parent"))


def _collect_active_quests(children, prefix, out):
    """Recurse the quest tree, appending (full_path, data) for every ACTIVE quest - so
    NESTED arc steps (`arc/step`, authored as nested quest keys) fire their triggers too.
    The path is '/'-separated so quest_get_key / quest_set_key / quest_mark_complete
    navigate it via quest_folder. Flat quests (no children) are unchanged (path == key)."""
    for cid, q in (children or {}).items():
        path = prefix + cid
        if int(q.get("state", 0) or 0) == int(QuestState.ACTIVE):
            out.append((path, q.get("data") or {}))
        sub = q.get("children")
        if sub:
            _collect_active_quests(sub, path + "/", out)


# `_active_quests` is called by four tick functions every 2 sim-seconds, per holder,
# and each call walks the agent's ENTIRE tree - COMPLETE, FAILED and SECRET nodes
# included - to build a fresh list of the active ones. On a tick where nothing
# changed state, that is four identical walks. Keyed on the generation, so it is
# exactly as fresh as the tree.
_ACTIVE_CACHE = {}
_ACTIVE_GEN = [-1]
_ANY_STATE_CACHE = {}
_ANY_STATE_GEN = [-1]


def _quest_holders():
    """Every agent that actually holds a quest tree.

    Quest trees live in the ``__quests__`` inventory key, so this class-level registry IS
    the holder set - the same shape ``brains_run_all`` uses for ``__BRAIN__``. It replaces
    ``[SHARED_ID] + players``, which silently skipped any quest granted to a station or a
    side: the quest existed, showed its objective, and its deadline never fired. Nothing
    logged, because nothing looked.

    Self-limiting by construction (an agent with no quests never appears), so it needs no
    separate bound. If a mission ever holds enough quests for this to matter, wrap it in a
    ``RollingSlicer`` the way brains and objectives already are.

    Returned as a LIST, not the live set. ``quest_mark_complete``/``_failed`` inside the
    walk can grant a follow-on quest to an agent that had none, which mutates the registry
    mid-iteration and raises "Set changed size during iteration" - the lesson
    ``brain.py`` s396-400 already paid for once.
    """
    from sbs_utils.procedural.inventory import has_inventory
    return list(has_inventory("__quests__"))


def _active_quests(agent_id):
    """(quest_id, data) for each ACTIVE quest on the agent, INCLUDING nested arc steps
    (quest_id is the full '/'-path). Every on_* trigger handler iterates this."""
    from sbs_utils.procedural.quest import quest_generation
    gen = quest_generation()
    if _ACTIVE_GEN[0] != gen:
        # Wholesale, not per-agent: it also means the cache never holds a dead
        # agent's entry for more than one generation.
        _ACTIVE_CACHE.clear()
        _ACTIVE_GEN[0] = gen
    hit = _ACTIVE_CACHE.get(agent_id)
    if hit is not None:
        return hit
    tree = quest_agent_quests(agent_id)
    out = []
    if tree is not None:
        _collect_active_quests(tree.get("children", {}), "", out)
    # The list is now SHARED between callers. That is safe for the same reason it was
    # safe before: callers mutate quest STATE, not this list, and any such write bumps
    # the generation and invalidates on the next call. (_quest_holders returns a
    # list(...) copy of the live set for the mirror-image reason - see its docstring.)
    _ACTIVE_CACHE[agent_id] = out
    return out


def quest_any_holder_state(qid, state):
    """True while ANY quest holder has `qid` in `state`.

    Behind the same generation guard as _active_quests. The urge system asks this per
    actor per urge on every pass, and it grows with the holder set - Open Universe
    makes every station with a waiting passenger a quest holder, so the scan grows
    with the number of populated systems.
    """
    from sbs_utils.procedural.quest import quest_generation, quest_get_state
    gen = quest_generation()
    if _ANY_STATE_GEN[0] != gen:
        _ANY_STATE_CACHE.clear()
        _ANY_STATE_GEN[0] = gen
    key = (qid, int(state))
    hit = _ANY_STATE_CACHE.get(key)
    if hit is None:
        hit = any(int(quest_get_state(h, qid) or 0) == int(state)
                  for h in _quest_holders())
        _ANY_STATE_CACHE[key] = hit
    return hit


def _advance_count(agent_id, qid, data, need):
    prog = (quest_get_key(agent_id, qid, "progress", 0) or 0) + 1
    quest_set_key(agent_id, qid, "progress", prog)
    if prog >= need:
        quest_mark_complete(agent_id, qid)


def _kill_is_hostile(killer_id, victim_id):
    """Was the victim an ENEMY? Of the killer if it has a side, otherwise of the
    players (e.g. a SHARED/game-level quest whose killer is Agent.SHARED_ID). Lets a
    kill quest count "enemies" by diplomacy instead of a hardcoded faction role, and
    stops a ceasefired/neutral (or surrendered) ship from counting."""
    killer = to_object(killer_id)
    kside = getattr(killer, "side", None) if killer is not None else None
    if kside:
        return side_are_enemies(kside, victim_id)
    return is_hostile_to_players(victim_id, scope_role=None)


def quest_on_kill(killer_id, destroyed_id):
    """Advance the killer's on_kill quests when an object is destroyed.

    The on_kill match is general — all keys optional and AND-combined:
      role    : victim must hold this role (exact; e.g. "raider"). Back-compatible.
      roles   : victim must hold ANY of these roles (a list) - a broader type filter.
      hostile : if truthy, the victim must have been an ENEMY by diplomacy (of the
                killer, or of the players for a SHARED quest). This is the general,
                faction-agnostic, ceasefire-safe way to score "destroy N enemies" -
                prefer it over a hardcoded raider role.
    Omitting all three counts any destruction (unchanged legacy behavior)."""
    if killer_id is None:
        return
    for qid, data in _active_quests(killer_id):
        trig = data.get("on_kill")
        if not isinstance(trig, dict):
            continue
        role = trig.get("role")
        if role and not has_role(destroyed_id, role):
            continue
        roles = trig.get("roles")
        if roles and not any(has_role(destroyed_id, r) for r in roles):
            continue
        if trig.get("hostile") and not _kill_is_hostile(killer_id, destroyed_id):
            continue
        _advance_count(killer_id, qid, data, trig.get("count", 1))


def quest_on_kill_shared(destroyed_id):
    """Advance game-level (SHARED) on_kill quests for any kill. Called once per
    kill (separate from per-killer credit) so SHARED counts aren't doubled by the
    source+parent calls."""
    quest_on_kill(Agent.SHARED_ID, destroyed_id)


def quest_on_scan(scanner_id, scanned_id):
    """Advance the scanner's (and game/SHARED) on_scan quests when science scans
    a target. on_scan {role: <role>} (optional) filters by the scanned role.

    Each DISTINCT target counts once toward a counted goal (re-scanning the same
    object does not over-count) - the ids already counted are kept in the quest's
    ``_scanned`` list."""
    if scanner_id is None:
        return
    for aid in (scanner_id, Agent.SHARED_ID):
        for qid, data in _active_quests(aid):
            trig = data.get("on_scan")
            if not isinstance(trig, dict):
                continue
            want = trig.get("role")
            if want and not has_role(scanned_id, want):
                continue
            seen = quest_get_key(aid, qid, "_scanned", None) or []
            if scanned_id in seen:
                continue
            seen.append(scanned_id)
            quest_set_key(aid, qid, "_scanned", seen)
            _advance_count(aid, qid, data, trig.get("count", 1))


def _quest_scan_reveals(scanner_id, scanned_id):
    """Active on_scan quests (on the scanner or SHARED) that carry declarative scan text
    (reveal_scan) and whose on_scan role matches the scanned object. Returns the list of
    reveal-text strings (usually one)."""
    out = []
    if scanner_id is None or scanned_id is None:
        return out
    for aid in (scanner_id, Agent.SHARED_ID):
        for qid, data in _active_quests(aid):
            reveal = data.get("reveal_scan")
            if not reveal:
                continue
            trig = data.get("on_scan")
            want = trig.get("role") if isinstance(trig, dict) else None
            if want and not has_role(scanned_id, want):
                continue
            out.append(str(reveal))
    return out


def quest_scan_enabled(scanner_id, scanned_id):
    """True if the scanned object is the target of an active on_scan quest that defines
    scan text. A //enable/science route gates on this so quest-scan targets become
    scannable without a hand-authored enable route."""
    return len(_quest_scan_reveals(scanner_id, scanned_id)) > 0


def quest_scan_text(scanner_id, scanned_id):
    """The declarative scan text to show for a quest-scan target (joins multiple matching
    quests). Rendered by the driver's //science route as the object's scan result."""
    return "^^".join(_quest_scan_reveals(scanner_id, scanned_id))


def quest_on_dock(ship_id, station_id):
    """Advance the ship's (and game/SHARED) on_dock quests when it docks a
    station. on_dock {role: <role>} (optional) filters by the station's role."""
    if ship_id is None:
        return
    for aid in (ship_id, Agent.SHARED_ID):
        for qid, data in _active_quests(aid):
            trig = data.get("on_dock")
            if not isinstance(trig, dict):
                continue
            want = trig.get("role")
            if want and not has_role(station_id, want):
                continue
            _advance_count(aid, qid, data, trig.get("count", 1))


def quest_on_tow(ship_id, towed_id):
    """Advance on_tow quests when `ship_id` delivers `towed_id` under tow.

    `on_tow {role: <role>}` filters by what was delivered, so "tow 2 survivors" and
    "tow the derelict home" are the same trigger with a different noun. Credit goes to
    the HAULER (and SHARED) - the ship that did the work, not whatever it was dragging.
    """
    if ship_id is None:
        return
    for aid in (ship_id, Agent.SHARED_ID):
        for qid, data in _active_quests(aid):
            trig = data.get("on_tow")
            if not isinstance(trig, dict):
                continue
            want = trig.get("role")
            if want and not has_role(towed_id, want):
                continue
            _advance_count(aid, qid, data, trig.get("count", 1))


def quest_on_signal(name):
    """Generic named trigger for on_signal / on_comms quests (escape hatch).

    A mission/comms route fires signal_emit("quest_signal", {"SIGNAL_NAME": ...});
    this advances any ACTIVE quest (players + SHARED) whose on_signal {name} or
    on_comms {option} matches. Lets authors add beats with no new driver code.
    """
    # _quest_holders(), like every sibling handler. This was the last place still
    # using `[SHARED] + players`, which is the exact pattern _quest_holders was written
    # to replace: it silently skips a quest granted to a station or a side, so a
    # `Held by:` job's `Done when: signal` never advanced and its `Fails when: signal`
    # never fired, with nothing logged because nothing looked.
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("on_signal") or data.get("on_comms")
            if isinstance(trig, dict):
                want = trig.get("name") or trig.get("option")
                if not want or want == name:
                    _advance_count(aid, qid, data, trig.get("count", 1))
            # Fail trigger: a matching signal fails the quest (mirror of on_signal).
            ftrig = data.get("fail_on_signal")
            if isinstance(ftrig, dict):
                fwant = ftrig.get("name") or ftrig.get("option")
                if not fwant or fwant == name:
                    quest_mark_failed(aid, qid)


def quest_credit_signal(agent_id, name):
    """Owner-scoped on_signal advance: like quest_on_signal but for ONE agent only, so a
    shared/contested quest target can credit the ship that completed it (peacetime
    multiplayer) instead of every holder. Crediting only (no fail-trigger handling)."""
    for qid, data in _active_quests(agent_id):
        trig = data.get("on_signal") or data.get("on_comms")
        if isinstance(trig, dict):
            want = trig.get("name") or trig.get("option")
            if not want or want == name:
                _advance_count(agent_id, qid, data, trig.get("count", 1))


def quest_set_owner(target, ship):
    """Claim a quest TARGET for a ship (peacetime multiplayer: shared-pool targets owned per-
    target so a non-owner can't complete or steal it). ship 0/None clears the claim. Stored as
    the target's 'quest_owner' inventory value."""
    set_inventory_value(to_id(target), "quest_owner", to_id(ship) if ship else 0)


def quest_owner(target):
    """The ship id that has claimed this quest target (0 = unclaimed)."""
    return get_inventory_value(to_id(target), "quest_owner", 0) or 0


def quest_is_owner(ship, target):
    """True if ship is the claimed owner of target."""
    return quest_owner(target) == to_id(ship)


def quest_fail_on_all_dead(destroyed_id=None):
    """Fail ACTIVE quests whose fail_on_all_dead {role} guard just emptied - the
    last holder of that role has died. Called from the killed route; the victim is
    still registered there, so it is excluded from the remaining count."""
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("fail_on_all_dead")
            if not isinstance(trig, dict):
                continue
            want = trig.get("role")
            if not want:
                continue
            count = len(role(want))
            if destroyed_id is not None and has_role(destroyed_id, want):
                count -= 1  # the ship dying right now still holds the role
            if count <= 0:
                quest_mark_failed(aid, qid)


def quest_tick_fail_after():
    """Watcher tick: fail ACTIVE quests whose fail_after deadline elapsed. The
    deadline is anchored lazily (a per-quest timer set on first sight), so
    activation needs no hook - general to any mission, not just siege."""
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("fail_after")
            if not isinstance(trig, dict):
                continue
            secs = int(trig.get("seconds", 0) or 0) + int(trig.get("minutes", 0) or 0) * 60
            if secs <= 0:
                continue
            tname = "qfail:" + str(qid)
            if not is_timer_set(aid, tname):
                set_timer(aid, tname, seconds=secs)
            elif is_timer_finished(aid, tname):
                quest_mark_failed(aid, qid)


# --- Deadline reminders -------------------------------------------------------------
# A countdown the crew has to open a tab to read is a countdown they discover by failing
# (PRM-11). These are the reminders, on comms, where a bridge already looks.
#
# ABSOLUTE marks, not a fixed interval and not fractions of the deadline. A fixed
# interval is spam by construction; fractions land three messages 15, 7 and 3 seconds
# apart on a short clock, which is a burst rather than a warning. Marks that FIT under
# the deadline mean a 6-minute job gets four and a 45-second job gets two, sparse early
# and tightening as it matters.
QUEST_COUNTDOWN_MARKS = (300, 120, 60, 30)

# The voice used when a quest names no speaker and its holder cannot talk. Registered by
# the MISSION, never named here: the library has no business knowing a faction exists, let
# alone which one is in charge. Unset means deadline reminders stay silent rather than
# arriving from nobody.
_QUEST_DISPATCH_VOICE = [None]


def quest_dispatch_voice(agent=None):
    """Register the fallback voice for quest reminders, or read the current one.

    A mission calls this once with the character its crews already hear from - LM has a
    "TSN Command" lifeform, Peacetime has Admiral Harkin. Pass None to read.

    Accepts an id, an object, OR a NAME (a Cast/landmark key), which is resolved lazily at
    send time. Lazily on purpose: a mission registers its voice while setting the story up,
    which is before the cast has spawned, so resolving eagerly would store None and stay
    that way for the whole mission.
    """
    if agent is not None:
        _QUEST_DISPATCH_VOICE[0] = agent
    return _QUEST_DISPATCH_VOICE[0]


def quest_dispatch_voice_clear():
    """Forget the registered voice. Part of the per-mission reset - a voice left over
    from the last mission names an agent that no longer exists."""
    _QUEST_DISPATCH_VOICE[0] = None


def _quest_dispatch_id():
    """The registered voice as an agent id, resolving a name if that is what was given."""
    voice = _QUEST_DISPATCH_VOICE[0]
    if voice is None:
        return None
    if isinstance(voice, str):
        ids = _quest_held_by(voice, "dispatch voice")
        return ids[0] if ids else None
    return to_id(voice)


def _quest_speaker(qid, data):
    """Who speaks for this quest, in order of how much the author asked for it.

    `Speaker:` names it outright - the shuttle crew calling in on their own rescue, the
    client chasing a delivery. Failing that, `Held by:` when it resolves to something that
    can talk: a station's job then speaks with the station's own face for no authoring at
    all. Failing that, the mission's registered dispatch voice.

    Returns None when nothing can speak, and the caller stays SILENT rather than sending
    an anonymous message - a reminder from nobody is worse than no reminder.
    """
    for field in ("speaker", "held_by"):
        name = data.get(field)
        if not name:
            continue
        ids = _quest_held_by(name, qid)
        if ids:
            return ids[0]
    return _quest_dispatch_id()


def _quest_countdown_body(data, speaker, fmt, final):
    """The words. Authored line first, then a voice-appropriate default.

    A speaker with no FACE is a machine - a beacon, a ship's transmitter, an empty hull
    with a distress signal still running - so it gets transmission phrasing rather than
    someone politely reporting the time. A cast character keeps the spoken form. The
    author overrides either with `Signal says:`, which is the only way to get wording
    specific to what is actually failing ("LIFE SUPPORT CRITICAL").
    """
    authored = data.get("reminder")
    if authored:
        # `{time}` on purpose rather than a general format: the line is authored text and
        # may legitimately contain braces, so nothing else is interpolated.
        return str(authored).replace("{time}", fmt)
    from sbs_utils.faces import get_face
    if not get_face(speaker):
        body = f"AUTOMATED SIGNAL - {fmt} REMAINING" if fmt else "AUTOMATED SIGNAL"
        return f"{body} - FINAL" if final else body
    body = f"{fmt} remaining." if fmt else "Time is almost up."
    return f"{body} Final warning." if final else body


def _quest_countdown_send(aid, qid, data, mark, left):
    from sbs_utils.procedural.comms import comms_message
    speaker = _quest_speaker(qid, data)
    if speaker is None:
        return
    title = quest_get_key(aid, qid, "display_text", None) or str(qid)
    fmt = format_time_remaining(aid, "qfail:" + str(qid)) or ""
    # The TITLE answers "which clock?" first - a crew can hold several timed jobs at once,
    # and an urgent line about the wrong one is worse than none. Time goes in the body,
    # urgency in the color.
    final = mark <= QUEST_COUNTDOWN_MARKS[-1]
    color = "#f66" if final else "#fc6"
    comms_message(_quest_countdown_body(data, speaker, fmt, final), speaker,
                  _quest_audience(aid), title=title, color=color, title_color=color)


def quest_tick_countdown_reminders():
    """Watcher tick: remind the crew, on comms, as a quest's deadline closes in.

    Rides the deadline `quest_tick_fail_after` already anchors, so a quest with no
    `Fails when:` costs nothing here and one that has not started its clock is skipped.

    Marks are latched per quest, so each fires exactly once. When a single tick crosses
    several at once (a long frame, a mission restart), all of them latch but only the most
    urgent is SENT - passing three marks must not produce three messages.
    """
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("fail_after")
            if not isinstance(trig, dict):
                continue
            total = int(trig.get("seconds", 0) or 0) + int(trig.get("minutes", 0) or 0) * 60
            if total <= 0:
                continue
            tname = "qfail:" + str(qid)
            if not is_timer_set(aid, tname) or is_timer_finished(aid, tname):
                continue
            left = get_time_remaining(aid, tname)
            if left is None:
                continue
            key = "qcd:" + str(qid)
            sent = get_inventory_value(aid, key, None) or []
            # `mark < total`: never warn about "5 minutes left" on a 5-minute deadline -
            # that fires the instant the job is accepted and reads as a bug.
            due = [m for m in QUEST_COUNTDOWN_MARKS
                   if m < total and m not in sent and left <= m]
            if not due:
                continue
            set_inventory_value(aid, key, list(sent) + due)
            _quest_countdown_send(aid, qid, data, min(due), left)


def quest_tick_complete_after():
    """Watcher tick: COMPLETE ACTIVE quests whose complete_after deadline elapsed.
    Symmetric to quest_tick_fail_after - the deadline is anchored lazily (a per-quest
    timer set on first ACTIVE sight), so a purely timed step needs no activation hook.
    On completion the quest's Then: reveal fires, advancing a reveal chain; this lets a
    timed narrative beat be authored as a quest instead of a hand-written timer loop."""
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("complete_after")
            if not isinstance(trig, dict):
                continue
            secs = int(trig.get("seconds", 0) or 0) + int(trig.get("minutes", 0) or 0) * 60
            if secs <= 0:
                continue
            tname = "qdone:" + str(qid)
            if not is_timer_set(aid, tname):
                set_timer(aid, tname, seconds=secs)
            elif is_timer_finished(aid, tname):
                quest_mark_complete(aid, qid)


def _obj_distance(id_a, id_b):
    """Straight-line distance between two space objects by id (Cosmos space), or a huge
    number if either is gone."""
    from sbs_utils.procedural.query import to_space_object
    a, b = to_space_object(id_a), to_space_object(id_b)
    if a is None or b is None:
        return float("inf")
    pa, pb = a.engine_object.pos, b.engine_object.pos
    return ((pa.x - pb.x) ** 2 + (pa.y - pb.y) ** 2 + (pa.z - pb.z) ** 2) ** 0.5


def quest_tick_reach():
    """Watcher tick: complete active ``on_reach{role[,radius]}`` quests when a player
    comes within ``radius`` of any object holding that role. This is the 2.8 "fly within
    R of <object>" navigation objective (absolute coords, not a sector); the sector form
    ``on_reach{sector}`` is handled event-style by :func:`quest_on_arrive`. One shared
    tick replaces a per-objective polling watcher."""
    players = to_object_list(role("__player__"))
    if not players:
        return
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("on_reach")
            if not isinstance(trig, dict) or not trig.get("role"):
                continue  # sector form (or not a reach) -> not ours
            radius = float(trig.get("radius", 5000) or 5000)
            targets = to_object_list(role(trig["role"]))
            if not targets:
                continue
            if any(_obj_distance(p.id, t.id) <= radius for p in players for t in targets):
                quest_mark_complete(aid, qid)


def quest_on_arrive(i, j):
    """Complete on_reach(sector) quests for every player arriving at (i,j).

    Reaching a place is a single event (not a count), so it completes the
    objective. Used by the Open Universe (signal universe_arrived).
    """
    target = [int(i), int(j)]
    for aid in _quest_holders():
        for qid, data in _active_quests(aid):
            trig = data.get("on_reach")
            if isinstance(trig, dict) and list(trig.get("sector") or []) == target:
                quest_mark_complete(aid, qid)


def quest_on_collect(holder_id, key):
    """Advance the holder's (and game/SHARED) on_collect quests on collection."""
    if holder_id is None:
        return
    for aid in (holder_id, Agent.SHARED_ID):
        for qid, data in _active_quests(aid):
            trig = data.get("on_collect")
            if not isinstance(trig, dict):
                continue
            if trig.get("key") and trig.get("key") != key:
                continue
            _advance_count(aid, qid, data, trig.get("count", 1))


# --- Quest log tab (accept/abandon) ------------------------------------------
# Rendering is shared with the end-game results Quests tab via
# procedural.quest quest_log_build_items / quest_log_template / quest_log_title, so
# the look lives in ONE place. Only `sources` (whose quests to show) differs between
# the two logs.
def quest_tab_items(client_id, ship_id):
    """Collapsible quest-log items for THIS console: the game (SHARED), the client,
    and its ship. Rows carry their owning agent (for accept/abandon)."""
    sources = [("Game", Agent.SHARED_ID)]
    if client_id and client_id != 0:
        sources.append(("You", client_id))
    if ship_id and ship_id != 0:
        sources.append(("Ship", ship_id))
    return quest_log_build_items(sources)


# --- Quests-tab action gating ------------------------------------------------
# WHICH consoles may Accept/Abandon or Engage a quest. Resolution order for a given
# quest: its own per-quest override (accept_consoles / engage_consoles, authored via
# the AMD `Accept On:` / `Engage On:` labels) FIRST, else the mission default
# (QUEST_ACCEPT_CONSOLES / QUEST_ENGAGE_CONSOLES). An empty spec means "any console
# that shows the tab" (set QUEST_ACCEPT_CONSOLES = "" to restore the old any-console
# behavior). quest_tab_controls_gate drives the tab: it decides buttons-vs-text per
# console and returns a signature so the tab repaints once when a selection actually
# changes what this console may do (a station-specific job).
def _quest_console_set(spec):
    """Normalise a console spec ("comms, admiral" or ["comms","admiral"] or None) to a
    lowercased set. None/"" -> empty set == 'any console'."""
    if spec is None:
        return set()
    if isinstance(spec, str):
        spec = spec.split(",")
    return {str(c).strip().lower() for c in spec if str(c).strip()}


def _quest_console_allowed(console, spec):
    """True if `console` may act under `spec` (empty spec allows any console)."""
    allowed = _quest_console_set(spec)
    return (not allowed) or ((console or "").strip().lower() in allowed)


def _quest_console_names(spec):
    """Human list of a spec's consoles: 'Comms', 'Comms or Admiral', 'Comms, Admiral or Helm'."""
    names = [c.capitalize() for c in sorted(_quest_console_set(spec))]
    if not names:
        return "any"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " or " + names[-1]


def _quest_effective_consoles(item, key, default_spec):
    """The per-quest console override for `key` (read fresh off the quest's AMD `data`,
    where the `Accept On:` / `Engage On:` labels store it, so it need not ride the log
    row), else the mission `default_spec`."""
    if item is not None and not gui_list_box_is_header(item):
        data = quest_get_data(item.get("agent_id"), item.get("key")) or {}
        per = data.get(key)
        if per not in (None, ""):
            return per
    return default_spec


def quest_tab_controls_gate(console, item, accept_consoles, engage_enabled, engage_consoles):
    """Resolve which Quests-tab action controls THIS console shows for the selected quest.

    Controls are gated by BOTH the console AND the quest's state: Accept is only for an
    available (IDLE) job, Abandon only for an accepted (ACTIVE) one, Engage only for an
    ACTIVE one. A completed/failed job (or a section header / no selection) shows no
    action controls.

    Returns a dict:
      show_accept  - show the Accept button  (console allowed + job IDLE)
      show_abandon - show the Abandon button (console allowed + job ACTIVE)
      show_engage  - show the Engage button  (engage enabled + console allowed + job ACTIVE)
      hint         - one line of guidance when this console shows no control for an
                     actionable job (who can act, or 'accept first'), else ""
      sig          - signature of the above; the tab repaints once when it changes on a
                     selection (so a differing state / station-specific job flips the
                     controls correctly)
    """
    console = (console or "").strip().lower()
    is_quest = item is not None and not gui_list_box_is_header(item)
    state = int(item.get("state")) if is_quest and item.get("state") is not None else None
    IDLE = int(QuestState.IDLE)
    ACTIVE = int(QuestState.ACTIVE)

    acc_spec = _quest_effective_consoles(item, "accept_consoles", accept_consoles)
    can_accept = _quest_console_allowed(console, acc_spec)
    eng_spec = _quest_effective_consoles(item, "engage_consoles", engage_consoles)
    can_engage = engage_enabled and _quest_console_allowed(console, eng_spec)

    show_accept = can_accept and state == IDLE
    show_abandon = can_accept and state == ACTIVE
    show_engage = can_engage and state == ACTIVE

    # One context-appropriate hint when this console offers no control for an actionable
    # (IDLE/ACTIVE) job. Engage consoles explain the accept-first step; other non-accept
    # consoles point to the console that manages jobs.
    hint = ""
    if can_engage and state == IDLE:
        if can_accept:
            hint = "Accept this job before engaging."
        else:
            hint = "Accept this job at the " + _quest_console_names(acc_spec) + " console before engaging."
    elif not can_accept and state in (IDLE, ACTIVE):
        hint = "Manage jobs at the " + _quest_console_names(acc_spec) + " console."

    sig = f"{int(show_accept)}|{int(show_abandon)}|{int(show_engage)}|{hint}"
    return {"show_accept": show_accept, "show_abandon": show_abandon,
            "show_engage": show_engage, "hint": hint, "sig": sig}


def _quest_sig_walk(children, aid, parts):
    for cid, q in (children or {}).items():
        parts.append(f"{aid}:{q.get('id') or cid}:{int(q.get('state', 0) or 0)}")
        _quest_sig_walk(q.get("children"), aid, parts)


def quest_tab_state_sig(client_id, ship_id):
    """A lightweight signature of the quest log shown on this console - every quest's
    (agent, key, state) across the same sources as quest_tab_items (including SECRET, so a
    reveal is caught). Changes whenever a quest is added, revealed, or changes state.

    Drive an `on change` off this to repaint the Quests tab when a quest's status changes
    from ANYWHERE - a kill/scan/dock completing it, a timer failing it, or another console
    accepting it - not just from this console's own buttons."""
    # O(1). This used to walk all three trees and join every node's state, and it is
    # driven by an `on change` in quest_tab.mast - so it ran EVERY FRAME on every
    # console with the Quests tab open, growing with TOTAL quest nodes rather than
    # active ones. Peacetime Remastered at 8 ships is ~270 nodes per console per frame.
    #
    # The trade, stated plainly: a quest changing on a tree this console does not
    # display now costs one extra repaint. A repaint is idempotent; the walk was not
    # free. (_quest_sig_walk is kept below as a debug helper.)
    from sbs_utils.procedural.quest import quest_generation
    return f"{client_id}:{ship_id}:{quest_generation()}"


def quest_tab_accept(item):
    """Accept an available (IDLE) quest. No-op on a section header."""
    if item is None or gui_list_box_is_header(item):
        return
    if item.get("state") == int(QuestState.IDLE):
        quest_mark_active(item.get("agent_id"), item.get("key"))


def quest_tab_abandon(item):
    """Abandon an active quest. No-op on a section header.

    Routes through `quest_mark_failed` rather than writing the state directly. Setting
    `state = FAILED` by hand looked equivalent and was not: it skipped the `Penalty:`,
    the `on_fail` overlay, the announcement, the `quest_failed_done` signal AND
    `_quest_maybe_end_game` - so abandoning was strictly cheaper than letting a quest
    fail on its own (Mercy Run costs 100 credits on the clock, nothing on the button),
    and an `end_lose` quest could be neutralised by abandoning it.

    A deliberate drop and a timed-out drop now mean the same thing.
    """
    if item is None or gui_list_box_is_header(item):
        return
    if item.get("state") == int(QuestState.ACTIVE):
        quest_mark_failed(item.get("agent_id"), item.get("key"))
