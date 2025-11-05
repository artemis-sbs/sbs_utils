from .links import link, unlink
from .query import is_space_object_id, to_id, to_object
from ..faces import set_face, get_face
from ..agent import Agent, get_story_id
from .signal import signal_emit


    
def lifeform_spawn(name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    """
    Spawn a new Agent and initialize it as a lifeform.
    Args:
        name (str): The name of the lifeform.
        face (str): The face string of the lifeform.
        roles (str): A comma-separated list of roles assigned to the lifeform.
        host (Agent | int, optional): The agent or id of the host space object. Default is None.
        comms_id (str, optional): The comms_id of the lifeform (unused). Default is None.
        path (str, optional): The comms path to use to communicate with this lifeform. Default is None.
        title_color (str, optional): The color of the title of comms messages with this lifeform. Default is "green".
        message_color (str, optional): The color of the message of comms messages with this lifeform. Default is "white".
    """
    a = Agent()
    a.id = get_story_id()
    a.add()
    lifeform_init(a, name, face, roles, host, comms_id, path, title_color, message_color)

    return a

def lifeform_init(self, name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    """
    Initialize a lifeform.
    Args:
        name (str): The name of the lifeform
        face (str): The face string of the lifeform.
        roles (str): A comma-separated list of roles assigned to the lifeform.
        host (Agent | int, optional): The agent or id of the host space object. Default is None.
        comms_id (str, optional): The comms_id of the lifeform (unused). Default is None.
        path (str, optional): The comms path to use to communicate with this lifeform. Default is None.
        title_color (str, optional): The color of the title of comms messages with this lifeform. Default is "green".
        message_color (str, optional): The color of the message of comms messages with this lifeform. Default is "white".
    """
    
    if face is not None:
        set_face(to_id(self), face)
    
    #TODO: This should be inventory only
    self.name = name
    self.add_role("lifeform")
    self.add_role(roles)

    lifeform_set_path(self.id,path)
    lifeform_transfer(self.id,host)

    self.INV.title_color = title_color
    self.INV.message_color = message_color



def lifeform_transfer(lifeform, new_host):
    """
    Assign a new host to this lifeform.
    Args:
        lifeform (Agent | int): The agent or id of the lifeform.
        new_host (Agent | int): The agent or id of the new host.
    """
    lifeform = to_object(lifeform)
    if lifeform is None:
        return

    new_host = to_id(new_host)
    lifeform.host = new_host

    lifeform.remove_role("ultra_beam")
    old_host_id = lifeform.get_inventory_value("host", 0)
    if old_host_id:
        unlink(old_host_id, "onboard", lifeform.id)
    new_host_id = to_id(new_host)
    lifeform.set_inventory_value("host", new_host_id)
    if new_host is not None and is_space_object_id(new_host_id):
        link(new_host_id, "onboard", lifeform.id)
    else:
        lifeform.add_role("ultra_beam")
    signal_emit("lifeform_transferred", {"lifeform": lifeform, "old_host": old_host_id, "new_host": new_host_id})

    # Emit signal?
def lifeform_set_path(lifeform, path=None):
    """
    Set the comms path of the lifeform. If the path is None, then the `comms_badge` role is removed from the lifeform.
    Args:
        lifeform (Agent | int): The agent or id of the lifeform
        path (str, optional): The new path to use. Default is None.
    """
    lifeform = to_object(lifeform)
    if lifeform is None:
        return
    lifeform.set_inventory_value("path", path)
    lifeform.remove_role("comms_badge")
    if path is not None:
        lifeform.add_role("comms_badge")

