from random import randrange,uniform, choice
from .procedural.query import to_id

# ter Terran_Big-revised
#* tor Torgoth_Set
#* ska Skaraan_Set
#- kra Krailen_Set
#- zim Zimni_Set
#- arv Arvonian

faces_map = {}

def get_face(ship_id):
    """
    Returns a face string for a specified ID

    Args:
        ship_id (Agent | int): The id of the ship/object

    Returns:
        str: A Face string
    """
    return faces_map.get(to_id(ship_id), "")

def set_face(ship_id, face):
    """
    Sets a face string for a specified ID.

    Args:
        ship_id (Agent | int): The id of the ship/object
        face (str): A Face string
    """
    faces_map[to_id(ship_id)] = face

def clear_face(ship_id):
    """ 
    Removes a face string for a specified ID.

    Args:
        ship_id (Agent | int): The id of the ship/object
    """
    faces_map.pop(to_id(ship_id), None)


skaraan_map = {
    "face": [(0,0)],
    "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
    "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
    "horns": [(0,6), (1,0),(2,0), (3,0),(4,0)],
    "hat": [(5,0), (6,0),(1,1), (1,2),(1,3)],
}


def skaraan(face_id, eye_id, mouth_id, horn_id, hat_id):
    """ 
    Create a skaraan face

    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        horn_id (int | None): The index of the horn 0-4 or None
        hat_id (int | None): The index of the hat 0-4 or None

    Returns:
        (str): A Face string
    """
    face = skaraan_map["face"][face_id]
    eye = skaraan_map["eyes"][eye_id]
    mouth = skaraan_map["mouth"][mouth_id]

    ret =  f"ska #fff {face[0]} {face[1]};ska #fff {eye[0]} {eye[1]};ska #fff {mouth[0]} {mouth[1]};"
    if horn_id  is not None:
        horns = skaraan_map["horns"][horn_id]
        ret += f"ska #fff {horns[0]} {horns[1]};"
    if hat_id is not None:
        hat = skaraan_map["hat"][hat_id]
        ret += f"ska #fff {hat[0]} {hat[1]};"
    return ret

def random_skaraan():
    """ 
    Create a random skaraan face.

    Returns:
        (str):   A Face string
    """
    face = randrange(0, len(skaraan_map["face"]))
    eye = randrange(0, len(skaraan_map["eyes"]))
    mouth = randrange(0, len(skaraan_map["mouth"]))
    horns = None
    hat = None
    if randrange(0,10) > 5:
        horns = randrange(0, len(skaraan_map["horns"]))
    if randrange(0,10) > 5:
        hat = randrange(0, len(skaraan_map["hat"]))
    return skaraan(face, eye, mouth, horns, hat)


torgoth_map = {
    "face": [(0,0)],
    "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
    "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
    "hair": [(0,6), (1,0),(2,0), (3,0),(4,0)],
    "extra": [(6,0),(1,1), (1,2),(1,3)], 
    "hat": [(5,0)], 
}


def torgoth(face_id, eye_id, mouth_id, hair_id, extra_id, hat_id):
    """ 
    Create a torgoth face.

    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        hair_id (int | None): The index of the hair 0-4 or None
        extra_id (int | None): The index of the extra 0-4 or None
        hat_id (int | None): The index of the hat 0 or None

    Returns:    
        (str):   A Face string
    """
    face = torgoth_map["face"][face_id]
    eye = torgoth_map["eyes"][eye_id]
    mouth = torgoth_map["mouth"][mouth_id]
    
    ret =  f"tor #fff {face[0]} {face[1]};tor #fff {eye[0]} {eye[1]};tor #fff {mouth[0]} {mouth[1]};"
    if hair_id is not None:
        hair = torgoth_map["hair"][hair_id]
        ret += f"tor #fff {hair[0]} {hair[1]};"
    if hat_id  is not None:
        hat = torgoth_map["hat"][hat_id]
        ret += f"tor #fff {hat[0]} {hat[1]};"

    if extra_id  is not None:
        extra = torgoth_map["extra"][extra_id]
        ret += f"tor #fff {extra[0]} {extra[1]};"
    return ret

def random_torgoth():
    """ 
    Create a random torgoth face.
    
    Returns:
        (str):   A Face string
    """
    face = randrange(0, len(torgoth_map["face"]))
    eye = randrange(0, len(torgoth_map["eyes"]))
    mouth = randrange(0, len(torgoth_map["mouth"]))
    hair = None
    extra = None
    hat = None
    if randrange(0,10) > 5:
        hair = randrange(0, len(torgoth_map["hair"]))
    if randrange(0,10) > 5:
        extra = randrange(0, len(torgoth_map["extra"]))
    if randrange(0,10) > 7:
        hat = randrange(0, len(torgoth_map["hat"]))
    return torgoth(face, eye, mouth, hair, extra, hat)

