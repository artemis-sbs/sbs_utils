from sbs_utils.pages.layout.button import Button
class CycleButton(Button):
    """A `Button` whose press advances it to its next state and wraps.
    
    Attributes:
        states (list[str]): the states, in cycle order.
        index (int): which one is showing.
        glyph (str): the marker drawn after the state."""
    def __init__ (self, tag, states, value=None, glyph='>'):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _props (self):
        """The button's props for the current state.
        
        The glyph rides INSIDE the text: an engine button is a single text run, so
        there is no second column to pin a marker to the right edge of. Two spaces
        rather than one so it reads as a separate mark and not as part of the word.
        
        The button shows the STATE only. What the setting is called belongs to a
        label row beside it, so the control stays one word wide in a narrow column.
        
        `Button.value`'s setter quotes `$text` itself, so a state carrying a `:` or
        `;` is already protected. This strips a literal backtick, which would close
        that quoting early. (Escaping here as well used to produce DOUBLE backticks;
        `Button.value` now leaves already-quoted text alone, as `Text.update` does,
        so either form is safe - but there is no reason to quote twice.)"""
    def advance (self, step=1):
        """Move `step` states on, wrapping. Returns the new state.
        
        Fewer than two states is a no-op, not an error - a caller building from data
        can legitimately end up with one option, and `% 0` would raise."""
    def mark_value_dirty (self, force_layout=False):
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
        the geometry does not move with the state."""
    def on_message (self, event):
        """A press advances FIRST, then the handlers run.
        
        Order matters: a handler reading `.state` is asking what the button now says,
        which is the whole point of pressing it."""
    @property
    def state (self):
        ...
    @state.setter
    def state (self, v):
        ...
    def update (self, states):
        """Replace the state LIST, keeping the shown state if it survives.
        
        `gui_update` routes here, so a caller can re-offer the options without
        resetting the control to its first one."""
