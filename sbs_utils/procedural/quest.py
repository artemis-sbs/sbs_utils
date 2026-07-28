"""
Quests modules

Quest are a data model for tracking various quests
Quests are attached to an Agent.
The tracking of quests are done by outside logic

When a quest is activated or completed a signal is sent

"""
from sbs_utils.procedural.query import to_id_list, to_object, to_id
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.helpers import FrameContext
from sbs_utils.fs import load_yaml_string
from enum import IntEnum
from sbs_utils.agent import Agent
from sbs_utils.procedural.gui.listbox import gui_list_box_header, gui_list_box_is_header

class QuestState(IntEnum):
    IDLE = 0
    ACTIVE = 1
    SECRET = 2
    POSTING = 3 # Job request, 
    FAILED = 98
    COMPLETE = 99


def quest_agent_quests(agent_id):
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
            ~~ print(tree.get("children").keys()) ~~
    """
    agent = to_object(agent_id)
    if agent is None:
        return None
    return agent.get_inventory_value("__quests__")

def quest_transfer(from_agent_id, to_agent_id, quest_id):
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
        quest_transfer(SHIP_ID, Agent.SHARED_ID, "rescue_mission")
    """
    quest = quest_remove(from_agent_id, quest_id)
    if quest is not None:
        quests, child_id = quest_folder(to_agent_id, quest_id)
        if quests is None:
            return False
        quests.get("children")[child_id] = quest
        return True
    return False

__quest_consoles = set()
def quest_console_enable(console, enable=True):
    """Mark one or more console types as quest-panel-enabled.

    Controls which console types display the quest panel. Multiple console
    names can be passed as a comma-separated string. Names are normalised to
    lowercase before storage.

    Args:
        console (str): Console name(s) to update, e.g. ``"helm"`` or
            ``"helm,comms,science"``.
        enable (bool, optional): ``True`` to enable, ``False`` to disable.
            Defaults to ``True``.

    Example:
        quest_console_enable("helm,comms")
        quest_console_enable("engineering", False)
    """
    global __quest_consoles
    consoles = console.split(",")
    for console in consoles:
        console = console.strip().lower()
        if enable:
            __quest_consoles.add(console)
        else:
            __quest_consoles.discard(console)

def quest_is_console_enabled(console):
    """Return whether a console type has quest-panel display enabled.

    Args:
        console (str): Console name to check, e.g. ``"helm"``.

    Returns:
        bool: ``True`` if enabled via ``quest_console_enable``.

    Example:
        if quest_is_console_enabled("helm"):
            ~~ show_quest_panel() ~~
    """
    global __quest_consoles
    return console.strip().lower() in __quest_consoles

def quest_folder(agent_id, quest_id):
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
            agent does not exist.
    """
    agent = to_object(agent_id)
    if agent is None:
        return None, None
    quest = agent.get_inventory_value("__quests__", None)
    if quest is None:
        quest = MastDataObject({"children": {}})
        agent.set_inventory_value("__quests__",quest)
    children = quest.get("children", {})

    path = quest_id.split("/")
    #
    #
    #

    if len(path) > 1:
        for i in range(len(path)-1):
            quest = children.get(path[i], None)
    return quest, path[-1]


def quest_get(agent, quest_id):
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
            "Patrol state: {q.get('state')}"
    """
    quest, child_id = quest_folder(agent, quest_id)
    children = quest.get("children")
    return children.get(child_id)

def quest_get_parent(agent, quest_id):
    """Return the parent container of a quest without the child itself.

    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier whose parent to retrieve.

    Returns:
        MastDataObject | None: The parent container, or ``None``.
    """
    quests, child_id = quest_folder(agent, quest_id)
    return quests


