from .bounds import Bounds, is_out_of_bounds
from ...helpers import FrameContext
from ...agent import Agent
from ...mast.parsers import SQUARE
from .clickable import Clickable
from .dirty import Dirty
import weakref


def apply_col_width(item, width):
    """Set `default_width` / `square` from a col-width value, keeping the two
    MUTUALLY EXCLUSIVE.

    `col-width: square` and an explicit width are two answers to one question,
    and holding both is an illegal state rather than a combination:
    `_resolve_col_widths` counts a square column in `squares` AND, if it also
    carries a width, in `assigned_cols`/`assigned_space` -- so `need_assigned`
    subtracts it twice and the row reserves its space twice over. The engine does
    not clip, so the surplus is drawn over and outside its neighbours.

    Setting either therefore clears the other. This does change behaviour for a
    screen that puts a col-width on an already-square widget (a face, an icon):
    it now gets the width it asked for, instead of the double-count.
    """
    if width is SQUARE:
        item.square = True
        item.default_width = None
        return
    item.default_width = width
    if width is not None:
        item.square = False

class Column:
    def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
        self._bounds = Bounds(left,top,right,bottom)

        self.padding = None
        self.border = None
        self.margin = None

        self.padding_style = None
        self.border_style = None
        self.margin_style = None
        self.bounds_style = None


        self.background_color = None
        self.background_image = "smallWhite"
        self.border_image = "smallWhite"
        self.border_color = None

        self.color = None
        self.default_color = None
        self.justify = None
        self.default_justify = None
        self.font = None
        self.default_font = None

        self.square = False
        self.default_width = None
        self.default_height = None
        # Set by Layout.calc on any column it actually measured for content
        # sizing. Defaults False so every existing layout keeps the cheap
        # visual-only update path when its value changes -- content sizing is
        # what turns a text change into a LAYOUT change, and only for the
        # columns that opted in.
        self.content_sized = False
        # Overflow policy: None/"spill" (draw anyway, the historical
        # behaviour), "shrink", "ellipsis" or "hide". See measure.py.
        self.overflow = None
        
        self.tag = None
        self.region_tag = ""
        self.click_text = None
        self.click_color = None
        self.click_background = None
        self.click_font = None
        self._click_tag = None
        self.data = None
        self.var_scope_id = None
        self.var_name = None
        self.on_message_cb = None
        self.client_id = None
        self._parent = None
        self._show = True
        """
        :func:`_show` represents the user's desire for a gui element to be displayed. This should only be set using `Column.show()`.
        """
        self._is_shown = True
        """
        :func:`_is_shown` is used internally to ensure that only gui elements that are within the bounds of their parent are displayed.
        If a gui element is outside the bounds of its parent, it will be hidden using `_is_shown = False`. *This is handled by the parent.*
        Don't change this manually. `Column.show()` uses :func:`_show` instead.
        """
        self.is_presenting = False
        """
        Used to determine if true bounds should be used, or if hidden bounds should be used instead. Primary purpose of this is for presenting. When NOT presenting, the true bounds should be used for calculations. If presenting, we hide a gui element (if applicable) using `Bounds.hidden`.
        """

    @property
    def click_tag(self):
        if self._click_tag is not None:
            return self._click_tag
        if self.click_text is not None:
            return f"__click:{self.tag}"
        
    @click_tag.setter
    def click_tag(self, v):
        self._click_tag = v

    @property
    def parent(self):
        if self._parent is None:
            return None

        return self._parent()
        
    @parent.setter
    def parent(self, v):
        
        self._parent = weakref.ref(v)
        

    def mark_layout_dirty(self):
        Dirty.mark_dirty(self.parent)

    def mark_visual_dirty(self):
        #
        # I think the engine handles this wrong, but this workaround 
        # fixes it, or is the right thing to do
        # if self.region_tag != "":
        #     Dirty.mark_dirty(self.parent)
        #     return
        Dirty.mark_dirty(self)

    @property
    def bounds(self):
        if not self.is_presenting:
            # If we're not presenting yet, then we don't want to use Bounds.hidden at all.
            return self._bounds
        # If we are presenting, then we need to check if Bounds.hidden should be used instead.
        if self._show and self._is_shown:
            return self._bounds
        return Bounds.hidden

    @bounds.setter
    def bounds(self, v):
        self._bounds = v


    def set_bounds(self, bounds) -> None:
        self.bounds.left=bounds.left
        self.bounds.top=bounds.top
        self.bounds.right=bounds.right
        self.bounds.bottom=bounds.bottom


    def show(self, _show):
        """
        Use to force the gui element to be hidden, or to allow it to be seen.
        If False - the gui element will always be hidden.
        If True - will be visible assuming that it is within the bounds of its parent.

        Args:
            _show (bool): Should the element be visible.
        """
        if self._show == _show:
            return
        self._show = _show
        self.mark_layout_dirty()

    @property
    def is_hidden(self):
        """
        Use :func:`is_hidden` only to check if the layout item is currently visible to the user.
        It checks both :func:`_show` and :func:`_is_shown`.
        If either of these are False, will return True.
        """
        return not self._show or not self._is_shown
        

    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        apply_col_width(self, width)

    def set_padding(self, padding):
        self._padding = padding

    def set_padding(self, padding):
        self._padding = padding

    
    def get_color(self):
        if self.color is not None:
            return self.color
        
        if self.default_color is not None:
            return self.default_color
        return self.color
    
    def get_justify(self):
        if self.justify is not None:
            return self.justify
        if self.default_justify is not None:
            return self.default_justify
        return self.justify
    
    def get_font(self):
        # self.font is set by calc
        if self.font is not None:
            return self.font
        if self.default_font is not None:
            return self.default_font
        return self.font
    
    def get_cascade_props(self,font = False, color = False, justify = False):
        props = ""
        if font:
            prop = self.get_font()
            if prop is not None:
                props += f"font:{prop};"
        if color:
            prop = self.get_color()
            if prop is not None:
                props += f"color:{prop};"
        if justify:
            prop = self.get_justify()
            if prop is not None:
                props += f"justify:{prop};"
        return props

    def set_margin(self, margin):
        self.margin = margin

    def set_border(self, border):
        self.border = border

    def represent(self, event):
        if self.client_id is None:
            return
        self.present(event)

    def present(self, event):
        self.client_id = event.client_id
        self.is_presenting = True
        self._pre_present(event)
        self._present(event)
        self._post_present(event)
        self.is_presenting = False

    def _present(self, event):
        pass

    def _pre_present(self, event):
        ctx = FrameContext.context
        if self.border is not None and self.border_color is not None:
            bb = Bounds(self.bounds)
            bb.grow(self.padding)
            bb.grow(self.border)
            bb_props = f"image:{self.border_image}; color:{self.border_color};draw_layer:1000;"
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bb:"+self.tag, bb_props,
                bb.left, bb.top, bb.right, bb.bottom)
            
        if self.background_color is not None:
            props = f"image:{self.background_image}; color:{self.background_color};draw_layer:1000;"
            
            #
            # Bounds include padding, margin for column
            # Layout Calc fills this in
            #
            bg = Bounds(self.bounds)
            bg.grow(self.padding)
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bg:"+self.tag, props,
                bg.left, bg.top, bg.right, bg.bottom)

    def _post_present(self, event):
        if self.click_text is not None or self.click_tag is not None:
            click_props = ""
            if self.click_text is not None:
                click_props = f"$text:{self.click_text};"
            if self.click_color:
                click_props += f"color: {self.click_color};"
            if self.click_font:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"
            if self.click_background is not None:
                click_props += f"background_color:{self.click_background};"
            else:
                click_props += f"background_color: white;"

            ctx = FrameContext.context
            #
            #
            #
            bounds = Bounds(self.bounds)
            if self.padding is not None:
                bounds.grow(self.padding)
            
            ctx.sbs.send_gui_clickregion(event.client_id, self.region_tag,
                self.click_tag, click_props,
                bounds.left, bounds.top, bounds.right, bounds.bottom)
            

    def invalidate_regions(self):
        pass

    def is_message_for(self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object

        Args:
            event (EVENT): the engine event

        Returns:
            bool: if the gui_message MessageTrigger should be True
        """
        return event.sub_tag == self.tag or event.sub_tag == self.click_tag
   
    def on_message(self, event):
        if self.tag is None:
            return
        is_click_tag = event.sub_tag == self.click_tag
        is_tag = event.sub_tag == self.tag
        if  not is_click_tag and not is_tag:
            return 
        if self.on_message_cb is not None:
            self.on_message_cb(event, self)
            return
        if is_click_tag:
            Clickable.clicked[event.client_id] = self
        

    def update(self, props):
        pass

    def calc(self, client_id):
        pass # Unused but here to be compatible with sub sections

    def note_measured(self, mode, avail_px, font, ar, size):
        """Record what a content measurement was taken with, and what it gave.

        Layout.calc calls this for any column it measured, so a later value
        change can re-measure under identical conditions and tell whether the
        size actually moved.
        """
        self._measure_ctx = (mode, avail_px, font, ar)
        self._measured_size = size

    def measured_size_changed(self):
        """True if re-measuring now would give a different size.

        Conservative: anything unknown returns True, so the layout is rebuilt
        rather than left stale.
        """
        ctx = getattr(self, "_measure_ctx", None)
        if ctx is None:
            return True
        previous = getattr(self, "_measured_size", None)
        if previous is None:
            return True
        mode, avail_px, font, ar = ctx
        current = self.measure(self.client_id, mode, avail_px, font, ar)
        if current is None:
            return True
        return (abs(current[0] - previous[0]) > 1e-6
                or abs(current[1] - previous[1]) > 1e-6)

    def mark_value_dirty(self, force_layout=False):
        """Dirty-mark after this widget's VALUE changed.

        Content sizing is what turns a text change into a LAYOUT change, and
        this is where that cost is contained. A full subtree re-calc happens
        only when the column is content-sized AND its measured size actually
        moved -- the common case (text changes, width does not) stays on the
        cheap visual-only path, and a layout using no content keywords never
        takes the expensive branch at all, since content_sized defaults False.

        The re-measure it costs is memoized and far cheaper than the calc() it
        avoids.
        """
        if force_layout or (self.content_sized and self.measured_size_changed()):
            self.mark_layout_dirty()
        else:
            self.mark_visual_dirty()

    def measure(self, client_id, mode, avail_px, font, ar):
        """Natural size of this column's content, in PERCENT, or None.

        Returns (width_pct, height_pct) for `col-width: content` and
        `row-height: content` to size against, or None when the widget has no
        measurable content.

        None is the important default. Every existing subclass inherits it, so
        adding content sizing changes NO existing layout until a subclass opts
        in by overriding. A column that cannot be measured -- an engine-owned
        console widget, a 3D ship, engine-drawn chrome -- falls back to flex,
        which is exactly today's behaviour. It must never fall back to 0: a
        section-level `col-width: content` cascades to every column in it, and
        zero-width widgets would be a far worse failure than an unsized one.

        Args:
            client_id: the client being laid out.
            mode:      a ContentSize -- content, min-content or max-content.
            avail_px:  width available to this column in pixels, or None when
                       it is not known yet. Needed because wrapped height
                       depends on the width the text is given.
            font:      the cascaded font, already resolved by the caller (see
                       effective_font). A font in the widget's own props string
                       overrides it, since present() appends the cascade AFTER
                       the message and the engine takes the last value.
            ar:        this client's aspect ratio, for the px -> percent
                       conversion.
        """
        return None

    def on_end_presenting(self, client_id):
        pass
    def on_begin_presenting(self, client_id):
        pass

    def update_variable(self):
        if self.var_scope_id:
            scope = Agent.get(self.var_scope_id)
            if scope is not None:
                scope.set_variable(self.var_name, self.value)

    def get_variable(self, default=None):
        if self.var_scope_id:
            scope = Agent.get(self.var_scope_id)
            if scope is not None:
                return scope.get_variable(self.var_name, default)
        return default

    @property
    def value(self):
        return None
    @value.setter
    def value(self, a):
        pass
        

