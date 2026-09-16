"""The Boarding Party app: join a landing party, and leave it.

A party is OFFERED rather than dealt (see `procedural/away.py`), so this is where a
console says yes. Before that it shows who is available; afterwards, who is down there
and the way back.

It is an app rather than a console because that is what makes ePADD able to replace the
crew console: the crew carry the same PADD down with them, and whatever job apps a
mission adds sit beside this one.
"""
from ...helpers import FrameContext
from ..boarding import (boarding_invitation, boarding_invite_title, boarding_open_roster,
                    boarding_invite_site,
                    boarding_beam_down, boarding_beam_up, boarding_held, boarding_me, boarding_team,
                    boarding_clients, boarding_job_text, boarding_is_open, boarding_client_of,
                    boarding_reserved, BOARDING_CONSOLE)
from ..query import to_object
from .epadd import ACCENT, DIM, PANEL, PANEL_HEAD, _esc, gui_app_chrome


def boarding_who(client_id=None):
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
    held = boarding_held(client_id)
    if not held:
        return None
    active = get_inventory_value(client_id, "BOARDING_ACTIVE", None)
    return active if active in held else boarding_me(client_id)


def boarding_set_who(client_id, lifeform):
    """Which of this console's characters is acting."""
    from ..inventory import set_inventory_value
    if lifeform in boarding_held(client_id):
        set_inventory_value(client_id, "BOARDING_ACTIVE", lifeform)


def boarding_label(lifeform):
    """A character as a person: their name and what they are for.

    The job words are not decoration - the scene guards read exactly these - so a crew
    member choosing a character is reading the same thing the story will.
    """
    who = to_object(lifeform)
    if who is None:
        return "somebody", ""
    return who.name, boarding_job_text(who, default="watching")


def _roster_template(item):
    """One character on offer. Sizes its ROW and returns None."""
    from .row import gui_row
    from .text import gui_text
    from .face import gui_face
    from ...faces import get_face
    name, job = boarding_label(item)
    gui_row("row-height: 2.2em;")
    face = get_face(item)
    if face:
        gui_face(face)
    gui_text(f"$text:{_esc(name)};font:gui-3;", style="col-width: 34;")
    gui_text(f"$text:{_esc(job)};font:gui-1;color:{DIM};overflow:ellipsis;")


def gui_boarding_screen(title="Boarding Party"):
    """Draw the join/leave screen for this console."""
    from .section import gui_section
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .listbox import gui_list_box
    from .message import gui_message_callback

    page = FrameContext.page
    client_id = getattr(page, "client_id", None) if page is not None else None
    held = boarding_held(client_id) if client_id is not None else []

    gui_app_chrome(title, subtitle=boarding_invite_title() if boarding_invitation() else None)
    gui_section(style="area: 0, 80px, 100, 100;")

    if held:
        _down_here(client_id, held)
        return

    if boarding_invitation() is None:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:No landing party.;font:gui-3;color:{DIM};")
        gui_row("row-height: content; padding: 24px, 4px, 24px, 0;")
        gui_text(f"$text:When one forms, this is where you join it.;"
                 f"font:gui-1;color:{DIM};")
        return

    mine = boarding_reserved(client_id)
    if mine is not None:
        _going_as(client_id, mine)
        return

    free = boarding_open_roster(client_id)
    if not free:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:The party is full.;font:gui-3;color:{DIM};")
        _who_is_down()
        return

    gui_row("row-height: content; padding: 24px, 14px, 24px, 6px;")
    gui_text(f"$text:{_esc('Going down to ' + boarding_invite_title())};"
             f"font:gui-1;color:{ACCENT};")

    gui_row("padding: 24px, 0, 24px, 8px;")
    lb = gui_list_box(free, "item-gap: 0.2em;", item_template=_roster_template,
                      select=True, reveal=True)

    # The pick is the character; the button is the commitment. Choosing a row and
    # pressing are separate so nobody lands on the surface by brushing a list.
    def _go(_cid=client_id):
        chosen = lb.get_value()
        got = boarding_beam_down(_cid, chosen) if chosen is not None else boarding_beam_down(_cid)
        if got is not None:
            boarding_go_down(_cid)

    gui_row("row-height: 2.6em; padding: 24px, 8px, 24px, 8px;")
    gui_button("BEAM DOWN", on_press=_go)


