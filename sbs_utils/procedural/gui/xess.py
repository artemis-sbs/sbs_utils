"""The xESS - the handheld a boarding party carries.

Exploration, Emergency and Shielding System, said as the letters. A communicator, a
weapon and a scanner in one, small enough for one hand, its display understood as an AR
projection in the crew member's visor. The ePADD's small sibling, and deliberately NOT a
second tablet: this is the thing you use while standing in a corridor looking at a body
on the floor.

    THE xESS ACTS. THE ePADD READS.

That rule is what keeps two devices from becoming two lists of the same things. The xESS
is a column beside a map you are watching, so everything on it is a glance and a
decision. Anything worth reading at length belongs on the ePADD, which takes the whole
screen and has the containers for it. One entry and a count, never a thread.

**The device owns the ACT; the mission owns the MEANING.** It aims, fires, reads a room
and opens a channel. What any of that does to the story is authored - through
`xess_fired`, through the scene's own choices, and through `dialogue_register_outcome`.

TWO BANDS, AND EVERY SURFACE IS AN APP
--------------------------------------
An identity bar, and the app area. Nothing else, and nothing pinned below them.

The first version of this device had three bands: a mode strip, a readout, and a
permanent band at the bottom holding the scene's choices and a Beam up button. Three of
the device's functions were apps behind tiles and two were loose chrome stapled
underneath - and the choices used select-a-row-then-press-ACT, which is a settings
screen's interaction on a thing held in one hand. Reported as "the choice buttons are
still weird" and "why is it always active and not an app", which is one complaint.

So: answering the scene is an app (ACT) and leaving the surface is an app (CREW). The
device has ONE region that changes shape rather than two that have to agree with a
reserve row, and there is no geometry arithmetic left to get wrong.

WHY THIS IS NOT THE ePADD'S REGISTRY
------------------------------------
`gui_app_open` JUMPS THE GUI TASK to the app's route label (`epadd.py:440`). The crew
console's GUI task is the one holding the map and this column in `await gui()` - jumping
it away takes the interior with it. So an xESS app draws IN PLACE, and the registry
carries a drawing function rather than a route. Everything else here is lifted from
`epadd.py` on purpose: the badge provider's safety, the tile's click-tag hit target, and
`_esc`. Those were paid for once already.
"""
from ...helpers import FrameContext
from ..query import to_id, to_object
from .epadd import ACCENT, DIM, PANEL, PANEL_HEAD, PANEL_HI, _esc

#: On the page, so it dies with the page rather than outliving it on a module.
VIEW = "__xess_view__"

#: On the CLIENT. Per console, like everything else in boarding: one crew member opening
#: SCAN must not open it on anybody else's screen.
KEY_APP = "XESS_APP"        # which app is open; None is the tile sheet
KEY_FOCUS = "XESS_FOCUS"    # the row an app has open, when it has a list
KEY_SEEN = "XESS_SEEN_SEQ"  # the beat this console last auto-opened for

APP_CREW = "crew"
APP_ACT = "act"
APP_SCAN = "scan"
APP_FIRE = "fire"
#: Flying the suit. Only ever available to a boarder wearing one, so a grid interior's
#: device never shows it.
APP_NAV = "nav"
#: The SUIT's Fire app. A separate key from `APP_FIRE` because the registry is keyed, but
#: the same title on purpose - the two are gated mutually exclusively.
APP_WORK = "work"

#: What the scene's line is allowed to take, in px, on HOME and in ACT.
#:
#: A CAP, NOT A SHARE. The prose is a `gui_text_area`, which is a Control: it scrolls its
#: own region, so capping it never hides anything. Everything else on the screen is what
#: the crew came to do, so the prose takes a fixed band and the choices take the rest -
#: the other way round, a three-line beat pushes the buttons off the bottom.
#:
#: `content` is not an option here: content sizing does nothing on a text area.
BEAT_PX = 170

#: The armed colour. Loud on purpose - the whole safety argument is that nobody should
#: discover they were armed by hitting a colleague.
ARMED = "#f66"
WARN = "#ffd76a"
GOOD = "#8f8"


# --- the registry ---------------------------------------------------------------------
#
# A mission-wide table, so `handlerhooks` resets it between missions. An app is a dict
# rather than a class because that is what `gui_app_list` hands around and the two
# devices should read the same way to somebody who has read one of them.

_APPS = {}

#: A badge provider is free to ask what the OTHER apps are reporting, which is a cycle.
#: The PADD found this the expensive way - one provider entered 332 times for one badge,
#: unwound only by Python's recursion limit, and the error logged several times a second.
_BADGE_RUNNING = set()
_BADGE_REPORTED = set()


def xess_register(key, title=None, icon=None, blurb=None, sort=100,
                  draw=None, badge=None, available=None):
    """Put an app on the device.

    Args:
        key (str): its name, unique. Lower-cased.
        title (str, optional): what the tile says. Defaults to the key, upper-cased.
        icon (str, optional): an icon NAME, resolved by `gui_icon_name`. An unknown name
            draws nothing and says so once, which is what lets an app be registered
            before its art exists.
        blurb (str, optional): the second line of the tile.
        sort (int, optional): tile order. Lower is earlier.
        draw (callable): ``draw(client_id)``, called INSIDE the app region to build the
            app. Required - an app with nothing to draw is a tile that does nothing.
        badge (str | callable, optional): short text on the tile - "3 here", "2 new".
            Called at build time; never allowed to raise (see :func:`xess_app_badge`).
        available (callable, optional): ``available(client_id)`` - False means no tile.
            The route's `if` is the ePADD's equivalent; this device has no routes.

    Returns:
        dict: the registration.
    """
    key = str(key).strip().lower()
    app = {
        "key": key,
        "title": title if title else key.upper(),
        "icon": icon,
        "blurb": blurb or "",
        "sort": sort,
        "draw": draw,
        "badge": badge,
        "available": available,
    }
    _APPS[key] = app
    return app


def xess_unregister(key):
    """Take an app off the device. True when there was one."""
    return _APPS.pop(str(key).strip().lower(), None) is not None


def xess_registered():
    """Every app key on the device. An accessor because MAST cannot see a module-level
    dict - only functions become MAST globals."""
    return sorted(_APPS)


def xess_clear():
    """Forget every registration. The mission reset calls this; the built-ins re-register
    themselves immediately after, so a reset never leaves a device with no apps."""
    _APPS.clear()
    _BADGE_RUNNING.clear()
    _BADGE_REPORTED.clear()
    _register_builtins()


def xess_app_count():
    """Reset-ledger probe: how many apps are registered."""
    return len(_APPS)


