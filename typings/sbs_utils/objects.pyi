from sbs_utils.spaceobject import MSpawnActive
from sbs_utils.spaceobject import MSpawnPassive
from sbs_utils.spaceobject import MSpawnPlayer
from sbs_utils.spaceobject import SpaceObject
class Active(SpaceObject, MSpawnActive):
    """Mixin to add Spawn as an Active"""
class Npc(SpaceObject, MSpawnActive):
    """Mixin to add Spawn as an Active"""
class Passive(SpaceObject, MSpawnPassive):
    """Mixin to add Spawn as an Passive"""
class PlayerShip(SpaceObject, MSpawnPlayer):
    """class PlayerShip"""
class Terrain(SpaceObject, MSpawnPassive):
    """Mixin to add Spawn as an Passive"""
