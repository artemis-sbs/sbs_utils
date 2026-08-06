from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from enum import IntEnum
from sbs_utils.mast.mast_node import MastDataObject
def _amd_slug (text):
    """A heading display -> a key: lowercase, non-alphanumeric runs -> single '_'."""
def _document_get_amd_file (file_path, root_display_text='', strip_comments=True, content=None, data_parser=None, allow_bare_headings=False):
    ...
def _quest_field (q, label):
    """A fence field, wherever it ended up. Only state / display_text / description are
    promoted onto the quest itself, so an AMD-authored `Reward:` is under `data` while a
    hand-built one may be on top - the same trap `_quest_show` documents."""
def _quest_kind (q):
    """The record's kind noun (`job` / `beat` / `arc` / ...), or None.
    
    Lives in the fence data like `Show:` does - only state / display_text / description
    are promoted onto the quest itself - so both places are checked here rather than in
    every caller."""
def _quest_log_rows (children, aid, group, depth):
    """One level of the quest tree. A quest that HAS visible children is emitted as a
    COLLAPSIBLE gui_list_box_header - so it folds its steps exactly like the Game/You/Ship
    group headers - followed by its children one level deeper; a leaf quest is a plain row.
    The list box itself does the fold + indent (a parent header sits at visual `depth`
    while its logical indent `depth+1` folds/indents its subtree; each row carries its own
    `indent`), so NO manual padding. State-sorted per level; SECRET (and subtrees) hidden."""
def _quest_need (q):
    """How many the goal counts, when it counts - `destroy 6 raiders` -> 6."""
def _quest_remaining (aid, qid):
    """Time left on a quest's fail deadline, `M:SS`, or "" when there is none. The driver
    anchors that timer lazily, so this is also how the log learns a deadline exists."""
def _quest_reward_text (q):
    """A reward as an author would read it back:
    `120 credits, 2 torpedoes, +10 honest with tsn`.
    
    Renders the three authored kinds EXPLICITLY rather than walking the dict, because a
    nested value formatted generically would emit braces (`{'torpedoes': 2} items`) - and
    a display string containing `{` is a runtime SyntaxError the moment MAST assigns it,
    reported against the author's line rather than this function. Any other scalar key
    still renders the old way, so a mission-specific key is not silently dropped; a
    nested one is skipped rather than turned into a crash."""
def _quest_show (q):
    """A quest's `Show:` - WHEN it is listed in the log, normalized.
    
    Fence fields live under the quest's `data`; only state / display_text / description
    are promoted onto the quest itself, so reading `q["show"]` returns None and the
    field silently does nothing. Both are checked here so there is one place to be
    wrong."""
def document_flatten (doc_obj, header=None, indent=0, data=None):
    """Flatten a nested quest/document tree into an ordered display list.
    
    Recursively walks the tree and returns ``gui_list_box_header`` items sorted
    active → idle → complete → failed at each level. Used internally by
    ``quest_flatten_list``.
    
    Args:
        doc_obj (MastDataObject | dict | None): The node to flatten.
        header (str, optional): Display label for this node. Defaults to None.
        indent (int, optional): Current nesting depth for visual indentation.
            Defaults to 0.
        data (optional): Data object attached to this node. Defaults to None.
    
    Returns:
        list: Flat ordered list of ``gui_list_box_header`` items."""
