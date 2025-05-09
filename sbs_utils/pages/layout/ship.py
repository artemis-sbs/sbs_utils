from .column import Column
from ...helpers import FrameContext

class Ship(Column):
    def __init__(self, tag, ship) -> None:
        super().__init__()

        self.ship = ship
        self.tag = tag
        #self.square = False


    @property
    def ship(self):
        
        return self.ship[8:]

    @ship.setter
    def ship(self, ship):
        if "hull_tag:" not in ship:
            ship = f"hull_tag:{ship}"
        self._ship = ship


    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_3dship(event.client_id, 
            self.region_tag,
            self.tag, self._ship,  
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    @property
    def value(self):
         return self.ship
       
    @value.setter
    def value(self, v):
        self.ship= v

    def update(self, ship):
        self.ship = ship

