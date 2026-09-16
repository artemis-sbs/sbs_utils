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
    from .widgets import gui_layout_widget
    from ...faces import get_face
    from ..boarding import boarding_line

    cid = _client(client_id)

    # THE MAP, IN ITS OWN SECTION. An engine widget draws at its own size over anything
    # MAST puts beside it, so it never shares a row - the controls do not overlap it,
    # they disappear under it.
    gui_section("area:0,0,%d,100;" % map_width)
    gui_layout_widget("ship_internal_view")

    gui_section("area:%d,3,99,97;" % (map_width + 1))

    who, name, job = _who(cid)
    face = get_face(who.id) if who is not None else None
    if face:
        gui_row("row-height: content; padding: 8px, 6px, 8px, 2px;")
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

    # THE ONLY PART THAT CHANGES SHAPE. A different scene offers a different NUMBER of
    # choices, so this is a region - a sub-section would leave every previous set of
    # buttons painted underneath the new one, because nothing clears a plain layout.
    actions = gui_region("area:%d,60,99,97;" % (map_width + 1))
    with actions:
        _draw_actions(cid, on_leave)

    view = {"cid": cid, "name": w_name, "job": w_job, "room": w_room, "line": w_line,
            "actions": actions, "on_leave": on_leave, "rev": boarding_console_revision(cid)}
    page = FrameContext.page
    if page is not None:
        setattr(page, VIEW, view)
    return view


def _draw_actions(client_id, on_leave=None):
    """The buttons for where this character is standing, and the way home.

    `on_press=` with `data=`, never an inline handler in the loop: a block registered in
    a `for` captures the loop variable at its LAST value, so every button would answer
    with the last choice.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from ..boarding import boarding_choices, boarding_answer, boarding_seq

    choices = []
    try:
        choices = boarding_choices(client_id) or []
    except Exception:
        # A console with no character, or no scene open. Ordinary, not an error - the
        # button below still has to be drawn or there is no way off the ship.
        choices = []

    seq = boarding_seq()
    for i, ch in enumerate(choices):
        gui_row("row-height: 2.4em; font:gui-2;")
        # The label PLAINLY. Wrapped in a `$text:`...`;` style string the engine draws
        # the backticks - they are a style-value quote, not markup it strips.
        gui_button(getattr(ch, "label", str(ch)),
                   on_press=_answer, data={"index": i, "seq": seq, "cid": client_id})

    gui_row("row-height: 1em;")
    gui_text("$text:` `;")

    gui_row("row-height: 2.4em; font:gui-2;")
    gui_button("Beam up", on_press=(on_leave or _leave), data={"cid": client_id})


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
    return True
