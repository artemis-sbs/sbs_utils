from sbs_utils.scatter import box_fill




for v in box_fill(10,10,10,0,0,0, 5000,5000,5000, True):
    print(f"{v.x}, {v.y}, {v.z}")