def xess_apps(client_id=None):
    """The apps this console may open, in tile order.

    An `available` that raises drops its own tile and nothing else - the same bargain the
    badge makes. A device that goes blank because one mission app asked an awkward
    question is worse than a device missing one tile.
    """
    cid = _client(client_id)
    out = []
    for app in _APPS.values():
        gate = app.get("available")
        if gate is not None:
            try:
                if not gate(cid):
                    continue
            except Exception as e:                       # noqa: BLE001
                _report_once(app["key"], e, "availability")
                continue
        out.append(app)
    return sorted(out, key=lambda a: (a.get("sort", 100), a["title"].lower()))


def xess_app_badge(app):
    """An app's live badge, as text, or None.

    Never raises: a provider that throws costs its own tile a badge and nothing else.
    A provider asking for its own badge is ANSWERED with None rather than re-entered.
    """
    provider = app.get("badge")
    if provider is None:
        return None
    key = app.get("key")
    if key in _BADGE_RUNNING:
        return None
    _BADGE_RUNNING.add(key)
    try:
        value = provider() if callable(provider) else provider
    except Exception as e:                               # noqa: BLE001
        _report_once(key, e, "badge")
        return None
    finally:
        _BADGE_RUNNING.discard(key)
    value = "" if value is None else str(value).strip()
    return value or None


def _report_once(key, exc, what):
    """SAID, NOT SWALLOWED - and said once. This runs per tile per build, so an unguarded
    log is several lines a second for the rest of the mission."""
    marker = (key, what, type(exc).__name__)
    if marker in _BADGE_REPORTED:
        return
    _BADGE_REPORTED.add(marker)
    from ..execution import log
    log("xESS %s provider for %r raised %s: %s" % (what, key, type(exc).__name__, exc),
        "xess", "warning")


# --- what this console is looking at ----------------------------------------------------

def _client(client_id=None):
    if client_id is not None:
        return client_id
    page = FrameContext.page
    return getattr(page, "client_id", None) if page is not None else None


def xess_opened(client_id=None):
    """The app this console has open, or None for the tile sheet."""
    from ..inventory import get_inventory_value
    cid = _client(client_id)
    if cid is None:
        return None
    key = get_inventory_value(cid, KEY_APP, None)
    return key if key in _APPS else None


def xess_open(client_id, key=None):
    """Open an app on this console, or go home with ``None``.

    Leaving FIRE DISARMS. Walking away from a live weapon with the gun still up is
    exactly the accident the disarm-on-shot rule exists to prevent, one step earlier.
    """
    from ..inventory import set_inventory_value
    from ..boarding_site import boarding_disarm
    cid = _client(client_id)
    if cid is None:
        return False
    key = str(key).strip().lower() if key else None
    if key is not None and key not in _APPS:
        return False
    if xess_opened(cid) == APP_FIRE and key != APP_FIRE:
        boarding_disarm(cid)
    set_inventory_value(cid, KEY_APP, key)
    set_inventory_value(cid, KEY_FOCUS, None)   # a new app opens on its own first row
    return True


def xess_focus(client_id=None):
    """The row the open app is showing, for the apps that are a list and a detail."""
    from ..inventory import get_inventory_value
    cid = _client(client_id)
    return get_inventory_value(cid, KEY_FOCUS, None) if cid is not None else None


def xess_set_focus(client_id, value):
    from ..inventory import set_inventory_value
    set_inventory_value(client_id, KEY_FOCUS, value)


def xess_revision(client_id=None):
    """What an `on change` watches. PER CONSOLE.

    A shared counter would mean one crew member opening an app repainting five other
    screens. Carries the armed state so the device redraws the moment the weapon goes
    live - that visibility is a safety feature, not decoration - and the badges, so a
    tile that starts saying "2 new" is seen to say it.
    """
    from ..boarding import boarding_seq
    from ..boarding_site import boarding_armed, boarding_setting
    cid = _client(client_id)
    if cid is None:
        return 0
    badges = tuple((a["key"], xess_app_badge(a)) for a in xess_apps(cid))
    return (xess_opened(cid), xess_focus(cid), boarding_seq(),
            boarding_armed(cid), boarding_setting(cid), badges)


# --- the surface ------------------------------------------------------------------------

def gui_xess(client_id=None):
    """Build the device: the identity bar, then the app area.

    The bar is a plain flow in its own section; the app area is a REGION, because it is
    the part that changes shape and a region is one of only two things in the library
    that can take its own content off the screen. A `gui_sub_section` cannot - refilling
    one leaves every earlier fill painted underneath, which is what three superimposed
    messages in the ePADD inbox turned out to be.

    Returns:
        dict: the held widgets, also stored on the page for :func:`gui_xess_tick`.
    """
    from .section import gui_section, gui_region
    from .row import gui_row
    from .text import gui_text
    from .blank import gui_blank
    from .boarding_console import (boarding_identity_area, boarding_app_area,
                                   NAME_PX, SUB_PX)

    cid = _client(client_id)
    name, job, at = _identity(cid)

    gui_section(boarding_identity_area())
    # THE NAME GETS ITS OWN ROW. Sharing one with the job and the room made a long
    # name wrap, and the wrapped half left the bar and drew over the app below - the
    # engine does not clip. A name's length is not ours to control: it comes from a
    # roster, an auto-namer or a mission.
    gui_row("row-height: %dpx; background: %s; padding: 0, 6px, 0, 14px;"
            % (NAME_PX, PANEL_HEAD))
    w_name = gui_text(_name_style(name))

    gui_row("row-height: %dpx; background: %s; padding: 0, 0, 4px, 14px;"
            % (SUB_PX, PANEL_HEAD))
    w_job = gui_text(_job_style(job))
    gui_blank()
    w_at = gui_text(_at_style(cid, at))

    app = gui_region(boarding_app_area())
    with app:
        _draw_app(cid)

    view = {"cid": cid, "name": w_name, "job": w_job, "at": w_at, "app": app,
            "rev": xess_revision(cid)}
    page = FrameContext.page
    if page is not None:
        setattr(page, VIEW, view)
    return view


def gui_xess_tick():
    """Refresh the device in place. What an `on change` should CALL.

    Never a jump back to the screen label: that re-sends every widget on the console over
    the network, and a watcher would do it forever.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page.
    """
    from .update import gui_rebuild
    page = FrameContext.page
    view = getattr(page, VIEW, None) if page is not None else None
    if not view:
        return False
    cid = view["cid"]
    _auto_open(cid)
    rev = xess_revision(cid)
    if rev == view.get("rev"):
        return True
    view["rev"] = rev

    # EVERY part, not only the interesting one. A bar that is right about the room and
    # stale about the name describes the previous person.
    name, job, at = _identity(cid)
    view["name"].update(_name_style(name))
    view["job"].update(_job_style(job))
    view["at"].update(_at_style(cid, at))
    gui_rebuild(view["app"])
    with view["app"]:
        _draw_app(cid)
    return True


