from .column import Column
from ...helpers import FrameContext

HULL_TAG = "hull_tag:"


class Ship(Column):
    def __init__(self, tag, ship) -> None:
        super().__init__()

        self.ship = ship
        self.tag = tag
        #self.square = False


    @property
    def ship(self):
        # len(HULL_TAG) is 9, and this used to be a hardcoded 8 - so the getter returned
        # ":tsn_light_cruiser" for every hull it was ever asked about. It survived because
        # nothing in the library or in any mission reads it; every caller only constructs.
        return self._ship[len(HULL_TAG):]

    @ship.setter
    def ship(self, ship):
        if HULL_TAG not in ship:
            ship = f"{HULL_TAG}{ship}"
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
        self.update(v)

    def update(self, ship):
        """Change the hull shown, and REPAINT it.

        The dirty mark is the whole point, and it was missing: both this and the `value`
        setter used to write `self.ship` and stop, so nothing re-sent `send_gui_3dship` and
        the model only changed on a full page present. Same shape of hole as the one Face
        and TextInput each had - see `Face.update` and tests/test_gui_input_update.py - and
        it bites hardest on exactly the thing a ship widget is for: a picker or a walk that
        swaps the model under a page it does not want to rebuild.

        `is_hidden_by_script` and not `is_hidden`, matching Face and Text: a widget merely
        clipped by its parent this frame must still register the change, or it scrolls back
        into view showing the previous hull.
        """
        self.ship = ship
        if not self.is_hidden_by_script:
            # Visual-only unless this column is content-sized and its measured size really
            # moved -- Column.mark_value_dirty contains that decision.
            self.mark_value_dirty()

