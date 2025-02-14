from .column import Column
from ...helpers import FrameContext
from .radio_button import RadioButton
from .layout import Layout
from .row import Row


class RadioButtonGroup(Column):
    def __init__(self, tag, buttons, value, vertical) -> None:
        super().__init__()
        buttons = buttons.split(",")
        self.tag = tag
        group = []
        self.group = group
        self.group_layout = Layout()
        row = Row()
        i=0
        for button in buttons:
            button = button.strip()
            radio =RadioButton(f"{tag}:{i}", button, self,  value==button)
            group.append(radio)
            row.add(radio)
            i+=1
            if vertical:
                self.group_layout.add(row)
                row = Row()
        self.group_layout.add(row)
        
    def set_bounds(self, bounds) -> None:
        self.group_layout.set_bounds(bounds)
        #self.group_layout.calc()

    def _present(self, event):
        #aspect_ratio = get_client_aspect_ratio(event.client_id)
        self.group_layout.calc(event.client_id)
        self.group_layout.present(event)
    
    def on_message(self, event):
        self.group_layout.on_message(event)

    @property
    def value(self):
        for item in self.group:
            if item.value:
                return item.message 
        return ""
       
    @value.setter
    def value(self, v):
        for item in self.group:
            if item.message == v:
                item.value = 1
            else:
                item.value = 0
        #
        #
        self.group.update_variable()

    def update(self, props):
        if props is None:
            return
        buts = props.split(",")
        i  = 0
        for but in buts:
            if i >= len(self.group):
                break
            self.group[i].message = but
            i+=1
            
        
