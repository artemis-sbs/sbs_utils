from .column import Column
from ...helpers import FrameContext, FrameContextOverride
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

    def is_message_for(self, event):
        if event.sub_tag.startswith(f"{self.tag}:"):
            return True
        return super().is_message_for(event)

    def on_message(self, event):
        self.group_layout.on_message(event)

        if event.tag!="gui_message":
                return
        if self.is_message_for(event):
            """
            Look for any runtime nodes for the radio button
            This is doing stuff for the page, that is too complex to add to the page for just radio buttons
            Not sure if this a hack or elegant solution
            Thus far NO Layout elements talk to tasks or pages
            But radio buttons are weird
            This lets on gui_message work for a radio button
            """
            page = FrameContext.page
            if page is not None:
                runtime_node = page.tag_map.get(self.tag)

            if runtime_node is not None and runtime_node[1] is not None:
                # tuple layout and runtime node
                runtime_node = runtime_node[1]
                with FrameContextOverride(page.gui_task, page):
                    runtime_node.on_message(event)




    @property
    def value(self):
        for item in self.group:
            # The selected item == 1
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
        self.update_variable()

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
            
        
    @property
    def selected_index(self):
        for i,item in enumerate(self.group):
            if item.value:
                return i
        return 0
       
    @selected_index.setter
    def selected_index(self, v):
        v = max(0, min(v, len(self.group)))
        self.value = self.group[v].message