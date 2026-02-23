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
    agent = to_object(agent_id)
    if agent is None:
        return None
    return agent.get_inventory_value("__quests__")

def quest_transfer(from_agent_id, to_agent_id, quest_id):
    quest = quest_remove(from_agent_id, quest_id)
    if quest is not None:
        quests, child_id = quest_folder(to_agent_id, quest_id)
        if quests is None:
            return False
        quests[child_id] = quest
        return True
    return False

__quest_consoles = set()
def quest_console_enable(console, enable=True):
    global __quest_consoles
    consoles = console.split(",")
    for console in consoles:
        console = console.strip().lower()
        if enable:
            __quest_consoles.add(console)
        else:
            __quest_consoles.discard(console)
        
def quest_is_console_enabled(console):
    global __quest_consoles
    return console.strip().lower() in __quest_consoles

def quest_folder(agent_id, quest_id):
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
    quest, child_id = quest_folder(agent, quest_id)
    children = quest.get("children")
    return children.get(child_id)

def quest_get_parent(agent, quest_id):
    quests, child_id = quest_folder(agent, quest_id)
    return quests


def quest_remove(agent, quest_id):
    quests, child_id = quest_folder(agent, quest_id)
    if quests is not None and child_id is not None:
        child = quests.pop(child_id)
        return child
    return None

def quest_add(agents, quest_id, display_text, description, state=QuestState.IDLE, data=None):
    """_summary_

    Args:
        agents (_type_): _description_
        quest_id (_type_): _description_
        display_text (_type_): _description_
        state (bool, optional): _description_. Defaults to False.
        data (_type_, optional): _description_. Defaults to None.
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
    agent_ids = to_id_list(agents)

    for agent_id in agent_ids:
        quest_set_state(agent_id, quest_id, QuestState.ACTIVE)

def quest_complete(agents, quest_id):
    agent_ids = to_id_list(agents)

    for agent_id in agent_ids:
        quest_set_state(agent_id, quest_id, QuestState.COMPLETE)


def quest_get_state(agent, quest_id):
    return quest_get_key(agent, quest_id, "state", QuestState.IDLE)

def quest_set_state(agent, quest_id, state):
    cur_state = quest_get_state(agent, quest_id)
    if cur_state == state:
        return
    
    quest = quest_get(agent, quest_id)
    if state == QuestState.ACTIVE:
        signal_emit("quest_activated", {"AGENT_ID": to_id(agent), "QUEST_ID": quest_id, "QUEST": quest})
    if state == QuestState.COMPLETE:
        signal_emit("quest_completed", {"AGENT_ID": to_id(agent), "QUEST_ID": quest_id, "QUEST": quest})


def quest_get_data(agent, quest_id):
    return quest_get_key(agent, quest_id, "data")

def quest_get_display_name(agent, quest_id):
    return quest_get_key(agent, quest_id, "display_name")

def quest_get_description(agent, quest_id):
    return quest_get_key(agent, quest_id, "description")

def quest_get_key(agent, quest_id, key, defa=None):
    quest = quest_get(agent, quest_id)
    if quest is None:
        return None
    return quest.get(key, defa)

def quest_set_key(agent, quest_id, key, value):
    quest = quest_get(agent, quest_id)
    if quest is None:
        return
    quest[key] = value

def quest_add_yaml(agents, yaml_text):
    quests = load_yaml_string(yaml_text)
    if quests is None:
        return
    for key, quest in quests.items():
        quest_add_object(agents, quest, key)



def quest_add_object(agents, obj, quest_id=None):
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
        lines = content.splitlines()
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
    try:
        return _document_get_amd_file(file_path, root_display_text, strip_comments, content)
    except Exception as e:
        return {"key": "__root__", "file_path": file_path, 
            "children": [], "description":"", "display_text": e}