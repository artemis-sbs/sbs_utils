from sbs_utils.agent import Agent
from sbs_utils.procedural.quest import QuestState
def _active_quests (agent_id):
    """(quest_id, data) for each ACTIVE quest on the agent, INCLUDING nested arc steps
    (quest_id is the full '/'-path). Every on_* trigger handler iterates this."""
def _advance_count (agent_id, qid, data, need):
    ...
def _arm_start_trigger (data):
    """A quest authored `Starts when: <trigger>` is granted armed with THAT trigger, its
    real advancement trigger set aside under `armed_trigger`.
    
    Doing it this way means a start trigger needs no matching code of its own: every
    on_kill / on_scan / on_dock / on_reach / on_signal matcher already knows how to
    recognize a trigger, so the start uses the same ones. `quest_mark_complete` swaps the
    real trigger back in instead of completing (see `_quest_swap_in_armed`).
    
    Before this, `Starts when:` wrote the SAME key `Done when:` writes, so a quest
    carrying both completed on whichever fired first - the gate could finish the job."""
def _collect_active_quests (children, prefix, out):
    """Recurse the quest tree, appending (full_path, data) for every ACTIVE quest - so
    NESTED arc steps (`arc/step`, authored as nested quest keys) fire their triggers too.
    The path is '/'-separated so quest_get_key / quest_set_key / quest_mark_complete
    navigate it via quest_folder. Flat quests (no children) are unchanged (path == key)."""
def _fire_overlay_directive (directive, to):
    """Fire one inline overlay directive: ``<kind> <text>`` (e.g. ``hero CONVOY
    SAVED``) or ``overlay <key>`` to fire a declared amd_overlays record. The kind's
    primary field (title/text/line) receives the text."""
def _install_dialogue_outcomes ():
    ...
def _kill_is_hostile (killer_id, victim_id):
    """Was the victim an ENEMY? Of the killer if it has a side, otherwise of the
    players (e.g. a SHARED/game-level quest whose killer is Agent.SHARED_ID). Lets a
    kill quest count "enemies" by diplomacy instead of a hardcoded faction role, and
    stops a ceasefired/neutral (or surrendered) ship from counting."""
def _obj_distance (id_a, id_b):
    """Straight-line distance between two space objects by id (Cosmos space), or a huge
    number if either is gone."""
def _quest_audience (agent_id):
    """Who should see a quest's complete/fail line. A per-ship quest is owned by a
    real space object -> tell that ship. A shared-scope quest is owned by the
    non-space SHARED story agent (Agent.SHARED_ID), which is NOT a player ship, so
    tell every player instead - passing SHARED to send_message_to_player_ship
    raises "invalid space object"."""
def _quest_author_announces (data, ref_key, inline_key):
    """True when the quest carries its own completion/failure announcement.
    
    `on_complete` / `on_fail` are overlay DIRECTIVES (`<kind> <text>`), so a quest that
    has one is already telling the crew - and the library adding its own line made every
    such quest announce twice, in two different vocabularies ("Job complete: Mercy Run"
    then "Mission complete: Mercy Run"). Authored wording wins where an author wrote any.
    
    TRADE-OFF worth knowing: the overlay is the attention layer and the broadcast is the
    durable log, so suppressing the broadcast means an authored completion leaves no line
    in the waterfall. That is the intent here (the duplicate is what playtesters
    reported), but if a quest wants both, it should say so rather than getting it by
    accident."""
def _quest_console_allowed (console, spec):
    """True if `console` may act under `spec` (empty spec allows any console)."""
def _quest_console_names (spec):
    """Human list of a spec's consoles: 'Comms', 'Comms or Admiral', 'Comms, Admiral or Helm'."""
def _quest_console_set (spec):
    """Normalise a console spec ("comms, admiral" or ["comms","admiral"] or None) to a
    lowercased set. None/"" -> empty set == 'any console'."""
def _quest_countdown_body (data, speaker, fmt, final):
    """The words. Authored line first, then a voice-appropriate default.
    
    A speaker with no FACE is a machine - a beacon, a ship's transmitter, an empty hull
    with a distress signal still running - so it gets transmission phrasing rather than
    someone politely reporting the time. A cast character keeps the spoken form. The
    author overrides either with `Signal says:`, which is the only way to get wording
    specific to what is actually failing ("LIFE SUPPORT CRITICAL")."""
def _quest_countdown_send (aid, qid, data, mark, left):
    ...
