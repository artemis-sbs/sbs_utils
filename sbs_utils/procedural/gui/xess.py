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

#: The device this file was written for. A SURFACE is a place the shell lives: the handheld
#: a boarding party carries, and - since the panel was generalised - any other console that
#: wants tiles and one app at a time (the OpenUniverse Admiral's right-hand column is the
#: first). Boarding is one surface registered like any other, which is what keeps
#: "the boarding imports must not run elsewhere" structural instead of a condition.
SURFACE_BOARDING = "boarding"

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

#: surface -> its app table. Boarding's IS `_APPS`, the same object it has always been, so
#: anything holding a reference to it keeps working.
_SURFACES = {SURFACE_BOARDING: _APPS}

#: surface -> how that surface differs: its identity bar, what it repaints for, what opens
#: itself, its prose line and its geometry. Registered with :func:`xess_surface`.
_SURFACE_DEFS = {}

#: A badge provider is free to ask what the OTHER apps are reporting, which is a cycle.
#: The PADD found this the expensive way - one provider entered 332 times for one badge,
#: unwound only by Python's recursion limit, and the error logged several times a second.
_BADGE_RUNNING = set()
_BADGE_REPORTED = set()


def _apps_for(surface):
    return _SURFACES.setdefault(surface, {})


def _key(base, surface):
    """A per-surface client-inventory key.

    Boarding keeps the bare name it has always written, so nothing on a live client's
    inventory moves and an upgrade mid-mission cannot lose a crew member's open app.
    """
    return base if surface == SURFACE_BOARDING else "%s:%s" % (base, surface)


def _view_key(surface):
    return VIEW if surface == SURFACE_BOARDING else "%s:%s" % (VIEW, surface)


def xess_surface(surface, title=None, identity=None, revision=None, auto_open=None,
                 home_text=None, identity_area=None, app_area=None, at_style=None):
    """Teach the device a new place to live.

    Everything a surface does differently is a callable here, so the shell itself holds no
    knowledge of any one console - and a surface's imports are reached only through its own
    descriptor. That is the whole point: a non-boarding panel must never drag the boarding
    and EVA modules in behind it.

    Args:
        surface (str): its name, used by every other function's ``surface=``.
        title (str, optional): the word at the top of the tile sheet. Defaults to "xESS".
        identity (callable, optional): ``identity(client_id) -> (name, job, at)``, the bar's
            three slots. ``None`` means NO identity bar - the panel is the app area alone.
        revision (callable, optional): ``revision(client_id) -> hashable``, folded in after
            ``(opened, focus, badges)``. What this surface must rebuild its app area for.
        auto_open (callable, optional): ``auto_open(client_id)`` - a surface that opens an
            app by itself (boarding opens ACT on a new beat). ``None`` means nothing does.
        home_text (callable, optional): ``home_text(client_id) -> str`` - prose above the
            tiles.
        identity_area (str | callable, optional): the bar's area, a style string or a
            zero-arg callable returning one.
        app_area (str | callable, optional): the app region's area, same forms.
        at_style (callable, optional): ``at_style(client_id, at) -> style`` for the third
            slot, when a surface needs to take it over (boarding's ARMED readout).

    Returns:
        dict: the descriptor.
    """
    surface = str(surface).strip().lower()
    _SURFACE_DEFS[surface] = {
        "surface": surface,
        "title": title or "xESS",
        "identity": identity,
        "revision": revision,
        "auto_open": auto_open,
        "home_text": home_text,
        "identity_area": identity_area,
        "app_area": app_area,
        "at_style": at_style,
    }
    _apps_for(surface)
    return _SURFACE_DEFS[surface]


def xess_surfaces():
    """Every surface name the device knows. An accessor because MAST cannot see a dict."""
    return sorted(_SURFACE_DEFS)


def _surface_def(surface):
    return _SURFACE_DEFS.get(surface, {})


def _area(value, fallback=None):
    """A descriptor's area: a style string, or a callable returning one."""
    if callable(value):
        return value()
    return value if value else fallback


