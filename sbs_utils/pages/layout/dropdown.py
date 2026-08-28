from .column import Column
from ...helpers import (FrameContext, gui_text_escape, merge_props,
                        props_display_text, split_props)


class Dropdown(Column):
    def __init__(self, tag, props) -> None:
        super().__init__()
        self.values = props
        self.tag = tag
        # The label the closed box is showing. Seeded from the props' own
        # text: so `.value` reports what is on screen before any click, rather
        # than "" -- and so it stays truthful after update() replaces the props.
        self._value = props_display_text(props)

    def measure(self, client_id, mode, avail_px, font, ar):
        """Deliberately unmeasurable -- do not "fix" this to measure the list.

        A dropdown's rendered width is its widest option PLUS engine-drawn
        chrome (the arrow, the border) whose size we cannot ask for. Sizing to
        the text alone would come out narrow, and because the engine does not
        clip, a narrow dropdown draws its label over its neighbour rather than
        truncating. Falling back to flex is the safe answer, and it is exactly
        what happened before content sizing existed.
        """
        return None

    def _present(self, event):
        ctx = FrameContext.context
        ctx.sbs.send_gui_dropdown(event.client_id, self.region_tag,
            self.tag, self.values,
            self.bounds.left, self.bounds.top, self.bounds.right, self.bounds.bottom)
        
    def on_message(self, event):
        if event.sub_tag == self.tag:
            # The engine is already drawing this selection, so record it
            # WITHOUT dirty-marking: a repaint here would re-send the widget
            # mid-interaction to show what it is showing already.
            self._set_value(event.value_tag, repaint=False)
        super().on_message(event)

    def update(self, props):
        """Replace the whole props string -- the option list AND the selection.

        Writes `values`, which is the string `_present` sends. It used to write
        a `props` attribute nothing reads, so `update()` -- and `gui_update()`
        with it, since that calls this -- was a silent no-op on a dropdown
        (LM #568).
        """
        self.values = props
        self._value = props_display_text(props)
        if not self.is_hidden_by_script:
            # Deliberately NOT is_hidden: a dropdown merely clipped by its
            # parent this frame must still register the change, or it scrolls
            # back into view showing the old selection.
            #
            # force_layout INSIDE A REGION - the same quirk Button, Checkbox and
            # TextInput all guard against. See _set_value.
            self.mark_value_dirty(force_layout=self.region_tag != "")

    @property
    def value(self):
        return self._value
       
    @value.setter
    def value(self, v):
        self._set_value(v, repaint=True)

    def _set_value(self, v, repaint):
        """Select `v`, in the props string as well as in `_value`.

        Holding the selection only in `_value` was the other half of LM #568:
        `_present` sends `values`, so a value the props string did not know
        about never reached the screen -- and was undone the next time the
        layout was presented.
        """
        self._value = v
        props = split_props(self.values, "$text")
        # Whichever spelling the author used is the one the engine reads; adding
        # the other would leave two answers in one string.
        key = "text" if "text" in props and "$text" not in props else "$text"
        props[key] = gui_text_escape(v)
        self.values = merge_props(props)
        self.update_variable()
        if repaint and not self.is_hidden_by_script:
            # Quirk, this should just be a visual update, but when in a
            # section/region it paints wrong - the same guard Button, Checkbox and
            # TextInput carry, and Dropdown was the one value-bearing widget
            # without it.
            #
            # Painting a region is BRACKETED: send_gui_sub_region, a clear on the
            # region tag, the children, a complete. That bracket is what makes the
            # region's contents replace rather than accumulate. A widget marked
            # visual-only re-presents itself with none of it, so the engine lands
            # it ON TOP of the one already there - set the value twice and there
            # are three. Reported as a console showing two "On Screen" drop-downs
            # with their labels overlapping. Marking the PARENT sends the whole
            # region through region_begin/region_end instead.
            self.mark_value_dirty(force_layout=self.region_tag != "")
