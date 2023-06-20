from random import randrange,uniform
import math
from enum import IntEnum

# ter Terran_Big-revised
#* tor Torgoth_Set
#* ska Skaraan_Set
#- kra Krailen_Set
#- zim Zimni_Set
#- arv Arvonian

faces_map = {}

def get_face(ship_id):
    """ returns a face string for a specified ID

    :param ship_id: The id of the ship/object
    :type ship_id: int
    :return: A Face string
    :rtype: string
    """
    return faces_map.get(ship_id, "")

def set_face(ship_id, face):
    """ sets a face string for a specified ID

    :param ship_id: The id of the ship/object
    :type ship_id: int
    :param face: A Face string
    :type face: string
    """
    faces_map[ship_id] = face

def clear_face(ship_id):
    """ Removes a face string for a specified ID

    :param ship_id: The id of the ship/object
    :type ship_id: int
    """
    faces_map.pop(ship_id, None)


skaraan_map = {
    "face": [(0,0)],
    "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
    "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
    "horns": [(0,6), (1,0),(2,0), (3,0),(4,0)],
    "hat": [(5,0), (6,0),(1,1), (1,2),(1,3)],
}


def skaraan(face_i, eye_i, mouth_i, horn_i, hat_i):
    """ Create a skaraan face

    :param face_i: The index of the face 0
    :type face_i: int
    :param eye_id: The index of the eyes 0-4
    :type eye_i: int
    :param mouth_id: The index of the mouth 0-4
    :type mouth_i: int
    :param horn_id: The index of the horn 0-4 or None
    :type horn_i: int or None
    :param hat_id: The index of the hat 0-4 or None
    :type hat_i: int or None
    :return: A Face string
    :rtype: string
    """
    face = skaraan_map["face"][face_i]
    eye = skaraan_map["eyes"][eye_i]
    mouth = skaraan_map["mouth"][mouth_i]

    ret =  f"ska #fff {face[0]} {face[1]};ska #fff {eye[0]} {eye[1]};ska #fff {mouth[0]} {mouth[1]};"
    if horn_i  is not None:
        horns = skaraan_map["horns"][horn_i]
        ret += f"ska #fff {horns[0]} {horns[1]};"
    if hat_i is not None:
        hat = skaraan_map["hat"][hat_i]
        ret += f"ska #fff {hat[0]} {hat[1]};"
    return ret

def random_skaraan():
    """ Create a random skaraan face

    :return: A Face string
    :rtype: string
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


def torgoth(face_i, eye_i, mouth_i, hair_i, extra_i, hat_i):
    """ Create a torgoth face

    :param face_i: The index of the face 0
    :type face_i: int
    :param eye_id: The index of the eyes 0-4
    :type eye_i: int
    :param mouth_id: The index of the mouth 0-4
    :type mouth_i: int
    :param hair_id: The index of the hair 0-4 or None
    :type hair_i: int or None
    :param extra_id: The index of the extra 0-4 or None
    :type extra_i: int or None
    :param hat_id: The index of the hat 0 or None
    :type hat_i: int or None
    
    :return: A Face string
    :rtype: string
    """
    face = torgoth_map["face"][face_i]
    eye = torgoth_map["eyes"][eye_i]
    mouth = torgoth_map["mouth"][mouth_i]
    
    ret =  f"tor #fff {face[0]} {face[1]};tor #fff {eye[0]} {eye[1]};tor #fff {mouth[0]} {mouth[1]};"
    if hair_i is not None:
        hair = torgoth_map["hair"][hair_i]
        ret += f"tor #fff {hair[0]} {hair[1]};"
    if hat_i  is not None:
        hat = torgoth_map["hat"][hat_i]
        ret += f"tor #fff {hat[0]} {hat[1]};"

    if extra_i  is not None:
        extra = torgoth_map["extra"][extra_i]
        ret += f"tor #fff {extra[0]} {extra[1]};"
    return ret

def random_torgoth():
    """ Create a random torgoth face
    
    :return: A Face string
    :rtype: string
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


