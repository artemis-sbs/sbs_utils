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
from sbs_utils.procedural.gui.listbox import gui_list_box_header

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

    Fires ``signal_emit("quest_completed", ...)`` for each agent. To also
    update the stored state, call ``quest_set_key(agent, quest_id, "state",
    QuestState.COMPLETE)`` or handle the signal in a ``//signal/quest_completed``
    route that sets the state.

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

    Emits ``quest_activated`` when ``state`` is ``QuestState.ACTIVE`` and
    ``quest_completed`` when ``state`` is ``QuestState.COMPLETE``. Does
    nothing if the quest is already in the requested state.

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


def _document_get_amd_file(file_path, root_display_text="", strip_comments=True, content=None):
    toc = {"key": "__root__", "file_path": file_path, "children": [], "description":"", "display_text": root_display_text}
    toc_stack = [toc]
    rule_section = re.compile(r"#+[ \t]+\[(?P<display_text>.*)\]\((?P<urn>.*)\)[ \t]*")

    lines = []
    if content is not None:
        lines = content.splitlines(True)
    elif file_path is not None:
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()
        except Exception as e:
            print("no file")

    for i, line in enumerate(lines):
        m = rule_section.match(line)

        #
        # Check for
        #
        if m is not None:
            level = line.split(None, 1)
            level = len(level[0])

            data = m.groupdict()
            display_text = data.get("display_text")
            
            urn = data.get("urn")
            urn = urn.split("?", 1)
            key = urn[0]
            
            section = {"key": key, "display_text": display_text, "children": [], "description":"", "state": 0}

            if len(urn) == 2:
                query_string = urn[1].split("&")
                for kvalue in query_string:
                    kvalue = kvalue.split("=")
                    if len(kvalue) != 2:
                        raise Exception(f"ERROR: URN invalid line Line {i}\n{line}")
                    this_key = kvalue[0]
                    value = kvalue[1]
                    section[this_key] = value
            elif len(urn) != 1:
                raise Exception(f"ERROR: URN invalid line Line {i}\n{line}")

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

def document_get_amd_file(file_path, root_display_text="", strip_comments=True, content=None):
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
        return _document_get_amd_file(file_path, root_display_text, strip_comments, content)
    except Exception as e:
        return {"key": "__root__", "file_path": file_path,
            "children": [], "description":"", "display_text": e}