arvonian_map = {
    "face": [(0,0)],
    "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
    "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
    "crown": [(0,6), (1,0),(2,0), (3,0),(4,0)],
    "collar": [(5,0), (6,0),(1,1), (1,2),(1,3)], 
}


def arvonian(face_id, eye_id, mouth_id, crown_id, collar_id):
    """ 
    Create an arvonian face

    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        crown_id (int | None): The index of the crown 0-4 or None
        collar_id (int | None): The index of the collar 0-4 or None

    Returns:    
        (str):   A Face string
    """
    face = arvonian_map["face"][face_id]
    eye = arvonian_map["eyes"][eye_id]
    mouth = arvonian_map["mouth"][mouth_id]
    
    ret =  f"arv #fff {face[0]} {face[1]};arv #fff {eye[0]} {eye[1]};arv #fff {mouth[0]} {mouth[1]};"
    if crown_id is not None:
        crown = arvonian_map["crown"][crown_id]
        ret += f"arv #fff {crown[0]} {crown[1]};"

    if collar_id  is not None:
        collar = arvonian_map["collar"][collar_id]
        ret += f"arv #fff {collar[0]} {collar[1]};"
    return ret

def random_arvonian():
    """ 
    Create a random arvonian face.

    Returns:
        (str):   A Face string
    """
    face = randrange(0, len(arvonian_map["face"]))
    eye = randrange(0, len(arvonian_map["eyes"]))
    mouth = randrange(0, len(arvonian_map["mouth"]))
    crown = None
    collar = None

    if randrange(0,10) > 5:
        crown = randrange(0, len(arvonian_map["crown"]))
    if randrange(0,10) > 5:
        collar = randrange(0, len(arvonian_map["collar"]))
    return arvonian(face, eye, mouth, crown, collar)


ximni_map = {
    "face": [(0,0)],
    "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
    "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
    "horns": [(0,6), (1,0),(2,0), (3,0),(4,0)],
    "mask": [(1,1), (1,2),(1,3)], 
    "collar": [(5,0), (6,0)], 
}


def ximni(face_id, eye_id, mouth_id, horns_id, mask_id, collar_id):
    """ 
    Create an ximni face

    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        horns_id (int | None): The index of the horns 0-4 or None
        mask_id (int | None): The index of the mask 0-4 or None
        collar_id (int | None): The index of the collar 0 or None
    
    Returns:
        (str):   A Face string
    """
    face = ximni_map["face"][face_id]
    eye = ximni_map["eyes"][eye_id]
    mouth = ximni_map["mouth"][mouth_id]
    
    ret =  f"zim #fff {face[0]} {face[1]};zim #fff {eye[0]} {eye[1]};zim #fff {mouth[0]} {mouth[1]};"
    if horns_id is not None:
        horns = ximni_map["horns"][horns_id]
        ret += f"zim #fff {horns[0]} {horns[1]};"
    if collar_id  is not None:
        collar = ximni_map["collar"][collar_id]
        ret += f"zim #fff {collar[0]} {collar[1]};"

    if mask_id  is not None:
        mask = ximni_map["mask"][mask_id]
        ret += f"zim #fff {mask[0]} {mask[1]};"
    return ret

def random_ximni():
    """ 
    Create a random ximni face.
    
    Returns:
        (str):   A Face string
    """
    face = randrange(0, len(ximni_map["face"]))
    eye = randrange(0, len(ximni_map["eyes"]))
    mouth = randrange(0, len(ximni_map["mouth"]))
    horns = None
    mask = None
    collar = None
    if randrange(0,10) > 5:
        horns = randrange(0, len(ximni_map["horns"]))
    if randrange(0,10) > 5:
        mask = randrange(0, len(ximni_map["mask"]))
    if randrange(0,10) > 7:
        collar = randrange(0, len(ximni_map["collar"]))
    return ximni(face, eye, mouth, horns, mask, collar)

kralien_map = {
    "face": [(0,0)],
    "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
    "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
    "scalp": [(0,6), (1,0),(2,0), (3,0),(4,0)],
    "extra": [(5,0), (6,0),(1,1), (1,2),(1,3)], 
}


def kralien(face_id, eye_id, mouth_id, scalp_id, extra_id):
    """ 
    Create an kralien face.

    Args:
        face_id (int): The index of the face 0
        eye_id (int): The index of the eyes 0-4
        mouth_id (int): The index of the mouth 0-4
        scalp_id (int | None): The index of the scalp 0-4 or None
        extra_id (int | None): The index of the extra 0-4 or None
    
    Returns:
        (str):   A Face string
    """
    face = kralien_map["face"][face_id]
    eye = kralien_map["eyes"][eye_id]
    mouth = kralien_map["mouth"][mouth_id]
    
    ret =  f"kra #fff {face[0]} {face[1]};kra #fff {eye[0]} {eye[1]};kra #fff {mouth[0]} {mouth[1]};"
    if scalp_id is not None:
        scalp = kralien_map["scalp"][scalp_id]
        ret += f"kra #fff {scalp[0]} {scalp[1]};"

    if extra_id  is not None:
        extra = kralien_map["extra"][extra_id]
        ret += f"kra #fff {extra[0]} {extra[1]};"
    return ret

