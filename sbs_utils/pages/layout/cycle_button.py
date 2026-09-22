"""A button that cycles: each press shows its next state and wraps.

The control the library was missing. For a setting with a handful of states the
question is not "which of these" but "change it", and the widgets that existed all
answer the first question: `gui_radio` draws one checkbox per option (wrong semantic
for an exclusive choice, and a small glyph is the wrong thing to aim a finger at), a
chip rail spends one target per option, and a dropdown costs two taps and covers what
is underneath. A cycle button is ONE target whatever the state count, which is what
makes it right on a touch console and in a narrow column.

It subclasses `Button` deliberately. `Button.value`'s setter ends in
`mark_value_dirty(...)`, so advancing a state re-renders THIS ONE WIDGET in place -
nothing rebuilds the panel around it. A control that needs its parent redrawn to show
its own new state is a control that stops working the moment the parent redraws for
some other reason.
"""
from .button import Button


#: The default marker that a button cycles. ASCII, because this reaches an
#: engine-rendered string, and the engine renders ASCII only.
CYCLE_GLYPH = ">"


class CycleButton(Button):
    """A `Button` whose press advances it to its next state and wraps.

    Attributes:
        states (list[str]): the states, in cycle order.
        index (int): which one is showing.
        glyph (str): the marker drawn after the state.
    """

    def __init__(self, tag, states, value=None, glyph=CYCLE_GLYPH):
        # Before super(): _props() reads all three, and Button.__init__ renders
        # immediately through the `value` setter.
        self.states = [str(s).strip() for s in (states or []) if str(s).strip()]
        self.glyph = glyph
        self.index = self.states.index(value) if value in self.states else 0
        super().__init__(tag, self._props())

    # --- what it draws --------------------------------------------------------
    def _props(self):
        """The button's props for the current state.

        The glyph rides INSIDE the text: an engine button is a single text run, so
        there is no second column to pin a marker to the right edge of. Two spaces
        rather than one so it reads as a separate mark and not as part of the word.

        The button shows the STATE only. What the setting is called belongs to a
        label row beside it, so the control stays one word wide in a narrow column.

        NO `gui_text_escape` here, deliberately. `Button.value`'s setter already
        backtick-wraps whatever it finds in `$text`, so escaping first produced
        DOUBLE backticks and a malformed props string. A state carrying a `:` or `;`
        is protected by Button's own wrapping; what this must do is strip a literal
        backtick, which would close that wrapping early.
        """
        return f"$text:{str(self.state).replace('`', '')}  {self.glyph};"

    # --- the state ------------------------------------------------------------
    #
    # `state` is the STATE; `value` stays Button's props string. Naming them apart is
    # deliberate: one accessor that answers two different shapes is exactly what
    # `LayoutListbox.get_selected()` does, and it crashed a console on a real bridge
    # the first time somebody indexed the wrong one.
    @property
    def state(self):
        return self.states[self.index] if self.states else ""

    @state.setter
    def state(self, v):
        """Show a state WITHOUT firing handlers - for seeding from stored settings.

        An unknown state is ignored rather than raising: the value usually comes from
        saved data, and a console that refuses to draw because a setting was renamed
        is worse than one showing the state it has.
        """
        if v in self.states:
            self.index = self.states.index(v)
            self.value = self._props()

    def advance(self, step=1):
        """Move `step` states on, wrapping. Returns the new state.

        Fewer than two states is a no-op, not an error - a caller building from data
        can legitimately end up with one option, and `% 0` would raise.
        """
        if len(self.states) < 2:
            return self.state
        self.index = (self.index + step) % len(self.states)
        # Button's setter: marks this widget dirty, so the engine re-renders it in
        # place. force_layout is handled there for the in-a-region quirk.
        self.value = self._props()
        return self.state

    def update(self, states):
        """Replace the state LIST, keeping the shown state if it survives.

        `gui_update` routes here, so a caller can re-offer the options without
        resetting the control to its first one.
        """
        was = self.state
        self.states = [str(s).strip() for s in (states or []) if str(s).strip()]
        self.index = self.states.index(was) if was in self.states else 0
        self.value = self._props()

    def mark_value_dirty(self, force_layout=False):
        """Inside a region: send NOTHING. The region owner repaints.

        `Button.value` already carries the finding, and it is worth quoting because
        overriding it reintroduced the bug it was written for:

            # Quirk, this should just be a visual update, but when in a
            # section/region it paints wrong.

        It paints wrong in a very specific way: the new label is drawn OVER the old
        one in the same rect, so the button reads as two overlapping words
        (`idodes>>` for icons over circles). Button's workaround is to force a LAYOUT
        mark instead, which re-presents the parent - but that is out of band too, and
        re-sends the whole sub-section unbracketed, which appends widgets the region
        only shows on its next swap.

        So NEITHER out-of-band path is safe in a region. The only correct update is
        the region owner's own present, which brackets with
        `send_gui_clear`/`send_gui_complete` - `TabbedPanel.present`, reached by
        returning 2 from a tab's tick. That is how every other control in a tabbed
        panel already updates, and why they behave while a self-updating one does
        not.

        Outside a region the normal dirty path applies and a visual mark is right:
        the geometry does not move with the state.
        """
        if self.region_tag:
            return
        self.mark_visual_dirty()

    # --- input ----------------------------------------------------------------
    def on_message(self, event):
        """A press advances FIRST, then the handlers run.

        Order matters: a handler reading `.state` is asking what the button now says,
        which is the whole point of pressing it.
        """
        if self.tag is not None and event.sub_tag == self.tag:
            self.advance()
        super().on_message(event)
