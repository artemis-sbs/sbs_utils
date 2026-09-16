"""The crew console: the interior you are walking, and who you are on it.

One call builds the whole screen, so a mission does not re-derive the layout. Without
this every boarding mission writes its own map-plus-panel by hand, and the first thing
each of them gets wrong is the same thing - an engine widget sharing a row with MAST
controls, which the engine draws over at its own size until the controls simply vanish.

    == crew_console
        gui_boarding_console()
        on change boarding_console_revision():
            gui_boarding_console_tick()
        await gui()

THE SHAPE IS BUILD-ONCE-THEN-UPDATE, and the `on change` calls a FUNCTION rather than
jumping back to the label. A repaint is not a local redraw: it re-sends every widget on
the screen over the network, to that console, on every change - and a screen caught
mid-build is what "it repaints empty" and "there are two lists" are reported as. So the
widgets are built once and kept on the page, and only the part that changes SHAPE - the
choice buttons - gets a `gui_region`, which is one of the only two things in the library
that can take its own content off the screen.

WHAT IS DELIBERATELY NOT HERE: `grid_object_list`, `grid_face` and `grid_control`. All
three follow the engine's grid SELECTION, which is one value per SHIP - several consoles
on one interior would each see their portrait and verb list follow whoever clicked last.
Giving them up is what lets a whole party board at once, and it is why the panel on the
right exists at all.
"""
from ...helpers import FrameContext
from ..query import to_object

# On the page, so it dies with the page rather than outliving it on a module.
VIEW = "__boarding_console_view__"

ACCENT = "#8cf"
DIM = "#789"

#: The device column's left edge, in screen percent. The map takes everything left of it.
PANEL_RIGHT = 99

#: The top of the device column.
PANEL_TOP = 3

#: What the choices take off the BOTTOM, in px. The flow reserves exactly this band with
#: its last row and the region is pinned to exactly this band, so the two agree at any
#: screen height - which is the whole point of stating it once as a number.
#:
#: THIS CONSTANT IS THE BUG FIX. The first version ran the flow section to y=97 with the
#: prose row declared `1fr` (so it expanded to the bottom) and then pinned the region at
#: y=60..97 on top of it. A region is positioned on an ABSOLUTE screen area
#: (`section.py:223`), the engine does not clip, and a TextArea clears only its own
#: sub-region - so the prose and the buttons were painted into the same pixels. The
#: idiom that works is `messages_gui`'s: the flow's last row RESERVES the band, and
#: nothing is left to agree by coincidence.
ACTIONS_BAND_PX = 230

#: What the xESS's own readout takes, above the choices. Same contract as the band below
#: it: the flow reserves it, the device's region is pinned to it, and it is one number.
XESS_BODY_PX = 190

#: How much of the screen the interior takes, in percent. The device is everything right
#: of it. A default rather than a constant so a mission can still hand a different width
#: to `gui_boarding_console`, but the two regions have to agree with the flow, so the
#: last width used is remembered here for `xess_body_area` to read.
MAP_WIDTH_DEFAULT = 66
_map_width = MAP_WIDTH_DEFAULT


def panel_left():
    """The device column's left edge, matching whatever map width was last built."""
    return _map_width + 1


def boarding_reserve_px():
    """Everything the two pinned regions take off the bottom.

    ONE row reserves both, because the flow has to stop above the HIGHER of them and a
    second reserve row after the first would sit inside the band it was trying to keep
    clear.
    """
    return XESS_BODY_PX + ACTIONS_BAND_PX


def boarding_actions_area(map_width):
    """The absolute area the choices region occupies. Paired with
    :func:`boarding_actions_reserve` - they describe the same band by construction."""
    return ("area: %d, 100-%dpx, %d, 100;"
            % (map_width + 1, ACTIONS_BAND_PX, PANEL_RIGHT))


def boarding_actions_reserve():
    """The row style that keeps the flow OUT of the bands the regions cover."""
    return "row-height: %dpx;" % boarding_reserve_px()


def _client(client_id=None):
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def boarding_console_revision(client_id=None):
    """A value that changes when anything on this console's screen should change.

    What an `on change` watches. Per CONSOLE, not global: one crew member answering a
    choice must not repaint the other five screens, and a shared counter would.
    """
    from ..boarding import boarding_seq, boarding_me
    from ..boarding_site import boarding_where
    cid = _client(client_id)
    if cid is None:
        return 0
    return (boarding_seq(), boarding_me(cid), boarding_where(cid))


def _where_text(client_id):
    """The room this console's character is standing in, in words."""
    from ..boarding_site import (boarding_my_host, boarding_where, boarding_room_at,
                                 boarding_room_name, boarding_room_roles)
    at = boarding_where(client_id)
    if at is None:
        return "aboard"
    host = boarding_my_host(client_id)
    room = boarding_room_at(host, at[0], at[1], boarding_room_roles())
    if room is None:
        return "a corridor"
    return boarding_room_name(room.name)