def random_kralien():
    """ 
    Create a random kralien face.
    
    Returns:
        (str):   A Face string
    """
    face = randrange(0, len(kralien_map["face"]))
    eye = randrange(0, len(kralien_map["eyes"]))
    mouth = randrange(0, len(kralien_map["mouth"]))
    scalp = None
    extra = None

    if randrange(0,10) > 5:
        scalp = randrange(0, len(kralien_map["scalp"]))
    if randrange(0,10) > 5:
        extra = randrange(0, len(kralien_map["extra"]))
    return kralien(face, eye, mouth, scalp, extra)

terran_map = {
    # add 3 to first value for female
    "face": [(0,0)], 
    # add 3 to first value for female
    "eyes": [   (1,0), (2,0), (0,1),(1,1), (2,1), (0,2)],
    # add 3 to first value for female
    "mouth": [(1,2), (2,2), (0,3),(1,3), (2,3), (0,4)],
    # add 3 to first value for female
    "shirt": [(1,4), (2,4), (0,5), (1,5), (2,5), (0,6), (1,6), (2,6), (0,7), (1,7)],

    "hair": [(8,0), (6,1),(6,2), (6,3),(7,3),(7,4),(8,4), (6,5), (7,5), (8,5)],
    "longhair": [(6,0), (7,0),(7,1), (8,1),(7,2), (8,2), (8,3),(6,4)],
    "facial": [(9,0), (10,0),(11,0), 
               (9,1), (10,1),(11,1),
               (9,2), (10,2),(11,2),
               (9,3), (10,3)],
    "extra": [(13,1),(14,1), (12,2),(13,2), (14,2), (12,3)], 
    "hat": [(12,0), (13,0), (14,0), (12,1)], 

    
}

# get second value then add 3 to first value for female
terran_uniform = [ 
    (0,0), (0,6), (0,8), # reds
    (1,2), (1,5),        # greens
    (2, 1), (2,3),       # blues
    (3,7), (3,8), (3,9)  # blacks
    ]

# https://huebliss.com/skin-color-code/
# http://starfleetlogistics.shoutwiki.com/wiki/Species_ID_color_palette
# https://www.schemecolor.com/thanos-skin-tones.php
skin_tones = [
    "ffffff", #no change
    "ffcd94", #c1
    "fff0bd", #c2
    "eac086", #c3
    "ffe39f", #c4
    "ffab60", #c4
    "f2efee", #fair1
    "efe6dd", #fair2
    "ebd3c5", #fair3
    "d7b6a5", #fair4
    "9f7967", #fair5
    "70361c", #dark1
    "714937", #dark2
    "65371e", #dark3
    "492816", #dark4
    "321b0f", #dark5
    "bf9169", #indian1
    "8c644d", #indian2
    "593123", #indian3
    "964b00",  #green1 (ursala green)
    "6d8b01", #green2
    "009973", #green3
    "69e1c3", #green4
    "0095b3",  #blue1
    "00c3e6",  #blue2
    "95e3f3",  #blue3
    "573d76", #thanos1
    "6e5e8e", #thanos2
    "acb057", #thanos3
    "c0caff", #thanos4
    "333d70", #thanos5

]

hair_tones = [
    "ffffff", #no change
    "FAF0BE", #blonde
    "3D2314", #Brown - Biste
    "CC9966", #BrownYellow
    "97502d", #chestnut
    "1E1a33", #dark Gunmetal
    "7C0A02", #red
    "968b00", #BrownGreen
    "964b00",  #green
    "3d0463", #Deep Violet
    "3d0463", #Indigo
    "FA01B3", #fashion Fuchsia

]

def probably(chance):
    """
    Will compare a float with a random float between 0 and 1. If the provided number is larger than the random number, will return True.
    Args:
        chance (float): A float between 0 and 1.
    """
    return uniform(0, 1) < chance

