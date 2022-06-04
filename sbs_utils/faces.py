from random import randrange

class Faces:
    skaraan_map = {
        "face": [(0,0)],
        "eyes": [(0,1), (0,2), (0,3),(0,4), (0,5)],
        "mouth": [(1,4), (1,5), (1,6),(2,1), (3,1)],
        "horns": [(0,6), (1,0),(2,0), (3,0),(4,0)],
        "hat": [(5,0), (6,0),(1,1), (1,2),(1,3)],
    }
    def random_skaraan():
        return Faces.random_face('ska', Faces.skaraan_map)

    def skaraan(face_i, eye_i, mouth_i, horn_i, hat_i):
        return Faces.random_face('ska', Faces.skaraan_map, face_i, eye_i, mouth_i, horn_i, hat_i)

    def random_face(tex, face_map):
        face = randrange(0, len(face_map["face"]))
        eye = randrange(0, len(face_map["eyes"]))
        mouth = randrange(0, len(face_map["mouth"]))
        horns = None
        hat = None
        if randrange(0,10) > 5:
            horns = randrange(0, len(face_map["horns"]))
        if randrange(0,10) > 5:
            hat = randrange(0, len(face_map["hat"]))
        return Faces.face(tex, face_map, face, eye, mouth, horns, hat)

    def face(tex, face_map, face_i, eye_i, mouth_i, horn_i, hat_i):
        face = face_map["face"][face_i]
        eye = face_map["eyes"][eye_i]
        mouth = face_map["mouth"][mouth_i]

        ret =  f"{tex} #fff {face[0]} {face[1]};{tex} #fff {eye[0]} {eye[1]};{tex} #fff {mouth[0]} {mouth[1]};"
        if horn_i:
            horns = face_map["horns"][horn_i]
            ret += f"{tex} #fff {horns[0]} {horns[1]};"
        if hat_i:
            hat = face_map["hat"][hat_i]
            ret += f"{tex} #fff {hat[0]} {hat[1]};"
        return ret