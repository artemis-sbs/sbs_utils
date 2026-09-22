from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.cycle_button import CycleButton, CYCLE_GLYPH
from .button import MessageHandler


def gui_cycle_button(states, value=None, style=None, data=None, on_press=None,
                     glyph=CYCLE_GLYPH, is_sub_task=None):
    """Add a cycle button: one press shows the next state, and the last wraps.

    The control for a setting with a handful of states. A radio group or a chip rail
    spends one touch target per option; this spends ONE whatever the state count,
    which is what makes it fit a narrow column and a finger. Prefer a dropdown only
    when the list is long enough that cycling to the far end is tedious.

    **Inside a sub-region (a tabbed panel tab, a listbox row, an overlay slot) this
    control does NOT repaint itself** - it cannot. A widget re-sent into a region
    out of band paints wrong: the engine draws the new label over the old one in the
    same rect. The region owner has to repaint, which for a tabbed panel means
    returning 2 (redraw) from that tab's tick. Outside a region it updates in place
    as any other widget does.

    Args:
        states (list[str] | str): the states in cycle order, as a list or a comma
            string (``"icons,circles"``) so MAST can call this too.
        value (str, optional): which state to show first. An unknown value, or None,
            shows the first. Defaults to None.
        style (str, optional): CSS-like overrides, as ``gui_button`` takes them
            (``"row-height:2.2em;justify:center;"``). Defaults to None.
        data (object, optional): passed to the handler, as ``gui_button``'s is.
        on_press (label | callable | Promise, optional): run AFTER the state
            advances, so a handler reading ``.state`` sees the new one. Takes the
            same three forms ``gui_button`` accepts.

            **To READ the new state, attach with ``gui_message_callback`` instead.**
            An ``on_press`` callable is called with nothing unless it declares a
            REQUIRED parameter, and the house idiom - a closure with bound defaults
            - declares none. So the obvious handler,
            ``lambda event=None, sender=None: apply(sender.state)``, is handed
            nothing, reads ``sender`` as None and silently does nothing::

                b = gui_cycle_button("icons,circles", value=cur)
                gui_message_callback(b, lambda e, sender: apply(sender.state))

            ``on_press`` is still right when the handler does not need the state -
            a label, a Promise, or a closure that already knows what it is toggling.
        glyph (str, optional): the marker drawn after the state, saying this cycles.
            ASCII only - it reaches an engine-rendered string. Defaults to ``">"``.
        is_sub_task (bool, optional): how an ``on_press`` LABEL runs. As
            ``gui_button``. Defaults to None (the library decides).

    Returns:
        CycleButton | None: the layout object. Read ``.state`` for the state;
        ``.value`` is the props string, as on any Button.

    Example:
        # Python
        rooms = gui_cycle_button(["icons", "circles"], value=cur,
                                 style="row-height:2.2em;",
                                 on_press=lambda _s=ship: apply_rooms(_s))

        # MAST
        rooms = gui_cycle_button("icons,circles", value=cur)
        on gui_message(rooms):
            apply_rooms(ship_id, rooms.state)
    """
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    if isinstance(states, str):
        states = states.split(",")
    tag = page.get_tag()
    layout_item = CycleButton(tag, states, value, glyph)
    layout_item.data = data
    # Last, in case a style renamed the tag - the same ordering every other widget
    # builder here keeps. MessageHandler must be built AFTER it, or it binds the old
    # tag and the handler never fires.
    apply_control_styles(".button", style, layout_item, task)
    runtime_item = MessageHandler(layout_item, task, on_press, is_sub_task)
    page.add_content(layout_item, runtime_item)
    return layout_item