def terran(face_id, eye_id, mouth_id, hair_id, longhair_id, facial_id, extra_id, uniform_id, skintone, hairtone):
    """ 
    Create a terran face.

    Args:
        face_id (int | None): The index of the face 0=male, 1=female, 2=fluid_male, 3=fluid_female
        eye_id (int | None): The index of the eyes 0-9
        mouth_id (int): The index of the mouth 0-9
        hair_id (int | None): The index of the hair 0-9 or None
        longhair_id (int | None): The index of the hair 0-7 or None
        facial_id (int | None): The index of the hair 0-11 or None
        extra_id (int | None): The index of the extra 0-5 or None
        uniform_id (int | None): The index of the uniform 0 or None. None = civilian
        skintone (int | str | None): The index of the skintone 0-??, string = color string or None. 
        hairtone (int | str | None): The index of the skintone 0-??, string = color string  or None.
    
    Returns:
        (str):   A Face string
    """

    is_fluid = False 
    # if not fluid mouth and eyes must match gender 
    # face and uniform need to match
    if face_id>=2: 
        #fluid
        face_id = face_id % 2
        is_fluid = True

    face = terran_map["face"][0]
    if face_id == 1:
        face = (face[0] + 3, face[1])


    eye_count =len(terran_map["eyes"])
    
    female_eyes =  (eye_id > eye_count)
    if not is_fluid and face_id==1:
        female_eyes = True

    eye = terran_map["eyes"][eye_id%eye_count]

    # offset cell
    if female_eyes:
        eye = (eye[0]+ 3, eye[1])
    
    mouth_count =len(terran_map["mouth"])
    female_mouth = mouth_id > mouth_count
    if not is_fluid and face_id==1:
        female_mouth = True

    mouth = terran_map["mouth"][mouth_id%mouth_count]
    # offset cell
    if female_mouth:
        mouth = (mouth[0] + 3, mouth[1])

    if skintone == None:
        skintone = "fff"
    elif not isinstance(skintone, str):
        skintone = skin_tones[skintone]

    
    if hairtone == None:
        hairtone = "fff"
    elif not isinstance(hairtone, str):
        hairtone = hair_tones[hairtone]

    ret = ""
    if longhair_id is not None:
        longhair = terran_map["longhair"][longhair_id]
        ret += f"ter #{hairtone} {longhair[0]} {longhair[1]} 6  -2;"

    ret +=  f"ter #{skintone} {face[0]} {face[1]};ter #{skintone} {eye[0]} {eye[1]};ter #{skintone} {mouth[0]} {mouth[1]};"
    if hair_id is not None:
        hair = terran_map["hair"][hair_id]
        ret += f"ter #{hairtone} {hair[0]} {hair[1]} 6 -2;"


    # Civilian
    if uniform_id == None:
        shirt = (2,5)
        hat = None
    else:
        uniform = terran_uniform[uniform_id]
        shirt = terran_map["shirt"][uniform[1]]
        hat = terran_map["hat"][uniform[0]]

    
    if hat:
        ret += f"ter #fff {hat[0]} {hat[1]} 14 -2;"
    
    if face_id == 1:
        shirt = (shirt[0]+3, shirt[1])

    ret += f"ter #fff {shirt[0]} {shirt[1]};"

    if facial_id is not None:
        facial = terran_map["facial"][facial_id]
        ret += f"ter #{hairtone} {facial[0]} {facial[1]} 12 4;"


    if extra_id  is not None:
        extra = terran_map["extra"][extra_id]
        ret += f"ter #fff {extra[0]} {extra[1]} 20 4;"
    return ret


def random_terran(face=None, civilian=None):
    """ 
    Create a random terran face.

    Args:
        face (int | None): The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
        civilian (boolean | None): The force this to be a civilian=True, For non-civilian=False or None= random

    Returns:    
        (str):   A Face string
    """
    is_fluid = False
    if face is None:
        fluid = probably(3/10)
    
        if fluid: # 3 out of 10
            face = 2
            is_fluid = True
        else:
            face = fluid % 2
    else:
        is_fluid = face >=2
        face = face % 2



    if is_fluid:
        eye = randrange(0, len(terran_map["eyes"])*2)
    else:
        eye = randrange(0, len(terran_map["eyes"]))

    if is_fluid:
        mouth = randrange(0, len(terran_map["mouth"])*2)
    else: 
        mouth = randrange(0, len(terran_map["mouth"]))

    hair = None
    extra = None
    longhair = None
    if is_fluid or face==1:
        if probably(95/100):
            hair = randrange(0, len(terran_map["hair"]))
    else:
        if probably(75/100):
            hair = randrange(0, len(terran_map["hair"]))

    facial = None
    # male more chance of facial hair
    if is_fluid or face==1:
        if probably(5/100):
            facial = randrange(0, len(terran_map["facial"]))
    else:
        if probably(65/100):
            facial = randrange(0, len(terran_map["facial"]))

    # if female 80% chance of long hair
    # male 20%
    if is_fluid or face==1:
        if probably(8/10):
            longhair = randrange(0, len(terran_map["longhair"]))
    else:
        if probably(2/10):
            longhair = randrange(0, len(terran_map["longhair"]))

    # 35% chance
    if probably(35/100):
        extra = randrange(0, len(terran_map["extra"]))

    if civilian ==True:
        uniform = None
    elif civilian == False:
        uniform = randrange(0, len(terran_uniform))
    else:
        if probably(2/10):
            uniform = None
        else:
            uniform = randrange(0, len(terran_uniform))

    skintone = randrange(0, len(skin_tones))
    hairtone = randrange(0, len(hair_tones))

    return terran(face, eye, mouth, hair, longhair, facial, extra, uniform, skintone, hairtone)