def _who(client_id):
    from ..boarding import boarding_me, boarding_job_text
    who = to_object(boarding_me(client_id))
    if who is None:
        return None, "Observer", "watching"
    return who, who.name, boarding_job_text(who, default="aboard")


def gui_boarding_console(client_id=None, map_width=66, on_leave=None):
    """Build the crew console: the interior on the left, who and where on the right.

    Args:
        client_id (optional): the console. Defaults to the page's own.
        map_width (int, optional): how much of the screen the interior takes, in percent.
        on_leave (optional): what the "Beam up" button calls. Defaults to
            `boarding_go_up`, which is almost always what it should be.

    Returns:
        dict: the held widgets, also stored on the page for
        :func:`gui_boarding_console_tick`.
    """
    from .section import gui_section, gui_region
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .face import gui_face
    from .button import gui_button
    from .blank import gui_blank
    from .widgets import gui_layout_widget
    from ...faces import get_face
    from ..boarding import boarding_line

    cid = _client(client_id)
    global _map_width
    _map_width = map_width

    # THE MAP, IN ITS OWN SECTION. An engine widget draws at its own size over anything
    # MAST puts beside it, so it never shares a row - the controls do not overlap it,
    # they disappear under it.
    gui_section("area:0,0,%d,100;" % map_width)
    gui_layout_widget("ship_internal_view")

    # THE DEVICE COLUMN, run to the BOTTOM. It reserves the choices' band with its last
    # row rather than stopping short of it at a guessed percentage - see ACTIONS_BAND_PX.
    gui_section("area:%d,%d,%d,100;" % (map_width + 1, PANEL_TOP, PANEL_RIGHT))

    who, name, job = _who(cid)
    face = get_face(who.id) if who is not None else None
    if face:
        # A FIXED HEIGHT, not `content`. `gui_face` builds a SQUARE with no `measure()`,
        # and `_measure_row_height` excludes squares by construction (layout.py:860-874):
        # "a row of nothing but squares therefore has no natural height at all and returns
        # None, falling back to flex". So `row-height: content` here was a second FLEX row
        # quietly competing with the prose row below for the same space. LM's MAST twin of
        # this screen states the height outright for the same reason.
        gui_row("row-height: 6em; padding: 8px, 6px, 8px, 2px;")
        gui_face(face)

    gui_row("row-height: 2.6em; font:gui-4;")
    w_name = gui_text("$text:`%s`;justify:center;font:gui-4;" % name)

    gui_row("row-height: 1.8em; font:gui-2;")
    w_job = gui_text("$text:`%s`;justify:center;font:gui-2;color:%s" % (job, ACCENT))

    gui_row("row-height: 1.8em; font:gui-2;")
    w_room = gui_text("$text:`%s`;justify:center;font:gui-2;color:%s"
                      % (_where_text(cid), DIM))

    # The scene's line. A text area rather than a text: it is prose, it can be several
    # lines, and it scrolls itself rather than spilling over what is under it.
    gui_row("row-height: 1fr;")
    w_line = gui_text_area(boarding_line() or " ")

    # THE DEVICE'S OWN STRIP, the last thing in the flow. Below it are two pinned
    # regions - the xESS's readout and the choices - so this is where the flow stops.
    from .xess import gui_xess
    xess = gui_xess(cid)

    # RESERVE BOTH BANDS. This row is the only thing keeping the prose above out of the
    # regions below: the engine does not clip, so without it a long line runs under them.
    # `messages_gui` does exactly this and says why - "the body must not flow into it".
    gui_row(boarding_actions_reserve())
    gui_blank()

    # THE ONLY PART THAT CHANGES SHAPE. A different scene offers a different NUMBER of
    # choices, so this is a region - a sub-section would leave every previous set of
    # buttons painted underneath the new one, because nothing clears a plain layout.
    actions = gui_region(boarding_actions_area(map_width))
    with actions:
        _draw_actions(cid, on_leave)

    view = {"cid": cid, "name": w_name, "job": w_job, "room": w_room, "line": w_line,
            "actions": actions, "xess": xess, "on_leave": on_leave,
            "rev": boarding_console_revision(cid)}
    page = FrameContext.page
    if page is not None:
        setattr(page, VIEW, view)
    return view


#: The way-home row, in px, taken off the bottom of the actions band. The list gets the
#: rest, so adding a choice lengthens the LIST rather than pushing Beam up off the screen.
LEAVE_ROW_PX = 46


