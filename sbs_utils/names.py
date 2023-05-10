from . import fs
from random import choice, randrange


data = fs.get_ship_data()
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
    return f'unknown {key}'


def filter_ship_data_by_side(test_key, sides, is_ship=False, ret_key_only=False):
    data = fs.get_ship_data()

    ret = []
    if sides is not None:
        if isinstance(sides, str):
            sides = {sides}
    
    for ship in data["#ship-list"]:
        if is_ship and not "hullpoints" in ship:
            continue

        key = ship["key"]
        if len(key)==0:
            ship["artfileroot"]

        key_met = test_key is None 
        if test_key is not None:
            key_met =  test_key in ship["key"]
        
        side_met = sides is None
        if sides is not None:
            side_met = ship["side"] in sides

        if key_met and side_met:
            if ret_key_only:
                ret.append(ship["key"])
            else:
                ret.append(ship)
    return ret


asteroid_keys_cache= filter_ship_data_by_side(None, "asteroid", False, True)
def asteroid_keys():
    return asteroid_keys_cache

crystal_asteroid_keys_cache= filter_ship_data_by_side("crystal", "asteroid", False, True)
def crystal_asteroid_keys():
    return crystal_asteroid_keys_cache

plain_asteroid_keys_cache= filter_ship_data_by_side("plain", "asteroid", False, True)
def plain_asteroid_keys():
    return plain_asteroid_keys_cache

    
danger_keys_cache =  filter_ship_data_by_side("danger", "pickup", False, True)
def danger_keys():
    return danger_keys_cache

container_keys_cache =  filter_ship_data_by_side("container", "pickup", False, True)
def container_keys():
    return container_keys_cache

alien_keys_cache =  filter_ship_data_by_side("alien", "pickup", False, True)
def alien_keys():
    return alien_keys_cache

terran_starbase_keys_cache =  filter_ship_data_by_side(None, "port", False, True)
def terran_starbase_keys():
    return terran_starbase_keys_cache

terran_ship_keys_cache =  filter_ship_data_by_side(None, "TSN", True, True)
def terran_ship_keys():
    return terran_ship_keys_cache

pirate_starbase_keys_cache =  filter_ship_data_by_side(None, "port", False, True)
def pirate_starbase_keys():
    return pirate_starbase_keys_cache

pirate_ship_keys_cache =  filter_ship_data_by_side(None, "pirate", True, True)
def pirate_ship_keys():
    return pirate_ship_keys_cache

ximni_starbase_keys_cache =  filter_ship_data_by_side(None, "port", False, True)
def ximni_starbase_keys():
    return ximni_starbase_keys_cache

ximni_ship_keys_cache =  filter_ship_data_by_side(None, "Ximni", True, True)
def ximni_ship_keys():
    return ximni_ship_keys_cache

arvonian_starbase_keys_cache =  filter_ship_data_by_side("starbase", "arvonian", False, True)
def arvonian_starbase_keys():
    return arvonian_starbase_keys_cache

arvonian_ship_keys_cache =  filter_ship_data_by_side(None, "Arvonian", True, True)
def arvonian_ship_keys():
    return arvonian_ship_keys_cache

skaraan_starbase_keys_cache = filter_ship_data_by_side("starbase", "skaraan", False, True)
def skaraan_starbase_keys():
    return skaraan_starbase_keys_cache

skaraan_ship_keys_cache =  filter_ship_data_by_side(None, "Skaraan", True, True)
def skaraan_ship_keys():
    return skaraan_ship_keys_cache

kralien_starbase_keys_cache =  filter_ship_data_by_side("starbase", "kralien", False, True)
def kralien_starbase_keys():
    return kralien_starbase_keys_cache

kralien_ship_keys_cache =  filter_ship_data_by_side(None, "Kralien", True, True)
def kralien_ship_keys():
    return kralien_ship_keys_cache

torgoth_starbase_keys_cache =  filter_ship_data_by_side("starbase", "torgoth", False, True)
def torgoth_starbase_keys():
    return torgoth_starbase_keys_cache

torgoth_ship_keys_cache =  filter_ship_data_by_side(None, "Torgoth", True, True)
def torgoth_ship_keys():
    return torgoth_ship_keys_cache


pirate_titles = [
    "The",
    "King's",
    "Ocean's",
    "Sky's",
    "Queen's",
    "Captain's"
]
pirate_first = [
    "Scorn",
    "Mistress",
    "Nights",
    "Hord",
    "Davey Jones",
    "Doom",
    "Galley"
]


def kralien_ship(id:int, key:str):
    trim = (id % (1295))
    trim1 = id % 6
    trim2 = ((trim/6) % 6) 
    trim3 = ((trim/36) % 6)
    trim4 = ((trim/216) % 6)
    return f"{trim2}{trim1}{trim4}{trim3}"
    


    



def random_pirate_ship():
    first = randrange(len(pirate_first))
    second = randrange(len(pirate_first)) 
    while first == second:
        first = randrange(len(pirate_first))
        second = randrange(len(pirate_first))

    return pirate_ship(
        randrange(len(pirate_titles)), 
        first,
        second,
        randrange(5)==4
        )


