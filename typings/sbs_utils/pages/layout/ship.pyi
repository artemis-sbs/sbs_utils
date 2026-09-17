from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
class Ship(Column):
    """class Ship"""
    def __init__ (self, tag, ship) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    @property
    def ship (self):
        ...
    @ship.setter
    def ship (self, ship):
        ...
    def update (self, ship):
        """Change the hull shown, and REPAINT it.
        
        The dirty mark is the whole point, and it was missing: both this and the `value`
        setter used to write `self.ship` and stop, so nothing re-sent `send_gui_3dship` and
        the model only changed on a full page present. Same shape of hole as the one Face
        and TextInput each had - see `Face.update` and tests/test_gui_input_update.py - and
        it bites hardest on exactly the thing a ship widget is for: a picker or a walk that
        swaps the model under a page it does not want to rebuild.
        
        `is_hidden_by_script` and not `is_hidden`, matching Face and Text: a widget merely
        clipped by its parent this frame must still register the change, or it scrolls back
        into view showing the previous hull."""
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
