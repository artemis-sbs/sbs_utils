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
        self.content.present(event)
    def on_message(self, event):
        self.content.on_message(event)
        v = self.content.get_value()
        if v != self._value:
            self._value = v
            self.update_variable()

    def invalidate_regions(self):
        self.content.invalidate_regions()

    @property
    def is_hidden(self):
        return self.content.is_hidden


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