def quest_remove(agent, quest_id):
    """Remove a quest from an agent and return it.

    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier to remove.

    Returns:
        MastDataObject | None: The removed quest, or ``None`` if not found.

    Example:
        removed = quest_remove(SHIP_ID, "patrol")
    """
    quests, child_id = quest_folder(agent, quest_id)
    if quests is not None and child_id is not None:
        children = quests.get("children", {})
        child = children.pop(child_id, None)
        return child
    return None

def quest_kill_count_for_difficulty(count, difficulty, baseline=5, grind_min=3, floor=1):
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
        below ``grind_min`` or the inputs aren't numeric).
    """
    try:
        count = int(count)
    except (TypeError, ValueError):
        return count
    if count < grind_min or baseline <= 0:
        return count
    try:
        difficulty = float(difficulty)
    except (TypeError, ValueError):
        return count
    return max(int(floor), int(round(count * difficulty / float(baseline))))


def quest_add(agents, quest_id, display_text, description, state=QuestState.IDLE, data=None):
    """Add a quest to one or more agents.

    Creates a new quest entry in each agent's quest tree. If the agent has no
    quest tree yet, one is initialised automatically. The ``quest_id`` may use
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
        quest_add(Agent.SHARED_ID, "rescue", "Rescue the crew", "Find the survivors.", state=QuestState.ACTIVE)
    """
    agent_ids = to_id_list(agents)

    for agent_id in agent_ids:
        quests, child_id = quest_folder(agent_id, quest_id)
        if quests is None:
            continue

        quest = MastDataObject({"id": quest_id, "display_text": display_text, "description": description, "state": state, "data": data, "children": {}})
        children = quests.get("children")
        if children is None:
            children = {}
            quests["children"] = children
        children[child_id] =  quest


def quest_activate(agents, quest_id):
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
        quest_set_key(SHIP_ID, "patrol", "state", QuestState.ACTIVE)
    """
    agent_ids = to_id_list(agents)

    for agent_id in agent_ids:
        quest_set_state(agent_id, quest_id, QuestState.ACTIVE)

def quest_complete(agents, quest_id):
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
        quest_set_key(SHIP_ID, "patrol", "state", QuestState.COMPLETE)
    """
    agent_ids = to_id_list(agents)

    for agent_id in agent_ids:
        quest_set_state(agent_id, quest_id, QuestState.COMPLETE)


def quest_get_state(agent, quest_id):
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
            "Patrol complete!"
    """
    return quest_get_key(agent, quest_id, "state", QuestState.IDLE)

def quest_set_state(agent, quest_id, state):
    """Set the state of a quest and emit the appropriate signal.

    Emits ``quest_activated`` when ``state`` is ``QuestState.ACTIVE``,
    ``quest_completed`` when ``state`` is ``QuestState.COMPLETE``, and
    ``quest_failed`` when ``state`` is ``QuestState.FAILED``. Does nothing if
    the quest is already in the requested state.

    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.
        state (QuestState): The new state to assign.
    """
    cur_state = quest_get_state(agent, quest_id)
    if cur_state == state:
        return

    quest = quest_get(agent, quest_id)
    if state == QuestState.ACTIVE:
        signal_emit("quest_activated", {"AGENT_ID": to_id(agent), "QUEST_ID": quest_id, "QUEST": quest})
    if state == QuestState.COMPLETE:
        signal_emit("quest_completed", {"AGENT_ID": to_id(agent), "QUEST_ID": quest_id, "QUEST": quest})
    if state == QuestState.FAILED:
        signal_emit("quest_failed", {"AGENT_ID": to_id(agent), "QUEST_ID": quest_id, "QUEST": quest})


def quest_get_data(agent, quest_id):
    """Return the ``data`` value attached to a quest.

    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.

    Returns:
        object | None: The data value passed to ``quest_add``, or ``None``.

    Example:
        d = quest_get_data(SHIP_ID, "patrol")
    """
    return quest_get_key(agent, quest_id, "data")