def _quest_dispatch_id ():
    """The registered voice as an agent id, resolving a name if that is what was given."""
def _quest_driver_log (message):
    ...
def _quest_effective_consoles (item, key, default_spec):
    """The per-quest console override for `key` (read fresh off the quest's AMD `data`,
    where the `Accept On:` / `Engage On:` labels store it, so it need not ride the log
    row), else the mission `default_spec`."""
def _quest_fire_overlays (agent_id, data, ref_key, inline_key):
    """Fire a quest lifecycle overlay to the quest's participant consoles. Supports
    BOTH forms: a declared-record reference (``ref_key`` -> ``overlay_amd(key)``) and
    an inline directive (``inline_key`` -> ``<kind> <text>``)."""
def _quest_grant_reputation (agent_id, block):
    """Apply a reward/penalty block's ``reputation`` map, if this holder can carry one.
    
    Deltas apply exactly as authored - a ``Penalty:`` never flips the sign for you (see
    ``amd_reward``)."""
def _quest_held_by (name, qid):
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
    "every listening post wants a resupply" is a legitimate thing to author."""
def _quest_holders ():
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
    ``brain.py`` s396-400 already paid for once."""
def _quest_maybe_end_game (agent_id, quest_id, data, win):
    """Fire game_over once if this quest is a game-ending mission quest.
    
    A quest with end_win (on COMPLETE) or end_lose (on FAILED) ends the game;
    win_text/lose_text (falling back to the display name) is the end-screen reason.
    Guarding the actual teardown lives in the //signal/game_over route."""
def _quest_noun (data):
    """What to call this quest to the crew: "Mission" only when it IS the mission.
    
    The player already meets three words for one thing - the tab says Quests, an AMD
    author writes Job, and the library used to say Mission for every last step of every
    arc. "Mission" is reserved for a quest that ends the game (`end_win`/`end_lose`),
    where it is simply true; everything else is a Quest, which is the word on the tab
    the player clicks to find it."""
def _quest_outcome (verb, apply_fn):
    """Build a dialogue outcome handler for `<verb> <quest_id>`.
    
    Never returns False. Returning False from an outcome refuses the whole PICK
    (`hail_answer` emits `refused` and nothing happens), so a quest id that does not
    resolve would make the choice silently unpressable - the worst possible reading of
    a typo. It logs and lets the answer through. Only a mission's own verb, which can
    mean "you cannot afford this", should ever refuse."""
def _quest_overlay_audience (agent_id):
    """The CONSOLE clients that should see a quest's overlays: the participant
    ships' linked consoles (overlays target consoles, not ships)."""
def _quest_rep_holder (agent_id):
    """True where a reputation line MEANS something: a player ship, or the shared story
    agent standing in for the crew.
    
    A world-held quest (a station, a side) carries no reputation. ``reputation_adjust``
    shifts *this agent's* standing with a faction, so a rep penalty on DS1's resupply
    quest would move DS1's own opinion of TSN - which no player can perceive and no
    author means. World stakes are world state (``Then:`` / ``Action:``). Silently
    ignoring the line would hide the mistake, so ``sbs lint`` rejects it at author time;
    this is the runtime backstop. DESIGN_RECORD.md s4."""
def _quest_scan_reveals (scanner_id, scanned_id):
    """Active on_scan quests (on the scanner or SHARED) that carry declarative scan text
    (reveal_scan) and whose on_scan role matches the scanned object. Returns the list of
    reveal-text strings (usually one)."""
def _quest_sig_walk (children, aid, parts):
    ...
def _quest_speaker (qid, data):
    """Who speaks for this quest, in order of how much the author asked for it.
    
    `Speaker:` names it outright - the shuttle crew calling in on their own rescue, the
    client chasing a delivery. Failing that, `Held by:` when it resolves to something that
    can talk: a station's job then speaks with the station's own face for no authoring at
    all. Failing that, the mission's registered dispatch voice.
    
    Returns None when nothing can speak, and the caller stays SILENT rather than sending
    an anonymous message - a reminder from nobody is worse than no reminder."""
def _quest_swap_in_armed (agent_id, quest_id, data):
    """The start trigger fired: arm the real one instead of completing. True when this
    was a start (so the caller must not complete, reward or announce)."""
def _quest_tree_parent (quest_id):
    """The parent path of a nested quest key (`arc/step` -> `arc`); None for a top-level key."""
