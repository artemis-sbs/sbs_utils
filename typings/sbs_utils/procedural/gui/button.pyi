from sbs_utils.pages.layout.button import Button
from sbs_utils.helpers import FrameContext
from sbs_utils.futures import Promise
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a button to the current GUI layout outside of an ``await gui()`` block.
    
    Unlike buttons declared with ``*`` or ``+`` inside ``await gui()``, this
    button is placed directly in the layout at the current position and fires
    its handler without ending the surrounding ``await gui()``. Use it for
    action buttons embedded in panels, listboxes, or info panels.
    
    Args:
        props (str): Button label text, optionally as a property string
            (e.g. ``"$text:Fire!;color:red;"``). Supports ``{var}``
            interpolation.
        style (str, optional): Additional CSS-like style overrides.
            End each property with a semicolon, e.g. ``"col-width:20%;"``.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the handler.
            Available as ``__ITEM__`` and (if a dict) as individual variables.
            Defaults to None.
        on_press (label | callable | Promise, optional): What to do when the
            button is pressed. A label is jumped to; a callable is called; a
            Promise has its result set. Defaults to None.
        is_sub_task (bool, optional): When ``True`` the handler runs as an
            independent sub-task. Use ``False`` (default) only when pressing
            the button will rebuild the entire GUI via ``await gui()``.
            Defaults to False.
    
    Valid Styles:
        area:
            Format as `top, left, bottom, right`.
            Just numbers indicates percentage of the section or page to cover.
            Can also use `px` (pixels) or `em` (1em = height of text font).
            Can combine different units, e.g. `5+5px, 3em, 100-10em, 50px;` is a valid area.
        color:
            The color of the text
        background-color:
            The background color of the button
        padding:
            A gap inside the element (makes the button smaller, but the background still is there.)
        margin:
            The gap outside the element (makes the button smaller).
        col-width:
            The width of the button
        justify:
            Where the text is placed inside the button. `left`, `center`, or `right`
        font:
            The font to use. Overrides the font in prefernces.json
    
    
    
    Returns:
        layout object: The Layout object created"""
def gui_host_task (task):
    """The page's live GUI task -- who can tick a handler this task registered."""
def host_handler_sub_task (builder, sub_task):
    """Give a handler sub-task a LIVE ticking parent when its builder has ended.
    
    A `gui_message(widget, label)` handler runs as a sub-task of the task that
    built the widget, and sub-tasks are only ever ticked by their parent's
    tick(). On a finished builder that is exactly one tick -- the
    tick_in_context() at the call site -- after which the handler stalls
    wherever it happens to be. Single-line handlers looked like they worked;
    anything that awaited did not.
    
    The page's gui_task takes over the TICKING only. root_task is deliberately
    left pointing at the builder, so the handler's variable scope is exactly
    what it is when the builder is alive.
    
    Returns True when the sub-task was re-hosted."""
def warn_dead_handler (task, label, loc, kind):
    """Report a click that landed on a task which has already finished.
    
    Without this the failure is completely silent: the widget draws, the click
    dispatches, the handler is discarded, and nothing is logged anywhere. That
    silence is most of what made LM issue #707 hard to place."""
class ButtonResult(object):
    """class ButtonResult"""
    def __init__ (self, layout_item, client_id):
        """Initialize self.  See help(type(self)) for accurate signature."""
    @property
    def data (self):
        ...
    @property
    def value (self):
        ...
class MessageHandler(object):
    """class MessageHandler"""
    def __init__ (self, layout_item, task, handler, is_sub_task) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def is_inert (self):
        """True when this handler has nothing to run.
        
        gui_button() builds one of these even with no on_press, because the
        click also sets __ITEM__ and unpacks the widget's data. With no handler
        it falls through to start_sub_task(None, ...), so it must not become a
        link in a chain -- see message_chain.compose_handler. (LM #614)"""
    def on_message (self, event):
        ...