def document_get_amd_file (file_path, root_display_text='', strip_comments=True, content=None, data_parser=None, allow_bare_headings=False):
    """Parse an AMD markdown file into a nested quest/document structure.
    
    AMD files use ``# [Display Name](key)`` headings to define hierarchical
    sections. The heading level controls depth (``#`` = level 1, ``##`` = level
    2, etc.). Lines between headings are accumulated as the section's
    ``description``. Lines starting with ``//`` are stripped when
    ``strip_comments`` is ``True``. Query-string parameters in the key URI
    (``key?param=value&…``) are parsed as extra attributes on the section.
    
    Returns a dict with keys ``"key"``, ``"display_text"``, ``"description"``,
    and ``"children"`` (list of the same structure). On parse error the
    exception message is returned as the root ``"display_text"``.
    
    Args:
        file_path (str | None): Path to the ``.amd`` file to read. Ignored if
            ``content`` is provided.
        root_display_text (str, optional): Label for the root node.
            Defaults to ``""``.
        strip_comments (bool, optional): Skip ``//`` lines. Defaults to
            ``True``.
        content (str | None, optional): Raw AMD text to parse instead of
            reading ``file_path``. Defaults to ``None``.
    
    Returns:
        dict: Nested document tree rooted at ``"__root__"``.
    
    Example:
        doc = document_get_amd_file("consoles/quest.amd", "Quests")
        items = document_flatten(doc)"""
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Create a collapsible section header for use in a listbox.
    
    When ``collapsible=True`` is set on the listbox, clicking a header toggles
    the visibility of items that follow it until the next header.
    
    Args:
        label (str): Header label text.
        collapse (bool, optional): Start in collapsed state. Defaults to
            ``False``.
        indent (int, optional): Logical indent level for tree structures.
            Defaults to 0.
        selectable (bool, optional): Whether clicking the header fires a
            selection event in addition to toggling collapse. Defaults to
            ``False``.
        data (object, optional): Arbitrary data attached to the header item.
            Defaults to None.
        visual_indent (int | None, optional): Override indent level for
            rendering only. Defaults to None (uses ``indent``).
    
    Returns:
        LayoutListBoxHeader: The header item."""
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
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
def quest_activate (agents, quest_id):
    """Emit a ``quest_activated`` signal for one or more agents.
    
    Fires ``signal_emit("quest_activated", ...)`` for each agent. To also
    update the stored state, call ``quest_set_key(agent, quest_id, "state",
    QuestState.ACTIVE)`` or handle the signal in a ``//signal/quest_activated``
    route that sets the state.
    
    Args:
        agents: Agent ID, object, or list/set of either.
        quest_id (str): Quest to activate.
    
    Example:
        quest_activate(SHIP_ID, "patrol")
        quest_set_key(SHIP_ID, "patrol", "state", QuestState.ACTIVE)"""
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
def quest_add_object (agents, obj, quest_id=None):
    """Add a quest from a dictionary object to one or more agents.
    
    Reads ``display_text``, ``description``, ``state``, and ``data`` from
    ``obj``. The ``state`` value may be a ``QuestState`` enum or a string name
    (e.g. ``"ACTIVE"``); unknown strings default to ``QuestState.IDLE``.
    Nested ``children`` are recursively added with ``/``-separated IDs.
    
    Args:
        agents: Agent ID, object, or list/set of either.
        obj (dict): Quest definition dict (typically from parsed YAML).
        quest_id (str, optional): Override key. If ``None``, uses ``obj["id"]``.
    
    Example:
        quest_add_object(SHIP_ID, {
            "display_text": "Patrol",
            "description": "Patrol sector 7.",
            "state": "ACTIVE",
        }, "patrol")"""
def quest_add_yaml (agents, yaml_text):
    """Parse a YAML string and add all quests defined in it to one or more agents.
    
    The YAML should be a mapping of quest IDs to quest objects. Each quest
    object supports the same keys as ``quest_add_object`` (``display_text``,
    ``description``, ``state``, ``data``, and nested ``children``).
    
    Args:
        agents: Agent ID, object, or list/set of either.
        yaml_text (str): YAML-formatted quest definitions.
    
    Example:
        quest_add_yaml(SHIP_ID, ~~
        patrol:
          display_text: "Patrol Sector 7"
          description: "Keep the peace."
          state: ACTIVE
        ~~)"""
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
def quest_complete (agents, quest_id):
    """Emit a ``quest_completed`` signal for one or more agents.
    
    ``quest_completed`` is an INPUT: you emit it to ASK for a quest to be completed.
    The LegendaryMissions quest driver listens for it and calls ``quest_mark_complete``.
    
    **To REACT to a quest finishing, listen for ``quest_succeeded``** - that is what the
    driver emits once it has finished processing a completion (``quest_failed_done`` for
    a failure, ``quest_started`` for an activation). Do not write
    ``//signal/quest_completed`` to catch a completion: nothing emits it except callers
    like this one, so the route waits forever and fails silently. The two names are
    near-identical and point opposite ways; this bug killed every narrated beat in the
    2.8 converter's output.
    
    To also update the stored state without the driver, call
    ``quest_set_key(agent, quest_id, "state", QuestState.COMPLETE)``.
    
    Args:
        agents: Agent ID, object, or list/set of either.
        quest_id (str): Quest to complete.
    
    Example:
        quest_complete(SHIP_ID, "patrol")
        quest_set_key(SHIP_ID, "patrol", "state", QuestState.COMPLETE)"""
def quest_console_enable (console, enable=True):
    """Mark one or more console types as quest-panel-enabled.
    
    Controls which console types display the quest panel. Multiple console
    names can be passed as a comma-separated string. Names are normalized to
    lowercase before storage.
    
    Args:
        console (str): Console name(s) to update, e.g. ``"helm"`` or
            ``"helm,comms,science"``.
        enable (bool, optional): ``True`` to enable, ``False`` to disable.
            Defaults to ``True``.
    
    Example:
        quest_console_enable("helm,comms")
        quest_console_enable("engineering", False)"""
def quest_flatten_list ():
    """Build a flat display list of all quests for the current client.
    
    Collects quests from three sources — shared game quests (``Agent.SHARED``),
    client quests, and the client's assigned ship quests — and flattens each
    tree into a sorted list of ``gui_list_box_header`` items ready for display
    in a listbox.
    
    Returns:
        list: Flat list of listbox header objects, ordered active → idle →
            complete → failed within each source group.
    
    Example:
        items = quest_flatten_list()
        gui_property_list_box(items, style="area:0,0,100,100;")"""
def quest_folder (agent_id, quest_id):
    """Return the parent container and child key for a quest path.
    
    Navigates the quest tree along the ``/``-separated components of
    ``quest_id``, creating the root tree if it does not yet exist. Used
    internally by most other quest functions.
    
    Args:
        agent_id: Agent ID or object that owns the quest tree.
        quest_id (str): Quest path, e.g. ``"main/patrol"``.
    
    Returns:
        tuple[MastDataObject | None, str | None]: The parent container and the
            final path component (the child key), or ``(None, None)`` if the
            agent does not exist."""
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
def quest_get_description (agent, quest_id):
    """Return the description of a quest.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
    
    Returns:
        str | None: The description string, or ``None`` if the quest does not exist.
    
    Example:
        desc = quest_get_description(SHIP_ID, "patrol")
        "Objective: {desc}""""
def quest_get_display_name (agent, quest_id):
    """Return the display name of a quest.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
    
    Returns:
        str | None: The display name, or ``None`` if the quest does not exist.
    
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
def quest_get_parent (agent, quest_id):
    """Return the parent container of a quest without the child itself.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier whose parent to retrieve.
    
    Returns:
        MastDataObject | None: The parent container, or ``None``."""
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
def quest_is_console_enabled (console):
    """Return whether a console type has quest-panel display enabled.
    
    Args:
        console (str): Console name to check, e.g. ``"helm"``.
    
    Returns:
        bool: ``True`` if enabled via ``quest_console_enable``.
    
    Example:
        if quest_is_console_enabled("helm"):
            ~~ show_quest_panel() ~~"""