def _scale_goal_counts (data, scale):
    """Return `data` with every explicit goal `count` scaled by `scale` (rounded, min 1),
    WITHOUT touching the shared doc (goal dicts are copied only when scaled). Goals with no
    authored count - singleton objectives like `reach the shuttle` - are left as-is. A scale
    of 1.0 (or falsy) returns `data` unchanged."""
def amd_kind_defaults (noun):
    """Every field a kind noun implies, as {field: value}. Singular / plural both work,
    matching `_kind_to_archetype` - an author writes `Beat` over one record and `Beats`
    over a section without being told there is a difference.
    
    `Quest` carries none - it is the neutral word, for a record that is neither a story
    moment nor clearly one of the two. `Job` restates today's defaults (per ship, waiting
    to be accepted) rather than changing them, so peacetime's board - which says none of
    this - keeps working exactly as written."""
def amd_signal_name (value):
    """A signal name, lowercased with spaces -> underscores (matched exactly).
    
    Lives here, not in a caller, because it IS the matching contract: the quest driver
    matches on it at runtime and the editor's signal join matches on it statically. Two
    copies held in agreement by a comment would silently stop agreeing the first time
    the rule widened."""
def comms_broadcast (ids_or_obj, msg, color=None, category=None, severity=None) -> None:
    """Send a text message to the text waterfall of one or more targets.
    
    Accepts player ship IDs or client/console IDs. Ship IDs use
    ``send_message_to_player_ship``; client IDs use
    ``send_message_to_client``.
    
    ALSO appends to the ship's log (``procedural.log_panel``), which is the waterfall's
    replacement - see mkdocs build/messages.md. Both surfaces are written during the changeover
    so they can be compared side by side; retiring the waterfall is then deleting the
    engine half of this function.
    
    Args:
        ids_or_obj: Agent ID, client ID, or set/list of either to send to.
            Pass ``None`` to send to the event's ``parent_id``.
        msg (str): The message text. Supports ``{var}`` interpolation.
        color (str, optional): Text color as a name or hex string, e.g.
            ``"red"`` or ``"#3ff"``. Defaults to ``"#fff"``.
        category (str, optional): Which log TAB this belongs in - ``"ship"`` or
            ``"mission"``. Omitted (the default) means it appears in the Log tab, which
            shows everything, and in no subset tab. That is what makes tagging
            incremental: nothing is lost by not being tagged.
        severity (str, optional): ``"tip"`` / ``"warning"`` / ``"danger"``. Draws the
            entry as a callout. Reserved for things that matter - a box costs two rows,
            so one per line would halve how much log fits on screen.
    
    Example:
        comms_broadcast(SHIP_ID, "Red alert!", color="red", severity="danger")"""
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def format_time_remaining (id_or_obj, name):
    """Return the time remaining on a timer as a ``M:SS`` string.
    
    Returns an empty string when the timer has expired or is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        str: Formatted remaining time, e.g. ``"1:30"``, or ``""`` if expired.
    
    Example:
        gui_text("Time: {format_time_remaining(SHIP_ID, 'mission')}")"""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def get_time_remaining (id_or_obj, name):
    """Return the number of whole seconds remaining on a timer.
    
    Returns ``0`` when the timer has expired or is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        int: Seconds remaining, or ``0`` if expired or not set.
    
    Example:
        secs = get_time_remaining(SHIP_ID, "mission")
        if secs < 60:
            "Less than a minute remaining!""""
def gui_list_box_is_header (item):
    """Return whether a listbox item is a collapsible header.
    
    Args:
        item: Any item from a listbox items list.
    
    Returns:
        bool: ``True`` if the item is a ``LayoutListBoxHeader``.
    
    Example:
        for item in items:
            if gui_list_box_is_header(item):
                ~~ print("header:", item.label) ~~"""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def is_hostile_to_players (target, scope_role=None) -> bool:
    """Return whether ``target`` is a hostile combatant to at least one player side.
    
    The player-perspective boolean (see :func:`is_hostile_combatant`): ``target``
    still carries the combat class role ``scope_role`` AND is diplomatically HOSTILE
    to some current player side. A ceasefired/neutral or surrendered ship is False.
    Pass ``scope_role=None`` for a pure diplomacy test.
    
    Args:
        target (str | int | Agent): The candidate to test.
        scope_role (str, optional): Combat-class role the target must hold. Defaults
            to ``"raider"``.
    
    Returns:
        bool: ``True`` if ``target`` is a hostile combatant to any player side."""
def is_space_object_id (id):
    """Return whether an ID belongs to a space object.
    
    Args:
        id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the space-object bit (0x4000…) is set."""