def xess_register(key, title=None, icon=None, blurb=None, sort=100,
                  draw=None, badge=None, available=None, surface=SURFACE_BOARDING):
    """Put an app on the device.

    Args:
        key (str): its name, unique within its surface. Lower-cased.
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
        surface (str, optional): which surface it belongs to. Defaults to the handheld.

    Returns:
        dict: the registration.
    """
    key = str(key).strip().lower()
    surface = str(surface).strip().lower()
    app = {
        "key": key,
        "title": title if title else key.upper(),
        "icon": icon,
        "blurb": blurb or "",
        "sort": sort,
        "draw": draw,
        "badge": badge,
        "available": available,
        "surface": surface,
    }
    _apps_for(surface)[key] = app
    return app


def xess_unregister(key, surface=SURFACE_BOARDING):
    """Take an app off the device. True when there was one."""
    return _apps_for(surface).pop(str(key).strip().lower(), None) is not None


def xess_registered(surface=SURFACE_BOARDING):
    """Every app key on a surface. An accessor because MAST cannot see a module-level
    dict - only functions become MAST globals."""
    return sorted(_apps_for(surface))


def xess_clear():
    """Forget every registration, on EVERY surface. The mission reset calls this; the
    built-ins re-register themselves immediately after, so a reset never leaves a device
    with no apps.

    A mission's own surface goes away entirely - its descriptor as well as its apps -
    because the next mission has no reason to carry it. A mission re-registers its
    surfaces when its console opens, which is why that call has to be idempotent.
    """
    for table in _SURFACES.values():
        table.clear()
    for surface in [s for s in _SURFACES if s != SURFACE_BOARDING]:
        del _SURFACES[surface]
    _SURFACE_DEFS.clear()
    _BADGE_RUNNING.clear()
    _BADGE_REPORTED.clear()
    _register_builtins()


def xess_app_count(surface=None):
    """Reset-ledger probe: how many apps are registered. Every surface when none is named,
    so a mission's leftovers are counted too."""
    if surface is None:
        return sum(len(t) for t in _SURFACES.values())
    return len(_apps_for(surface))


def xess_apps(client_id=None, surface=SURFACE_BOARDING):
    """The apps this console may open, in tile order.

    An `available` that raises drops its own tile and nothing else - the same bargain the
    badge makes. A device that goes blank because one mission app asked an awkward
    question is worse than a device missing one tile.
    """
    cid = _client(client_id)
    out = []
    for app in _apps_for(surface).values():
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


def xess_opened(client_id=None, surface=SURFACE_BOARDING):
    """The app this console has open on this surface, or None for the tile sheet."""
    from ..inventory import get_inventory_value
    cid = _client(client_id)
    if cid is None:
        return None
    key = get_inventory_value(cid, _key(KEY_APP, surface), None)
    return key if key in _apps_for(surface) else None


def xess_open(client_id, key=None, surface=SURFACE_BOARDING):
    """Open an app on this console, or go home with ``None``.

    Leaving FIRE DISARMS. Walking away from a live weapon with the gun still up is
    exactly the accident the disarm-on-shot rule exists to prevent, one step earlier.
    That is the HANDHELD's rule, and the import that serves it lives inside the branch -
    a panel on some other console must not drag the boarding modules in to open a tile.
    """
    from ..inventory import set_inventory_value
    cid = _client(client_id)
    if cid is None:
        return False
    key = str(key).strip().lower() if key else None
    if key is not None and key not in _apps_for(surface):
        return False
    if surface == SURFACE_BOARDING and xess_opened(cid, surface) == APP_FIRE and key != APP_FIRE:
        from ..boarding_site import boarding_disarm
        boarding_disarm(cid)
    set_inventory_value(cid, _key(KEY_APP, surface), key)
    # a new app opens on its own first row
    set_inventory_value(cid, _key(KEY_FOCUS, surface), None)
    return True


def xess_focus(client_id=None, surface=SURFACE_BOARDING):
    """The row the open app is showing, for the apps that are a list and a detail."""
    from ..inventory import get_inventory_value
    cid = _client(client_id)
    return get_inventory_value(cid, _key(KEY_FOCUS, surface), None) if cid is not None else None


