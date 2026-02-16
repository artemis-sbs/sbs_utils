from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
from enum import IntEnum
from sbs_utils.mast.mast_node import MastDataObject
def _document_get_amd_file (file_path, root_display_text='', strip_comments=True):
    ...
def document_flatten (doc_obj, header=None, indent=0, data=None):
    ...
def document_get_amd_file (file_path, root_display_text='', strip_comments=True):
    ...
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Created a gui_list_box_header element
    
    Args:
        label (str): The label text
        collapse (bool, optional): Default the collapsed state. Defaults to False.
        indent (int): The indention level e.g. for a tree like structure
        selectable (bool): If the header is also selectable
        collapse_pixel_size (int): The size in pixels for the hit area (only used if selectable)
        select_first (bool): If the select area is before the collapse click area (only used if selectable)
        data (any): Optional additional data
    
    Returns:
        LayoutListBoxHeader : _description_"""
def load_yaml_string (s):
    """Parse a YAML string.
    
    Attempts to parse using ryaml first for better comment handling,
    falls back to standard yaml.safe_load if ryaml is unavailable.
    
    Args:
        s (str): YAML content as a string.
    
    Returns:
        dict or None: Parsed YAML data, or None if parsing fails."""
def quest_activate (agents, quest_id):
    ...
def quest_add (agents, quest_id, display_text, description, state=<QuestState.IDLE: 0>, data=None):
    """_summary_
    
    Args:
        agents (_type_): _description_
        quest_id (_type_): _description_
        display_text (_type_): _description_
        state (bool, optional): _description_. Defaults to False.
        data (_type_, optional): _description_. Defaults to None."""
def quest_add_object (agents, obj, quest_id=None):
    ...
def quest_add_yaml (agents, yaml_text):
    ...
def quest_agent_quests (agent_id):
    ...
def quest_complete (agents, quest_id):
    ...
def quest_console_enable (console, enable=True):
    ...
def quest_flatten_list ():
    ...
def quest_folder (agent_id, quest_id):
    ...
def quest_get (agent, quest_id):
    ...
def quest_get_data (agent, quest_id):
    ...
def quest_get_description (agent, quest_id):
    ...
def quest_get_display_name (agent, quest_id):
    ...
def quest_get_key (agent, quest_id, key, defa=None):
    ...
def quest_get_parent (agent, quest_id):
    ...
def quest_get_state (agent, quest_id):
    ...
def quest_is_console_enabled (console):
    ...
def quest_remove (agent, quest_id):
    ...
def quest_set_key (agent, quest_id, key, value):
    ...
def quest_set_state (agent, quest_id, state):
    ...
def quest_transfer (from_agent_id, to_agent_id, quest_id):
    ...
def signal_emit (name, data=None):
    """Emit a signal to trigger all instances of the signal route to run.
    Args:
        name (str): The name of the signal.
        data (dict): The data to provide to the signal route."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_id_list (the_set):
    """Converts a set to a list of ids
    Args:
        the_set (set[Agent | int] | list[Agent | int]): a set or list of agents or ids
    Returns:
        list[int]: A list of agent ids"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
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