def random_terran_male(civilian=None):
    """ 
    Create a random terran male face.

    Args:
        civilian (boolean, optional): The force this to be a civilian=True, For non-civilian=False, or None= random. Default is None.
    
    Returns:
        (str):   A Face string
    """
    return random_terran(0, civilian)

def random_terran_female(civilian=None):
    """ 
    Create a random terran female face.

    Args:    
        civilian (boolean, optional): The force this to be a civilian=True, For non-civilian=False or None= random. Default is None.
    
    Returns:
        (str):   A Face string
    """
    return random_terran(1, civilian)

def random_terran_fluid(civilian=None):
    """ 
    Create a random fluid terran face i.e. may have male or female features.

    Args:
        civilian (boolean, optional): The force this to be a civilian=True, For non-civilian=False or None= random. Default is None.
    
    Returns:
        (str):   A Face string
    """
    return random_terran(randrange(0, 10)%2+2, civilian)


_FACE_KEYWORDS = {
    "terran": random_terran, "male": random_terran_male, "terran_male": random_terran_male,
    "female": random_terran_female, "terran_female": random_terran_female,
    "fluid": random_terran_fluid, "terran_fluid": random_terran_fluid,
}


def face_resolve(spec):
    """Resolve a declarative face spec to a face string. A KEYWORD (terran / male / female /
    fluid) -> a fresh random face of that kind; a literal face string -> itself unchanged;
    None/empty -> a random terran. Lets AMD/data author a face as a simple word instead of a
    raw face string. (Promoted from Open Universe's lifeform_face.)"""
    if not spec:
        return random_terran()
    gen = _FACE_KEYWORDS.get(str(spec).strip().lower())
    return gen() if gen is not None else spec


# --- Mod-registered face sheets and races -------------------------------------
# The six stock races are built up layer by layer from their atlas (eyes, mouth,
# hat...). A mod atlas does not have to work that way: the TNG sheets are one whole
# bust per cell, so their "builder" is just a ready-made face string. Both kinds can
# live here at once because a face string is a face string either way.
#
# Registration is what makes `random_face("klingon")` reach a mod race at all. Before
# this the race list was a hard-coded match statement - hence the TODO that used to
# sit in random_face.
#
# Both dicts are per-mission module state, so they are cleared by
# reset_mission_state() and declared to the reset ledger in handlerhooks. An
# unregistered container is invisible to the restart soak, and a face registry that
# survived a reload would hand mission 2 the face strings of mission 1 pointing at an
# atlas alias that is no longer registered.
_MOD_SHEETS: dict = {}          # alias -> {"cols": int, "rows": int}
_MOD_RACES: dict = {}           # race  -> {"any": [...], "roles": {role: [...]}, "in_random": bool}


def face_register_sheet(alias, cols=8, rows=8):
    """Declare a mod atlas alias and its cell grid.

    `alias` is the short name in a face string ("tng1") and must match the name the
    engine reads from data/graphics/allFaceFiles.txt - the library cannot write that
    file, so registering here does NOT make the sheet loadable, it only teaches the
    library and the browser compositor how to read cells out of it.
    """
    _MOD_SHEETS[str(alias)] = {"cols": int(cols), "rows": int(rows)}


def face_sheet_grid(alias):
    """(cols, rows) for an alias. Stock geometry for the six built-ins: the Terran
    sheet is 15 wide, every other sheet is 8."""
    m = _MOD_SHEETS.get(str(alias))
    if m:
        return m["cols"], m["rows"]
    if alias in _FACE_ALIAS_TO_RACE:
        return (15 if alias == "ter" else 8), 8
    return None


def face_registered_sheets():
    """{alias: {"cols","rows"}} - what the mock compositor and AMD renderer need."""
    return dict(_MOD_SHEETS)


def face_register_race(race, faces, roles=None, in_random=True):
    """Declare ready-made face strings for a race so random_face(race) can use them.

    Args:
        race:      race name as scripts will ask for it, case-insensitive.
        faces:     list of face strings - the pool used when no role is asked for.
        roles:     optional {role: [face strings]} for role-filtered picks, e.g.
                   random_face("klingon", "command").
        in_random: whether a bare random_face()/random_face("random") may return this
                   race. A mod that only wants its faces when asked for by name
                   passes False.
    """
    key = str(race).lower()
    e = _MOD_RACES.setdefault(key, {"any": [], "roles": {}, "in_random": bool(in_random)})
    e["any"].extend(faces or [])
    e["in_random"] = bool(in_random)
    for role, pool in (roles or {}).items():
        e["roles"].setdefault(str(role).lower(), []).extend(pool or [])


def face_registered_races(in_random_only=False):
    if in_random_only:
        return [r for r, e in _MOD_RACES.items() if e["in_random"] and e["any"]]
    return [r for r, e in _MOD_RACES.items() if e["any"]]


