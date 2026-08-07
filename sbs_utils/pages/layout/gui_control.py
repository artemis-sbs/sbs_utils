from .column import Column
from ...helpers import FrameContext


class GuiControl(Column):
    def __init__(self,  tag,content) -> None:
        self.content = content
        super().__init__()
        self.tag = tag
        
        self.content.tag = tag
        self._value=self.content.get_value()

    def _present(self, event):
        # Re-hand the bounds INSIDE the present pass. set_bounds runs during
        # calc, where `bounds` deliberately does not apply the parent's clipping
        # verdict -- so a control scrolled out of its region would otherwise draw
        # at the real position it was last laid out at. Here `bounds` carries
        # both the script's hide and the clipping, which is what the content
        # needs to be told.
        self.content.bounds = self.bounds
        self.content.present(event)

    def on_message(self, event):
        self.content.on_message(event)
        v = self.content.get_value()
        if v != self._value:
            self._value = v
            self.update_variable()

    def invalidate_regions(self):
        self.content.invalidate_regions()

    # NOTE: is_hidden / is_hidden_by_script are deliberately NOT overridden.
    #
    # They used to delegate to self.content, which made gui_hide(control) a lie:
    # the wrapper's _show went False while is_hidden kept answering False, because
    # the content is not a layout item and nothing ever hides it. measure() and
    # has_square ask exactly that question, so a hidden control went on
    # contributing its measured size to the row.
    #
    # The wrapper IS the column in the layout tree. Its own flags are the truth,
    # and Column's implementations are correct for it. The content learns about
    # visibility the only way it can -- through the bounds it is handed, in
    # set_bounds and again in _present.

    @property
    def region_tag(self, v):
        return self.content.region_tag

    @region_tag.setter
    def region_tag(self, v):
        self.content.region_tag = v

    def set_bounds(self, bounds) -> None:
        super().set_bounds(bounds)
        # self.content.left = self.bounds.left
        # self.content.top = self.bounds.top
        # self.content.right = self.bounds.right
        # self.content.bottom = self.bounds.bottom
        self.content.bounds = self.bounds
        self.content.gui_state = ""

    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value = v
        self.content.set_value(v)
        self.update_variable()

    def update(self, props):
        self.content.update(props)