def quest_kill_count_for_difficulty (count, difficulty, baseline=5, grind_min=3, floor=1):
    """Scale a 'grind' kill target to the current difficulty.
    
    The authored ``count`` is treated as the target at ``baseline`` difficulty and
    scaled linearly (``count * difficulty / baseline``). Only grind-sized targets
    (``>= grind_min``) scale, so single-target / boss kill quests are left exactly
    as authored. The result never drops below ``floor``.
    
    Args:
        count (int): Authored kill target (the value at ``baseline`` difficulty).
        difficulty (float): Current difficulty (e.g. the DIFFICULTY setting).
        baseline (int): Difficulty at which ``count`` is used unchanged. Default 5.
        grind_min (int): Smallest target that scales; below this, return as-is.
        floor (int): Minimum returned target.
    
    Returns:
        int: The difficulty-adjusted kill target (or ``count`` unchanged if it is
        below ``grind_min`` or the inputs aren't numeric)."""
def quest_log_build_items (sources):
    """Build the collapsible quest-log item list shared by both logs.
    
    `sources` is a list of (section_label, agent_id). Each becomes a
    gui_list_box_header followed by that agent's non-SECRET quests. Child quests
    (nested via `/`-separated keys, e.g. `arc/step1`) render indented under their
    parent as a TREE (see _quest_log_rows); empty sections are skipped. Rows are
    MastDataObject with agent_id / key / group / depth / title / state /
    state_label / progress / desc, so quest_log_template renders them the same
    everywhere. The ONLY thing the two callers vary is `sources`."""