def face_random_registered(race, role=None):
    """A random registered face for a race, or None if the race was never registered.

    A role with no faces falls back to the race pool rather than returning nothing -
    asking for a Breen science officer should still get a Breen.
    """
    e = _MOD_RACES.get(str(race).lower())
    if not e:
        return None
    pool = e["roles"].get(str(role).lower()) if role else None
    if not pool:
        pool = e["any"]
    return choice(pool) if pool else None


def face_overlay(face_string, *overlays):
    """Stack overlay layers onto an existing face string.

    This is the whole point of keeping implants as separate cells: any face can be
    assimilated at runtime, including one that was never drawn with implants. Layers
    composite lowest-first, so overlays go last.

        face_overlay(random_face("terran"), "tng6 #fff 2 1", "tng6 #fff 5 3")

    Empty/None overlays are skipped so a caller can pass an optional one straight in.
    """
    parts = [p.strip() for p in str(face_string or "").split(";") if p.strip()]
    for o in overlays:
        parts.extend(p.strip() for p in str(o or "").split(";") if p.strip())
    return ";".join(parts) + ";" if parts else ""


def face_mod_reset():
    """Drop every mod registration. Called by reset_mission_state()."""
    _MOD_SHEETS.clear()
    _MOD_RACES.clear()


def face_mod_size():
    """Reset-ledger probe: how much mod registration is currently held."""
    return len(_MOD_SHEETS) + len(_MOD_RACES)


def face_race_mapped(race):
    """Re-point a race name at the face race its portraits should come from. ART ONLY.

    The third of the mod re-skin maps (`RACE_ART` and `ART_KEYS` are the other two, in
    procedural/ship_data.py). Returns `race` unchanged unless a mission or profile set
    ``RACE_FACES``, so stock behavior is untouched.

    WHY FACES NEED THEIR OWN MAP AND CANNOT REUSE `RACE_ART`: face races are SPECIES,
    ship-data sides are FACTIONS, and they do not spell the same. A mod's Federation ships
    are crewed by `human`, not by `federation`; a faction can field hulls and register no
    portraits at all (Cosmos-TNG-Mod has Breen ships and no Breen faces). Feeding a faction
    name to random_face() therefore matches nothing and falls back to terran - the exact
    "NPC comms faces are still stock" symptom this exists to fix.

    Applied INSIDE random_face() rather than at its call sites, because a mission has many
    (LM alone has four for NPCs, one of them in a fleet spawner) and a missed one looks
    identical to the bug. A name with no entry passes through untouched, so player faces
    already named by species (`human`) are unaffected.
    """
    if not race:
        return race
    try:
        from .procedural.settings import settings_get_defaults
        raw = settings_get_defaults().get("RACE_FACES") or {}
        if not raw:
            # An explicit setting wins; otherwise the active THEATER supplies it, so the
            # roster, the hull art and the crew faces all come from one declaration and
            # cannot drift apart.
            from .procedural.amd_theater import theater_faces
            raw = theater_faces()
    except Exception:
        return race
    if not isinstance(raw, dict):
        return race
    mapped = raw.get(str(race).strip().lower())
    if not mapped:
        for k, v in raw.items():
            if str(k).strip().lower() == str(race).strip().lower():
                mapped = v
                break
    return mapped if mapped else race


def random_face(race=None, role=None):
    """
    Returns a random face for the specified race.

    Mod races registered with face_register_race() are checked FIRST, so an add-on
    can supply "klingon" or "cardassian" without this function knowing they exist.
    That is what the TODO which used to sit here was asking for.

    Args:
        race (str): The Race Terran, Torgoth etc, or a registered mod race.
        role (str): optional role filter for registered races ("command", "ops"...).
                    Ignored by the six stock races, which have no role concept.

    Returns:
        str: The Face String
    """
    # Mod re-skin map first - identity unless RACE_FACES is set. See face_race_mapped.
    race = face_race_mapped(race)
    if race is not None and str(race).lower() != "random":
        s = face_random_registered(race, role)
        if s is not None:
            return s
    if race is None or race.lower() == "random":
        pool = ["kralien", "arvonian", "skaraan", "torgoth", "ximni", "terran", "civilian"]
        pool += face_registered_races(in_random_only=True)
        race = choice(pool)
        s = face_random_registered(race, role)
        if s is not None:
            return s
    race = race.lower()    
    match race:
        case "terran":
            return random_terran()
        case "terran_male":
            return random_terran_male()
        case "terran_female":
            return random_terran_female()
        case "terran_fluid":
            return random_terran_fluid()
        case "terran_civilian":
            return random_terran_fluid()
        case "torgoth":
            return random_torgoth()
        case "skaraan":
            return random_skaraan()
        case "ximni":
            return random_ximni()
        case "arvonian":
            return random_arvonian()
        case "kralien":
            return random_kralien()
    return random_terran()


