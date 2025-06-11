from .links import link, unlink
from .query import is_space_object_id, to_id, to_object
from ..faces import set_face, get_face
from ..agent import Agent, get_story_id

class Lifeform(Agent):
    def __init__(self):
        super().__init__()
        self.name = ""
        self.id = get_story_id()
        self.add()
        self.add_role("lifeform")
        self._comms_id = None
        self._path = "//comms/lifeform"
        self._host_id = None
        self.title_color = "green"
        self.message_color = "white"

    @property
    def face(self):
        return get_face(self.id)
    
    @property
    def comms_id(self):
        if self._comms_id is not None:
            return self._comms_id
        return self.name
    
    @comms_id.setter
    def comms_id(self, v):
        self._comms_id = v

    @property
    def path(self):
        return self._path
    
    @path.setter
    def path(self, v):
        self.remove_role("comms_badge")
        self._path = v
        if self._path is not None:
            self.add_role("comms_badge")

    @property
    def host(self):
        return self._host_id
    
    @host.setter
    def host(self, host_id):
        self.remove_role("long_range")
        if self._host_id:
            unlink(self._host_id, "onboard", self.id)
        self._host_id = to_id(host_id)
        if host_id is not None and is_space_object_id(host_id):
            link(self._host_id, "onboard", self.id)
        else:
            self.add_role("long_range")


def lifeform_spawn(name, face, roles, host=None, comms_id=None, path=None, title_color="green", message_color="white"):
    a = Lifeform()
    a.name = name
    a.comms_id = comms_id
    a.title_color = title_color
    a.message_color = message_color
    a.add_role(roles)

    set_face(a.id, face)

    a.host = to_id(host)
    a.path = path
    return a


def lifeform_transfer(lifeform, new_host):
    lifeform = to_object(lifeform)
    if lifeform is None:
        return

    new_host = to_id(new_host)
    lifeform.host = new_host

    # Emit signal?