def xess_set_focus(client_id, value, surface=SURFACE_BOARDING):
    from ..inventory import set_inventory_value
    set_inventory_value(client_id, _key(KEY_FOCUS, surface), value)


def xess_revision(client_id=None, surface=SURFACE_BOARDING):
    """What an `on change` watches. PER CONSOLE.

    A shared counter would mean one crew member opening an app repainting five other
    screens. Carries the armed state so the device redraws the moment the weapon goes
    live - that visibility is a safety feature, not decoration - and the badges, so a
    tile that starts saying "2 new" is seen to say it.

    BOTH BODIES' ARMED STATE. A boarder has a cell to stand in or a suit to fly, and each
    holds its weapon somewhere different: the grid one in `boarding_armed` /
    `boarding_setting`, the suit's verb in `eva_armed`. Only the grid pair was watched, so
    pressing BEAM or TETHER in the suit's Fire app changed the state and moved nothing on
    screen - the `> ` marker stayed where it was. It was not dead, it was SLOW: the only
    other thing in this tuple a suit can shift is its badge, so the pick finally appeared
    whenever the nearest target's name or distance bucket happened to change. Stationary
    in front of one target, it never appeared at all.

    The running job needs nothing here - `_work_badge` already reports the countdown as
    "%ds", which changes every second and repaints on its own. Adding the seconds would
    force a rebuild every tick for a number the badge is already carrying.

    What is COMMON to every surface is here; what a surface adds is its descriptor's
    `revision`. Boarding's own half is `_boarding_revision`, so its imports are reached
    only when boarding is the surface being asked about.
    """
    cid = _client(client_id)
    if cid is None:
        return 0
    badges = tuple((a["key"], xess_app_badge(a)) for a in xess_apps(cid, surface))
    base = (xess_opened(cid, surface), xess_focus(cid, surface), badges)
    extra = _surface_def(surface).get("revision")
    if extra is None:
        return base
    try:
        return base + (extra(cid),)
    except Exception as e:                               # noqa: BLE001
        # A surface that cannot say what changed must not take the panel down with it.
        _report_once(surface, e, "revision")
        return base


def _boarding_revision(client_id):
    """The handheld's own half of the revision - see :func:`xess_revision`."""
    from ..boarding import boarding_seq
    from ..boarding_site import boarding_armed, boarding_setting
    from ..eva_tools import eva_armed
    # _team_health: the Crew app shows each member's HP, which nothing else here moves.
    return (boarding_seq(), boarding_armed(client_id), boarding_setting(client_id),
            eva_armed(client_id), _team_health())


def xess_panel_revision(client_id=None, surface=SURFACE_BOARDING):
    """What a panel's `on change` watches: the bar AND the app area.

    Two channels, deliberately. :func:`gui_xess_tick` updates the bar's three widgets in
    place and rebuilds the app region only when the app half moved, so a status line that
    ticks every second never rebuilds a listbox somebody is halfway through clicking.
    """
    cid = _client(client_id)
    if cid is None:
        return 0
    return (_bar_styles(cid, surface), xess_revision(cid, surface))


# --- the surface ------------------------------------------------------------------------

def gui_xess(client_id=None):
    """Build the handheld. The boarding surface of :func:`gui_xess_panel`."""
    return gui_xess_panel(client_id, SURFACE_BOARDING)


