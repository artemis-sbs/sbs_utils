from ..objects import Terrain, PlayerShip, Npc
from ..gridobject import GridObject

def npc_spawn(x,y,z,name, side, art_id, behave_id):
    so = Npc()
    return so.spawn(x,y,z,name, side, art_id, behave_id)
    
def player_spawn(x,y,z,name, side, art_id):
    so = PlayerShip()
    return so.spawn(x,y,z,name, side, art_id)

def terrain_spawn(x,y,z,name, side, art_id, behave_id):
    so = Terrain()
    return so.spawn(x,y,z,name, side, art_id, behave_id)

def grid_spawn(id, name, tag, x,y, icon, color, roles):
    so = GridObject()
    return so.spawn(id, name, tag, x,y, icon, color, roles)