def _going_as(client_id, lifeform):
    """A place held for this console: who they already are, and one button.

    No picker. The crew member has BEEN this person all evening - the party was
    derived from the bridge, not cast - so asking them to choose themselves off a list
    is a step that can only be got wrong. What they need to see is the face and the
    job words the scene guards will read.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .face import gui_face
    from ...faces import get_face

    name, job = boarding_label(lifeform)
    gui_row("row-height: content; padding: 24px, 14px, 24px, 6px;")
    gui_text(f"$text:{_esc('Going down to ' + boarding_invite_title())};"
             f"font:gui-1;color:{ACCENT};")

    gui_row("row-height: content; padding: 24px, 10px, 24px, 4px;")
    face = get_face(lifeform)
    if face:
        gui_face(face)
    gui_text(f"$text:{_esc(name)};font:gui-4;", style="col-width: content;")
    gui_text(f"$text:{_esc(job)};font:gui-1;color:{ACCENT};")

    _who_is_down()

    def _go(_cid=client_id):
        if boarding_beam_down(_cid) is not None:
            boarding_go_down(_cid)

    gui_row("row-height: 2.6em; padding: 24px, 14px, 24px, 8px;")
    gui_button("BEAM DOWN", on_press=_go)


def _down_here(client_id, held):
    """What a console on the surface sees: who it is, and the way back."""
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .face import gui_face
    from ...faces import get_face

    active = boarding_who(client_id)
    name, job = boarding_label(active)

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
            other_name, _ = boarding_label(other)
            gui_row("row-height: 2.2em; padding: 24px, 2px, 24px, 0;")

            def _switch(_cid=client_id, _who=other):
                boarding_set_who(_cid, _who)

            gui_button(other_name, on_press=_switch)

    _who_is_down()

    gui_row("row-height: 2.6em; padding: 24px, 14px, 24px, 8px;")
    gui_button("BEAM UP", on_press=lambda _cid=client_id: boarding_go_up(_cid))


def _who_is_down():
    """The rest of the party, so nobody is alone down there by accident."""
    from .row import gui_row
    from .text import gui_text
    team = sorted(boarding_team())
    if not team:
        return
    gui_row("row-height: content; padding: 24px, 12px, 24px, 2px;")
    gui_text(f"$text:On the surface;font:gui-1;color:{DIM};")
    for member in team:
        name, job = boarding_label(member)
        gui_row("row-height: content; padding: 24px, 2px, 24px, 0;")
        gui_text(f"$text:{_esc(name)};font:gui-2;", style="col-width: 34;")
        gui_text(f"$text:{_esc(job)};font:gui-1;color:{DIM};overflow:ellipsis;")


# --- the console half of going, which the model deliberately does not do ------------
#
# `boarding_beam_down` takes a character. THIS turns the console into somebody: the morph,
# and remembering the post to come back to. They are separate because a headless test,
# a mission script and a soak all want to move the team without a console in the way.

RETURN_KEY = "BOARDING_RETURN"


HOME_KEY = "BOARDING_HOME_SHIP"


def boarding_home_ship(client_id):
    """The ship this console BELONGS to, even while it is looking at a boarded interior.

    `viewscreen_home_ship` cannot answer once a console is boarded: it falls back to
    `sbs.get_ship_of_client`, and boarding has just pointed that at the site. So the real
    answer is captured on the way down and kept here.
    """
    from ..inventory import get_inventory_value
    from .viewscreen import viewscreen_home_ship
    return get_inventory_value(client_id, HOME_KEY, None) or viewscreen_home_ship(client_id)


def boarding_go_down(client_id, host=None):
    """Morph this console into the character it just took, and show it where it is.

    The PADD stays open across it - the crew pressed a button on a screen and that
    screen is still there, now saying who they are. That is the whole reason identity
    lives in the bar rather than in an app.

    **`gui_console_enter` is given the console's OWN ship, never the host**, and the
    assignment to the host is a separate line afterwards. That split is not tidiness; it
    is the difference between a player keeping their name and losing it. The door
    re-asserts the crew seat with `crew_assign(client_id, home, console_type)`, and
    `own_pick` is None for anybody auto-named - so handing it the host resolves the seat
    against the HOST's roster and hull and, failing both, autonames from
    `_complement_key(host, slot)`. `crew_resolve`'s own docstring says it outright:
    moving seats RENAMES an auto-named player. The crew would beam across and arrive as
    strangers.

    So the seat and the camera stay home; only the interior view follows the host.

    Args:
        client_id: the console going down.
        host (optional): the ship or station whose interior it will walk. Without one
            this is the old dialogue-only morph, which is still a valid way to play.

    Returns:
        bool: False when this console is not holding anybody.
    """
    from ..inventory import get_inventory_value, set_inventory_value
    from .console import gui_console_enter
    from ..crew import crew_assign
    from ..query import to_id, is_client_id
    from ..signal import signal_emit
    from .viewscreen import viewscreen_home_ship
    if not boarding_held(client_id):
        return False
    # THE INVITATION KNOWS WHERE THEY ARE GOING. Taking the site from there rather than
    # from the caller is what lets the shipped BEAM DOWN button put a party on a floor
    # without knowing a floor exists: a mission that passes `site=` to `boarding_invite`
    # gets the spatial version, and one that does not gets the dialogue-only party it
    # always had. An explicit `host` still wins, for a mission moving a console between
    # two interiors.
    if host is None:
        host = boarding_invite_site()
    # Captured BEFORE anything moves, because the move is what makes it unanswerable.
    home = viewscreen_home_ship(client_id)
    set_inventory_value(client_id, HOME_KEY, home)
    # Who they are, read before the morph rewrites it.
    post_name = get_inventory_value(client_id, "CREW_NAME", None)
    post_face = get_inventory_value(client_id, "CREW_FACE", None)
    post_portrait = get_inventory_value(client_id, "CREW_PORTRAIT", None)
    if not get_inventory_value(client_id, RETURN_KEY, None):
        # Remembered BEFORE the morph, because the morph is what overwrites it.
        set_inventory_value(client_id, RETURN_KEY,
                            get_inventory_value(client_id, "CONSOLE_TYPE", "helm"))
    gui_console_enter(client_id, BOARDING_CONSOLE, ship=home)
    # KEEP THEIR NAME ACROSS THE MORPH, and this is a second, separate rename from the
    # host one. `gui_console_enter` re-asserts the seat as `crew_assign(cid, home,
    # "crew")`, and `crew_resolve` autonames per (ship, CONSOLE) seat - so science and
    # crew are different seats and an auto-named player is renamed by the morph alone,
    # even with the right ship. That is correct for a bridge crew changing station
    # (`crew_resolve` documents it) and wrong here: a boarding party is the SAME people,
    # now standing on a deck. Re-assert what they were called, which wins as tier `own`.
    if post_name:
        crew_assign(client_id, home, BOARDING_CONSOLE, own_name=post_name, own_face=post_face,
                    own_portrait=post_portrait)
    if host is not None and (is_client_id(client_id) or client_id == 0):
        # AFTER the door, and unconditionally for a real console. `gui_console_enter`
        # returns False and does nothing at all when the type is unchanged, so a console
        # moving from one site to another would never be re-assigned if this were left
        # to it.
        #
        # THE GUARD IS NOT CEREMONY. This was the one `assign_client_to_ship` in the
        # library that reached the engine unfiltered - the three in camera.py all sit
        # inside `consoles_of`, which screens ids for exactly this. The engine asserts
        # when handed an id that is not a client, and "a client id was sent that was not
        # a client id" is a hard stop on a live bridge, not a logged warning. A caller
        # holding a set of agents that merely LOOKS like consoles is an easy mistake:
        # `role("crew")` already means damcon grid objects, which is how this was found.
        #
        # `or client_id == 0` because the SERVER console is id 0 and `is_client_id` tests
        # the 0x8000... bit, which 0 does not have - the same carve-out log_panel_gui and
        # overlay make.
        FrameContext.context.sbs.assign_client_to_ship(client_id, to_id(host))
    if host is not None:
        _give_a_body(client_id, host)
    signal_emit("boarding_went_down", {"BOARDING_CLIENT": client_id,
                                       "BOARDING_WHO": boarding_me(client_id),
                                       "BOARDING_HOST": to_id(host) if host else 0})
    return True


def _give_a_body(client_id, host):
    """Put this console's character on the interior, and hand the console that body.

    Idempotent: a console that already has a figure keeps it, so a second beam-down (a
    reconnect, a move between sites) does not leave an abandoned body standing on the
    floor for the rest of the mission.
    """
    from ..boarding_site import (boarding_figure_of, boarding_figure_spawn, boarding_take,
                                 boarding_my_figure, boarding_entry_cell)
    from ..query import to_id
    who = boarding_me(client_id)
    if not who:
        return None
    fig = boarding_figure_of(who)
    if not fig:
        x, y = boarding_entry_cell(host)
        fig = boarding_figure_spawn(host, who, x, y)
    if fig:
        boarding_take(client_id, fig, host)
    return fig


def boarding_go_up(client_id):
    """Put this console back at the post it left.

    The character is released first, so somebody still down there could take them.
    Where the console goes next is the mission's business - `boarding_came_back` is how it
    is told - but the console TYPE is restored here, because leaving a crew member
    wearing `away` is what the role-strip bug was.
    """
    from ..inventory import get_inventory_value, set_inventory_value
    from .console import gui_console_enter
    from ..signal import signal_emit
    from ..boarding_site import boarding_release
    if not boarding_beam_up(client_id):
        return False
    # Read the home ship BEFORE the keys are dropped, and pass it explicitly. Left to
    # resolve itself the door would ask `sbs.get_ship_of_client`, which still answers with
    # the site - so the console would be "returned" onto the ship it just left, keeping
    # the interior view and taking its crew seat there.
    home = boarding_home_ship(client_id)
    back = get_inventory_value(client_id, RETURN_KEY, None) or "helm"
    set_inventory_value(client_id, RETURN_KEY, None)
    set_inventory_value(client_id, HOME_KEY, None)
    boarding_release(client_id)
    gui_console_enter(client_id, back, ship=home)
    signal_emit("boarding_came_back", {"BOARDING_CLIENT": client_id,
                                       "BOARDING_CONSOLE": back,
                                       "BOARDING_HOME": home})
    return True


def boarding_relevant(client_id=None):
    """Whether the Boarding Party app has anything to offer this console.

    True when a party is forming, or when this console is already down there. A
    mission with no landing parties in it has neither, and the tile is then pure
    noise on every console - which is what a playtest reported: six screens each
    carrying a button that says "No landing party".

    Put this on the ROUTE (`//gui/tab/boarding_team if boarding_relevant()`) rather than
    inventing a visibility flag: a route's own condition is already what ePADD tests
    when it builds the app list, and it is how `casino` and `brain` gate themselves.
    """
    if boarding_invitation() is not None:
        return True
    if client_id is None:
        page = FrameContext.page
        client_id = getattr(page, "client_id", None) if page is not None else None
    return bool(client_id is not None and boarding_held(client_id))