def gui_xess_panel(client_id=None, surface=SURFACE_BOARDING,
                   identity_area=None, app_area=None):
    """Build a panel: the identity bar, then the app area.

    The bar is a plain flow in its own section; the app area is a REGION, because it is
    the part that changes shape and a region is one of only two things in the library
    that can take its own content off the screen. A `gui_sub_section` cannot - refilling
    one leaves every earlier fill painted underneath, which is what three superimposed
    messages in the ePADD inbox turned out to be.

    A surface whose descriptor has no `identity` gets NO bar - the panel is the app area
    alone, and `gui_xess_tick` then has only one thing to do.

    Args:
        client_id (int, optional): the console. PASS IT: a panel on a console riding a
            detached camera cannot rely on the ambient page being its own.
        surface (str, optional): which surface to build. Defaults to the handheld.
        identity_area (str, optional): override the descriptor's bar area.
        app_area (str, optional): override the descriptor's app area.

    Returns:
        dict: the held widgets, also stored on the page for :func:`gui_xess_tick`.
    """
    from .section import gui_section, gui_region
    from .row import gui_row
    from .text import gui_text
    from .blank import gui_blank
    from .boarding_console import NAME_PX, SUB_PX

    cid = _client(client_id)
    sdef = _surface_def(surface)
    bar = _bar_styles(cid, surface)

    w_name = w_job = w_at = None
    if bar is not None:
        gui_section(_area(identity_area or sdef.get("identity_area")))
        # THE NAME GETS ITS OWN ROW. Sharing one with the job and the room made a long
        # name wrap, and the wrapped half left the bar and drew over the app below - the
        # engine does not clip. A name's length is not ours to control: it comes from a
        # roster, an auto-namer or a mission.
        gui_row("row-height: %dpx; background: %s; padding: 0, 6px, 0, 14px;"
                % (NAME_PX, PANEL_HEAD))
        w_name = gui_text(bar[0])

        gui_row("row-height: %dpx; background: %s; padding: 0, 0, 4px, 14px;"
                % (SUB_PX, PANEL_HEAD))
        w_job = gui_text(bar[1])
        gui_blank()
        w_at = gui_text(bar[2])

    app = gui_region(_area(app_area or sdef.get("app_area")))
    with app:
        _draw_app(cid, surface)

    view = {"cid": cid, "surface": surface, "name": w_name, "job": w_job, "at": w_at,
            "app": app, "bar": bar, "rev": xess_revision(cid, surface)}
    page = FrameContext.page
    if page is not None:
        setattr(page, _view_key(surface), view)
    return view


def gui_xess_tick(surface=SURFACE_BOARDING):
    """Refresh a panel in place. What an `on change` should CALL.

    Never a jump back to the screen label: that re-sends every widget on the console over
    the network, and a watcher would do it forever.

    TWO CHANNELS, AND THAT IS THE POINT. The bar's three widgets are updated whenever the
    bar's text moves; the app region is rebuilt only when the app half of the revision
    moves. A panel whose bar carries a countdown would otherwise rebuild its app every
    second - which, on a screen holding a selectable queue, means the row you are reaching
    for is replaced under the cursor. It also makes the bar honest: it used to be updated
    only when the APP's revision moved, so walking into a new room left the bar naming the
    old one until something unrelated happened to change.

    Returns:
        bool: False when the screen is gone - a handler can outlive the page.
    """
    from .update import gui_rebuild
    page = FrameContext.page
    view = getattr(page, _view_key(surface), None) if page is not None else None
    if not view:
        return False
    cid = view["cid"]
    _auto_open(cid, surface)

    # `view.get("name")`: a panel with no identity bar has no widgets to update, and a
    # caller (a test, a mission holding its own view) may have built a view without them.
    bar = _bar_styles(cid, surface) if view.get("name") is not None else None
    if bar is not None and bar != view.get("bar"):
        view["bar"] = bar
        # EVERY part, not only the interesting one. A bar that is right about the room and
        # stale about the name describes the previous person.
        view["name"].update(bar[0])
        view["job"].update(bar[1])
        view["at"].update(bar[2])

    rev = xess_revision(cid, surface)
    if rev == view.get("rev"):
        return True
    view["rev"] = rev
    gui_rebuild(view["app"])
    with view["app"]:
        _draw_app(cid, surface)
    return True


def _auto_open(client_id, surface=SURFACE_BOARDING):
    """The surface's own auto-open, if it has one."""
    opener = _surface_def(surface).get("auto_open")
    if opener is None:
        return False
    try:
        return opener(client_id)
    except Exception as e:                               # noqa: BLE001
        _report_once(surface, e, "auto_open")
        return False


