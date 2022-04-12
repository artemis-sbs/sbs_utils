debug = True

def mark_loc(sim, name: str, x:float, y: float, z: float, color:str):
    if debug:
        return sim.add_navpoint(x, y,z, name, color)
    return None

def log(s: str):
    if debug:
        print(s)