def is_timer_finished (id_or_obj, name):
    """Return whether a timer has expired. Returns ``True`` if the timer is not set.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        bool: ``True`` if the timer has expired or was never set.
    
    Example:
        if is_timer_finished(SHIP_ID, "repair"):
            "Repair bay ready.""""
def is_timer_set (id_or_obj, name):
    """Return whether a named timer exists on an agent.
    
    Args:
        id_or_obj (Agent | int): Agent ID or object.
        name (str): Timer name.
    
    Returns:
        bool: ``True`` if the timer has been set (even if already expired).
    
    Example:
        if not is_timer_set(SHIP_ID, "cooldown"):
            set_timer(SHIP_ID, "cooldown", seconds=10)"""
def overlay_amd (key, to=None, fields=None, consoles=None):
    """Fire a declared overlay by key. ``fields`` (a dict) merge over the record's
    fields; a ``seconds`` field auto-dismisses. ``to`` accepts a console, ship, side
    or set (see ``consoles_of``); ``consoles`` narrows by console role. Returns the
    record, or None for an unknown key."""
def overlay_kind (kind, to=None, consoles=None, slot=None, seconds=None, **fields):
    """Low-level front door: show any registered ``kind`` with its default slot.
    
    The escape hatch for callers that pick the kind at runtime (the quest driver's
    inline overlay directives, AMD records). Prefer the named wrappers when the
    kind is known at author time."""
def quest_add (agents, quest_id, display_text, description, state=<QuestState.IDLE: 0>, data=None):
    """Add a quest to one or more agents.
    
    Creates a new quest entry in each agent's quest tree. If the agent has no
    quest tree yet, one is initialized automatically. The ``quest_id`` may use
    ``/`` separators for nested quests (e.g. ``"main/rescue"``), but all parent
    levels must already exist.
    
    Args:
        agents: Agent ID, object, or list/set of either.
        quest_id (str): Unique key for this quest, e.g. ``"patrol"`` or
            ``"main/patrol"``.
        display_text (str): Short label shown to the player.
        description (str): Longer description text.
        state (QuestState, optional): Initial state. Defaults to
            ``QuestState.IDLE``.
        data (object, optional): Arbitrary data attached to the quest and
            accessible via ``quest_get_data``. Defaults to None.
    
    Example:
        quest_add(SHIP_ID, "patrol", "Patrol Sector 7", "Keep the peace in sector 7.")
        quest_add(Agent.SHARED_ID, "rescue", "Rescue the crew", "Find the survivors.", state=QuestState.ACTIVE)"""
def quest_agent_quests (agent_id):
    """Return the raw quest tree stored on an agent, or ``None`` if none exist yet.
    
    The tree is a ``MastDataObject`` with a ``children`` dict keyed by quest ID.
    Most scripts should prefer ``quest_get`` over accessing the tree directly.
    
    Args:
        agent_id: Agent ID, object, or ``Agent.SHARED_ID`` for global quests.
    
    Returns:
        MastDataObject | None: The root quest container, or ``None``.
    
    Example:
        tree = quest_agent_quests(SHIP_ID)
        if tree is not None:
            ~~ print(tree.get("children").keys()) ~~"""
def quest_any_holder_state (qid, state):
    """True while ANY quest holder has `qid` in `state`.
    
    Behind the same generation guard as _active_quests. The urge system asks this per
    actor per urge on every pass, and it grows with the holder set - Open Universe
    makes every station with a waiting passenger a quest holder, so the scan grows
    with the number of populated systems."""
def quest_credit_signal (agent_id, name):
    """Owner-scoped on_signal advance: like quest_on_signal but for ONE agent only, so a
    shared/contested quest target can credit the ship that completed it (peacetime
    multiplayer) instead of every holder. Crediting only (no fail-trigger handling)."""
def quest_dispatch_voice (agent=None):
    """Register the fallback voice for quest reminders, or read the current one.
    
    A mission calls this once with the character its crews already hear from - LM has a
    "TSN Command" lifeform, Peacetime has Admiral Harkin. Pass None to read.
    
    Accepts an id, an object, OR a NAME (a Cast/landmark key), which is resolved lazily at
    send time. Lazily on purpose: a mission registers its voice while setting the story up,
    which is before the cast has spawned, so resolving eagerly would store None and stay
    that way for the whole mission."""
