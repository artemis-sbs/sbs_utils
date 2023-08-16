from sbs_utils.scatter import box
from sbs_utils.scattervec import box as boxv
from sbs_utils.vec import Vec3

for v in box(10,0,0,0, 5000,5000,5000, True):
    print(f"{v.x}, {v.y}, {v.z}")

v1 = Vec3(0,0,0)
v2 = Vec3(5000,5000,5000)
r = Vec3(45,45,45)
for v in boxv(10, v1, v2, True):
    print(f"{v.x}, {v.y}, {v.z}")

for v in boxv(5, v1, v2, True, r):
    print(f"{v.x}, {v.y}, {v.z}")