def arvonian(face_i, eye_i, mouth_i, crown_i, collar_i):
    """ Create an arvonian face

    :param face_i: The index of the face 0
    :type face_i: int
    :param eye_id: The index of the eyes 0-4
    :type eye_i: int
    :param mouth_id: The index of the mouth 0-4
    :type mouth_i: int
    :param crown_id: The index of the crown 0-4 or None
    :type crown_i: int or None
    :param collar_id: The index of the collar 0-4 or None
    :type collar_i: int or None
    
    :return: A Face string
    :rtype: string
    """
    face = arvonian_map["face"][face_i]
    eye = arvonian_map["eyes"][eye_i]
    mouth = arvonian_map["mouth"][mouth_i]
    
    ret =  f"arv #fff {face[0]} {face[1]};arv #fff {eye[0]} {eye[1]};arv #fff {mouth[0]} {mouth[1]};"
    if crown_i is not None:
        crown = arvonian_map["crown"][crown_i]
        ret += f"arv #fff {crown[0]} {crown[1]};"

    if collar_i  is not None:
        collar = arvonian_map["collar"][collar_i]
        ret += f"arv #fff {collar[0]} {collar[1]};"
    return ret

def random_arvonian():
    """ Create a random arvonian face
    
    :return: A Face string
    :rtype: string
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


def ximni(face_i, eye_i, mouth_i, horns_i, mask_i, collar_i):
    """ Create an ximni face

    :param face_i: The index of the face 0
    :type face_i: int
    :param eye_id: The index of the eyes 0-4
    :type eye_i: int
    :param mouth_id: The index of the mouth 0-4
    :type mouth_i: int
    :param horns_id: The index of the horns 0-4 or None
    :type horns_i: int or None
    :param mask_id: The index of the mask 0-4 or None
    :type mask_i: int or None
    :param collar_id: The index of the collar 0 or None
    :type collar_i: int or None
    
    :return: A Face string
    :rtype: string
    """
    face = ximni_map["face"][face_i]
    eye = ximni_map["eyes"][eye_i]
    mouth = ximni_map["mouth"][mouth_i]
    
    ret =  f"zim #fff {face[0]} {face[1]};zim #fff {eye[0]} {eye[1]};zim #fff {mouth[0]} {mouth[1]};"
    if horns_i is not None:
        horns = ximni_map["horns"][horns_i]
        ret += f"zim #fff {horns[0]} {horns[1]};"
    if collar_i  is not None:
        collar = ximni_map["collar"][collar_i]
        ret += f"zim #fff {collar[0]} {collar[1]};"

    if mask_i  is not None:
        mask = ximni_map["mask"][mask_i]
        ret += f"zim #fff {mask[0]} {mask[1]};"
    return ret

def random_ximni():
    """ Create a random ximni face
    
    :return: A Face string
    :rtype: string
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


def kralien(face_i, eye_i, mouth_i, scalp_i, extra_i):
    """ Create an kralien face

    :param face_i: The index of the face 0
    :type face_i: int
    :param eye_id: The index of the eyes 0-4
    :type eye_i: int
    :param mouth_id: The index of the mouth 0-4
    :type mouth_i: int
    :param scalp_id: The index of the scalp 0-4 or None
    :type scalp_i: int or None
    :param extra_id: The index of the extra 0-4 or None
    :type extra_i: int or None
    
    :return: A Face string
    :rtype: string
    """
    face = kralien_map["face"][face_i]
    eye = kralien_map["eyes"][eye_i]
    mouth = kralien_map["mouth"][mouth_i]
    
    ret =  f"kra #fff {face[0]} {face[1]};kra #fff {eye[0]} {eye[1]};kra #fff {mouth[0]} {mouth[1]};"
    if scalp_i is not None:
        scalp = kralien_map["scalp"][scalp_i]
        ret += f"kra #fff {scalp[0]} {scalp[1]};"

    if extra_i  is not None:
        extra = kralien_map["extra"][extra_i]
        ret += f"kra #fff {extra[0]} {extra[1]};"
    return ret

