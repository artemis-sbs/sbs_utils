from .column import Column
from ...helpers import FrameContext, merge_props, split_props

class Checkbox(Column):
    def __init__(self, tag, message, value=False) -> None:
        super().__init__()
        self.icon = False
        self.update(message)
        self.tag = tag
        self._value = value
        self.background_color_on = "#fff7"
        self.background_color_off = "#fff0"

    def _present(self, event):
        message = f"state: {self._value};{self.message}"
        message += self.get_cascade_props(True, True, True)
        ctx = FrameContext.context
        if self.icon:
            if self._value:
                
                ctx.sbs.send_gui_rawiconbutton(event.client_id, self.region_tag,
                    self.tag, "icon_index: 121;color:#fff7", 
                    # 1 if self._value else 0,
                    self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

                ctx.sbs.send_gui_icon(event.client_id, self.region_tag,
                    self.tag+":icon", message, 
                    # 1 if self._value else 0,
                    self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
          
                
            else:
                w = self.bounds.width
                h = self.bounds.height

                ctx.sbs.send_gui_rawiconbutton(event.client_id, self.region_tag,
                    self.tag, "icon_index: 121;color:#fff7", 
                    # 1 if self._value else 0,
                    self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)


                ctx.sbs.send_gui_icon(event.client_id, self.region_tag,
                    self.tag+":icon", message, 
                    # 1 if self._value else 0,
                    self.bounds.left, self.bounds.bottom-h*0.4, self.bounds.left +  w*0.4, self.bounds.bottom)
        else:
            ctx.sbs.send_gui_checkbox(event.client_id, self.region_tag,
                self.tag, message, 
                # 1 if self._value else 0,
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
        
    def on_message(self, event):
        if event.sub_tag == self.tag and event.tag == "gui_message":
            self.value= not self.value
            # Quirk, this should just be a 
            # visual update, but when in a 
            # section/region it paints wrong.
            if self.region_tag != "":
                self.mark_layout_dirty()
            else:
                self.mark_visual_dirty()
        super().on_message(event)
            #self.value = int(event.sub_float)

    def update(self, message):
        #
        # If the value is a bool or number, it is just a state change
        #
        if not isinstance(message, str):
            self._value = message
            return
        
        props = split_props(message, "$text")
        
        self.icon = False
        if props.get("icon_index") is not None:
            self.icon = True
        else:
            text = props.get("$text", props.get("text"))
            if text is None:
                props["$text"] = ""

        self.square = self.icon
        self._value = props.get("state", "False") 

        self.message = merge_props(props)
        
        #self.present(event)


    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, v):
        self.update(v)
        self.update_variable()