def quest_get_display_name(agent, quest_id):
    """Return the display name of a quest.

    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.

    Returns:
        str | None: The display name, or ``None`` if the quest does not exist.

    Example:
        name = quest_get_display_name(SHIP_ID, "patrol")
        "Mission: {name}"
    """
    return quest_get_key(agent, quest_id, "display_name")

def quest_get_description(agent, quest_id):
    """Return the description of a quest.

    Args:
        agent: Agent ID or object that owns the quest.
        quest_id (str): Quest identifier.

    Returns:
        str | None: The description string, or ``None`` if the quest does not exist.

    Example:
        desc = quest_get_description(SHIP_ID, "patrol")
        "Objective: {desc}"
    """
    return quest_get_key(agent, quest_id, "description")

def quest_get_key(agent, quest_id, key, defa=None):
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
        difficulty = quest_get_key(SHIP_ID, "patrol", "difficulty", "normal")
    """
    quest = quest_get(agent, quest_id)
    if quest is None:
        return defa
    return quest.get(key, defa)

def quest_set_key(agent, quest_id, key, value):
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
        quest_set_key(SHIP_ID, "patrol", "difficulty", "hard")
    """
    quest = quest_get(agent, quest_id)
    if quest is None:
        return
    setattr(quest, key, value)

def quest_add_yaml(agents, yaml_text):
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
        ~~)
    """
    quests = load_yaml_string(yaml_text)
    if quests is None:
        return
    for key, quest in quests.items():
        quest_add_object(agents, quest, key)



def quest_add_object(agents, obj, quest_id=None):
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
        }, "patrol")
    """
    if quest_id is None:
        quest_id = obj.get("id")

    display_text = obj.get("display_text")
    description = obj.get("description", display_text)
    state = obj.get("state", QuestState.IDLE)
    if isinstance(state, str):
        try:
            state = QuestState[state]
        except KeyError:
            state = QuestState.IDLE
            
    data = obj.get("data")
    children = obj.get("children", {})

    quest = quest_add(agents, quest_id, display_text, description, state, data)
    for key, child in children.items():
        quest_add_object(agents, child, f"{quest_id}/{key}")

def document_flatten(doc_obj, header=None, indent=0, data=None):
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
        list: Flat ordered list of ``gui_list_box_header`` items.
    """
    active = []
    idle = []
    completed = []
    failed = []

    if doc_obj is None:
        return []

    
    
    # root headers have no data
    # when data is not None this is adding the 
    # Parent so the indent is one less
    visual_indent = indent
    children = doc_obj.get("children")
    if data is None:
        if header is None:
            header = doc_obj.get("display_text")
            data = doc_obj
        active.append(gui_list_box_header(header,False,indent, data is not None,data, 0))
    elif len(children)>0:
        visual_indent = max(indent-1,0)
        active.append(gui_list_box_header(header,False,indent, data is not None,data, visual_indent))
        
        

    
    if len(children)==0 and data is not None:
        return [data]

    for q in children:
        q = MastDataObject(q)
        q.indent = indent
        q.visual_indent = indent

        state = q.get("state", QuestState.IDLE)
        if isinstance(state, str):
            try:
                state = QuestState[state]
                q.state = state
            except Exception:
                state = QuestState.IDLE
        if  state == QuestState.ACTIVE:
            active.extend(document_flatten(q, q.display_text, indent+1, q))
        if  state == QuestState.IDLE:
            idle.extend(document_flatten(q, q.display_text, indent+1, q))
        if state == QuestState.COMPLETE:
            completed.extend(document_flatten(q, q.display_text, indent+1, q))
        if state == QuestState.FAILED:
            failed.extend(document_flatten(q, q.display_text, indent+1, q))

    active.extend(idle)
    active.extend(completed)
    active.extend(failed)
    
    return active

def quest_flatten_list():
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
        gui_property_list_box(items, style="area:0,0,100,100;")
    """
    game_quests = quest_agent_quests(Agent.SHARED_ID)
    # game_quests = document_get_amd_file("consoles/quest.amd")
    client_id = FrameContext.client_id
    client_quests = None
    ship_quests = None

    if client_id != 0:
        client_quests = quest_agent_quests(client_id)
        ship_id = FrameContext.context.sbs.get_ship_of_client(client_id)
        if ship_id != 0:
            ship_quests = quest_agent_quests(ship_id)

    ret = []

    ret.extend(document_flatten(game_quests, "Game"))
    ret.extend(document_flatten(client_quests, "Client"))
    ret.extend(document_flatten(ship_quests, "Ship"))

    return ret