def _boarding_auto_open(client_id):
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
    from ..eva_tools import eva_armed, eva_working
    seq = boarding_seq()
    if get_inventory_value(client_id, KEY_SEEN, None) == seq:
        return False
    set_inventory_value(client_id, KEY_SEEN, seq)
    # EITHER BODY'S WEAPON. A boarder has a cell to stand in or a suit to fly, and the
    # weapon lives somewhere different in each - only the grid one was checked, so a new
    # beat yanked a crew member off a suit holding BEAM, which is precisely the accident
    # this rule exists to prevent. A job already running counts too: taking the screen
    # away mid-cut loses the Stop button.
    if boarding_armed(client_id) or eva_armed(client_id):
        return False
    if eva_working(client_id)[0] is not None:
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

def _bar_styles(client_id, surface=SURFACE_BOARDING):
    """The bar's three STYLE strings, or None when this surface has no bar.

    Styles rather than the raw text, because comparing them is how the tick decides the
    bar moved - and the third slot's style is itself a signal on the handheld, where it
    turns red the moment the weapon is live.
    """
    sdef = _surface_def(surface)
    identity = sdef.get("identity")
    if identity is None:
        return None
    try:
        name, job, at = identity(client_id)
    except Exception as e:                               # noqa: BLE001
        _report_once(surface, e, "identity")
        return None
    at_style = sdef.get("at_style")
    if at_style is not None:
        try:
            third = at_style(client_id, at)
        except Exception as e:                           # noqa: BLE001
            _report_once(surface, e, "at_style")
            third = _dim_style(at)
    else:
        third = _dim_style(at)
    return (_name_style(name), _job_style(job), third)


def _identity(client_id):
    from ..boarding import boarding_me, boarding_job_text
    from .boarding_console import where_text
    who = to_object(boarding_me(client_id))
    if who is None:
        return "Observer", "watching", where_text(client_id)
    return who.name, boarding_job_text(who, default="aboard"), where_text(client_id)


def _dim_style(text):
    """The third slot, for a surface that has nothing special to say with it.

    SHRINK, NEVER WRAP. The bar is two rows by construction, so a slot that wraps leaves
    the bar and draws over the app beneath it - the engine does not clip. Boarding's
    third slot is a room name or "ARMED - BEAM" and never had the problem; the Admiral's
    is a status line written by a mission ("No extractors yet - build an Extractor on a
    worldlet to produce ore and gas."), and a mission's sentence is not ours to keep
    short. Seen in the engine, 2026-09-19.
    """
    return ("$text:%s;font:gui-1;color:%s;col-width: content;overflow:shrink;"
            % (_esc(text), DIM))


def _name_style(name):
    return "$text:%s;font:gui-2;overflow:shrink;" % _esc(name)


def _job_style(job):
    # Shrink for the same reason as the third slot: two rows, and nothing clips.
    return ("$text:%s;font:gui-1;color:%s;col-width: content;overflow:shrink;"
            % (_esc(job), ACCENT))


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

