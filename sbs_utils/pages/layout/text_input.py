from .column import Column
from .measure import measure_props, apply_overflow
from ...helpers import FrameContext, gui_text_escape
import re

class TextInput(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self._value = ""
        self.props = ""
        self._take_props(props)
        self.tag = tag

    def _take_props(self, props):
        """Split a props string into the VALUE and everything else.

        Shared by __init__ and update() so a widget built from a props string
        and one restyled by gui_update() can never disagree about how that
        string was read.
        """
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
                self._value = self._sanitize(m.group('text'))
                props = props[:m.start()] + props[m.end():]

        self.props = props

    # Characters that cannot survive a round trip through the engine, whatever
    # the player pressed to produce them:
    #
    #   `   the delimiter gui_text_escape quotes the value with -- one inside
    #       the value closes the quote early.
    #   ^   the engine's LINE BREAK. Quoting does NOT neutralise it, so a caret
    #       in a typein splits the box's text across two lines, and a value bound
    #       to a ship name carries that break onward to every screen that draws
    #       the name (see spaceobject.safe_name, which strips the same character
    #       on the way to the engine).
    #   control characters, newline included. A typein is one line.
    #
    # All of them are DROPPED rather than folded to a space: this is text someone
    # is typing, and a keystroke that quietly turns into a space reads as a bug.
    # ':' and ';' are left alone -- _text_prop re-quotes on every present, so they
    # are literal text, and both are legitimate in a typed value.
    _UNSAFE = re.compile(r"[`\^\x00-\x1f\x7f]")

    @staticmethod
    def _sanitize(v):
        # Store the value with the unsafe characters stripped so it round-trips
        # cleanly to the bound var / persistence. Wrapping for the wire happens
        # in _text_prop via the shared gui_text_escape helper.
        if v:
            v = TextInput._UNSAFE.sub("", v)
        return v

    def _text_prop(self):
        # Re-quote the value on EVERY present so ':' / ';' the player typed are
        # always treated as literal text, never as style properties (#569).
        # gui_text_escape returns "" for an empty value, so the box stays blank
        # with no stray ` (#641).
        return f"$text:{gui_text_escape(self._value)};"

    def measure(self, client_id, mode, avail_px, font, ar):
        # Measured on the CURRENT value, exactly what _present sends. A typein
        # sized to its content therefore grows and shrinks as the player types,
        # which is why the dirty guard only escalates to a re-layout when the
        # measured size actually changes.
        return measure_props(self._text_prop() + self.props,
                             mode, avail_px, font, ar)

    def _present(self, event):
        ctx = FrameContext.context
        props = self._text_prop()
        props += self.props
        props += self.get_cascade_props(True, True, True, True, props)

        # A typein is the one widget whose text the PLAYER controls, so a
        # policy here reacts as they type. `shrink` is the sane choice --
        # `ellipsis` would truncate what someone is still editing, and `hide`
        # would make the box vanish mid-word. Both are still allowed, because
        # the author may know better for a read-only field, but neither is a
        # good default and this is why the widget stays opt-in.
        if self.overflow:
            props, draw = apply_overflow(props, self.bounds, self.overflow,
                                         self.get_font())
            if not draw:
                return

        ctx.sbs.send_gui_typein(event.client_id, self.region_tag,
            self.tag, props,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)

    def update(self, props):
        """Restyle / re-value this input from a props string.

        Without this override Column.update's `pass` ran, so gui_update() on a
        gui_input was a silent no-op: the widget was re-sent with its OLD props
        and the author's new font / desc / value never arrived.

        A props string carrying no `text:` leaves the VALUE alone. The text in
        a typein belongs to the player, and restyling the box must not wipe
        what someone is in the middle of typing -- which is why this cannot
        just forward to the value setter the way Button.update does.
        """
        self._take_props(props)
        # Same region quirk as Button/Checkbox: inside a section/region a
        # visual-only mark paints wrong.
        self.mark_value_dirty(force_layout=self.region_tag != "")

    def on_message(self, event):
        if event.sub_tag == self.tag:
            # Assigned through _value, NOT the property: the player can already
            # see what they typed, and re-sending the box on every keystroke
            # fights their cursor. Only a value we had to CHANGE is pushed back.
            self._value = self._sanitize(event.value_tag)
            self.update_variable()
            if self._value != event.value_tag:
                # A character had to be stripped (a backtick, a caret, a
                # control character); push the corrected value back so the box
                # matches what we stored.
                self.mark_value_dirty()
        super().on_message(event)

    @property
    def value(self):
         return self._value

    @value.setter
    def value(self, v):
        # A SCRIPT-side assignment repaints, like every other value-bearing
        # widget (Text/Button/Checkbox/Dropdown). Without this the new text sat
        # in _value until something else forced a full repaint. The player-typing
        # path goes through on_message and deliberately does not come here.
        self._value = self._sanitize(v)
        self.update_variable()
        self.mark_value_dirty(force_layout=self.region_tag != "")
