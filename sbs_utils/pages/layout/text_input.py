from .column import Column
from ...helpers import FrameContext, gui_text_escape
import re

class TextInput(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self._value = ""
        if "text:" in props:
            # Pull the $text: value out of the props and store it RAW (no
            # backticks). gui_input wraps the initial value in backticks so any
            # ':' or ';' in it survives the style parser (#569); accept both the
            # quoted and the bare form here, and keep any trailing props so the
            # description / hint / styling is preserved.
            m = re.search(r"\$?text:`(?P<text>[^`]*)`;?", props)
            if m is None:
                m = re.search(r"\$?text:(?P<text>[^;]*);?", props)
            if m is not None:
                text = self._sanitize(m.group('text'))
                if text:
                    self._value = text
                props = props[:m.start()] + props[m.end():]

        self.tag = tag
        self.props = props

    @staticmethod
    def _sanitize(v):
        # Store the value with the backtick delimiter stripped so it round-trips
        # cleanly to the bound var / persistence. Wrapping for the wire happens
        # in _text_prop via the shared gui_text_escape helper.
        if v and "`" in v:
            v = v.replace("`", "")
        return v

    def _text_prop(self):
        # Re-quote the value on EVERY present so ':' / ';' the player typed are
        # always treated as literal text, never as style properties (#569).
        # gui_text_escape returns "" for an empty value, so the box stays blank
        # with no stray ` (#641).
        return f"$text:{gui_text_escape(self._value)};"

    def _present(self, event):
        ctx = FrameContext.context
        props = self._text_prop()
        props += self.props
        props += self.get_cascade_props(True, True, True)
        ctx.sbs.send_gui_typein(event.client_id, self.region_tag,
            self.tag, props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def on_message(self, event):
        if event.sub_tag == self.tag:
            self.value = event.value_tag
            if self.value != event.value_tag:
                # A character had to be stripped (a backtick); push the
                # corrected value back so the box matches what we stored.
                self.mark_visual_dirty()
        super().on_message(event)

    @property
    def value(self):
         return self._value

    @value.setter
    def value(self, v):
        self._value = self._sanitize(v)
        self.update_variable()