def quest_dispatch_voice_clear ():
    """Forget the registered voice. Part of the per-mission reset - a voice left over
    from the last mission names an agent that no longer exists."""
def quest_fail_on_all_dead (destroyed_id=None):
    """Fail ACTIVE quests whose fail_on_all_dead {role} guard just emptied - the
    last holder of that role has died. Called from the killed route; the victim is
    still registered there, so it is excluded from the remaining count."""
def quest_get (agent, quest_id):
    """Return a quest object by ID, or ``None`` if it does not exist.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier, e.g. ``"patrol"`` or
            ``"main/patrol"``.
    
    Returns:
        MastDataObject | None: The quest data object, or ``None``.
    
    Example:
        q = quest_get(SHIP_ID, "patrol")
        if q is not None:
            "Patrol state: {q.get('state')}""""
def quest_get_data (agent, quest_id):
    """Return the ``data`` value attached to a quest.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
    
    Returns:
        object | None: The data value passed to ``quest_add``, or ``None``.
    
    Example:
        d = quest_get_data(SHIP_ID, "patrol")"""
def quest_get_display_name (agent, quest_id):
    """Return the display name of a quest.
    
    Reads ``display_text`` - the field ``quest_add`` actually writes. It used to read
    only ``display_name``, which NOTHING in the codebase ever sets, so this returned
    ``None`` for every quest and each caller fell back to the raw quest id. That is why
    the text waterfall announced `job_ghost/hail` instead of "Hail the Derelict": not a
    missing display name on some quests, but a key mismatch affecting all of them.
    
    ``display_name`` is still honored first, so anything that deliberately set it with
    ``quest_set_key`` keeps overriding.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
    
    Returns:
        str | None: The display name, or ``None`` if the quest does not exist or has
            no name of either kind.
    
    Example:
        name = quest_get_display_name(SHIP_ID, "patrol")
        "Mission: {name}""""
def quest_get_key (agent, quest_id, key, defa=None):
    """Return an arbitrary attribute from a quest object.
    
    Reads any key stored on the quest's ``MastDataObject``. Built-in keys are
    ``"state"``, ``"display_text"``, ``"description"``, and ``"data"``.
    Custom keys can be set with ``quest_set_key``.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
        key (str): Attribute name to read.
        defa (optional): Value returned when the quest is missing or the key
            has not been set. Defaults to ``None``.
    
    Returns:
        object: The stored value, or ``defa``.
    
    Example:
        difficulty = quest_get_key(SHIP_ID, "patrol", "difficulty", "normal")"""
def quest_get_state (agent, quest_id):
    """Return the current state of a quest.
    
    Returns ``QuestState.IDLE`` both when the quest does not exist and when
    its state has never been explicitly set.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
    
    Returns:
        QuestState: Current state value.
    
    Example:
        if quest_get_state(SHIP_ID, "patrol") == QuestState.COMPLETE:
            "Patrol complete!""""
def quest_grant_amd (agent_id, doc, _prefix='', count_scale=1.0):
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
    authored count) never scale; the default 1.0 leaves every existing caller unchanged."""
def quest_grant_penalty (agent_id, penalty):
    """Apply a quest penalty (mirror of quest_grant_reward): deduct credits from
    the agent's side, remove items from the agent, and apply any reputation block
    (player/SHARED holders only). Credits and items never go below zero; reputation
    applies as authored, so a penalty's ``earns`` carries its own sign."""
def quest_grant_reward (agent_id, reward):
    """Grant a quest reward: credits to the agent's side, items to the agent, and
    reputation to the agent (player/SHARED holders only - see ``_quest_rep_holder``)."""
def quest_holders_of (quest_id, prefer=None):
    """Every agent holding `quest_id`, most-specific first.
    
    A hail belongs to one player SHIP; a `Scope: shared` quest lives on the story
    agent; a `Held by:` job lives on a station. So "who does this answer resolve for"
    has no single answer and has to be looked up.
    
    `prefer` (the ship that answered) comes first when it holds the quest, so two
    bridges each carrying their own copy of a job resolve their own."""
def quest_is_owner (ship, target):
    """True if ship is the claimed owner of target."""
def quest_log_build_items (sources):
    """Build the collapsible quest-log item list shared by both logs.
    
    `sources` is a list of (section_label, agent_id). Each becomes a
    gui_list_box_header followed by that agent's non-SECRET quests. Child quests
    (nested via `/`-separated keys, e.g. `arc/step1`) render indented under their
    parent as a TREE (see _quest_log_rows); empty sections are skipped. Rows are
    MastDataObject with agent_id / key / group / depth / title / state /
    state_label / progress / desc, so quest_log_template renders them the same
    everywhere. The ONLY thing the two callers vary is `sources`."""
