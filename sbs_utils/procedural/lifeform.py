from .links import link, unlink
from .query import is_space_object_id, to_id, to_object
from ..faces import set_face, get_face
from ..agent import Agent, get_story_id

class Lifeform(Agent):
    def __init__(self):
        super().__init__()
    #     self.name = ""
        self.id = get_story_id()
        self.add()
    #     self.add_role("lifeform")
    #     self._comms_id = None
    #     self.path = "//comms/lifeform"
    #     self._host_id = None
    #     self.title_color = "green"
    #     self.message_color = "white"

    # @property
    # def face(self):
    #     return get_face(self.id)
    
    # @property
    # def comms_id(self):
    #     if self._comms_id is not None:
    #         return self._comms_id
    #     return self.name
    
    # @comms_id.setter
    # def comms_id(self, v):
    #     self._comms_id = v

    # @property
    # def path(self):
    #     return self.get_inventory_value("path")
        
    
    # @path.setter
    # def path(self, v):
    #     self.remove_role("comms_badge")
    #     self.set_inventory_value("path", v)
    #     if v is not None:
    #         self.add_role("comms_badge")

    # @property
    # def host(self):
    #     return self.get_inventory_value("host", 0)
    
    # @host.setter
    # def host(self, host_id):
    #     self.remove_role("ultra_beam")
    #     old_host_id = self.get_inventory_value("host", 0)
    #     if old_host_id:
    #         unlink(old_host_id, "onboard", self.id)
    #     new_host_id = to_id(host_id)
    #     self.set_inventory_value("host", new_host_id)
    #     if host_id is not None and is_space_object_id(new_host_id):
    #         link(new_host_id, "onboard", self.id)
    #     else:
    #         self.add_role("ultra_beam")


def lifeform_spawn(name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    a = Agent()
    a.id = get_story_id()
    a.add()
    lifeform_init(a, name, face, roles, host, comms_id, path, title_color, message_color)
    # a.name = name
    # a.comms_id = comms_id
    #a.title_color = title_color
    #a.message_color = message_color
    # a.add_role(roles)

    # set_face(a.id, face)

    # a.host = to_id(host)
    # a.path = path
    return a

def lifeform_init(self, name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    if face is not None:
        set_face(to_id(self), face)
    self.INV.name = name
    #TODO: This should be inventory only
    self.name = name
    self.add_role("lifeform")
    self.add_role(roles)

    lifeform_set_path(self.id,path)
    lifeform_transfer(self.id,host)

    self.INV.title_color = title_color
    self.INV.message_color = message_color



def lifeform_transfer(lifeform, new_host):
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

    # Emit signal?
def lifeform_set_path(lifeform, path=None):
    lifeform = to_object(lifeform)
    if lifeform is None:
        return
    lifeform.set_inventory_value("path", path)
    lifeform.remove_role("comms_badge")
    if path is not None:
        lifeform.add_role("comms_badge")