def _choice_row(item, **kwargs):
    """One choice as a list row. Returns None, so the listbox sizes the item itself.

    NEVER return a size from an item template: the listbox only calls
    `resize_to_content()` when the template returns None, and an item section starts at
    zero height - returning one leaves it degenerate, which kills selection and the
    click region.
    """
    from .row import gui_row
    from .text import gui_text
    gui_row("row-height: 1.6em; font:gui-2;")
    # `overflow:shrink`, because a label that wraps makes this row a different height
    # from every other one and the engine does not clip - the second line draws over
    # whatever is under it.
    gui_text("$text:`%s`;font:gui-2;overflow:shrink;" % _choice_text(item))


def _choice_text(item):
    """A choice's label, with who it is for when that is not obvious.

    `boarding_choices` tags each choice with the body that may take it, and the duty
    console additionally receives choices nobody present is qualified for - marked here
    the way the inbox marks them, so a crew member can see they are covering."""
    label = getattr(item, "label", None) or str(item)
    covering = getattr(item, "covering", None)
    if covering:
        return "%s  (covering for %s)" % (label, covering)
    return label


def _draw_actions(client_id, on_leave=None):
    """The choices for where this character is standing, and the way home.

    A LIST, not a stack of buttons. Every choice used to get a fixed `2.4em` row inside a
    fixed-height region, and fixed rows are never scaled down - so past what fitted, the
    buttons spilled out over the map. A `gui_list_box` scrolls, which is also the house
    pattern for anything repeating (the quest log, the hangar board, Messages, Status).

    The pick and the commitment stay separate, as they are on the roster screen: choosing
    a row does nothing until ACT is pressed, so nobody answers a scene by brushing a list.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .listbox import gui_list_box
    from ..boarding import boarding_choices, boarding_seq

    choices = []
    try:
        choices = boarding_choices(client_id) or []
    except Exception:
        # A console with no character, or no scene open. Ordinary, not an error - the
        # way home below still has to be drawn or there is no way off the ship.
        choices = []

    seq = boarding_seq()
    if choices:
        gui_row("row-height: 1fr;")
        lb = gui_list_box(list(choices), "item-gap: 0.2em;", item_template=_choice_row,
                          select=True, reveal=True)
        gui_row("row-height: 2.4em; font:gui-2;")
        # `gui_message_callback`, not `on_press=` with an index: the index would be
        # captured at build time and a re-entered list would answer the wrong one. The
        # callback reads the SELECTION at the moment it is pressed.
        act = gui_button("Act")
        _bind_act(act, lb, client_id, seq)
    else:
        gui_row("row-height: 1fr;")
        gui_text("$text:` `;")

    gui_row("row-height: %dpx; font:gui-2;" % LEAVE_ROW_PX)
    gui_button("Beam up", on_press=(on_leave or _leave), data={"cid": client_id})


def _bind_act(button, listbox, client_id, seq):
    """Answer with whatever is selected WHEN PRESSED."""
    from .message import gui_message_callback

    def _go(event=None, sender=None, **kwargs):
        from ..boarding import boarding_answer
        picked = listbox.get_value()
        if picked is None:
            return
        try:
            index = list(listbox.items).index(picked)
        except ValueError:
            return
        boarding_answer(client_id, index, seq=seq)

    gui_message_callback(button, _go)


def _answer(event=None, sender=None, **kwargs):
    from ..boarding import boarding_answer
    data = getattr(sender, "data", None) or kwargs
    boarding_answer(data.get("cid"), data.get("index"), seq=data.get("seq"))


def _leave(event=None, sender=None, **kwargs):
    from .boarding_gui import boarding_go_up
    data = getattr(sender, "data", None) or kwargs
    boarding_go_up(data.get("cid"))


def gui_boarding_console_tick():
    """Refresh the crew console in place. What an `on change` should CALL.

    Never `jump` back to the screen label instead: that re-sends every widget over the
    network to that console, and does it again on the next change, forever.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page that
        registered it, and this is called from one.
    """
    from .update import gui_rebuild
    from ..boarding import boarding_line

    page = FrameContext.page
    view = getattr(page, VIEW, None) if page is not None else None
    if not view:
        return False

    cid = view["cid"]
    rev = boarding_console_revision(cid)
    if rev == view.get("rev"):
        return True
    view["rev"] = rev

    # EVERY part, not only the interesting one. A panel that is right about the line and
    # stale about the name is worse than a blank one - it describes the previous person.
    who, name, job = _who(cid)
    view["name"].update("$text:`%s`;justify:center;font:gui-4;" % name)
    view["job"].update("$text:`%s`;justify:center;font:gui-2;color:%s" % (job, ACCENT))
    view["room"].update("$text:`%s`;justify:center;font:gui-2;color:%s"
                        % (_where_text(cid), DIM))
    view["line"].value = boarding_line() or " "

    gui_rebuild(view["actions"])
    with view["actions"]:
        _draw_actions(cid, view.get("on_leave"))
    # The device keeps its own revision - switching tool must not wait for a scene beat,
    # and a scene beat must not rebuild a tool that has not changed.
    from .xess import gui_xess_tick
    gui_xess_tick()
    return True