def random_kralien():
    """ Create a random kralien face
    
    :return: A Face string
    :rtype: string
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
    return uniform(0, 1) < chance

def terran(face_i, eye_i, mouth_i, hair_i, longhair_i, facial_i, extra_i, uniform_i, skintone, hairtone):
    """ Create an terran face

    :param face_i: The index of the face 0=male, 1=female, 2=fluid_male, 3=fluid_female
    :type face_i: int or None 
    :param eye_i: The index of the eyes 0-9
    :type eye_i: int or None
    :param mouth_i: The index of the mouth 0-9
    :type mouth_i: int
    :param hair_i: The index of the hair 0-9 or None
    :type hair_i: int or None
    :param longhair_i: The index of the hair 0-7 or None
    :type longhair_i: int or None
    :param facial_i: The index of the hair 0-11 or None
    :type facial_i: int or None
    :param extra_i: The index of the extra 0-5 or None
    :type extra_i: int or None
    :param uniform_i: The index of the uniform 0 or None. None = civilian
    :type uniform_i: int or None
    :param skintone_i: The index of the skintone 0-??, string = color string or None. 
    :type skintone_i: int, str or None
    :param hairtone_i: The index of the skintone 0-??, string = color string  or None.
    :type hairtone_i: int, str or None
    
    :return: A Face string
    :rtype: string
    """

    is_fluid = False 
    # if not fluid mouth and eyes must match gender 
    # face and uniform need to match
    if face_i>=2: 
        #fluid
        face_i = face_i % 2
        is_fluid = True

    face = terran_map["face"][0]
    if face_i == 1:
        face = (face[0] + 3, face[1])


    eye_count =len(terran_map["eyes"])
    
    female_eyes =  (eye_i > eye_count)
    if not is_fluid and face_i==1:
        female_eyes = True

    eye = terran_map["eyes"][eye_i%eye_count]

    # offset cell
    if female_eyes:
        eye = (eye[0]+ 3, eye[1])
    
    mouth_count =len(terran_map["mouth"])
    female_mouth = mouth_i > mouth_count
    if not is_fluid and face_i==1:
        female_mouth = True

    mouth = terran_map["mouth"][mouth_i%mouth_count]
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
    if longhair_i is not None:
        longhair = terran_map["longhair"][longhair_i]
        ret += f"ter #{hairtone} {longhair[0]} {longhair[1]} 6  -2;"

    ret +=  f"ter #{skintone} {face[0]} {face[1]};ter #{skintone} {eye[0]} {eye[1]};ter #{skintone} {mouth[0]} {mouth[1]};"
    if hair_i is not None:
        hair = terran_map["hair"][hair_i]
        ret += f"ter #{hairtone} {hair[0]} {hair[1]} 6 -2;"


    # Civilian
    if uniform_i == None:
        shirt = (2,5)
        hat = None
    else:
        uniform = terran_uniform[uniform_i]
        shirt = terran_map["shirt"][uniform[1]]
        hat = terran_map["hat"][uniform[0]]

    
    if hat:
        ret += f"ter #fff {hat[0]} {hat[1]} 14 -2;"
    
    if face_i == 1:
        shirt = (shirt[0]+3, shirt[1])

    ret += f"ter #fff {shirt[0]} {shirt[1]};"

    if facial_i is not None:
        facial = terran_map["facial"][facial_i]
        ret += f"ter #{hairtone} {facial[0]} {facial[1]} 12 4;"


    if extra_i  is not None:
        extra = terran_map["extra"][extra_i]
        ret += f"ter #fff {extra[0]} {extra[1]} 20 4;"
    return ret


def random_terran(face=None, civilian=None):
    """ Create a random terran face

    :param face: The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
    :type face: int or None
    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string
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
    """ Create a random terran male face

    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string
    """
    return random_terran(0, civilian)

def random_terran_female(civilian=None):
    """ Create a random terran female face

    :param face: The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
    :type face: int or None
    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string
    """
    return random_terran(1, civilian)

def random_terran_fluid(civilian=None):
    """ Create a random fluid terran face i.e. may have male or female features

    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string
    """
    return random_terran(randrange(0, 10)%2+2, civilian)


def random_face(race):
    if "kralien" in race:
        return random_kralien()
    if "arvonian" in race:
        return random_arvonian()
    if "skaraan" in race:
        return random_skaraan()
    if "torgoth" in race:
        return random_torgoth()
    if "ximni" in race:
        return random_ximni()
    elif "xim" in race:
        return random_ximni()
    return random_terran()

#class Characters(StrEnum): # Python 3.11 will have StrEnum
class Characters:
    """
    A set of predefined faces
    """
    URSULA  = "ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;ter #fff 3 5;ter #964b00 8 4;"