import re


def _amd_slug(text):
    """A heading display -> a key: lowercase, non-alphanumeric runs -> single '_'."""
    return "_".join("".join(c if c.isalnum() else " " for c in str(text).lower()).split())


def _document_get_amd_file(file_path, root_display_text="", strip_comments=True, content=None, data_parser=None, allow_bare_headings=False):
    from sbs_utils.procedural.amd import (amd_parse_facts, amd_kind_line, KIND_KEY,
                                          FenceScanner, RE_HEADING)
    from sbs_utils.procedural.amd_schema import amd_resolve_kind

    toc = {"key": "__root__", "file_path": file_path, "children": [], "description":"", "display_text": root_display_text}
    toc_stack = [toc]
    # ONE grammar, imported from `amd` and shared with amd_core (the linter/LSP
    # model). Two copies of these rules is how the tooling and the game came to
    # read the same file differently.
    rule_section = RE_HEADING
    # Bare/simplified heading (only when allow_bare_headings): `# Display` or
    # `# Display (key)`. Default off, so markdown-in-prose files (LM documents/
    # doc_viewer that use `# Heading` as rendered text) are unaffected.
    rule_bare = re.compile(r"#+[ \t]+(?P<rest>\S.*?)[ \t]*$")
    rule_bare_key = re.compile(r"^(?P<display>.*\S)[ \t]+\((?P<key>[\w.\-]+)\)$")
    rule_data = re.compile(r"\s*-{3,}\s*$")

    lines = []
    if content is not None:
        lines = content.splitlines(True)
    elif file_path is not None:
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()
        except Exception as e:
            print("no file")

    scanner = FenceScanner()
    data_lines = []
    for i, line in enumerate(lines):
        #
        # Data section: the `---` fence. The scanner enforces the non-toggling rule
        # (a fence opens only right after a heading, closes only while open), so one
        # stray rule in prose can no longer invert data-and-body for the whole file.
        #
        action = scanner.feed(line, i + 1)
        if action == "open":
            data_lines = []
            continue
        if action == "data":
            data_lines.append(line)
            continue
        if action == "close":
            section = toc_stack[-1]
            block = "".join(data_lines)
            if data_parser is not None:
                parsed = data_parser(block)
            else:
                # ONE reader. This used to default to raw YAML, which is why the
                # runtime and the linter could disagree about the same bytes - and
                # why `Color: #86c` needed an opt-in parser to survive at all.
                kinds = [s.get("kind") for s in reversed(toc_stack) if s.get("kind")]
                sections = [s.get("key") for s in reversed(toc_stack)
                            if s.get("key") and s.get("key") != "__root__"]
                from sbs_utils.procedural.amd import amd_fact_lines
                section["kind"] = amd_resolve_kind(
                    own_kind=amd_kind_line(block), ancestor_kinds=kinds,
                    section_key=section.get("key"), ancestor_sections=sections,
                    field_labels=[lab for lab, _v in amd_fact_lines(block)])
                parsed = amd_parse_facts(block, archetype=section["kind"])
            if isinstance(parsed, dict):
                merged = section.get("data") or {}
                merged.update(parsed)
                section["data"] = merged
            data_lines = []
            continue

        m = rule_section.match(line) if action == "heading" else None

        #
        # Heading: the `# [Display](key)` form, or (when enabled) a simplified
        # `# Display` / `# Display (key)`. Build display_text + key + any query
        # params, then place the section in the nesting stack by heading level.
        #
        display_text = None
        key = None
        query = {}
        if m is not None:
            data = m.groupdict()
            display_text = data.get("display")
            urn = data.get("urn").split("?", 1)
            key = urn[0]
            if len(urn) == 2:
                for kvalue in urn[1].split("&"):
                    kvalue = kvalue.split("=")
                    if len(kvalue) != 2:
                        raise Exception(f"ERROR: URN invalid line Line {i}\n{line}")
                    query[kvalue[0]] = kvalue[1]
            elif len(urn) != 1:
                raise Exception(f"ERROR: URN invalid line Line {i}\n{line}")
        elif allow_bare_headings:
            mb = rule_bare.match(line)
            if mb is not None:
                rest = mb.group("rest")
                mk = rule_bare_key.match(rest)
                if mk is not None:
                    display_text = mk.group("display")
                    key = mk.group("key")
                else:
                    display_text = rest
                    key = _amd_slug(rest)

        if display_text is not None:
            level = line.split(None, 1)
            level = len(level[0])

            section = {"key": key, "display_text": display_text, "children": [], "description":"", "state": 0}
            for qk, qv in query.items():
                section[qk] = qv

            # The root is level 0
            if level == len(toc_stack):
                toc_stack.append(section)
            elif level == len(toc_stack) + 1:
                toc_stack[level] = section
            elif level < len(toc_stack):
                toc_stack = toc_stack[: level + 1]
                toc_stack[level] = section
            else:
                raise Exception(f"ERROR: Document structure error Line {i}\n{line}")
            

            root = toc_stack[level - 1]
            children = root.get("children")
            children.append(section)
        elif strip_comments and line.startswith("//"):
            continue
        else:
            section = toc_stack[-1]
            desc = section.get("description", "")
            # if len(desc)>0:
            #     desc += "\n"
            desc += line
            section["description"] = desc
    # fs.save_json_data(file_path+".json", toc)
    return toc

