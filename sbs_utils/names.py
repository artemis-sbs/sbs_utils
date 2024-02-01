from . import fs
from random import choice, randrange
from .procedural import ship_data




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
    ship_name = ship_data.get_ship_name(key)
    if ship_name is None:
        return f"unknown {key}"
        
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

