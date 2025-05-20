from .links import link, linked_to, unlink, get_dedicated_link, set_dedicated_link
from .query import is_space_object_id, to_id
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
    def host(self):
        return get_dedicated_link(self.id, "onboard")
    
    @host.setter
    def host(self, host_id):
        host_id = to_id(host_id)
        if host_id is not None and is_space_object_id(host_id):
            set_dedicated_link(self.id, "onboard", host_id)
        else:
            set_dedicated_link(self.id, "onboard", None)


def lifeform_spawn(name, face, roles, host, comms_id=None):
    a = Lifeform()
    a.name = name
    a.comms_id = comms_id
    
    a.add_role(roles)

    set_face(a.id, face)

    host = to_id(host)
    if is_space_object_id(host):
        link(host, "onboard", a.id)
        set_dedicated_link(a.id, "onboard", host)
    return a


def lifeform_transfer(lifeform, new_host):
    lifeform = to_id(lifeform)

    old_host = get_dedicated_link("onboard")
    if is_space_object_id(old_host):
        unlink(old_host, "onboard", lifeform)
        # Remove deicated link
        unlink(lifeform, "onboard", old_host)

    new_host = to_id(new_host)
    if is_space_object_id(new_host):
        link(new_host, "onboard", lifeform)
        set_dedicated_link(lifeform, "onboard", new_host)

    # Emit signal?