def document_get_amd_file(file_path, root_display_text="", strip_comments=True, content=None, data_parser=None, allow_bare_headings=False):
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
        items = document_flatten(doc)
    """
    try:
        return _document_get_amd_file(file_path, root_display_text, strip_comments, content, data_parser, allow_bare_headings)
    except Exception as e:
        return {"key": "__root__", "file_path": file_path,
            "children": [], "description":"", "display_text": e}

# --- Shared quest-log GUI ----------------------------------------------------
# One renderer for BOTH the in-game quest tab and the end-game results tab, so the
# look is fixed in a single place; the callers differ ONLY in the `sources` list.
QUEST_LOG_STATE_ICON = 101

_QUEST_LOG_STATE_LABEL = {
    int(QuestState.ACTIVE): "Active", int(QuestState.IDLE): "Available",
    int(QuestState.COMPLETE): "Done", int(QuestState.FAILED): "Failed",
    int(QuestState.POSTING): "Posted",
}
# The square state icon (101) recolored by state: amber active, gray available,
# green done, red failed.
_QUEST_LOG_STATE_ICON_COLOR = {
    int(QuestState.ACTIVE): "#cc0", int(QuestState.IDLE): "#888",
    int(QuestState.COMPLETE): "#151", int(QuestState.FAILED): "#a22",
    int(QuestState.POSTING): "#88a",
}
# Row order within a section: active -> available/posted -> done -> failed.
_QUEST_LOG_STATE_ORDER = {
    int(QuestState.ACTIVE): 0, int(QuestState.IDLE): 1, int(QuestState.POSTING): 1,
    int(QuestState.COMPLETE): 2, int(QuestState.FAILED): 3,
}


def quest_log_state_label(state):
    """Display label for a quest state (Active / Available / Done / Failed / ...)."""
    return _QUEST_LOG_STATE_LABEL.get(int(state or 0), "")


def quest_log_state_icon_color(state):
    """Hex color for the state icon (defaults to gray)."""
    return _QUEST_LOG_STATE_ICON_COLOR.get(int(state or 0), "#888")


_QUEST_LOG_MAX_DEPTH = 5


def _quest_show(q):
    """A quest's `Show:` - WHEN it is listed in the log, normalised.

    Fence fields live under the quest's `data`; only state / display_text / description
    are promoted onto the quest itself, so reading `q["show"]` returns None and the
    field silently does nothing. Both are checked here so there is one place to be
    wrong."""
    from sbs_utils.procedural.amd_schema import amd_kind_show_default
    qd = q.get("data") or {}
    get = qd.get if hasattr(qd, "get") else (lambda k, d=None: d)
    raw = get("show") or q.get("show", "")
    if not raw:
        # No explicit `Show:` - fall back to what the record CALLED itself. `Beat` and
        # `Arc` say when they belong in the log as plainly as the field does, and an
        # author reaching for a screenplay word should not also have to configure it.
        raw = amd_kind_show_default(get("__kind__"))
    return str(raw or "always").strip().lower().replace("_", " ")


def _quest_log_rows(children, aid, group, depth):
    """One level of the quest tree. A quest that HAS visible children is emitted as a
    COLLAPSIBLE gui_list_box_header - so it folds its steps exactly like the Game/You/Ship
    group headers - followed by its children one level deeper; a leaf quest is a plain row.
    The list box itself does the fold + indent (a parent header sits at visual `depth`
    while its logical indent `depth+1` folds/indents its subtree; each row carries its own
    `indent`), so NO manual padding. State-sorted per level; SECRET (and subtrees) hidden."""
    entries = []
    for cid, q in (children or {}).items():
        st = int(q.get("state", QuestState.IDLE) or 0)
        if st == int(QuestState.SECRET):
            continue
        # `Show:` - WHEN this quest is listed. A story beat drives its events while
        # running but is not a to-do, so `when done` keeps it out of the log until it
        # RESOLVES (complete or failed), where it reads as history. Distinct from
        # SECRET, which also stops the triggers; a beat has to keep running.
        show = _quest_show(q)
        if show == "never":
            continue
        if show == "when done" and st not in (int(QuestState.COMPLETE), int(QuestState.FAILED)):
            continue
        entries.append((cid, q, st, show))
    entries.sort(key=lambda e: _QUEST_LOG_STATE_ORDER.get(e[2], 9))
    out = []
    for cid, q, st, show in entries:
        # `key` is the FULL path (q["id"], e.g. "arc/step1") so accept/abandon/Engage look
        # it up path-aware; falls back to the child segment for older quests.
        row = MastDataObject({
            "agent_id": aid, "key": q.get("id") or cid, "group": group, "indent": depth,
            "title": str(q.get("display_text", cid)), "state": st,
            "state_label": quest_log_state_label(st),
            "progress": q.get("progress", 0),
            "desc": (q.get("description") or "").strip(),
        })
        kids = q.get("children")
        visible_kids = _quest_log_rows(kids, aid, group, depth + 1) if kids else []
        has_visible_kids = bool(visible_kids)
        # `with children`: a pure grouping heading, worth a row only while something
        # under it is listed - otherwise it names a thread that has not started yet.
        # Declared, never inferred: a multi-step JOB also has children but is a quest in
        # its own right (it sits on the board to be accepted), and hiding it would make
        # it unacceptable.
        if show == "with children" and not has_visible_kids:
            continue
        if has_visible_kids and depth < _QUEST_LOG_MAX_DEPTH:
            # Parent quest -> collapsible header carrying the quest's row data; its steps
            # follow one level deeper and fold under it.
            out.append(gui_list_box_header(row.get("title"), False, depth + 1, True, row, visual_indent=depth))
            out.extend(visible_kids)
        else:
            out.append(row)
    return out


def quest_log_build_items(sources):
    """Build the collapsible quest-log item list shared by both logs.

    `sources` is a list of (section_label, agent_id). Each becomes a
    gui_list_box_header followed by that agent's non-SECRET quests. Child quests
    (nested via `/`-separated keys, e.g. `arc/step1`) render indented under their
    parent as a TREE (see _quest_log_rows); empty sections are skipped. Rows are
    MastDataObject with agent_id / key / group / depth / title / state /
    state_label / progress / desc, so quest_log_template renders them the same
    everywhere. The ONLY thing the two callers vary is `sources`.
    """
    items = []
    for group, aid in sources:
        tree = quest_agent_quests(aid)
        children = tree.get("children") if tree is not None else None
        rows = _quest_log_rows(children, aid, group, 0)
        if not rows:
            continue  # don't show an empty section header
        items.append(gui_list_box_header(str(group), False, 0, True, {"section": group}))
        items.extend(rows)
    return items


def quest_log_title():
    """Shared list title for the quest log."""
    from sbs_utils.procedural.gui import gui_row, gui_text
    gui_row("row-height: 1.2em;padding:13px;background:#1578;")
    gui_text("$text:Quest Log;justify: left;")


def quest_log_template(item):
    """Canonical quest-log row renderer (section headers + quest rows), shared by
    the in-game and end-game logs. Fix the look here and both update."""
    from sbs_utils.procedural.gui import gui_row, gui_text, gui_icon
    # A header row. Two kinds: a source group (Game / You / Ship) is a bare label + fold
    # arrow; a PARENT QUEST (its data carries a quest `key`) folds its steps and renders
    # like a quest row - state icon + title - with the fold arrow. The list box handles the
    # indent (by header level); this template does not pad.
    if gui_list_box_is_header(item):
        icon_index = 155 if not item.collapse else 154   # fold arrow: open / collapsed
        hdata = getattr(item, "data", None) or {}
        if hdata.get("key") is not None:
            gui_row("row-height: 1.2em;padding:6px;")
            gui_icon(f"icon_index:{QUEST_LOG_STATE_ICON};color:{quest_log_state_icon_color(hdata.get('state'))};", "padding:5px,0,5px,0;")
            gui_text(f"$text:{item.label};justify: left;", "padding:5px,6px,0,0;")
            arrow = gui_icon(f"icon_index:{icon_index};color:#fff;", "padding:0,0,5px,0;")
            gui_row("row-height: 1.0em;padding:6px;")
            gui_text(f"$text:{quest_log_state_label(hdata.get('state'))};justify: left;font:gui-1")
        else:
            gui_row("row-height: 1.4em;padding:6px;")
            gui_text(f"$text:{item.label};justify: left;color:#fff;", "padding:5px,6px,0,0;background:#1578")
            arrow = gui_icon(f"icon_index:{icon_index};color:#fff;", "padding:0,0,5px,0;background:#1578;")
        if item.selectable:
            arrow.click_text = ""
            arrow.click_tag = item.collapse_tag
            arrow.click_background = "#aaaa"
            arrow.click_color = "black"
        return
    # Leaf quest row: state icon (recolored) + title, then the state label on a second row.
    # The list box indents it by its `indent` level (no manual padding).
    icon_color = quest_log_state_icon_color(item.get("state"))
    gui_row("row-height: 1.2em;padding:6px;")
    gui_icon(f"icon_index:{QUEST_LOG_STATE_ICON};color:{icon_color};", "padding:5px,0,5px,0;")
    gui_text(f"$text:{item.get('title')};justify: left;", "padding:5px,6px,0,0;")
    gui_row("row-height: 1.0em;padding:6px;")
    gui_text(f"$text:{quest_log_state_label(item.get('state'))};justify: left;font:gui-1")
