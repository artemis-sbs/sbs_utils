from enum import IntEnum
def arvonian (face_i, eye_i, mouth_i, crown_i, collar_i):
    """Create an arvonian face
    
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
    :rtype: string"""
def clear_face (ship_id):
    """Removes a face string for a specified ID
    
    :param ship_id: The id of the ship/object
    :type ship_id: int"""
def get_face (ship_id):
    """returns a face string for a specified ID
    
    :param ship_id: The id of the ship/object
    :type ship_id: int
    :return: A Face string
    :rtype: string"""
def kralien (face_i, eye_i, mouth_i, scalp_i, extra_i):
    """Create an kralien face
    
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
    :rtype: string"""
def probably (chance):
    ...
def random_arvonian ():
    """Create a random arvonian face
    
    :return: A Face string
    :rtype: string"""
def random_face (race):
    ...
def random_kralien ():
    """Create a random kralien face
    
    :return: A Face string
    :rtype: string"""
def random_skaraan ():
    """Create a random skaraan face
    
    :return: A Face string
    :rtype: string"""
def random_terran (face=None, civilian=None):
    """Create a random terran face
    
    :param face: The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
    :type face: int or None
    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string"""
def random_terran_female (civilian=None):
    """Create a random terran female face
    
    :param face: The index of the hair 0=male,1=female,2=fluid male, 3=fluid female or None= random
    :type face: int or None
    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string"""
def random_terran_fluid (civilian=None):
    """Create a random fluid terran face i.e. may have male or female features
    
    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string"""
def random_terran_male (civilian=None):
    """Create a random terran male face
    
    :param civilian: The force this to be a civilian=True, For non-civilian=False or None= random
    :type civilian: boolean or None
    
    :return: A Face string
    :rtype: string"""
def random_torgoth ():
    """Create a random torgoth face
    
    :return: A Face string
    :rtype: string"""
def random_ximni ():
    """Create a random ximni face
    
    :return: A Face string
    :rtype: string"""
def set_face (ship_id, face):
    """sets a face string for a specified ID
    
    :param ship_id: The id of the ship/object
    :type ship_id: int
    :param face: A Face string
    :type face: string"""
def skaraan (face_i, eye_i, mouth_i, horn_i, hat_i):
    """Create a skaraan face
    
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
    :rtype: string"""
def terran (face_i, eye_i, mouth_i, hair_i, longhair_i, facial_i, extra_i, uniform_i, skintone, hairtone):
    """Create an terran face
    
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
    :rtype: string"""
def torgoth (face_i, eye_i, mouth_i, hair_i, extra_i, hat_i):
    """Create a torgoth face
    
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
    :rtype: string"""
def ximni (face_i, eye_i, mouth_i, horns_i, mask_i, collar_i):
    """Create an ximni face
    
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
    :rtype: string"""
class Characters(object):
    """A set of predefined faces"""
