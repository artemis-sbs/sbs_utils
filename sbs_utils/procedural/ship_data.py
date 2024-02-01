from ..fs import load_json_data, get_artemis_data_dir, get_mission_dir
import os

ship_data_cache = load_json_data( os.path.join(get_artemis_data_dir(), "shipData.json"))
def get_ship_data():
    global ship_data_cache
    if ship_data_cache is not None:
        return ship_data_cache
    
    ship_data_cache = load_json_data( os.path.join(get_artemis_data_dir(), "shipData.json"))
    
    script_ship_data = load_json_data( os.path.join(get_mission_dir(), "shipData.json"))
    if script_ship_data is not None:
        ship_data_cache |= script_ship_data
    

data = get_ship_data()
ship_index = {

}
for i,ship in enumerate(data["#ship-list"]):
    this_ship_index = ship_index.get(ship['side'])
    if not this_ship_index:
        this_ship_index = set()
        ship_index[ship['side']] = this_ship_index
    this_ship_index.add(i)
    ship_index[ship['key']] = ship

def get_ship_name(key):
    ship = ship_index.get(key)
    if ship:
        return ship['name']
    return None

def get_ship_data_for(key):
    return ship_index.get(key)


def filter_ship_data_by_side(test_key, sides, role=None, ret_key_only=False):
    data = get_ship_data()

    ret = []
    if sides is not None:
        if isinstance(sides, str):
            sides=sides.lower()
            sides = {sides}
    
    for ship in data["#ship-list"]:
        if role:
            roles = ship.get("roles", None)
            if roles is None:
                continue
            roles = roles.lower()
            roles = set(roles.split(","))
            role = role.lower()
            if not (role in roles):
                continue

        key = ship["key"]
        if len(key)==0:
            ship["artfileroot"]

        key_met = test_key is None 
        if test_key is not None:
            key_met =  test_key in ship["key"]
        
        side_met = sides is None
        if sides is not None:
            side_met = ship["side"].lower() in sides

        if key_met and side_met:
            if ret_key_only:
                ret.append(ship["key"])
            else:
                ret.append(ship)
    return ret


asteroid_keys_cache= filter_ship_data_by_side(None, "asteroid", None, True)
def asteroid_keys():
    return asteroid_keys_cache

crystal_asteroid_keys_cache= filter_ship_data_by_side("crystal", "asteroid", None, True)
def crystal_asteroid_keys():
    return crystal_asteroid_keys_cache

plain_asteroid_keys_cache= filter_ship_data_by_side("plain", "asteroid", None, True)
def plain_asteroid_keys():
    return plain_asteroid_keys_cache

    
danger_keys_cache =  filter_ship_data_by_side("danger", "pickup", None, True)
def danger_keys():
    return danger_keys_cache

container_keys_cache =  filter_ship_data_by_side("container", "pickup", None, True)
def container_keys():
    return container_keys_cache

alien_keys_cache =  filter_ship_data_by_side("alien", "pickup", None, True)
def alien_keys():
    return alien_keys_cache

terran_starbase_keys_cache =  filter_ship_data_by_side(None, "port", "station", True)
def terran_starbase_keys():
    return terran_starbase_keys_cache

terran_ship_keys_cache =  filter_ship_data_by_side(None, "TSN", "ship", True)
def terran_ship_keys():
    return terran_ship_keys_cache

pirate_starbase_keys_cache =  filter_ship_data_by_side(None, "port", None, True)
def pirate_starbase_keys():
    return pirate_starbase_keys_cache

pirate_ship_keys_cache =  filter_ship_data_by_side(None, "pirate", "ship", True)
def pirate_ship_keys():
    return pirate_ship_keys_cache

ximni_starbase_keys_cache =  filter_ship_data_by_side(None, "ximni", "station", True)
def ximni_starbase_keys():
    return ximni_starbase_keys_cache

ximni_ship_keys_cache =  filter_ship_data_by_side(None, "Ximni", "ship", True)
def ximni_ship_keys():
    return ximni_ship_keys_cache

arvonian_starbase_keys_cache =  filter_ship_data_by_side(None, "arvonian", "station", True)
def arvonian_starbase_keys():
    return arvonian_starbase_keys_cache

arvonian_ship_keys_cache =  filter_ship_data_by_side(None, "Arvonian", "ship", True)
def arvonian_ship_keys():
    return arvonian_ship_keys_cache

skaraan_starbase_keys_cache = filter_ship_data_by_side(None, "skaraan", "station", True)
def skaraan_starbase_keys():
    return skaraan_starbase_keys_cache

skaraan_ship_keys_cache =  filter_ship_data_by_side(None, "Skaraan", "ship", True)
def skaraan_ship_keys():
    return skaraan_ship_keys_cache

kralien_starbase_keys_cache =  filter_ship_data_by_side(None, "kralien", "station", True)
def kralien_starbase_keys():
    return kralien_starbase_keys_cache

kralien_ship_keys_cache =  filter_ship_data_by_side(None, "Kralien", "ship", True)
def kralien_ship_keys():
    return kralien_ship_keys_cache

torgoth_starbase_keys_cache =  filter_ship_data_by_side(None, "torgoth", "station", True)
def torgoth_starbase_keys():
    return torgoth_starbase_keys_cache

torgoth_ship_keys_cache =  filter_ship_data_by_side(None, "Torgoth", "ship", True)
def torgoth_ship_keys():
    return torgoth_ship_keys_cache