def quest_mark_active (agent_id, quest_id):
    """Set a quest ACTIVE (idempotent)."""
def quest_mark_complete (agent_id, quest_id):
    """Complete a quest (idempotent): set state, grant reward, announce.
    
    A quest waiting on a `Starts when:` trigger passes through here when that trigger
    fires - it is armed with it - and STARTS instead: its real advancement trigger is
    swapped in and nothing else happens (no reward, no announcement, no reveal)."""
def quest_mark_failed (agent_id, quest_id):
    """Fail an active quest (idempotent): set state, apply penalty, announce, then
    fire the lose (if end_lose) and bubble up to the parent mission."""
def quest_on_arrive (i, j):
    """Complete on_reach(sector) quests for every player arriving at (i,j).
    
    Reaching a place is a single event (not a count), so it completes the
    objective. Used by the Open Universe (signal universe_arrived)."""
def quest_on_collect (holder_id, key):
    """Advance the holder's (and game/SHARED) on_collect quests on collection."""
def quest_on_dock (ship_id, station_id):
    """Advance the ship's (and game/SHARED) on_dock quests when it docks a
    station. on_dock {role: <role>} (optional) filters by the station's role."""
def quest_on_kill (killer_id, destroyed_id):
    """Advance the killer's on_kill quests when an object is destroyed.
    
    The on_kill match is general — all keys optional and AND-combined:
      role    : victim must hold this role (exact; e.g. "raider"). Back-compatible.
      roles   : victim must hold ANY of these roles (a list) - a broader type filter.
      hostile : if truthy, the victim must have been an ENEMY by diplomacy (of the
                killer, or of the players for a SHARED quest). This is the general,
                faction-agnostic, ceasefire-safe way to score "destroy N enemies" -
                prefer it over a hardcoded raider role.
    Omitting all three counts any destruction (unchanged legacy behavior)."""
def quest_on_kill_shared (destroyed_id):
    """Advance game-level (SHARED) on_kill quests for any kill. Called once per
    kill (separate from per-killer credit) so SHARED counts aren't doubled by the
    source+parent calls."""
def quest_on_scan (scanner_id, scanned_id):
    """Advance the scanner's (and game/SHARED) on_scan quests when science scans
    a target. on_scan {role: <role>} (optional) filters by the scanned role.
    
    Each DISTINCT target counts once toward a counted goal (re-scanning the same
    object does not over-count) - the ids already counted are kept in the quest's
    ``_scanned`` list."""
def quest_on_signal (name):
    """Generic named trigger for on_signal / on_comms quests (escape hatch).
    
    A mission/comms route fires signal_emit("quest_signal", {"SIGNAL_NAME": ...});
    this advances any ACTIVE quest (players + SHARED) whose on_signal {name} or
    on_comms {option} matches. Lets authors add beats with no new driver code."""
def quest_on_tow (ship_id, towed_id):
    """Advance on_tow quests when `ship_id` delivers `towed_id` under tow.
    
    `on_tow {role: <role>}` filters by what was delivered, so "tow 2 survivors" and
    "tow the derelict home" are the same trigger with a different noun. Credit goes to
    the HAULER (and SHARED) - the ship that did the work, not whatever it was dragging."""
def quest_owner (target):
    """The ship id that has claimed this quest target (0 = unclaimed)."""
def quest_reeval_mission (agent_id, parent_qid):
    """Re-evaluate a mission (parent) quest from its children's states.
    
    Any `critical` child FAILED -> the mission FAILS; else once every `required`
    child is COMPLETE the mission COMPLETES. No-op unless the parent is ACTIVE, so
    it settles exactly once. Children link up via their data `parent: <parent_qid>`."""
def quest_reeval_tree_parent (agent_id, quest_id):
    """A quest with CHILDREN completes when ALL its children are COMPLETE - the natural
    'the arc is done when its steps are done'. Called when a nested `arc/step` settles: it
    completes the tree parent, which recurses UP via quest_mark_complete. SECRET children
    are unrevealed future steps, so they block completion (the arc isn't finished). Only an
    ACTIVE parent is settled; idempotent (quest_mark_complete no-ops if already complete).
    
    Author a parent as a pure CONTAINER (no own When trigger) with leaf children as the
    objectives, so its completion is driven only by the children (unambiguous)."""
