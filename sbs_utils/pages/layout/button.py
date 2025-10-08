from .column import Column
from ...helpers import FrameContext
from .bounds import Bounds

class Button(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        self.tag = tag
        if "$text:" not in message:
            if "text:" not in message:
                self.message = f"$text:{message};"
        else:
            self.message = message

    def _pre_present(self, event):
        # This eliminates the issue of the Column#_pre_present() where it makes a background that isn't the button.
        ctx = FrameContext.context
        if self.background_color is not None:
            bg = Bounds(self.bounds)
            bg.grow(self.padding)
            # NOTE: sbs.send_gui_colorbutton uses the `color` parameter for the background color.
            # If there's a better way to do this, feel free to make it so. But it works great as is.
            # What we're doing is swapping out any existing `color` attributes and adding a new one, with the value for self.background_color.
            import re
            button_message = re.sub(r"[^-]color:.*?(;|$)","",self.message, flags=re.M) # This removes any existing color tag, which is used for text color, but in this case we need it for the backgorund color
            button_message = f"color:{self.background_color};{button_message}" # Prepend instead of append so we don't need to depend on user to include a tailing semicolon
            # This color button is now effectively the background.
            ctx.sbs.send_gui_colorbutton(event.client_id, self.region_tag,
                self.tag, button_message, 
                bg.left, bg.top, bg.right, bg.bottom)


    def _present(self,  event):
        ctx = FrameContext.context
        message = self.message
        message += self.get_cascade_props(True, True, True)
        
        if self.background_color is None:
            ctx.sbs.send_gui_button(event.client_id, self.region_tag,
                self.tag, message, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        else:
            # Since background-color is specified, we have to do this a bit differently.
            # sbs.send_gui_button() can only change the color of the text, not the background.
            # sbs.send_gui_colorbuttton() doesn't show any text at all, but the background color can be shown.
            # So to have a colored backgound and text, we need to couple sbs.send_gui_colorbutton() with sbs.send_gui_text()
            
            if message.find("draw_layer") == -1:
                message = "draw_layer:10000;" + message # draw layer has to be high or the button covers the text

            # TODO: Find a way to use padding so the text isn't righ up close to the edge of the button's border.
            ctx.sbs.send_gui_text(event.client_id, self.region_tag,
                self.tag+"_text", message, 
                self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
            
        

    def update(self, message):
        if "$text:" not in message:
            message = f"$text:{message};"
        self.message = message


    @property
    def value(self):
        return self.message

    @value.setter
    def value(self, v):
        if "$text:" not in v:
            v = f"$text:{v}"

        self.message = v
