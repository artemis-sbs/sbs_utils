
from .spaceobject import MSpawnPlayer, SpaceObject, MSpawnActive, MSpawnPassive


class PlayerShip(SpaceObject, MSpawnPlayer):
	pass


class Npc(SpaceObject, MSpawnActive):
	pass

class Terrain(SpaceObject, MSpawnPassive):
	pass

class Active(SpaceObject, MSpawnActive):
	pass

class Passive(SpaceObject, MSpawnPassive):
	pass