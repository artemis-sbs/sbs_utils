from .column import Column
from .measure import measure_props, apply_overflow
from ...helpers import FrameContext, merge_props, split_props

class Text(Column):
    def __init__(self, tag, message) -> None:
        super().__init__()
        self.message = message
        self.value = message
        self.tag = tag

    def _present(self, event):
        ctx = FrameContext.context
        message = self.message + self.get_cascade_props(True, True, True, True, self.message)
        if self.overflow:
            # Honour `overflow:` now that the final rect is known. Only widgets
            # that declare a policy pay for this; the default is to spill.
            message, draw = apply_overflow(message, self.bounds, self.overflow,
                                           self.get_font())
            if not draw:
                return
        ctx.sbs.send_gui_text(event.client_id, self.region_tag,
            self.tag, message,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def measure(self, client_id, mode, avail_px, font, ar):
        return measure_props(self.message, mode, avail_px, font, ar)

    def update(self, message):
        props = split_props(message, "$text")
        text = props.get("$text", props.get("text"))
        if text is None:
            props["$text"] = ""
        elif '`' not in text:
            props["$text"] = "`"+text+"`"
        

        message = merge_props(props)
        self.message = message
        if not self.is_hidden_by_script:
            # Visual-only unless this column is content-sized AND its measured
            # size actually moved -- see Column.mark_value_dirty.
            # Deliberately NOT is_hidden: a control merely clipped by its parent
            # this frame must still register the change, or it scrolls back into
            # view showing stale text.
            self.mark_value_dirty()

    
    @property
    def value(self):
         return self.message
       
    @value.setter
    def value(self, v):
        self.update(v)
