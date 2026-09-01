"""The Away Team app: join a landing party, and leave it.

A party is OFFERED rather than dealt (see `procedural/away.py`), so this is where a
console says yes. Before that it shows who is available; afterwards, who is down there
and the way back.

It is an app rather than a console because that is what makes ePADD able to replace the
away screen: the crew carry the same PADD down with them, and whatever job apps a
mission adds sit beside this one.
"""
from ...helpers import FrameContext
from ..away import (away_invitation, away_invite_title, away_open_roster,
                    away_beam_down, away_beam_up, away_held, away_me, away_team,
                    away_clients, away_job_text, away_is_open, away_client_of)
from ..query import to_object
from .epadd import ACCENT, DIM, PANEL, PANEL_HEAD, _esc, gui_app_chrome


def away_who(client_id=None):
    """The character this console is playing, or None.

    A console holding several has an ACTIVE one - the roster picker sets it - because
    four characters' readings side by side is a dozen buttons and no sense of who is
    doing what.
    """
    from ..inventory import get_inventory_value
    if client_id is None:
        page = FrameContext.page
        client_id = getattr(page, "client_id", None) if page is not None else None
    if client_id is None:
        return None
    held = away_held(client_id)
    if not held:
        return None
    active = get_inventory_value(client_id, "AWAY_ACTIVE", None)
    return active if active in held else away_me(client_id)


def away_set_who(client_id, lifeform):
    """Which of this console's characters is acting."""
    from ..inventory import set_inventory_value
    if lifeform in away_held(client_id):
        set_inventory_value(client_id, "AWAY_ACTIVE", lifeform)


def away_label(lifeform):
    """A character as a person: their name and what they are for.

    The job words are not decoration - the scene guards read exactly these - so a crew
    member choosing a character is reading the same thing the story will.
    """
    who = to_object(lifeform)
    if who is None:
        return "somebody", ""
    return who.name, away_job_text(who, default="watching")


def _roster_template(item):
    """One character on offer. Sizes its ROW and returns None."""
    from .row import gui_row
    from .text import gui_text
    from .face import gui_face
    from ...faces import get_face
    name, job = away_label(item)
    gui_row("row-height: 2.2em;")
    face = get_face(item)
    if face:
        gui_face(face)
    gui_text(f"$text:{_esc(name)};font:gui-3;", style="col-width: 34;")
    gui_text(f"$text:{_esc(job)};font:gui-1;color:{DIM};overflow:ellipsis;")


def gui_away_screen(title="Away Team"):
    """Draw the join/leave screen for this console."""
    from .section import gui_section
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .listbox import gui_list_box
    from .message import gui_message_callback

    page = FrameContext.page
    client_id = getattr(page, "client_id", None) if page is not None else None
    held = away_held(client_id) if client_id is not None else []

    gui_app_chrome(title, subtitle=away_invite_title() if away_invitation() else None)
    gui_section(style="area: 0, 109px, 100, 100;")

    if held:
        _down_here(client_id, held)
        return

    if away_invitation() is None:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:No landing party.;font:gui-3;color:{DIM};")
        gui_row("row-height: content; padding: 24px, 4px, 24px, 0;")
        gui_text(f"$text:When one forms, this is where you join it.;"
                 f"font:gui-1;color:{DIM};")
        return

    free = away_open_roster()
    if not free:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:The party is full.;font:gui-3;color:{DIM};")
        _who_is_down()
        return

    gui_row("row-height: content; padding: 24px, 14px, 24px, 6px;")
    gui_text(f"$text:{_esc('Going down to ' + away_invite_title())};"
             f"font:gui-1;color:{ACCENT};")

    gui_row("padding: 24px, 0, 24px, 8px;")
    lb = gui_list_box(free, "item-gap: 0.2em;", item_template=_roster_template,
                      select=True, reveal=True)

    # The pick is the character; the button is the commitment. Choosing a row and
    # pressing are separate so nobody lands on the surface by brushing a list.
    def _go(_cid=client_id):
        chosen = lb.get_value()
        got = away_beam_down(_cid, chosen) if chosen is not None else away_beam_down(_cid)
        if got is not None:
            away_go_down(_cid)

    gui_row("row-height: 2.6em; padding: 24px, 8px, 24px, 8px;")
    gui_button("BEAM DOWN", on_press=_go)


