"""
Quests modules

Quest are a data model for tracking various quests
Quests are attached to an Agent.
The tracking of quests are done by outside logic

When a quest is activated or completed a signal is sent

"""
from sbs_utils.procedural.query import to_id_list, to_object, to_id
from sbs_utils.procedural.signal import signal_emit
from sbs_utils.fs import load_yaml_string
from enum import IntEnum

class QuestState(IntEnum):
    IDLE = 0
    ACTIVE = 1
    SECRET = 2
    COMPLETE = 99


def quest_folder(agent_id, quest_id):
    agent = to_object(agent_id)
    if agent is None:
        return None, None
    quest = agent.get_inventory_value("__quests__", None)
    if quest is None:
        quest = {"children": {}}
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

        quest = {"display_text": display_text, "description": description, "state": state, "data": data, "children": {}}
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
    
def quest_add_object(agents, obj, path):
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

    quest = quest_add(agents, path, display_text, description, state, data)
    for key, child in children.items():
        quest_add_object(agents, child, f"{path}/{key}")


