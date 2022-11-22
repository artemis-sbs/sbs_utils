

# https://www.redblobgames.com/grids/hexagons/#hex-to-pixel

class HexCell:
    def __init__(self, x,y,z, race):
        self.x = x
        self.y = y
        self.z = z
        self.race = race


class Grid:
    def _init__(self, abs_size):
        self.grid=[]
        self.size = (abs_size-1)*2+1
        for x in range(self.size):
            for y in range(self.size):
                self.grid.append(GridCell(x-abs_size, y-abs_size ))




class GridCell:
    def __init__(self, x,y):
        self.x = x
        self.y = y
        self.z = z
        self.race = race

