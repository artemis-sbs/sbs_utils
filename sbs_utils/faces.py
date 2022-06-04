from random import randrange



URSULA  = "ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;ter #fff 3 5;ter #964b00 8 4;"

"""
ter Terran_Big-revised
tor Torgoth_Set
ska Skaraan_Set
kra Krailen_Set
zim Zimni_Set
arv Arvonian
"""

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
    """ Create a skaraan face

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
