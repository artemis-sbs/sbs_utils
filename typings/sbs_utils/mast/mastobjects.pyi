from sbs_utils.spaceobject import MSpawnActive
from sbs_utils.spaceobject import MSpawnPassive
from sbs_utils.spaceobject import MSpawnPlayer
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastScheduler
class MastSpaceObject(SpaceObject):
    """class MastSpaceObject"""
    def __init__ (self, scheduler: sbs_utils.mast.mastscheduler.MastScheduler):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def destroyed (self):
        ...
    def start_task (self, label='main', inputs=None, task_name=None) -> sbs_utils.mast.mastscheduler.MastAsyncTask:
        ...
class Npc(MastSpaceObject, MSpawnActive):
    """Mixin to add Spawn as an Active"""
    def __init__ (self, scheduler):
        """Initialize self.  See help(type(self)) for accurate signature."""
class PlayerShip(MastSpaceObject, MSpawnPlayer):
    """class PlayerShip"""
    def __init__ (self, scheduler):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Terrain(MastSpaceObject, MSpawnPassive):
    """Mixin to add Spawn as an Passive"""
    def __init__ (self, scheduler):
        """Initialize self.  See help(type(self)) for accurate signature."""
