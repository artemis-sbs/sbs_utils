from .links import link, unlink
from .query import is_space_object_id, to_id, to_object
from ..faces import set_face, get_face
from ..agent import Agent, get_story_id
from .signal import signal_emit


    
def lifeform_spawn(name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    """Create a new Agent and initialise it as a lifeform.

    Args:
        name (str): Display name of the lifeform.
        face (str): Face image key.
        roles (str): Comma-separated roles to assign (e.g. ``"crew,medic"``).
        host (Agent | int, optional): Space object the lifeform boards.
            Defaults to None.
        comms_id (str, optional): Unused. Defaults to None.
        path (str, optional): Comms route path for this lifeform. Defaults to
            None.
        title_color (str, optional): Color of the comms title line. Defaults
            to ``"green"``.
        message_color (str, optional): Color of the comms message text.
            Defaults to ``"white"``.

    Returns:
        Agent: The newly created lifeform agent.
    """
    a = Agent()
    a.id = get_story_id()
    a.add()
    lifeform_init(a, name, face, roles, host, comms_id, path, title_color, message_color)

    return a

def lifeform_init(self, name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    """Initialise an existing Agent as a lifeform (in-place version of ``lifeform_spawn``).

    Args:
        self (Agent): The agent to initialise.
        name (str): Display name of the lifeform.
        face (str): Face image key.
        roles (str): Comma-separated roles to assign.
        host (Agent | int, optional): Space object the lifeform boards.
            Defaults to None.
        comms_id (str, optional): Unused. Defaults to None.
        path (str, optional): Comms route path. Defaults to None.
        title_color (str, optional): Color of the comms title line. Defaults
            to ``"green"``.
        message_color (str, optional): Color of the comms message text.
            Defaults to ``"white"``.
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
    """Move a lifeform to a new host space object, emitting ``lifeform_transferred``.

    Unlinks from the old host (if any) and links to the new one. If
    ``new_host`` is not a space object ID the lifeform gains the
    ``"ultra_beam"`` role instead.

    Args:
        lifeform (Agent | int): The lifeform agent or its ID.
        new_host (Agent | int): The new host space object or its ID.
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
    """Set the comms route path for a lifeform.

    Clears the ``comms_badge`` role when ``path`` is ``None``, and adds it
    when a path is set.

    Args:
        lifeform (Agent | int): The lifeform agent or its ID.
        path (str, optional): The comms route path. Defaults to None (clears).
    """
    lifeform = to_object(lifeform)
    if lifeform is None:
        return
    lifeform.set_inventory_value("path", path)
    lifeform.remove_role("comms_badge")
    if path is not None:
        lifeform.add_role("comms_badge")