def quest_log_detail (row):
    """The second line of a row - the most useful thing known about it.
    
    It used to repeat the state, which the icon's COLOR already says; a line that says
    what the reader can already see is a line they stop reading. In order: how far along,
    what it pays while it is still a choice, how long is left, and only then the state
    (which for `Done` / `Failed` IS the news)."""
def quest_log_icon (row):
    """The icon NAME for a row: its kind if it has one, else the plain state pip.
    
    Shape says what KIND of thing it is, color says what STATE it is in - two facts in
    one glyph, where before every row was the same square and the kind was invisible. The
    name resolves through the icon sheet, so a mission that ships its own art re-skins
    every quest log without touching this."""
def quest_log_state_icon_color (state):
    """Hex color for the state icon (defaults to gray)."""
def quest_log_state_label (state):
    """Display label for a quest state (Active / Available / Done / Failed / ...)."""
def quest_log_template (item):
    """Canonical quest-log row renderer (section headers + quest rows), shared by
    the in-game and end-game logs. Fix the look here and both update."""
def quest_log_title ():
    """Shared list title for the quest log."""
def quest_remove (agent, quest_id):
    """Remove a quest from an agent and return it.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier to remove.
    
    Returns:
        MastDataObject | None: The removed quest, or ``None`` if not found.
    
    Example:
        removed = quest_remove(SHIP_ID, "patrol")"""
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
def quest_set_state (agent, quest_id, state):
    """Set the state of a quest and emit the appropriate signal.
    
    Emits ``quest_activated`` when ``state`` is ``QuestState.ACTIVE``,
    ``quest_completed`` when ``state`` is ``QuestState.COMPLETE``, and
    ``quest_failed`` when ``state`` is ``QuestState.FAILED``. Does nothing if
    the quest is already in the requested state.
    
    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
        state (QuestState): The new state to assign."""
def quest_transfer (from_agent_id, to_agent_id, quest_id):
    """Move a quest from one agent to another.
    
    Removes the quest from ``from_agent_id`` and adds it to ``to_agent_id``
    under the same ``quest_id``. Returns ``False`` if the quest does not exist
    on the source agent.
    
    Args:
        from_agent_id: Source agent ID or object.
        to_agent_id: Destination agent ID or object.
        quest_id (str): The quest to transfer, e.g. ``"patrol/sector7"``.
    
    Returns:
        bool: ``True`` if the quest was found and transferred, ``False`` otherwise.
    
    Example:
        quest_transfer(SHIP_ID, Agent.SHARED_ID, "rescue_mission")"""
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
class QuestState(IntEnum):
    """int([x]) -> integer
    int(x, base=10) -> integer
    
    Convert a number or string to an integer, or return 0 if no arguments
    are given.  If x is a number, return x.__int__().  For floating point
    numbers, this truncates towards zero.
    
    If x is not a number or if base is given, then x must be a string,
    bytes, or bytearray instance representing an integer literal in the
    given base.  The literal can be preceded by '+' or '-' and be surrounded
    by whitespace.  The base defaults to 10.  Valid bases are 0 and 2-36.
    Base 0 means to interpret the base from the string as an integer literal.
    >>> int('0b100', base=0)
    4"""
    ACTIVE : 1
    COMPLETE : 99
    FAILED : 98
    IDLE : 0
    POSTING : 3
    SECRET : 2