def _auto_open(client_id):
    """A new beat OPENS the ACT app, on every console at the site.

    Nobody should have to notice a badge to be in the scene - a beat that nobody answers
    because nobody looked is a scene that did not happen.

    Two rules that are the whole of it:

    * **The seq is recorded even when the app is not opened**, or a beat somebody
      dismissed pops straight back on the next tick and cannot be got rid of.
    * **Never while armed.** Yanking a crew member off a live weapon screen is the exact
      accident the safety rules exist to prevent, and it would happen at the worst
      possible moment - the one where something just started happening.
    """
    from ..inventory import get_inventory_value, set_inventory_value
    from ..boarding import boarding_seq, boarding_is_open, boarding_choices
    from ..boarding_site import boarding_armed
    seq = boarding_seq()
    if get_inventory_value(client_id, KEY_SEEN, None) == seq:
        return False
    set_inventory_value(client_id, KEY_SEEN, seq)
    if boarding_armed(client_id):
        return False
    if not boarding_is_open():
        return False
    try:
        if not (boarding_choices(client_id) or []):
            return False
    except Exception:                                    # noqa: BLE001
        return False
    if xess_opened(client_id) == APP_ACT:
        return False
    xess_open(client_id, APP_ACT)
    return True


# --- the identity bar --------------------------------------------------------------------

def _identity(client_id):
    from ..boarding import boarding_me, boarding_job_text
    from .boarding_console import where_text
    who = to_object(boarding_me(client_id))
    if who is None:
        return "Observer", "watching", where_text(client_id)
    return who.name, boarding_job_text(who, default="aboard"), where_text(client_id)


def _name_style(name):
    return "$text:%s;font:gui-2;overflow:shrink;" % _esc(name)


def _job_style(job):
    return ("$text:%s;font:gui-1;color:%s;col-width: content;" % (_esc(job), ACCENT))


def _at_style(client_id, at):
    """Where you are - REPLACED BY THE WEAPON when it is live.

    The bar is the only band on screen in every state, the tile sheet included, so it is
    the only place an armed weapon can be seen from everywhere. An app you have navigated
    away from cannot tell you anything.
    """
    from ..boarding_site import boarding_armed, boarding_setting
    if boarding_armed(client_id):
        return ("$text:%s;font:gui-1;color:%s;col-width: content;"
                % (_esc("ARMED - " + str(boarding_setting(client_id)).upper()), ARMED))
    return "$text:%s;font:gui-1;color:%s;col-width: content;" % (_esc(at), DIM)


# --- the app area -------------------------------------------------------------------------