def pirate_ship(v1,v2,v3, of_the):
    name = pirate_titles[v1%len(pirate_titles)]
    name += " " + pirate_first[v2%len(pirate_first)]
    if of_the:
        name += " of the"
    name += " " + pirate_first[v3%len(pirate_first)]
    return name


from random import shuffle, choice, sample
import sys

###########

id_pool = {
    "kralien_battleship": [],
    "kralien_cruiser": [],
    "kralien_dreadnought": [], 
    "kralien_inquisitor": []}
def get_pool(key):
        return id_pool[key]
# 36 00-55 in base 6
for i in range(1296):
    if i<36:
        id_pool["kralien_inquisitor"].append(i)
    elif i < 216:
        id_pool["kralien_battleship"].append(i)
        id_pool["kralien_dreadnought"].append(i)
    else:
        id_pool["kralien_cruiser"].append(i)

# randomize order and make a circular list
for key in id_pool:
    shuffle(id_pool[key])

def random_kralien_name(id):
     # 15
     cons = "dghklmnqrsŝtyz "
     # 6
     vows = "aeiouŭ"
     #73
     cluster = "Dd,dl,dy,gg,gl,gy,gs,hh,kl,km,kr,ks,ky,ld,lg,lk,ll,lm,ln,lq,ls,lt,ly,lz,ml,mm,mn,mr,my,mz,nd,ng,nk,nl,nn,nq,nr,ns,nt,ny,nz,q,rd,rg,rh,rk,rl,rm,rn,rq,rs,rt,ry,rz,sh,sk,sl,sm,sn,sq,ss,st,sy,th,tl,tr,tt,ty,ngl,ngr,ndr,nkl,ynd"
     cluster = cluster.split(",")
     c = sample(cons,2)
     c1 = c[0].strip()
     c2 = c[1].strip()
     v1 = choice(vows)
     v2 = choice(vows)
     r = choice(cluster)
     first = f"{c1}{v1}{r}{v2}".capitalize()
     last = f"{c2}{v1}{r}{v2}".capitalize()
     return f"{first}-{last}"
     

def kralien_name(id):
     id += 1296 // 2 
     # 15
     cons = "dghklmnqrsŝtyz "
     # 6
     vows = "aeiouŭ"
     #73
     cluster = "Dd,dl,dy,gg,gl,gy,gs,hh,kl,km,kr,ks,ky,ld,lg,lk,ll,lm,ln,lq,ls,lt,ly,lz,ml,mm,mn,mr,my,mz,nd,ng,nk,nl,nn,nq,nr,ns,nt,ny,nz,q,rd,rg,rh,rk,rl,rm,rn,rq,rs,rt,ry,rz,sh,sk,sl,sm,sn,sq,ss,st,sy,th,tl,tr,tt,ty,ngl,ngr,ndr,nkl,ynd"
     cluster = cluster.split(",")
     i1 = (id  )%  len(cons)
     i2 = (id >> 1) % len(cons)
     if i1==i2:
         i2 = (not i1) % len(cons)

     c1 = cons[i1].strip()
     c2 = cons[i2].strip()
     
     v1 = vows[id % len(vows)]
     v2 = vows[(id >> 3) % len(vows)]
     r =  cluster[(id >> 4) % len(cluster)]
     first = f"{c1}{v1}{r}{v2}".capitalize()
     last = f"{c2}{v1}{r}{v2}".capitalize()
     return f"{first}-{last}"


def canonical_kralien_comms_id(id, key:str):
    key = key.lower()
    length = 4
    ship_name = ship_name = get_ship_name(key)

        
    trim1 = id % 6
    trim2 = ((id//6) % 6) 
    trim3 = ((id//36) % 6)
    trim4 = ((id//216) % 6)
    if length==3:
        return f"{ship_name} {trim3}{trim2}{trim1} "
    elif length==2:
        return f"{ship_name} {trim2}{trim1} "
    return f"{ship_name} {trim4}{trim3}{trim2}{trim1} "

def random_canonical_kralien_comms_id(id, key:str):
    key = key.lower()
    this_id_pool = id_pool.get(key, id_pool["kralien_cruiser"])
    this_id = this_id_pool.pop(0)
    this_id_pool.append(this_id)
    trim = (this_id% 1296)
    return canonical_kralien_comms_id(trim,key)


# Guaranteed unique for 1295 calls
def random_common_kralien(key:str):
    global kralien_id
    id = kralien_id
    kralien_id += 1
    name = random_kralien_name(id)
    comms_id = canonical_kralien_comms_id(id, key)
    face = ""
    return (name, comms_id, face)

def arvonian_name(id):
    cons = "b,br,bl,by,d,dr,dl,dy,k,kl,kr,ky,l,l,l,l,ly,ly,m,m,my,n,ny,p,pr,pl,py,r,r,ry,s,s,sl,sr,st,sy,t,ty,v,vr,vy,w,w,wy,y,y, , "
    cons = cons.split(",")
    vows = "a,e,i,o,u,ay,ay,ah,ah"
    vows = vows.split(",")
    count = [2,2,2,3,3,3,3,3,4,4,4]

    count = choice(count)
    name = ""
    for i in range(count):
        c = choice(cons).strip()
        v = choice(vows)
        name += c+v
    return name.capitalize()

def arvonian_comms_id(id):
    pass