def quest_reveal (agent_id, reveal):
    """Activate sub-quests revealed on completion (reveal: id, or [ids]).
    
    The revealed quests must already exist on the agent (added SECRET/IDLE when
    the parent story was granted); this flips them ACTIVE so their triggers go
    live - the next step(s) of a multi-step bridge story."""
def quest_run_action (agent, quest_id):
    """Run this quest's ``Action:`` stage directions, if it declares any. Returns how
    many applied.
    
    Called automatically when a quest goes ACTIVE. Public because a mission that drives
    quests its own way still wants the block to fire.
    
    ONE PER AGENT. A quest activated on five player ships runs its block five times -
    the same multiplicity as a ``//signal`` route, and the same footgun. It is safe today
    because every built-in verb is idempotent (``becomes``/``joins`` set state,
    ``arrives`` is keyed on the landmark, ``departs`` deletes something already gone), and
    a mission registering its own verb has to keep that property or scope the quest to
    ``Agent.SHARED_ID``."""
def quest_scan_enabled (scanner_id, scanned_id):
    """True if the scanned object is the target of an active on_scan quest that defines
    scan text. A //enable/science route gates on this so quest-scan targets become
    scannable without a hand-authored enable route."""
def quest_scan_text (scanner_id, scanned_id):
    """The declarative scan text to show for a quest-scan target (joins multiple matching
    quests). Rendered by the driver's //science route as the object's scan result."""
def quest_set_key (agent, quest_id, key, value):
    """Set an arbitrary attribute on a quest object.
    
    Use this to write any key — including ``"state"`` when you want to update
    it directly. ``quest_activate`` and ``quest_complete`` only emit signals;
    call this to actually store the new state.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
        key (str): Attribute name to write.
        value: Value to store.
    
    Example:
        quest_set_key(SHIP_ID, "patrol", "state", QuestState.ACTIVE)
        quest_set_key(SHIP_ID, "patrol", "difficulty", "hard")"""
def quest_set_owner (target, ship):
    """Claim a quest TARGET for a ship (peacetime multiplayer: shared-pool targets owned per-
    target so a non-owner can't complete or steal it). ship 0/None clears the claim. Stored as
    the target's 'quest_owner' inventory value."""
def quest_shared_state (quest_id):
    """State of a game-level (SHARED) quest - convenience for narrative arcs."""
def quest_tab_abandon (item):
    """Abandon an active quest. No-op on a section header.
    
    Routes through `quest_mark_failed` rather than writing the state directly. Setting
    `state = FAILED` by hand looked equivalent and was not: it skipped the `Penalty:`,
    the `on_fail` overlay, the announcement, the `quest_failed_done` signal AND
    `_quest_maybe_end_game` - so abandoning was strictly cheaper than letting a quest
    fail on its own (Mercy Run costs 100 credits on the clock, nothing on the button),
    and an `end_lose` quest could be neutralised by abandoning it.
    
    A deliberate drop and a timed-out drop now mean the same thing."""
def quest_tab_accept (item):
    """Accept an available (IDLE) quest. No-op on a section header."""
def quest_tab_controls_gate (console, item, accept_consoles, engage_enabled, engage_consoles):
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
                     controls correctly)"""
def quest_tab_items (client_id, ship_id):
    """Collapsible quest-log items for THIS console: the game (SHARED), the client,
    and its ship. Rows carry their owning agent (for accept/abandon)."""
def quest_tab_state_sig (client_id, ship_id):
    """A lightweight signature of the quest log shown on this console - every quest's
    (agent, key, state) across the same sources as quest_tab_items (including SECRET, so a
    reveal is caught). Changes whenever a quest is added, revealed, or changes state.
    
    Drive an `on change` off this to repaint the Quests tab when a quest's status changes
    from ANYWHERE - a kill/scan/dock completing it, a timer failing it, or another console
    accepting it - not just from this console's own buttons."""
def quest_tick_complete_after ():
    """Watcher tick: COMPLETE ACTIVE quests whose complete_after deadline elapsed.
    Symmetric to quest_tick_fail_after - the deadline is anchored lazily (a per-quest
    timer set on first ACTIVE sight), so a purely timed step needs no activation hook.
    On completion the quest's Then: reveal fires, advancing a reveal chain; this lets a
    timed narrative beat be authored as a quest instead of a hand-written timer loop."""