def _draw_app(client_id):
    """The open app, or the tile sheet when none is."""
    key = xess_opened(client_id)
    if key is None:
        return _home(client_id)
    app = _APPS.get(key)
    draw = app.get("draw") if app else None
    if draw is None:
        return _home(client_id)
    try:
        return draw(client_id)
    except Exception as e:                               # noqa: BLE001
        # An app that blows up costs itself, not the device. Without this the crew
        # console goes blank and there is no way back to the tiles.
        _report_once(key, e, "draw")
        from .row import gui_row
        from .text import gui_text
        gui_xess_head(client_id, app["title"] if app else key)
        gui_row("row-height: 1fr;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("This app stopped. Back, and try another."), WARN))


def gui_xess_head(client_id, title, back=True):
    """An app's title line, with the way back to the tiles.

    Every app draws this, so Back is in the same place on all of them - which is the
    only reason a crew member can leave an app they have never seen before.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .blank import gui_blank
    gui_row("row-height: 2.2em; font:gui-2; padding: 10px, 8px, 10px, 4px;")
    gui_text("$text:%s;font:gui-2;color:%s;" % (_esc(str(title).upper()), ACCENT))
    gui_blank()
    if back:
        # A ZERO-ARGUMENT CLOSURE WITH THE CLIENT BOUND IN, and that is the only
        # shape that works. `MessageHandler.on_message` calls a callable handler as
        # `self.handler()` (button.py:90) - with NO arguments - so a handler that
        # reads `sender.data` is handed nothing and every value in it is None.
        # `data=` reaches MAST task variables, never a Python callable.
        #
        # It fails SILENTLY and it fails INTERMITTENTLY, which is the worst pair:
        # `xess_open(None, ...)` falls back to the ambient page for the client, so
        # the button works whenever that page happens to be this console's and does
        # nothing when it is not. Reported as "Back does nothing on the first run,
        # then beam up and down and it works" and "the FIRE app doesn't work at all".
        # `messages_gui._reply_strip` already says this in a comment.
        gui_button("Back", on_press=lambda _cid=client_id: xess_open(_cid, None))


def _home(client_id):
    """The tile sheet: what is happening, then the tools.

    The scene's line is here AS WELL AS inside ACT, so the device always has something to
    say when you glance at it and you are never answering a question you scrolled past.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .blank import gui_blank
    from ..boarding import boarding_line

    gui_row("row-height: 2.2em; font:gui-2; padding: 10px, 8px, 10px, 4px;")
    gui_text("$text:%s;font:gui-2;color:%s;" % (_esc("xESS"), ACCENT))

    line = boarding_line() or ""
    if line:
        # A text area, not a text: prose, several lines, and it scrolls itself rather
        # than spilling over what is under it. CAPPED for the same reason as in ACT - on
        # `1fr` it took every pixel the tiles were not using and pushed them to the foot
        # of the column.
        gui_row("row-height: %dpx;" % BEAT_PX)
        gui_text_area(line)

    for app in xess_apps(client_id):
        _tile(client_id, app)

    # The slack goes HERE, under the tiles, rather than into the prose or into the last
    # tile. A row that flexes is the only way to say "leave the rest empty"; without one
    # the tiles are stretched to fill the column.
    gui_row("row-height: 1fr;")
    gui_blank()


def _tile(client_id, app):
    """One app tile: a clickable panel holding its icon, name, blurb and badge.

    The WHOLE panel is the hit target - a sub-section with `click_text` emits a click
    region over its own bounds, the same mechanism the PADD's tiles and the tab strip
    use. `click_text` must be EMPTY, not absent: a sub-section emits its region only when
    `click_text is not None`, so dropping the property turns every tile into decoration.
    """
    from .section import gui_sub_section
    from .row import gui_row
    from .text import gui_text
    from .icon import gui_icon_name
    from .message import gui_message_callback

    key = app["key"]
    click = "xess-app-%s" % key
    badge = xess_app_badge(app)
    # margin, not only padding: padding is INSIDE the panel, so tiles with padding alone
    # have their backgrounds touching and read as one block.
    style = ("background: %s;"
             "click_tag: %s;"
             "click_text: ;"
             "click_background: %s;"
             "margin: 0, 0, 10px, 10px;"
             "padding: 12px, 10px, 12px, 10px;" % (PANEL, click, PANEL_HI))
    gui_row("row-height: content;")
    tile = gui_sub_section(style=style)
    with tile:
        gui_row("row-height: content;")
        if app.get("icon"):
            gui_icon_name(app["icon"], color=ACCENT, style="col-width: content;")
        # shrink, not wrap: a title that takes two lines makes its tile a different
        # height from every other tile, and the engine does not clip.
        gui_text("$text:%s;font:gui-3;overflow:shrink;" % _esc(app["title"]))
        if badge:
            gui_text("$text:%s;font:gui-1;color:%s;col-width: content;"
                     % (_esc(badge), ACCENT))
        if app.get("blurb"):
            gui_row("row-height: content;")
            gui_text("$text:%s;font:gui-1;color:%s;" % (_esc(app["blurb"]), DIM))

    item = getattr(tile, "sub_section", tile)

    def _open(event, sender, _key=key, _tag=click):
        # FILTERED. `Layout.on_message` hands every event to every callback during its
        # walk of the tree, not only ones aimed at this one - a listbox filters first, a
        # plain section does not. Unfiltered, any click anywhere would open an app, and
        # which one would depend on tree order.
        if getattr(event, "sub_tag", None) != _tag:
            return
        xess_open(client_id, _key)

    gui_message_callback(item, _open)
    return tile


# --- ACT: the beat, then one button per choice ---------------------------------------------

def _act_app(client_id):
    """The scene's line, and what this character can do about it.

    ONE PRESS PER CHOICE. The old panel made you select a row of text and then press a
    separate ACT button - a settings screen's interaction on a thing held in one hand,
    and reported as exactly that. The listbox's own selection IS the commitment here, the
    way the PADD's fallback app list works.

    A LISTBOX, not a stack of rows: a fixed row is never scaled down, so a scene with
    more choices than fit would spill its buttons out over the map. That is not
    hypothetical - it is the bug the first version of this screen shipped with.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .listbox import gui_list_box
    from .message import gui_message_callback
    from ..boarding import boarding_line, boarding_choices, boarding_seq, boarding_answer

    gui_xess_head(client_id, "Act")

    line = boarding_line() or ""
    if line:
        # A CAPPED BAND, and the list below gets `1fr`. This row used to be `1fr` with
        # the list on `2fr` - which is not a size. `1fr` IS THE ONLY FLEX SPELLING the
        # parser knows (`parsers.py` MODES); `2fr` lexes as the NUMBER 2, i.e. 2% of
        # SCREEN HEIGHT, about 15px at 720p. So the prose took the whole app area and the
        # choices were a 15px sliver at the bottom - reported as "the ACT buttons are at
        # the bottom and less than 20 pixels", which is exactly what 2% is.
        gui_row("row-height: %dpx;" % BEAT_PX)
        gui_text_area(line)

    try:
        choices = list(boarding_choices(client_id) or [])
    except Exception:                                    # noqa: BLE001
        # A console with no character, or no scene open. Ordinary, not an error.
        choices = []

    if not choices:
        gui_row("row-height: 1fr;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("Nothing to decide here."), DIM))
        return

    # CAPTURED AT BUILD TIME, and that is exactly why the seq goes with it.
    # `boarding_answer` re-derives the list and indexes into it, so an index from a
    # superseded beat would answer the WRONG choice. It refuses a stale seq outright, so
    # a button left over from the previous beat answers nothing instead.
    seq = boarding_seq()
    gui_row("row-height: 1fr; padding: 4px, 8px, 4px, 8px;")
    lb = gui_list_box(choices, "item-gap: 0.3em;", item_template=_choice_row,
                      select=True, reveal=True)

    def _pick(event, sender):
        item = lb.get_value()
        if item is None:
            return
        try:
            index = list(lb.items).index(item)
        except ValueError:
            return
        boarding_answer(client_id, index, seq=seq,
                        agent=getattr(item, "agent", None))

    gui_message_callback(lb, _pick)


def _choice_row(item, **kwargs):
    """One choice as a list row. Returns None, so the listbox sizes the item itself.

    NEVER return a size from an item template: the listbox only calls
    `resize_to_content()` when the template returns None, and an item section starts at
    zero height - returning one leaves it degenerate, which kills selection and the click
    region along with it.
    """
    from .row import gui_row
    from .text import gui_text
    gui_row("row-height: 1.6em; padding: 6px, 4px, 6px, 4px; background: %s;" % PANEL_HI)
    # `overflow:shrink`, because a label that wraps makes this row a different height
    # from every other one and the engine does not clip - the second line draws over
    # whatever is under it.
    gui_text("$text:%s;font:gui-2;overflow:shrink;" % _esc(_choice_text(item)))


def _choice_text(item):
    """A choice's label, with who it is really for when that is not obvious.

    The attribute is `forwarded` - the guard text `boarding_orphan_choices` puts on a
    choice nobody present qualifies for, which the duty console is shown so a crew member
    can see they are covering. This read `covering` for its whole life, which nothing has
    ever set, so the mark has never once appeared on this screen.
    """
    label = getattr(item, "label", None) or str(item)
    covering = getattr(item, "forwarded", None)
    if covering:
        return "%s  (covering for %s)" % (label, covering)
    return label


# --- CREW: everyone you can reach, and the way home ------------------------------------------

def _crew_app(client_id):
    """Who is out here - the ship included - what each last said, and BEAM UP.

    HAIL AND PARTY WERE THE SAME APP. One held three abstract audience tokens
    (SHIP / PARTY / ALL) and the other held the actual people; an audience picker and a
    roster are one list. Merged, the roster IS the inbox, grouped by who said it, which
    costs nothing because every message already carries a `from`.

    A list and a detail, which is the house pattern for anything repeating (the quest
    log, the hangar board, Messages, Status). The list scrolls; the detail holds the
    actions, so a row is never two buttons wide.
    """
    from .row import gui_row
    from .text import gui_text
    from .listbox import gui_list_box
    from .message import gui_message_callback
    from ..boarding import boarding_invite_title, boarding_team

    gui_xess_head(client_id, "Crew")

    callers = _callers(client_id)
    title = boarding_invite_title() or "On the surface"
    gui_row("row-height: 1.6em; font:gui-1; padding: 0, 4px, 0, 8px;")
    gui_text("$text:%s;font:gui-1;color:%s;"
             % (_esc("%s - %d down" % (title, len(boarding_team() or ()))), DIM))

    focus = xess_focus(client_id)
    picked = next((c for c in callers if c["id"] == focus), None) or callers[0]

    gui_row("row-height: 1fr; padding: 4px, 6px, 4px, 6px;")
    lb = gui_list_box(callers, "item-gap: 0.2em;", item_template=_caller_row,
                      select=True, reveal=True)
    index = callers.index(picked)
    lb.set_selected_index(index, False)

    def _pick(event, sender):
        item = lb.get_value()
        if item is None:
            return
        xess_set_focus(client_id, item["id"])

    gui_message_callback(lb, _pick)
    _caller_detail(client_id, picked)


def _callers(client_id):
    """Everyone this console can reach, the ship first.

    The SHIP IS A ROW, and it is the row that carries BEAM UP: the ship is what beams you
    up, so leaving lives with the thing that does it rather than under every screen.
    """
    from ..boarding import (boarding_team, boarding_me, boarding_job_text,
                            boarding_client_of)
    from ..boarding_site import boarding_where, boarding_my_host, boarding_room_at
    from ..boarding_site import boarding_room_name, boarding_room_roles
    from ..messages import message_crew_token

    mine = to_id(boarding_me(client_id))
    out = [{"id": "ship", "name": _ship_name(client_id), "job": "ship", "room": "",
            "to": "ship", "you": False}]

    # SORTED, because `boarding_team` is a SET - an unsorted roster reshuffles itself on
    # every rebuild and nobody can find the same person twice.
    people = []
    for lf in (boarding_team() or set()):
        who = to_object(lf)
        if who is None:
            continue
        cid = boarding_client_of(lf)
        room = ""
        at = boarding_where(cid) if cid is not None else None
        if at is not None:
            node = boarding_room_at(boarding_my_host(cid), at[0], at[1],
                                    boarding_room_roles())
            room = boarding_room_name(node.name) if node is not None else "a corridor"
        people.append({"id": to_id(lf), "name": who.name,
                       "job": boarding_job_text(who, default="aboard"),
                       "room": room, "to": message_crew_token(lf),
                       "you": to_id(lf) == mine})
    out.extend(sorted(people, key=lambda p: str(p["name"]).lower()))
    out.append({"id": "all", "name": "Everyone", "job": "all channels", "room": "",
                "to": "*", "you": False})
    return out


def _ship_name(client_id):
    from .boarding_gui import boarding_home_ship
    ship = to_object(boarding_home_ship(client_id))
    return getattr(ship, "name", None) or "The ship"


def _caller_row(item, **kwargs):
    """One caller as a list row. Returns None - see :func:`_choice_row`."""
    from .row import gui_row
    from .text import gui_text
    gui_row("row-height: 1.4em;")
    gui_text("$text:%s;font:gui-2;overflow:shrink;" % _esc(item["name"]))
    if item.get("you"):
        gui_text("$text:%s;font:gui-1;color:%s;col-width: content;"
                 % (_esc("(you)"), DIM))
    else:
        unread = _unread_from(item)
        if unread:
            gui_text("$text:%s;font:gui-1;color:%s;col-width: content;"
                     % (_esc(unread), ACCENT))
        elif item.get("room"):
            gui_text("$text:%s;font:gui-1;color:%s;col-width: content;"
                     % (_esc(item["room"]), DIM))


def _unread_from(item):
    """How many unread messages this caller has sent. "" when none - the convention the
    PADD's own badge providers follow."""
    try:
        from ..messages import message_inbox, message_is_read
    except Exception:                                    # noqa: BLE001
        return ""
    name = item.get("name")
    n = sum(1 for m in message_inbox()
            if m.get("from") == name and not message_is_read(m.get("id")))
    return "%d new" % n if n else ""


def _caller_detail(client_id, item):
    """The last thing this caller said, and what can be said back.

    ONE ENTRY AND A COUNT, never a thread - the thread is what the ePADD is for, and it
    is what keeps this device off a scrollbar.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .button import gui_button
    from ..boarding import boarding_me

    last = _last_from(item)
    gui_row("row-height: 1.4em; font:gui-1; padding: 8px, 4px, 0, 8px;")
    gui_text("$text:%s;font:gui-1;color:%s;"
             % (_esc("%s - %s" % (item["name"], item["job"])), ACCENT))
    if item.get("room"):
        gui_text("$text:%s;font:gui-1;color:%s;col-width: content;"
                 % (_esc(item["room"]), DIM))

    gui_row("row-height: 1fr; padding: 0, 8px, 0, 8px;")
    if last is not None:
        gui_text_area(str(last.get("text") or ""))
    else:
        gui_text_area("Nothing said yet.")

    more = _older_count(item)
    if more:
        gui_row("row-height: 1.2em; font:gui-1; padding: 0, 4px, 0, 8px;")
        gui_text("$text:%s;font:gui-1;color:%s;"
                 % (_esc("%d older on the ePADD" % more), DIM))

    if item.get("you"):
        return                                  # nobody calls themselves

    who = to_object(boarding_me(client_id))
    from_name = who.name if who is not None else "Boarding party"
    label = "Report in" if item["id"] == "ship" else (
        "Call for help" if item["id"] == "all" else "Call %s" % item["name"])
    text = ("%s, reporting in." % from_name if item["id"] == "ship"
            else "%s needs assistance." % from_name if item["id"] == "all"
            else "%s, are you there?" % item["name"])
    # BOUND DEFAULTS, not a reference to the loop's variables: `on_press` calls a
    # callable with no arguments, so nothing else can tell one press from another.
    gui_row("row-height: 2.2em; font:gui-2;")
    gui_button(label, on_press=(lambda _t=text, _to=item["to"], _by=from_name:
                                _say(_t, _to, _by)))

    if item["id"] == "ship":
        # THE WAY HOME, on the ship's row and nowhere else. It used to be a button under
        # the choices on every screen, where a thumb rests.
        gui_row("row-height: 2.2em; font:gui-2;")
        gui_button(_leave_label(client_id),
                   on_press=lambda _cid=client_id: _leave(_cid))


def _last_from(item):
    """The newest message from this caller. For the party row, the newest from anyone."""
    try:
        from ..messages import message_inbox
    except Exception:                                    # noqa: BLE001
        return None
    inbox = message_inbox() or []
    if item["id"] == "all":
        return inbox[0] if inbox else None
    return next((m for m in inbox if m.get("from") == item.get("name")), None)


def _older_count(item):
    try:
        from ..messages import message_inbox
    except Exception:                                    # noqa: BLE001
        return 0
    inbox = message_inbox() or []
    if item["id"] == "all":
        return max(0, len(inbox) - 1)
    mine = [m for m in inbox if m.get("from") == item.get("name")]
    return max(0, len(mine) - 1)


def _say(text, to, by):
    try:
        from ..messages import message_send
        message_send(text, to=to, sender=by, kind="crew")
    except Exception:                                    # noqa: BLE001
        # A mission with no inbox is not an error; the device simply has nowhere to put
        # the line, and refusing to draw the button would be worse.
        pass


def _leave_label(client_id):
    """What the way home is CALLED. You do not beam up out of a suit, you fly back."""
    from .boarding_gui import _come_back_word
    return _come_back_word(client_id)[1]


def _leave(client_id):
    """The way home, and it has to match the way out.

    A console that suited up has a SHIP to delete and a different console type to restore;
    `boarding_go_up` knows about neither, so sending an EVA console through it would leave
    the suit drifting in the ruin and the console on a dead 3D view. One branch, shared
    with the PADD's button.
    """
    from .boarding_gui import _come_back_word
    _come_back_word(client_id)[2](client_id)


# --- SCAN --------------------------------------------------------------------------------

def _scan_app(client_id):
    """Read the room you are standing in.

    The readout is the library's own node description rather than a second one - LM
    already renders a grid node's condition, and two descriptions of the same thing
    drift apart.
    """
    from .row import gui_row
    from .text import gui_text_area
    from ..boarding_site import (boarding_where, boarding_my_host, boarding_room_at,
                                 boarding_room_name, boarding_room_roles)

    gui_xess_head(client_id, "Scan")
    at = boarding_where(client_id)
    if at is None:
        gui_row("row-height: 1fr;")
        gui_text_area("No reading. You are not standing anywhere.")
        return
    host = boarding_my_host(client_id)
    room = boarding_room_at(host, at[0], at[1], boarding_room_roles())
    if room is not None:
        lines = ["## %s" % boarding_room_name(room.name), _condition(room)]
    else:
        lines = ["## A corridor", "Nothing here but the way through."]
    gui_row("row-height: 1fr;")
    gui_text_area("\n".join(lines))
    _file(client_id, room)


def _condition(room):
    """One line on how a node is doing, in the words the library already uses."""
    try:
        from ..internal_damage import grid_node_state, grid_node_wear
        state = grid_node_state(room)
        wear = grid_node_wear(room)
        return "Condition %s, wear %d%%." % (state, int(round(float(wear) * 100)))
    except Exception:                                    # noqa: BLE001
        return "No condition reading."


def _file(client_id, room):
    """Scanning files the entry - there is no Record button, so the party's record fills
    in as they explore and nobody has to remember to keep it.

    A no-op until the store lands in pass 2. Deliberately called anyway: the seam is the
    thing that is hard to add later.
    """
    try:
        from ..survey_log import xess_log
    except ImportError:
        return
    if room is None:
        return
    xess_log("scan", room.name, _condition(room), by=client_id)


# --- FIRE ---------------------------------------------------------------------------------

def _fire_app(client_id):
    """Arm, and choose what the shot is.

    THREE SETTINGS, AND THEY ARE A LADDER: stop a person, open a thing, destroy it. The
    third exists so that killing somebody is a NAMED CHOICE rather than something that
    falls out of pointing a cutting tool at them - the same argument that puts the
    setting ahead of the target.

    Each setting says what it does BEFORE it is armed. A setting whose effect you have to
    guess is the same problem as inferring it from what you hit.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .button import gui_button
    from ..boarding_site import (boarding_armed, boarding_setting, boarding_settings,
                                 boarding_setting_text, FIRE_RANGE)

    gui_xess_head(client_id, "Fire")
    armed = boarding_armed(client_id)
    setting = boarding_setting(client_id)

    gui_row("row-height: 2.4em; font:gui-3; padding: 6px, 6px, 6px, 6px;")
    if armed:
        gui_text("$text:%s;justify:center;font:gui-3;color:%s;background: %s;"
                 % (_esc("ARMED - %s" % str(setting).upper()), ARMED, PANEL_HI))
    else:
        gui_text("$text:%s;justify:center;font:gui-3;color:%s;"
                 % (_esc("SAFE"), DIM))

    for value in boarding_settings():
        on = value == setting
        gui_row("row-height: 2.2em; font:gui-2;")
        # BOUND DEFAULTS. The buttons are built in a LOOP, so a closure over `value`
        # would leave every one of them picking the last setting - and since
        # `on_press` calls a callable with no arguments, there is nothing else to
        # tell the presses apart with.
        gui_button("%s%s" % ("> " if on else "", str(value).upper()),
                   on_press=(lambda _cid=client_id, _v=value:
                             _pick_setting(_cid, _v)))

    gui_row("row-height: 1fr; padding: 6px, 6px, 6px, 6px;")
    gui_text_area(boarding_setting_text(setting))

    gui_row("row-height: 1.4em; font:gui-1;")
    if armed:
        gui_text("$text:%s;font:gui-1;color:%s;"
                 % (_esc("The next click on the map is a shot. One shot, then safe."),
                    ARMED))
    else:
        gui_text("$text:%s;font:gui-1;color:%s;"
                 % (_esc("Range %d cells." % FIRE_RANGE), DIM))

    gui_row("row-height: 2.2em; font:gui-2;")
    if armed:
        gui_button("Make safe", on_press=lambda _cid=client_id: _safe(_cid))
    else:
        gui_button("Arm", on_press=(lambda _cid=client_id, _s=setting:
                                    _arm(_cid, _s)))


def _pick_setting(client_id, setting):
    """Choose the verb WITHOUT arming. Picking a setting and firing must be two
    decisions, or changing your mind about the setting is a shot."""
    from ..inventory import set_inventory_value
    from ..boarding_site import KEY_SETTING
    set_inventory_value(client_id, KEY_SETTING, setting)


def _arm(client_id, setting):
    from ..boarding_site import boarding_arm
    boarding_arm(client_id, setting)


def _safe(client_id):
    from ..boarding_site import boarding_disarm
    boarding_disarm(client_id)


# --- WORK (the suit's own Fire app) ----------------------------------------------------
#
# DELIBERATELY TITLED "Fire", the same as the grid one above. `_standing_somewhere` and
# `_in_a_suit` are mutually exclusive - a boarder has a cell to stand in or a suit to fly,
# never both - so one Fire tile appears whichever body they are wearing, and a crew member
# who moves between the two does not have to learn a second word for the same idea.
#
# The target selection is Nav's, not the grid app's: a LIST, nearest first, and the
# selection is the commitment. There is nothing to aim, because a suit is being flown by
# destination and a boarder's hands are busy.

def _work_app(client_id):
    """What is in reach, and the two things a suit can do about it."""
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .listbox import gui_list_box
    from .message import gui_message_callback
    from ..eva_tools import (VERB_BEAM, VERB_TETHER, eva_abort, eva_arm, eva_armed,
                             eva_disarm, eva_reach, eva_targets, eva_use, eva_working)

    gui_xess_head(client_id, "Fire")

    target, verb, left, display = eva_working(client_id)
    if target is not None:
        gui_row("row-height: 2.4em; font:gui-3; padding: 6px, 6px, 6px, 6px;")
        gui_text("$text:%s;justify:center;font:gui-3;color:%s;background: %s;"
                 % (_esc("%s - %s, %ds" % (str(verb).upper(), display or target,
                                           int(left))), ARMED, PANEL_HI))
        gui_row("row-height: 2.2em; font:gui-2;")
        gui_button("Stop", on_press=lambda _cid=client_id: eva_abort(_cid))
        return

    held = eva_armed(client_id) or VERB_BEAM
    gui_row("row-height: 2.2em; font:gui-2;")
    for value in (VERB_BEAM, VERB_TETHER):
        on = value == held
        # BOUND DEFAULTS. Built in a LOOP, and `on_press` calls a callable with NO
        # arguments - a closure over the loop variable gives every button the last verb.
        gui_button("%s%s" % ("> " if on else "", value.upper()),
                   on_press=lambda _cid=client_id, _v=value: eva_arm(_cid, _v))

    rows = []
    for key, label, kind, gap, verbs in eva_targets(client_id):
        mark = "" if held in verbs else "  (wrong tool)"
        rows.append((key, "%s   %d%s" % (label, int(gap), mark)))
    if not rows:
        gui_row("row-height: 1fr;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("Nothing in reach. Fly closer."), DIM))
    else:
        gui_row("row-height: 1fr; padding: 4px, 8px, 4px, 8px;")
        lb = gui_list_box(rows, "item-gap: 0.3em;", item_template=_nav_row,
                          select=True, reveal=True)

        def _use(event, sender):
            item = lb.get_value()
            if item is not None:
                eva_use(client_id, item[0])

        gui_message_callback(lb, _use)

    gui_row("row-height: 1.4em; font:gui-1;")
    gui_text("$text:%s;font:gui-1;color:%s;"
             % (_esc("Reach %d. BEAM cuts a way open; TETHER hauls a find in."
                     % int(eva_reach(client_id))), DIM))

    gui_row("row-height: 2.2em; font:gui-2;")
    gui_button("Stow", on_press=lambda _cid=client_id: eva_disarm(_cid))


def _work_badge():
    """What is in reach, and how far - and it has to MOVE.

    `gui_xess_tick` only rebuilds when `xess_revision` changes, and the badge is the part
    of that tuple a moving suit can shift. Without a number that changes, the whole screen
    freezes the moment the suit starts flying.
    """
    cid = _client()
    if cid is None:
        return ""
    from ..eva_tools import eva_targets, eva_working
    target, _verb, left, _display = eva_working(cid)
    if target is not None:
        return "%ds" % int(left)
    rows = eva_targets(cid)
    if not rows:
        return ""
    return "%s %d" % (rows[0][1], int(rows[0][3]) // 25)


def _in_a_suit_with_tools(client_id):
    from ..eva import eva_my_suit
    return eva_my_suit(client_id) is not None


# --- NAV ------------------------------------------------------------------------------
#
# The device flies the suit. There is no stick and there is not going to be one: a relic's
# walls are not walls (`exclusion_radius` is zero on every prop, and containment is a
# graded RESPONSE rather than a barrier), so the way not to fly into one is to fly a route
# that was planned inside the volume. Picking a destination IS the flight control.

def _nav_app(client_id):
    """Where you can go in this relic, and the way to stop going there."""
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .listbox import gui_list_box
    from .message import gui_message_callback
    from ..eva import eva_goto, eva_no_way, eva_points, eva_route, eva_stop

    gui_xess_head(client_id, "Nav")

    dest, legs, togo = eva_route(client_id)
    if dest:
        gui_row("row-height: 1.8em; padding: 4px, 8px, 2px, 8px;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("Under way: %s, %d out" % (dest, int(togo))), ACCENT))
        gui_row("row-height: 2.2em; padding: 2px, 8px, 4px, 8px;")
        # ZERO-ARG CLOSURE WITH THE CLIENT BOUND BY DEFAULT ARG. `MessageHandler` calls a
        # callable handler as `self.handler()` with no arguments and `data=` never reaches
        # it, so a handler that reads the ambient page works until the day it does not.
        gui_button("Hold station", on_press=lambda _cid=client_id: eva_stop(_cid))

    # A PLACE THE ROUTER REFUSED, said out loud. `eva_goto` will not fly a straight line
    # through a ruin, so a destination it cannot reach does nothing when pressed - and a
    # button that does nothing is indistinguishable from a broken screen.
    stuck = eva_no_way(client_id)
    if stuck and not dest:
        gui_row("row-height: 1.8em; padding: 4px, 8px, 2px, 8px;")
        gui_text("$text:%s;font:gui-1;color:%s;overflow:shrink;"
                 % (_esc("No way through to %s from here." % stuck), DIM))

    places = eva_points(client_id)
    if not places:
        gui_row("row-height: 1fr;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("Nowhere charted yet. Fly, and the ruin will draw itself."), DIM))
        _nav_speed_row(client_id)
        _nav_view_row(client_id)
        return

    rows = [(name, "%s   %s" % (label, _nav_far(client_id, pos)))
            for name, label, pos in places]
    gui_row("row-height: 1fr; padding: 4px, 8px, 4px, 8px;")
    lb = gui_list_box(rows, "item-gap: 0.3em;", item_template=_nav_row,
                      select=True, reveal=True)

    def _pick(event, sender):
        item = lb.get_value()
        if item is None:
            return
        # The SELECTION is the commitment, the way ACT works. A separate Go button would
        # be a settings screen's interaction on a thing held in one hand.
        eva_goto(client_id, item[0])

    gui_message_callback(lb, _pick)
    _nav_speed_row(client_id)
    _nav_view_row(client_id)


def _nav_speed_row(client_id):
    """How hard to fly: three named speeds, as three buttons.

    NOT A SLIDER. The choice a boarder makes is "pick through this" or "get there", and a
    continuous control invites fiddling with a number whose units mean nothing to anybody
    on a bridge. The chosen one is marked rather than removed, so the row never moves.
    """
    from .row import gui_row
    from .button import gui_button
    from ..eva import eva_speed, eva_speeds

    now = eva_speed(client_id)
    gui_row("row-height: 2.0em; padding: 4px, 2px, 4px, 6px;")
    for name in eva_speeds():
        label = ("[%s]" % name) if name == now else name
        # ZERO-ARG CLOSURE, CLIENT AND NAME BOUND BY DEFAULT ARG - `MessageHandler` calls
        # a callable handler with no arguments, and a late-binding loop variable would
        # give every button the last speed in the list.
        gui_button(label, on_press=lambda _cid=client_id, _n=name: eva_speed(_cid, _n))


def _nav_view_row(client_id):
    """Orbit and dolly, as four presses and a way back.

    ON NAV RATHER THAN AN APP OF ITS OWN. Looking round is part of flying, not a settings
    screen - and a tile costs a whole row of the device to say "the camera".

    The centre control is deliberately ONE button. "The camera is somewhere odd" is one
    problem however it got there - a stray orbit, a dolly left in, or both - and a console
    that has lost the view wants it back, not a menu.
    """
    from .row import gui_row
    from .button import gui_button
    from .eva_camera import (eva_camera_dolly, eva_camera_orbit, eva_camera_recenter,
                             eva_camera_state)

    _yaw, _pitch, dist, free = eva_camera_state(client_id)
    gui_row("row-height: 2.0em; padding: 2px, 2px, 4px, 6px;")
    # ZERO-ARG CLOSURES, CLIENT BOUND BY DEFAULT ARG - `MessageHandler` calls a callable
    # handler with no arguments and `data=` never reaches it.
    gui_button("<", on_press=lambda _cid=client_id: eva_camera_orbit(_cid, -24.0))
    gui_button("-", on_press=lambda _cid=client_id: eva_camera_dolly(_cid, -30.0))
    gui_button("View" if (dist is None and not free) else "[View]",
               on_press=lambda _cid=client_id: eva_camera_recenter(_cid))
    gui_button("+", on_press=lambda _cid=client_id: eva_camera_dolly(_cid, 30.0))
    gui_button(">", on_press=lambda _cid=client_id: eva_camera_orbit(_cid, 24.0))


def _nav_gap(client_id, pos):
    """How far this console's suit is from a point, or None when it cannot be measured.

    NONE RATHER THAN ZERO, and that is the whole of a bridge report. `helm_position` only
    understood things with a `.x`, an authored place is a plain (x, y, z) TUPLE, so every
    measurement answered `inf` - which this function turned into 0.0 and the app printed
    beside every destination. "They all show 0 for the distance." A number that is wrong
    is worse than no number: it reads as a working readout saying you have arrived.
    (`helm_position` takes a tuple now, so this is belt and braces.)
    """
    from ..eva import eva_my_suit
    from ..helm import helm_distance
    try:
        d = helm_distance(eva_my_suit(client_id), pos)
    except Exception:                                    # noqa: BLE001
        return None
    return None if d == float("inf") else d


def _nav_far(client_id, pos):
    """That distance as a label. `--` when there is nothing to measure from."""
    d = _nav_gap(client_id, pos)
    return "--" if d is None else "%d" % int(d)


def _nav_row(item, **kwargs):
    """One destination as a list row. Returns None, so the listbox sizes it - see
    `_choice_row` for why returning a size kills selection."""
    from .row import gui_row
    from .text import gui_text
    gui_row("row-height: 1.6em; padding: 6px, 4px, 6px, 4px; background: %s;" % PANEL_HI)
    gui_text("$text:%s;font:gui-2;overflow:shrink;" % _esc(str(item[1])))


# --- the built-ins --------------------------------------------------------------------------

def _act_badge():
    """How many choices are waiting. This is what makes a beat findable without the
    device taking the screen - and the auto-open is what makes it findable anyway."""
    from ..boarding import boarding_choices
    try:
        n = len(boarding_choices(_client()) or [])
    except Exception:                                    # noqa: BLE001
        return ""
    return "%d here" % n if n else ""


def _crew_badge():
    from ..messages import message_unread
    try:
        n = message_unread()
    except Exception:                                    # noqa: BLE001
        return ""
    return "%d new" % n if n else ""


def _fire_badge():
    from ..boarding_site import boarding_armed
    return "ARMED" if boarding_armed(_client()) else ""


def _nav_badge():
    """Where you are heading, and roughly how far.

    THE DISTANCE IS IN HERE ON PURPOSE. `gui_xess_tick` only rebuilds when
    `xess_revision` changes, and a suit crossing a chamber changes nothing else in that
    tuple - so without a badge that moves, the Nav screen would freeze the moment you
    pressed a destination and never show you arriving. Coarse, so it is a repaint every
    hundred units rather than every tick.
    """
    from ..eva import eva_route
    try:
        dest, _legs, togo = eva_route(_client())
    except Exception:                                    # noqa: BLE001
        return ""
    return "" if not dest else "%s %d" % (dest, int(togo) // 100)


def _in_a_suit(client_id):
    """NAV needs a suit to fly. On a grid interior there is nothing for it to do."""
    from ..eva import eva_my_suit
    try:
        return eva_my_suit(client_id) is not None
    except Exception:                                    # noqa: BLE001
        return False


def _standing_somewhere(client_id):
    """SCAN and FIRE need a body on a floor. A tile that cannot do anything is worse than
    no tile - it is a promise the device does not keep."""
    from ..boarding_site import boarding_where
    return boarding_where(client_id) is not None


def _register_builtins():
    xess_register(APP_CREW, title="Crew", icon="epadd.boarding", sort=10,
                  blurb="Who is out here, and the way home",
                  draw=_crew_app, badge=_crew_badge)
    xess_register(APP_ACT, title="Act", icon="epadd.quests", sort=20,
                  blurb="What you can do here",
                  draw=_act_app, badge=_act_badge)
    xess_register(APP_SCAN, title="Scan", icon="epadd.status", sort=30,
                  blurb="Read the room you are in",
                  draw=_scan_app, available=_standing_somewhere)
    xess_register(APP_WORK, title="Fire", icon="epadd.damage", sort=35,
                  blurb="What is in reach, and what to do about it",
                  draw=_work_app, badge=_work_badge, available=_in_a_suit_with_tools)
    xess_register(APP_FIRE, title="Fire", icon="epadd.damage", sort=40,
                  blurb="Arm, then click the map",
                  draw=_fire_app, badge=_fire_badge, available=_standing_somewhere)
    xess_register(APP_NAV, title="Nav", icon="epadd.helm", sort=25,
                  blurb="Where you can go, and going there",
                  draw=_nav_app, badge=_nav_badge, available=_in_a_suit)


_register_builtins()
