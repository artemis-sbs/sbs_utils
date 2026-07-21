from .column import Column
from .measure import measure_props, apply_overflow
from ...helpers import FrameContext


class RadioButton(Column):
    def __init__(self, tag,  message, parent, value=False) -> None:
        super().__init__()
        self.message = message
        self.tag = tag
        self._value = value
        self.radio_parent = parent
        self.group = parent.group
        
    def _present(self, event):
        ctx = FrameContext.context
        props = f"state:{self._value==1};$text:{self.message};"

        # NOTE self.message is PLAIN text here, not a props string -- it is
        # wrapped above. apply_overflow reads the wrapped form, so it sees the
        # same $text the engine will.
        if self.overflow:
            props, draw = apply_overflow(props, self.bounds, self.overflow,
                                         self.get_font())
            if not draw:
                return

        ctx.sbs.send_gui_checkbox(event.client_id, self.region_tag,
            self.tag, props,
            # 1 if self._value else 0,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
    
    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = 1
            
            for e in self.group:
                if e != self:
                    e.value = 0
                e.present(event)
            #
            #
            self.radio_parent.update_variable()
        super().on_message(event)

    def measure(self, client_id, mode, avail_px, font, ar):
        # NOTE: unlike the other widgets self.message here is PLAIN text, not a
        # props string, so it is wrapped the same way _present wraps it.
        return measure_props(f"$text:{self.message};", mode, avail_px, font, ar)

    @property
    def value(self):
         return self._value
       
    @value.setter
    def value(self, v):
        self._value= v