def quest_tick_countdown_reminders ():
    """Watcher tick: remind the crew, on comms, as a quest's deadline closes in.
    
    Rides the deadline `quest_tick_fail_after` already anchors, so a quest with no
    `Fails when:` costs nothing here and one that has not started its clock is skipped.
    
    Marks are latched per quest, so each fires exactly once. When a single tick crosses
    several at once (a long frame, a mission restart), all of them latch but only the most
    urgent is SENT - passing three marks must not produce three messages."""
def quest_tick_fail_after ():
    """Watcher tick: fail ACTIVE quests whose fail_after deadline elapsed. The
    deadline is anchored lazily (a per-quest timer set on first sight), so
    activation needs no hook - general to any mission, not just siege."""
def quest_tick_reach ():
    """Watcher tick: complete active ``on_reach{role[,radius]}`` quests when a player
    comes within ``radius`` of any object holding that role. This is the 2.8 "fly within
    R of <object>" navigation objective (absolute coords, not a sector); the sector form
    ``on_reach{sector}`` is handled event-style by :func:`quest_on_arrive`. One shared
    tick replaces a per-objective polling watcher."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def set_timer (id_or_obj, name, seconds=0, minutes=0, signal=None):
    """Start a named countdown timer on an agent.
    
    Records the expiry tick in the agent's inventory. Use ``is_timer_finished``
    or ``get_time_remaining`` to check progress.
    
    Pass ``signal`` to have the library emit that signal once, when the timer
    expires, instead of polling for it. The emit carries ``TIMER_AGENT_ID`` and
    ``TIMER_NAME``. It is purely additive - the timer is still an ordinary timer
    afterwards, so ``is_timer_set_and_finished`` and ``format_time_remaining``
    behave exactly as they do without it. Handle it with
    ``//shared/signal/<name>`` for anything with a side effect; a plain
    ``//signal/<name>`` runs once per console (see SIGNAL_ROUTING.md).
    
    No signal is emitted if the timer is cleared, re-set without ``signal``, or
    its agent is deleted before it expires. A paused sim does not advance the
    timer, so it does not expire while paused.
    
    Args:
        id_or_obj (Agent | int): The agent to set the timer on.
        name (str): Unique timer name for this agent.
        seconds (int, optional): Duration in seconds. Defaults to 0.
        minutes (int, optional): Additional duration in minutes. Defaults to 0.
        signal (str, optional): Signal to emit once when the timer expires.
            Defaults to None (no signal - poll it instead).
    
    Example:
        set_timer(SHIP_ID, "repair", seconds=30)
        if is_timer_finished(SHIP_ID, "repair"):
            "Repairs complete!"
    
        set_timer(SHIP_ID, "repair", seconds=30, signal="repair_done")
        # //shared/signal/repair_done runs on the server when it expires"""
def side_are_enemies (side1, side2) -> bool:
    """Return whether two sides are hostile to each other.
    
    Args:
        side1 (str | int | Agent): First side — key, agent ID, or object.
        side2 (str | int | Agent): Second side — key, agent ID, or object.
    
    Returns:
        bool: ``True`` if the sides have a ``side_hostile`` link."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_id_list (the_set):
    """Convert a set or list of agents/IDs to a list of integer IDs.
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[int]: Resolved integer IDs; unresolvable items are excluded."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
def to_set (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Normalize any agent-like value or collection into a set of integer IDs.
    
    Args:
        other (Agent | CloseData | int | set | list | None): Value to normalize.
    
    Returns:
        set[int]: A set of integer IDs; ``None`` becomes an empty set."""
def to_side_id (key_or_id_or_object, warn=True):
    """Resolve any side reference to the side agent's ID.
    
    Accepts a side key string, a side agent ID, a side agent object, or any
    space object (in which case its side property is used).
    
    A leading ``#`` on a side key is a display-hide marker only (it tells the
    engine not to draw the side name); it is not part of the side identity, so
    ``"#raider"`` resolves to the ``"raider"`` side. An empty or all-``#`` key
    means the object has NO side (asteroids, cambots, hidden objects) and
    resolves to ``None`` silently — that is a legitimate state, not a miss.
    
    Args:
        key_or_id_or_object (str | int | Agent): Side key, side agent ID, side
            agent, or a space object whose side should be resolved.
        warn (bool): Warn (once per distinct key) when a genuinely-named side
            can't be resolved. Pass ``False`` for existence probes (e.g. a
            create-if-missing check) where a miss is expected, not an error.
    
    Returns:
        int | None: The side agent ID, or ``None`` if not found."""