def _down_here(client_id, held):
    """What a console on the surface sees: who it is, and the way back."""
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .face import gui_face
    from ...faces import get_face

    active = away_who(client_id)
    name, job = away_label(active)

    gui_row("row-height: content; padding: 24px, 14px, 24px, 4px;")
    face = get_face(active)
    if face:
        gui_face(face)
    gui_text(f"$text:{_esc(name)};font:gui-4;", style="col-width: content;")
    gui_text(f"$text:{_esc(job)};font:gui-1;color:{ACCENT};")

    # A console speaking for several bodies picks which one is acting. One at a time,
    # deliberately: four characters' readings at once is a dozen buttons and no sense
    # of who is doing what.
    if len(held) > 1:
        gui_row("row-height: content; padding: 24px, 10px, 24px, 2px;")
        gui_text(f"$text:Also speaking for;font:gui-1;color:{DIM};")
        for other in held:
            if other == active:
                continue
            other_name, _ = away_label(other)
            gui_row("row-height: 2.2em; padding: 24px, 2px, 24px, 0;")

            def _switch(_cid=client_id, _who=other):
                away_set_who(_cid, _who)

            gui_button(other_name, on_press=_switch)

    _who_is_down()

    gui_row("row-height: 2.6em; padding: 24px, 14px, 24px, 8px;")
    gui_button("BEAM UP", on_press=lambda _cid=client_id: away_go_up(_cid))


def _who_is_down():
    """The rest of the party, so nobody is alone down there by accident."""
    from .row import gui_row
    from .text import gui_text
    team = sorted(away_team())
    if not team:
        return
    gui_row("row-height: content; padding: 24px, 12px, 24px, 2px;")
    gui_text(f"$text:On the surface;font:gui-1;color:{DIM};")
    for member in team:
        name, job = away_label(member)
        gui_row("row-height: content; padding: 24px, 2px, 24px, 0;")
        gui_text(f"$text:{_esc(name)};font:gui-2;", style="col-width: 34;")
        gui_text(f"$text:{_esc(job)};font:gui-1;color:{DIM};overflow:ellipsis;")


# --- the console half of going, which the model deliberately does not do ------------
#
# `away_beam_down` takes a character. THIS turns the console into somebody: the morph,
# and remembering the post to come back to. They are separate because a headless test,
# a mission script and a soak all want to move the team without a console in the way.

RETURN_KEY = "AWAY_RETURN"


def away_go_down(client_id):
    """Morph this console into the character it just took.

    The PADD stays open across it - the crew pressed a button on a screen and that
    screen is still there, now saying who they are. That is the whole reason identity
    lives in the bar rather than in an app.
    """
    from ..inventory import get_inventory_value, set_inventory_value
    from .console import gui_console_enter
    from ..signal import signal_emit
    if not away_held(client_id):
        return False
    if not get_inventory_value(client_id, RETURN_KEY, None):
        # Remembered BEFORE the morph, because the morph is what overwrites it.
        set_inventory_value(client_id, RETURN_KEY,
                            get_inventory_value(client_id, "CONSOLE_TYPE", "helm"))
    gui_console_enter(client_id, "away")
    signal_emit("away_went_down", {"AWAY_CLIENT": client_id,
                                   "AWAY_WHO": away_me(client_id)})
    return True


def away_go_up(client_id):
    """Put this console back at the post it left.

    The character is released first, so somebody still down there could take them.
    Where the console goes next is the mission's business - `away_came_back` is how it
    is told - but the console TYPE is restored here, because leaving a crew member
    wearing `away` is what the role-strip bug was.
    """
    from ..inventory import get_inventory_value, set_inventory_value
    from .console import gui_console_enter
    from ..signal import signal_emit
    if not away_beam_up(client_id):
        return False
    back = get_inventory_value(client_id, RETURN_KEY, None) or "helm"
    set_inventory_value(client_id, RETURN_KEY, None)
    gui_console_enter(client_id, back)
    signal_emit("away_came_back", {"AWAY_CLIENT": client_id, "AWAY_CONSOLE": back})
    return True