# --- Face builder recipe (ported from modding_tools char_editor) --------------
# Per race: the ordered features a builder shows one control for (label, max index,
# optional). `build_face` turns chosen indices into a face string. Living here (in
# sbs_utils) keeps the recipe available without the modding_tools mission.
FACE_FEATURES = {
    "terran": [
        {"label": "Body", "max": 1}, {"label": "Eyes", "max": 9}, {"label": "Mouth", "max": 9},
        {"label": "Hair", "max": 4, "optional": True}, {"label": "Long Hair", "max": 7, "optional": True},
        {"label": "Facial Hair", "max": 4, "optional": True}, {"label": "Extra", "max": 4, "optional": True},
        {"label": "Uniform", "max": 9, "optional": True},
        {"label": "Skin Tone", "max": len(skin_tones) - 1}, {"label": "Hair Tone", "max": len(hair_tones) - 1},
    ],
    "skaraan": [
        {"label": "Eyes", "max": 4}, {"label": "Mouth", "max": 4},
        {"label": "Horn", "max": 4, "optional": True}, {"label": "Hat", "max": 4, "optional": True},
    ],
    "torgoth": [
        {"label": "Eyes", "max": 4}, {"label": "Mouth", "max": 4},
        {"label": "Hair", "max": 4, "optional": True}, {"label": "Extra", "max": 3, "optional": True},
        {"label": "Hat", "max": 0, "optional": True},
    ],
    "arvonian": [
        {"label": "Eyes", "max": 4}, {"label": "Mouth", "max": 4},
        {"label": "Crown", "max": 4, "optional": True}, {"label": "Jewels", "max": 4, "optional": True},
    ],
    "kralien": [
        {"label": "Eyes", "max": 4}, {"label": "Mouth", "max": 4},
        {"label": "Scalp", "max": 4, "optional": True}, {"label": "Extra", "max": 4, "optional": True},
    ],
    "ximni": [
        {"label": "Eyes", "max": 4}, {"label": "Mouth", "max": 4},
        {"label": "Horns", "max": 4, "optional": True}, {"label": "Mask", "max": 2, "optional": True},
        {"label": "Tattoo", "max": 1, "optional": True},
    ],
}

_FACE_BUILDERS = {
    "terran": terran, "skaraan": skaraan, "torgoth": torgoth,
    "arvonian": arvonian, "kralien": kralien, "ximni": ximni,
}


def build_face(race, values, enables=None):
    """Build a face string from per-feature indices in FACE_FEATURES order.

    `values[i]` is the chosen index for feature i; `enables[i]` False sets an
    (optional) feature to None. Terran maps 1:1 to terran(); other races prepend
    face_id 0 (the slot their builders expect). Returns '' for an unknown race.
    """
    race = str(race).lower()
    fn = _FACE_BUILDERS.get(race)
    if fn is None:
        return ""
    vals = list(values)
    if enables is None:
        enables = [True] * len(vals)
    args = [(v if (i < len(enables) and enables[i]) else None) for i, v in enumerate(vals)]
    if race != "terran":
        args = [0] + args
    return fn(*args)


# Inverse of build_face — recover per-feature indices from a face string so an
# editor can seed its sliders from an existing face instead of starting at
# defaults. FACE_FEATURES order -> the *_map key each feature came from.
_FACE_ALIAS_TO_RACE = {
    "ter": "terran", "tor": "torgoth", "ska": "skaraan",
    "kra": "kralien", "zim": "ximni", "arv": "arvonian",
}
_FACE_FEATURE_KEYS = {
    "skaraan":  ["eyes", "mouth", "horns", "hat"],
    "torgoth":  ["eyes", "mouth", "hair", "extra", "hat"],
    "arvonian": ["eyes", "mouth", "crown", "collar"],
    "kralien":  ["eyes", "mouth", "scalp", "extra"],
    "ximni":    ["eyes", "mouth", "horns", "mask", "collar"],
}
_FACE_MAPS = {
    "skaraan": skaraan_map, "torgoth": torgoth_map, "arvonian": arvonian_map,
    "kralien": kralien_map, "ximni": ximni_map,
}


def _parse_face_layers(face_string):
    layers = []
    for seg in (face_string or "").split(";"):
        p = seg.split()
        if len(p) < 4:
            continue
        try:
            layers.append({
                "alias": p[0], "color": p[1].lstrip("#").lower(),
                "col": int(p[2]), "row": int(p[3]),
                "ox": int(p[4]) if len(p) > 4 else 0,
                "oy": int(p[5]) if len(p) > 5 else 0,
            })
        except ValueError:
            continue
    return layers


def _tone_index(color, tones):
    c = (color or "").lower()
    if c in ("fff", "ffffff"):
        return 0
    for i, t in enumerate(tones):
        if t.lower() == c:
            return i
    return 0