def _draw_app(client_id, surface=SURFACE_BOARDING):
    """The open app, or the tile sheet when none is."""
    key = xess_opened(client_id, surface)
    if key is None:
        return _home(client_id, surface)
    app = _apps_for(surface).get(key)
    draw = app.get("draw") if app else None
    if draw is None:
        return _home(client_id, surface)
    try:
        return draw(client_id)
    except Exception as e:                               # noqa: BLE001
        # An app that blows up costs itself, not the device. Without this the crew
        # console goes blank and there is no way back to the tiles.
        _report_once(key, e, "draw")
        from .row import gui_row
        from .text import gui_text
        gui_xess_head(client_id, app["title"] if app else key, surface=surface)
        gui_row("row-height: 1fr;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("This app stopped. Back, and try another."), WARN))


def gui_xess_head(client_id, title, back=True, surface=SURFACE_BOARDING):
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
        gui_button("Back",
                   on_press=lambda _cid=client_id, _s=surface: xess_open(_cid, None, _s))


def _home(client_id, surface=SURFACE_BOARDING):
    """The tile sheet: what is happening, then the tools.

    The scene's line is here AS WELL AS inside ACT, so the device always has something to
    say when you glance at it and you are never answering a question you scrolled past.
    A surface with no `home_text` simply has tiles.
    """
    from .row import gui_row
    from .text import gui_text, gui_text_area
    from .blank import gui_blank

    sdef = _surface_def(surface)
    gui_row("row-height: 2.2em; font:gui-2; padding: 10px, 8px, 10px, 4px;")
    gui_text("$text:%s;font:gui-2;color:%s;" % (_esc(sdef.get("title") or "xESS"), ACCENT))

    prose = sdef.get("home_text")
    try:
        line = (prose(client_id) or "") if prose is not None else ""
    except Exception as e:                               # noqa: BLE001
        _report_once(surface, e, "home_text")
        line = ""
    if line:
        # A text area, not a text: prose, several lines, and it scrolls itself rather
        # than spilling over what is under it. CAPPED for the same reason as in ACT - on
        # `1fr` it took every pixel the tiles were not using and pushed them to the foot
        # of the column.
        gui_row("row-height: %dpx;" % BEAT_PX)
        gui_text_area(line)

    for app in xess_apps(client_id, surface):
        _tile(client_id, app, surface)

    # The slack goes HERE, under the tiles, rather than into the prose or into the last
    # tile. A row that flexes is the only way to say "leave the rest empty"; without one
    # the tiles are stretched to fill the column.
    gui_row("row-height: 1fr;")
    gui_blank()


def _tile(client_id, app, surface=SURFACE_BOARDING):
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
    # A click region is matched by tag alone, so a second panel on the same screen needs
    # its own tags. The handheld keeps the bare tag it has always emitted - it is the one
    # surface that existed before there were surfaces, and its tags are asserted.
    click = ("xess-app-%s" % key if surface == SURFACE_BOARDING
             else "xess-app-%s-%s" % (surface, key))
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

    def _open(event, sender, _key=key, _tag=click, _surface=surface):
        # FILTERED. `Layout.on_message` hands every event to every callback during its
        # walk of the tree, not only ones aimed at this one - a listbox filters first, a
        # plain section does not. Unfiltered, any click anywhere would open an app, and
        # which one would depend on tree order.
        if getattr(event, "sub_tag", None) != _tag:
            return
        xess_open(client_id, _key, _surface)

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
        hp, max_hp = _crew_health(lf)
        people.append({"id": to_id(lf), "name": who.name,
                       "job": boarding_job_text(who, default="aboard"),
                       "room": room, "to": message_crew_token(lf),
                       "you": to_id(lf) == mine, "hp": hp, "max_hp": max_hp})
    out.extend(sorted(people, key=lambda p: str(p["name"]).lower()))
    out.append({"id": "all", "name": "Everyone", "job": "all channels", "room": "",
                "to": "*", "you": False})
    return out


def _crew_health(lifeform):
    """(hp, max_hp) for a party member, read off the BODY they walk around in - the
    figure on the grid carries the HP, not the person. (None, None) when they have no
    body on this interior, so nothing is shown rather than a made-up full bar."""
    try:
        from ..boarding_site import boarding_figure_of
        from ..internal_damage import grid_get_max_hp
        from ..inventory import get_inventory_value
        fig = boarding_figure_of(lifeform)
        if fig is None:
            return None, None
        max_hp = int(grid_get_max_hp() or 0)
        return int(get_inventory_value(fig, "HP", max_hp) or 0), max_hp
    except Exception:                                    # noqa: BLE001
        return None, None


def _team_health():
    """Every party member's HP, for the revision - a hit repaints the Crew app."""
    try:
        from ..boarding import boarding_team
        return tuple(sorted((to_id(lf), _crew_health(lf)[0]) for lf in (boarding_team() or ())))
    except Exception:                                    # noqa: BLE001
        return ()


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
    # ONE text area: the caller's FACE leading their name and job, where they are, then
    # what they last said. It was a colored text line, a room word squeezed beside it,
    # and the message below - three widgets, no face.
    gui_row("row-height: 1fr; padding: 8px, 8px, 0, 8px;")
    gui_text_area(_caller_detail_text(item, last))

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


def _caller_detail_text(item, last):
    """The Crew detail as text-area markdown - see :func:`_caller_detail`.

    A person's line leads with their face (two text lines tall); the ship and "Everyone"
    have no face and lead with nothing. Values are made safe for a table cell and a
    lead line: a `|` would split the row, a `]` or `)` would end the face reference.
    """
    def _safe(text):
        return str(text if text is not None else "").replace("|", "/").replace(chr(10), " ").strip()

    head = "%s - %s" % (_safe(item.get("name")), _safe(item.get("job")))
    face = ""
    if isinstance(item.get("id"), int):
        try:
            from ...faces import get_face
            face = get_face(item["id"]) or ""
        except Exception:                                # noqa: BLE001
            face = ""
    face = face.replace(")", "").replace("]", "").replace("?", "")
    lines = ["![](face://%s) %s" % (face, head) if face else head]
    facts = []
    if item.get("room"):
        facts.append("| Room | %s |" % _safe(item["room"]))
    if item.get("max_hp"):
        facts.append("| Health | [HP](gauge://%d?max=%d&show=frac) |"
                     % (int(item.get("hp") or 0), int(item["max_hp"])))
    if facts:
        lines += ["", "| | |", "|:--|:--|"] + facts
    said = str(last.get("text") or "") if last is not None else "Nothing said yet."
    lines += ["", said]
    return chr(10).join(lines)


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


# The grid's own colors for a node's condition (engineering draws the same four), so
# a room reads the same on the handheld as on the engineer's screen.
_CONDITION_COLOR = {"damaged": "Crimson", "worn": "Gold", "tuned": "#40E0E0",
                    "nominal": "springgreen"}


def _condition(room):
    """How a node is doing: its condition as a colored pip and a word, then its wear
    as a gauge. Text-area markdown - the same text is filed to the survey log, so the
    ePADD Survey entry draws the same readout."""
    try:
        from ..internal_damage import (grid_node_state, grid_node_wear,
                                       WEAR_WORN_MIN, WEAR_TUNED_MAX)
        state = grid_node_state(room)
        wear = min(1.0, max(0.0, float(grid_node_wear(room))))
    except Exception:                                    # noqa: BLE001
        return "No condition reading."
    color = _CONDITION_COLOR.get(state, "white")
    # Wear is more-is-worse, so the gauge is INVERTED: yellow from the worn line,
    # red when nearly worn out; a tuned node keeps the tuned cyan.
    bar = "%s?max=1&show=pct&invert=1&warn=%s&crit=0.15" % (
        round(wear, 3), round(1.0 - WEAR_WORN_MIN, 3))
    if wear <= WEAR_TUNED_MAX:
        bar += "&color=#40E0E0"
    return "\n".join([
        "![](icon://square?color=%s) %s" % (color, state.capitalize()),
        "[Wear](gauge://%s)" % bar,
    ])


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
    from ..eva_tools import (VERB_BEAM, VERB_TETHER, eva_abort, eva_aim, eva_arm,
                             eva_armed, eva_disarm, eva_reach, eva_selected_target,
                             eva_targets, eva_use, eva_working)

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

    # WHAT THE CREW ALREADY SELECTED WINS. A suit is a player ship, so it has the same
    # weapons selection every other console does - and a click on the 2D view and a row in
    # this list should be the same act rather than two competing ideas of the target.
    aimed = eva_selected_target(client_id)

    rows = []
    for key, label, kind, gap, verbs in eva_targets(client_id):
        ok = held in verbs
        mark = "" if ok else "  (wrong tool)"
        on = (key == aimed)
        rows.append((key, "%s%s   %d%s" % ("> " if on else "", label, int(gap), mark),
                     on, ok, kind))
    if not rows:
        gui_row("row-height: 1fr;")
        gui_text("$text:%s;font:gui-2;color:%s;"
                 % (_esc("Nothing in reach. Fly closer."), DIM))
    else:
        gui_row("row-height: 1fr; padding: 4px, 8px, 4px, 8px;")
        lb = gui_list_box(rows, "item-gap: 0.3em;", item_template=_fire_row,
                          select=True, reveal=True)

        def _use(event, sender):
            item = lb.get_value()
            if item is None:
                return
            # SELECTING AIMS; a second press works. Locking on a thing and cutting it are
            # two decisions, the same way choosing a verb and using it are - and a list
            # where touching a row fires a beam is a list nobody can browse.
            if item[0] == aimed:
                eva_use(client_id, item[0])
            else:
                eva_aim(client_id, item[0])

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

    # The row carries what the RENDERER needs, which is not what `eva_points` returns -
    # that is a three-tuple its callers destructure, so the flags are asked for here.
    from ..eva import eva_seen, eva_visited
    rows = [(name, "%s   %s" % (label, _nav_far(client_id, pos)),
             eva_visited(client_id, name), eva_seen(client_id, name))
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


#: What a destination's row says about itself. ASCII, because the engine draws no others,
#: and two characters wide so the names still line up.
NAV_MARK_VISITED = "* "     # been there
NAV_MARK_SEEN = "- "        # its marker lit, but the suit never arrived
NAV_MARK_NEW = "  "


def _nav_mark(item):
    """The prefix for one destination. Visited beats seen - arriving implies seeing.

    A nav row is ``(name, label, visited, seen)``; anything shorter is a caller that
    predates the marks and draws a blank rather than raising.
    """
    if len(item) > 2 and item[2]:
        return NAV_MARK_VISITED
    if len(item) > 3 and item[3]:
        return NAV_MARK_SEEN
    return NAV_MARK_NEW


#: A reach target's color, by what can be done to it. The 2D view colors a contact by
#: what it IS; this colors it by what the held tool can do with it, which is the question
#: the app exists to answer.
FIRE_COLOR_AIMED = "#f66"      # locked on - the same red the ARMED banner uses
FIRE_COLOR_READY = "#8cf"      # in reach, and the held verb works on it
FIRE_COLOR_WRONG = "#9ab"      # in reach, wrong tool held


def _fire_row(item, **kwargs):
    """One reach target. Colored by whether the held tool can do anything with it.

    Returns None so the listbox sizes it - see `_choice_row` for why returning a size
    kills selection.
    """
    from .row import gui_row
    from .text import gui_text
    aimed = len(item) > 2 and item[2]
    ok = len(item) > 3 and item[3]
    color = FIRE_COLOR_AIMED if aimed else (FIRE_COLOR_READY if ok else FIRE_COLOR_WRONG)
    gui_row("row-height: 1.6em; padding: 6px, 4px, 6px, 4px; background: %s;" % PANEL_HI)
    gui_text("$text:%s;font:gui-2;overflow:shrink;color:%s;"
             % (_esc(str(item[1])), color))


def _nav_row(item, **kwargs):
    """One destination as a list row. Returns None, so the listbox sizes it - see
    `_choice_row` for why returning a size kills selection.

    A RUIN IS A MAP YOU ARE DRAWING. Without a mark, every room reads the same whether
    the crew cleared it an hour ago or have never been near it, and the only record of
    where they had been was in their heads. Visited is dimmed: it is done, and the row
    worth looking at is the one that is not.
    """
    from .row import gui_row
    from .text import gui_text
    visited = len(item) > 2 and item[2]
    gui_row("row-height: 1.6em; padding: 6px, 4px, 6px, 4px; background: %s;" % PANEL_HI)
    gui_text("$text:%s;font:gui-2;overflow:shrink;color:%s;"
             % (_esc(_nav_mark(item) + str(item[1])), DIM if visited else ACCENT))


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


def _boarding_home_text(client_id):
    from ..boarding import boarding_line
    return boarding_line() or ""


def _register_builtins():
    # THE HANDHELD IS A SURFACE LIKE ANY OTHER. Everything boarding-specific about the
    # shell is named here - its bar, what it repaints for, what opens itself, its prose
    # and its geometry - so nothing else in this file reaches for a boarding module.
    from .boarding_console import boarding_identity_area, boarding_app_area
    xess_surface(SURFACE_BOARDING, title="xESS",
                 identity=_identity, revision=_boarding_revision,
                 auto_open=_boarding_auto_open, home_text=_boarding_home_text,
                 identity_area=boarding_identity_area, app_area=boarding_app_area,
                 at_style=_at_style)
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
    xess_register(APP_NAV, title="Nav", icon="helm-wheel", sort=25,
                  blurb="Where you can go, and going there",
                  draw=_nav_app, badge=_nav_badge, available=_in_a_suit)


_register_builtins()