def _parse_face_generic(race, feats, layers):
    keys = _FACE_FEATURE_KEYS[race]
    fmap = _FACE_MAPS[race]
    values = [0] * len(feats)
    # Non-optional features are always on; optionals start off until a layer hits.
    enables = [not f.get("optional", False) for f in feats]
    lookup = {}
    for fi, key in enumerate(keys):
        for ci, cell in enumerate(fmap[key]):
            lookup.setdefault((cell[0], cell[1]), (fi, ci))
    for L in layers:
        pos = (L["col"], L["row"])
        if pos == (0, 0):   # base face
            continue
        hit = lookup.get(pos)
        if hit is None:
            continue
        fi, ci = hit
        values[fi] = ci
        enables[fi] = True
    return {"race": race, "values": values, "enables": enables}


def _parse_face_terran(feats, layers):
    tm = terran_map
    values = [0] * 10
    enables = [True] * 10
    for i in (3, 4, 5, 6, 7):    # Hair, Long Hair, Facial Hair, Extra, Uniform
        enables[i] = False

    # Gender from the base face layer (male col 0, female col 3).
    female = False
    for L in layers:
        if L["ox"] == 0 and L["oy"] == 0 and L["row"] == 0 and L["col"] in (0, 3):
            female = (L["col"] == 3)
            break
    values[0] = 1 if female else 0     # Body

    def unf(col):
        return col - 3 if (female and col >= 3) else col

    def find(key, col, row):
        try:
            return tm[key].index((col, row))
        except ValueError:
            return None

    def find_either(key, col, row):
        """A feature cell, whichever gender column it sits in.

        Eyes and mouth carry their own +3 female offset INDEPENDENTLY of the base face -
        that is exactly what a `fluid` face is - so the body's gender cannot be used to
        un-shift them. Reading them through `unf` alone missed every mismatched pair and
        left the value at 0, which is not a failure the caller can see: it is a real index,
        so the face came back with somebody else's eyes and mouth.
        """
        i = find(key, col, row)
        if i is None and col >= 3:
            i = find(key, col - 3, row)
        return i

    shirt_i = None
    hat_i = None
    for L in layers:
        col, row, ox, oy, color = L["col"], L["row"], L["ox"], L["oy"], L["color"]
        if (ox, oy) == (6, -2):                       # hair or long hair
            i = find("longhair", col, row)
            if i is not None:
                values[4] = i; enables[4] = True; values[9] = _tone_index(color, hair_tones)
            else:
                i = find("hair", col, row)
                if i is not None:
                    values[3] = i; enables[3] = True; values[9] = _tone_index(color, hair_tones)
            continue
        if (ox, oy) == (14, -2):                      # uniform hat
            hat_i = find("hat", col, row)
            continue
        if (ox, oy) == (12, 4):                       # facial hair
            i = find("facial", col, row)
            if i is not None:
                values[5] = i; enables[5] = True; values[9] = _tone_index(color, hair_tones)
            continue
        if (ox, oy) == (20, 4):                        # extra
            i = find("extra", col, row)
            if i is not None:
                values[6] = i; enables[6] = True
            continue
        # No offset: face / eyes / mouth / shirt (skintone-tinted, shirt is #fff).
        c = unf(col)
        if (c, row) == (0, 0):                         # face
            values[8] = _tone_index(color, skin_tones)
            continue
        i = find_either("eyes", col, row)
        if i is not None:
            values[1] = i; values[8] = _tone_index(color, skin_tones); continue
        i = find_either("mouth", col, row)
        if i is not None:
            values[2] = i; values[8] = _tone_index(color, skin_tones); continue
        i = find_either("shirt", col, row)
        if i is not None:
            shirt_i = i

    # Uniform: a hat + a non-civilian shirt map back to a terran_uniform entry.
    civilian_shirt = tm["shirt"].index((2, 5))
    if hat_i is not None or (shirt_i is not None and shirt_i != civilian_shirt):
        try:
            values[7] = terran_uniform.index((hat_i if hat_i is not None else 0, shirt_i if shirt_i is not None else 0))
            enables[7] = True
        except ValueError:
            enables[7] = False
    return {"race": "terran", "values": values, "enables": enables}


def parse_face(face_string):
    """Recover (race, values, enables) from a face string — the inverse of
    build_face. Returns None if the string is not a recognized face. The result
    rebuilds to the same visual face via build_face (indices reproduce the same
    cells), so an editor can seed its controls from an existing face.
    """
    layers = _parse_face_layers(face_string)
    if not layers:
        return None
    race = _FACE_ALIAS_TO_RACE.get(layers[0]["alias"])
    if race is None or race not in FACE_FEATURES:
        return None
    feats = FACE_FEATURES[race]
    if race == "terran":
        return _parse_face_terran(feats, layers)
    return _parse_face_generic(race, feats, layers)



def get_face_from_data(race):
    """
    ### Deprecated in v1.1.0.
    Use random_race instead.

    Args:
        race (_type_): _description_

    Returns:
        _type_: _description_
    """
    print("get_face_from_data is depricated in v1.1.0 use random_race instead")
    return random_face(race)


#class Characters(StrEnum): # Python 3.11 will have StrEnum
class Characters:
    """
    A set of predefined faces
    """
    URSULA  = "ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;ter #fff 3 5;ter #964b00 8 4;"
