"""ePADD - one console tab that holds the apps.

The console tab strip is a junk drawer. A bridge console carries `help`, `library`,
`upgrade`, `quest` and (in a dev build) `debug` before Engineering adds `fabricate`
and `cargo` - seven of the eight slots `TAB_MAX_VISIBLE` allows, after which the rest
roll into a `More (n)` dropdown. And the strip cannot be ordered: position is `.mast`
load order, reversed by `add_front`, and the button label is the raw lowercase route
path, so every tab reads `fabricate`, `upgrade`, `cargo`.

ePADD replaces the strip with ONE button. Opening it gives a home screen of app tiles,
grouped and scoped to the station that should see them. An app IS a tab - the same
`//gui/tab/<name>` route, unchanged - plus the presentation the route grammar has no
room for (`[\\w]+` and an optional `if` is the whole of it).

    //gui/tab/cargo                       # untouched
        jump cargo_screen

    gui_app_register("cargo", title="Cargo", icon="cargo",
                     consoles="engineering", group="Ship", sort=10)

ALWAYS ON. It used to be opt-in, with `gui_app_mode()` per client and an
`EPADD_ENABLED` setting behind it. That went when apps became their own route kind: an
app is no longer a tab, so switching the PADD off does not fall back to the classic
strip - it leaves the apps with no way in at all. Nothing about the declare-every-build
contract changes: the page still consumes `console_tabs` and `__back_tab__` every build.

AN APP IS ITS OWN ROUTE KIND. A screen on the PADD is `//gui/app/<name>`, not
`//gui/tab/<name>`, because the two answer different questions: a tab's `if` says
whether it may be OFFERED ON THE BAR, an app's says whether the app is AVAILABLE. One
route kind doing both is what let `//gui/tab/away if not gui_app_mode_is_on()` hide the
away tab correctly and delete the way back to the away console with it.

There used to be an ADOPTION bridge here: a tab nobody registered showed up under
"Other" so an addon that had never heard of ePADD kept working. It was removed when
apps got their own route kind - a name can no longer be both - so an app that names a
route no `.mast` declares is now REPORTED rather than silently left off the PADD.
"""
from ...agent import Agent
from ...helpers import FrameContext
from ..inventory import get_inventory_value, set_inventory_value


APPS_KEY = "__EPADD_APPS__"
#: There is NO on/off any more, and that is a consequence of the app/tab split rather
#: than a simplification for its own sake. Apps are `//gui/app` routes, so they are not
#: on the tab bar at all - with the PADD suppressed an engineering console draws its
#: Back button and nothing else, and Cargo, Fabricate, Help, Library, Quests and
#: Upgrades become unreachable. "Off" is not the classic strip any more; it is no way in.

# Groups render in this order; anything else lands after them alphabetically.
GROUP_ORDER = ["Ship", "Mission", "Systems"]

#: The PADD's own shell route. It is an app like any other - which is what keeps it off
#: `__active_tab__` and so preserves the tab a player was on - but it is the CONTAINER,
#: not a tile inside itself.
SHELL_APP = "epadd"

#: App names already reported as having no route. Per mission; cleared by
#: `reset_mission_state`, which is also what stops the same line every build.
_MISSING_ROUTE_REPORTED = set()

# `normal_engi` is what the engine calls the console; `engineering` is what everything
# a script writes calls it. This table lived, unused, inside gui_queue_console_tabs -
# it computed the translation and then never applied it. Scoping needs it, so it moves
# here and the page uses this one.
CONSOLE_ALIASES = {
    "normal_helm": "helm",
    "normal_weap": "weapons",
    "normal_sci": "science",
    "normal_engi": "engineering",
    "normal_comm": "comms",
}


def _console_identity(client_id=None):
    """Which console this client is on, for scoping the app list.

    The BUILD's own declaration first, the door's record as the fallback - the same
    precedence `MastStoryPage._console_identity` uses, and for the same reason.

    Reading `page.console` alone is what broke here: it is per BUILD and reset to "" at
    every swap, and the PADD's own screens declare no console at all. So once a player
    opened the PADD, `_scoped_here` saw "" and dropped every app scoped to a console -
    Cargo and Fabricate on engineering, Airwing and Casino on the hangar - and
    `gui_app_revision` moved for the same reason, re-entering home once on its own. The
    guard existed in the page and had been applied in one place only.
    """
    page = FrameContext.page
    page_console = getattr(page, "console", None) if page is not None else None
    if page_console:
        return page_console
    cid = _client_id() if client_id is None else client_id
    return get_inventory_value(cid, "CONSOLE_TYPE", None)


def epadd_console_name(console):
    """The name a script would use for a console, whatever the engine calls it."""
    if console is None:
        return None
    console = str(console).strip().lower()
    return CONSOLE_ALIASES.get(console, console)


def _client_id():
    """Whose PADD this is: the PAGE's client, not the current event's.

    Same rule, and the same reason, as `console_tab._tab_client_id` - a page that
    rebuilds because something else emitted a signal runs under the EMITTER's event
    while `FrameContext.page` is correctly the console's.
    """
    page = FrameContext.page
    cid = getattr(page, "client_id", None) if page is not None else None
    return FrameContext.client_id if cid is None else cid


def _apps():
    return Agent.SHARED.get_inventory_value(APPS_KEY, {})


def _save(apps):
    Agent.SHARED.set_inventory_value(APPS_KEY, apps)


# --- registration -----------------------------------------------------------------

AWAY_CONSOLE = "away"


def gui_app_register(tab, title=None, icon=None, consoles="*", group=None, sort=100,
                     description=None, status=None, away=False):
    """Present an existing `//gui/tab/<tab>` route as an ePADD app.

    The route is not touched and keeps its own `if` condition, which is still what
    decides whether the app is offered at all.

    Args:
        tab (str): the `//gui/tab/` path this app opens.
        title (str, optional): the tile's name. Defaults to the tab path, title-cased.
        status (callable | str, optional): a short live value for the tile's badge -
            "3 unread", "2 building", "42/60". A callable is called at build time and
            anything it raises is swallowed, because a badge must never be able to
            take the home screen down with it. This is what the crew read WITHOUT
            opening anything, and it is why the apps that carry live state do not each
            need a panel of their own.
        icon (str, optional): an icon NAME for `gui_icon_name` - a meaning or a look,
            never a sheet index. An unknown name draws nothing and says so once, so an
            app can be registered before its art exists.
        consoles (str, optional): comma list of console names, or "*" for every SHIP
            console. Matched after `epadd_console_name`, so "engineering" matches the
            engine's `normal_engi`. Defaults to "*".
        away (bool, optional): also offer this app to the away console. `"*"` does NOT
            include it: an away team is not everywhere on the ship, it is somewhere
            else entirely, and a landing party has no use for the cargo hold. An app
            opts in, or names `consoles="away"` to go there and nowhere else.
        group (str, optional): heading to file the tile under. Defaults to "Mission".
        sort (int, optional): order within the group, low first. Ties break on title.
        description (str, optional): the tile's second line.
    """
    tab = str(tab).strip().lower()
    if not tab:
        return
    apps = _apps()
    apps[tab] = {
        "tab": tab,
        "title": title if title else tab.replace("_", " ").title(),
        "icon": icon,
        "consoles": _console_set(consoles),
        "away": bool(away),
        "group": group if group else "Mission",
        "sort": sort,
        "description": description,
        "status": status,
    }
    _save(apps)


def gui_app_unregister(tab):
    """Drop an app registration. The `//gui/app/` route is untouched - it simply stops
    being offered on the PADD."""
    apps = _apps()
    if apps.pop(str(tab).strip().lower(), None) is not None:
        _save(apps)


def gui_app_is_registered(tab):
    return str(tab).strip().lower() in _apps()


def gui_app_get_registered():
    """Every registration, unfiltered - the raw table, for tools and tests."""
    return dict(_apps())


def _console_set(consoles):
    """"engineering, hangar" -> {"engineering", "hangar"}; "*" -> None, meaning any."""
    if consoles is None:
        return None
    if not isinstance(consoles, str):
        consoles = ",".join(str(c) for c in consoles)
    consoles = consoles.strip()
    if consoles in ("", "*"):
        return None
    return {epadd_console_name(c) for c in consoles.split(",") if c.strip()}


# --- the list the home screen draws ------------------------------------------------

def gui_app_list(console=None, client_id=None):
    """The apps this console should offer, in the order they should be drawn.

    Registered apps scoped to `console`. An entry whose `//gui/app/` route does not
    exist, or whose route condition is false right now, is left out - the route's own
    `if` is still the authority on whether a panel is available. A MISSING route is
    reported by name; it is almost always a typo or an unmigrated `//gui/tab`.

    Returns:
        list[dict]: each with tab, title, icon, group, sort, description, label.
    """
    from ...mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel

    if console is None:
        console = _console_identity(client_id)
    console = epadd_console_name(console)

    routes = GuiAppDecoratorLabel.all
    task = FrameContext.task
    apps = _apps()
    out = []
    seen = set()

    def route_ok(tab):
        label = routes.get(tab)
        if label is None:
            # SAID, NOT SWALLOWED. An app registered against a route no `.mast`
            # declares used to be dropped in silence - no tile, no log - and with the
            # adoption bridge gone that is the entire failure mode of a mistyped or
            # unmigrated route. Once per name per mission.
            if tab not in _MISSING_ROUTE_REPORTED:
                _MISSING_ROUTE_REPORTED.add(tab)
                from ..execution import log
                log(f"app {tab!r} has no //gui/app/{tab} route - it cannot be opened, "
                    f"so it is left off the PADD", "epadd", "warning")
            return None
        if task is not None and isinstance(label, GuiAppDecoratorLabel):
            if not label.test(task):
                return None                 # its own `if` says no
        return label

    for tab, app in apps.items():
        if tab == SHELL_APP:
            continue                        # the PADD is not a tile on itself
        if not _scoped_here(app, console):
            continue
        label = route_ok(tab)
        if label is None:
            continue
        entry = dict(app)
        entry["label"] = label
        out.append(entry)
        seen.add(tab)

    out.sort(key=lambda a: (_group_rank(a["group"]), a["group"],
                            a["sort"], a["title"].lower()))
    return out


def _scoped_here(app, console):
    """Whether this app belongs on this console.

    `"*"` means every SHIP console. The away console has to be named or opted into,
    because a landing party carrying the fabricator is not a scoping bug anybody would
    notice until it was on screen.
    """
    wanted = app.get("consoles")
    if console == AWAY_CONSOLE:
        return bool(app.get("away")) or (wanted is not None and AWAY_CONSOLE in wanted)
    if wanted is None:
        return True
    return console is None or console in wanted


def _group_rank(group):
    """GROUP_ORDER first in the order given, then anything else alphabetically."""
    try:
        return GROUP_ORDER.index(group)
    except ValueError:
        return len(GROUP_ORDER)


def gui_app_revision(console=None, client_id=None):
    """What the HOME screen watches to know it must repaint.

    A signal does not wake `await gui()`, so the home screen polls - the same shape
    the inbox and the away console use. Two things change under it: a badge (mail
    arrives, a build finishes) and the app LIST itself, because a route condition can
    turn an app on or off while the PADD is open. Without this the home screen was
    frozen at whatever it said when it was opened.

    Cheap: the badges are computed for the tiles anyway.
    """
    parts = []
    for app in gui_app_list(console, client_id):
        parts.append(app.get("tab") or "")
        parts.append(gui_app_badge(app) or "")
    return hash(tuple(parts)) & 0x7FFFFFFF


def gui_app_groups(console=None, client_id=None):
    """`gui_app_list` folded into (heading, apps) pairs, in drawing order.

    An empty group is not returned at all, which is why Helm - registering no ship
    apps - draws no "Ship" heading rather than an empty one.
    """
    groups = []
    for app in gui_app_list(console, client_id):
        if not groups or groups[-1][0] != app["group"]:
            groups.append((app["group"], []))
        groups[-1][1].append(app)
    return groups


def _apps_count():
    """Reset-ledger probe. `Agent.SHARED` is rebuilt by `clear_shared()` on every
    mission reset, so this should always report 0 after one - it is registered so that
    a future move off SHARED cannot go unnoticed."""
    try:
        return len(_apps())
    except Exception:
        return 0


# --- the shell ---------------------------------------------------------------------
# One place for the numbers, so the design canvas and the code cannot drift. Values
# from design/epadd/Spec.dc.html, which took them off the engine and off LM.
PANEL = "#1572"          # the house panel fill
PANEL_HI = "#1575"       # hover / selected
PANEL_HEAD = "#1578"     # the PADD bar, and every list title section
ACCENT = "#8cf"
DIM = "#9ab"
BAR_HEIGHT = "1em+16px"
# A grid row that declares nothing is 1fr and shares out the whole sheet, so
# three short bands of cards stretch over the screen. Size them to content.
TILE_ROW = "row-height: content;"
TILE_GAP = "14px"     # between cards; padding would sit inside the panel
TILE_COLUMNS = 4
TILE_COLUMNS_DENSE = 6   # past DENSE_AFTER apps, narrower tiles without descriptions
DENSE_AFTER = 12
# A tile narrower than this cannot hold an icon and a title on one line, and a title
# that wraps makes its tile a different height from every other tile - which is what
# "the brain scan behaves different than the others" was at 1024x768. "Brain scan" is
# the only two-word title LM registers, so it was the only one that could wrap.
#
# 300px is also where the mock and the engine agree about wrapping (measure.py: >=600
# is exact, >=300 is 94%, below that they diverge), so it is the width below which a
# layout tuned here stops predicting the bridge.
MIN_TILE_PX = 300

# What a band actually costs, so the code can work out whether the tiles fit instead
# of anyone predicting it. These follow the styles below - change one, change both.
BODY_TOP_PX = 45      # where a console's content starts, under the 35px strip
BAR_PX = 40           # BAR_HEIGHT "1em+16px" at the default gui-2 row font
HEADING_PX = 40       # a gui-1 heading line plus its row padding
TILE_PX = 88          # title 32 + description 22 + padding 20 + margin 14
TILE_PX_DENSE = 66    # the same without the description


def gui_app_open(tab):
    """Open an app: send the GUI task to that app's label.

    The same two lines `TabControl.on_message` runs when a tab button is clicked, so
    an app opened from the PADD arrives exactly as a tab would have.

    Returns:
        bool: False when the app has no route or there is no GUI task to send.
    """
    from ...mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
    tab = str(tab).strip().lower()
    # A ROUTE IS A SCREEN; a REGISTRATION is a tile. `gui_app_list` reads the registry,
    # so an app route with no `gui_app_register` is reachable from another screen and
    # never appears on the home grid - which is all a "page" ever needed to be. A
    # second route kind for that was a second mechanism for one distinction.
    label = GuiAppDecoratorLabel.all.get(tab)
    if label is None:
        # SAID, NOT SWALLOWED. A tile whose route is missing used to do NOTHING when
        # pressed, with no log - "clicking the app does not go to the app", and nothing
        # to go on. The likeliest cause is a half-built install: a library that reads the
        # app table beside a mastlib still declaring `//gui/tab`, so rebuild BOTH.
        if tab not in _MISSING_ROUTE_REPORTED:
            _MISSING_ROUTE_REPORTED.add(tab)
            from ..execution import log
            log(f"no //gui/app/{tab} route - opening it can do nothing. If it used to "
                f"be a //gui/tab, rebuild the mastlib too", "epadd", "warning")
        return False
    page = FrameContext.page
    task = getattr(page, "gui_task", None) if page is not None else None
    if task is None:
        return False
    _nav_push(tab)
    task.jump(label)
    task.tick_in_context()
    return True


# --- the PADD's own navigation ----------------------------------------------------
#
# THE PADD KNOWS WHERE IT IS. Opening an app used to be `task.jump(label)` and nothing
# else - the same call a tab click makes - so the PADD had no idea it was open, and its
# Back had to be reconstructed from tab state. A stack of its own is what lets home be a
# STATE rather than an app you happen to open, and gives a future app-to-app drill-down
# a real way back.
#
# NOT `procedural/gui/navigation.py`. Its `gui_history_jump` / `gui_history_back` look
# like exactly this, but `gui_history_store` is a STUB that computes `back_label` and
# returns without storing it, and nothing in the library or in LegendaryMissions calls
# any of it. An unexercised API is a worse bet than a small stack that does one job.
# Please do not "helpfully" merge them without fixing that first.

#: Per client, the apps entered, deepest last. It rides the client's own Agent
#: inventory, which `reset_mission_state` wipes wholesale via `Agent.clear()` - the same
#: place `__active_tab__` and `__active_app__` live - so it needs no reset-ledger entry
#: of its own. A module-level container WOULD have needed one.
NAV_KEY = "epadd_nav"


def _nav(client_id=None):
    cid = _client_id() if client_id is None else client_id
    return list(get_inventory_value(cid, NAV_KEY, None) or [])


def _nav_set(stack, client_id=None):
    cid = _client_id() if client_id is None else client_id
    set_inventory_value(cid, NAV_KEY, list(stack))


def _nav_push(tab):
    """Record a screen as entered. HOME IS AN ENTRY, like a browser's first page.

    That is what makes a separate HOME button redundant: with history [home, messages],
    Back from Messages IS home, and Back from home is what leaves the PADD. A HOME
    control would only be a second way to do what Back already does.
    """
    stack = _nav()
    if stack and stack[-1] == tab:
        return                          # a repaint re-opening the current screen
    stack.append(tab)
    _nav_set(stack)


def gui_app_depth(client_id=None):
    """How many screens deep this client is. 0 is "not in the PADD", 1 is home."""
    return len(_nav(client_id))


def gui_app_back(client_id=None):
    """One step back inside the PADD.

    Browser semantics. Pops the current screen and returns the one underneath, which
    from an app is HOME. Returns None when there is nothing underneath - the caller's
    cue to leave the PADD entirely, which is what Back at home means.
    """
    stack = _nav(client_id)
    if len(stack) < 2:
        return None
    stack.pop()
    _nav_set(stack, client_id)
    target = stack[-1]
    # Re-entering re-pushes, so pop to the one BELOW and let the open put it back -
    # otherwise going back would grow the trail instead of shortening it.
    stack.pop()
    _nav_set(stack, client_id)
    gui_app_open(target)
    return target


def gui_app_nav_reset(client_id=None):
    """Forget the trail - leaving the PADD, and the mission reset."""
    _nav_set([], client_id)


def _esc(text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
    from ...helpers import gui_text_escape
    return gui_text_escape("" if text is None else str(text))


def gui_app_chrome(title, subtitle=None, back_text="<", on_back=None):
    """The PADD's own nav bar. Every screen inside the PADD draws it.

    ePADD owns this row and nothing below it, so an app's own body is unchanged.

    ONE CONTROL, BROWSER-STYLE. It used to be a HOME button, which became redundant the
    moment the PADD kept a real history: with a trail of [home, Messages], Back from
    Messages IS home, so HOME was a second way to do what Back already does. Back at
    home leaves the PADD for the tab the console came from.

    IDENTITY IS NOT HERE ANY MORE. The strip's status region owns who this console is -
    it has to, because it is also the way IN to the PADD from a console - and drawing it
    here as well put two names in the same band, which is what the playtest screenshot
    caught. The chrome owns navigation; the strip owns identity.

    Args:
        title (str): the screen's name.
        subtitle (str, optional): a second, dimmer line of context.
        back_text (str, optional): the back control's label.
        on_back (callable | label, optional): what Back does. Defaults to the PADD's own
            history, so a screen does not need to know what opened it.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .blank import gui_blank

    if on_back is None:
        on_back = lambda *_a: gui_app_go_back()

    gui_row(f"row-height: {BAR_HEIGHT}; background: {PANEL_HEAD};")
    gui_button(f"$text:{_esc(back_text)};", style="col-width: content;",
               on_press=on_back)
    gui_text(f"$text:{_esc(title)};font:gui-4;", style="col-width: content;")
    if subtitle:
        gui_text(f"$text:{_esc(subtitle)};font:gui-1;color:{DIM};",
                 style="col-width: content;")
    else:
        gui_blank()


def gui_app_go_back(client_id=None):
    """Back, as the chrome's control means it: one screen, or out of the PADD.

    `gui_app_back` returns None when there is nothing underneath - that is home - and
    leaving is then this function's job, because the history layer has no business
    knowing about tabs.
    """
    from .console_tab import gui_tab_get_active
    if gui_app_back(client_id) is not None:
        return True
    gui_app_nav_reset(client_id)
    # Out. Back to whatever tab the console was showing when the PADD was opened; an
    # app route never writes `__active_tab__`, so it still says.
    from ...mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
    label = GuiTabDecoratorLabel.all.get(gui_tab_get_active() or "")
    page = FrameContext.page
    task = getattr(page, "gui_task", None) if page is not None else None
    if label is None or task is None:
        return False
    task.jump(label)
    task.tick_in_context()
    return True


#: Tabs whose status provider is running right now, so a provider that asks for its own
#: badge is answered rather than re-entered. Cleared in a `finally`, so it cannot outlive
#: the call and does not need a reset-ledger entry.
_BADGE_RUNNING = set()

#: (tab, exception type) pairs already reported. A provider that keeps failing is worth
#: saying ONCE - it is called per tile per build AND by the badge ticker, so an unguarded
#: log is several lines a second for the rest of the mission.
_BADGE_REPORTED = set()


def gui_app_badge(app):
    """An app's live badge, as text.

    Never raises: a provider that throws costs its own tile a badge and nothing else.

    RE-ENTRANT PROVIDERS ARE ANSWERED, NOT RE-ENTERED. A provider is free to ask what
    the other apps are reporting - LM's Status tile does exactly that, counting the apps
    with something to say - and `status_rows` computes a badge for EVERY app, the asking
    one included. That is a cycle: the provider was entered 332 times for one badge
    (measured), unwound only when Python's own recursion limit tripped, and the
    RecursionError caught below was logged as "status provider for 'status' raised" on
    every badge computation, several times a second. The badge still came out right,
    which is why it read as noise rather than as a bug.
    """
    provider = app.get("status")
    if provider is None:
        return None
    tab = app.get("tab")
    if tab in _BADGE_RUNNING:
        return None                     # asked for its own badge; it has no answer yet
    _BADGE_RUNNING.add(tab)
    try:
        value = provider() if callable(provider) else provider
    except Exception as e:              # noqa: BLE001 - a badge never takes a page down
        from ..execution import log
        key = (tab, type(e).__name__)
        if key not in _BADGE_REPORTED:
            _BADGE_REPORTED.add(key)
            # NAME THE CAUSE. Without it this is the same unactionable line forever.
            log(f"status provider for {tab!r} raised "
                f"{type(e).__name__}: {e}", "epadd", "warning")
        return None
    finally:
        _BADGE_RUNNING.discard(tab)
    value = "" if value is None else str(value).strip()
    return value or None


def _tile(app, dense):
    """One app tile: a clickable panel holding its icon, name and description.

    The WHOLE panel is the hit target, not just a button inside it - a sub-section
    with `click_text` emits a click region over its own bounds (Layout._post_present),
    which is the same mechanism the tab strip and the text area's links use.
    """
    from .section import gui_sub_section
    from .row import gui_row
    from .text import gui_text
    from .icon import gui_icon_name
    from .message import gui_message_callback

    tab = app["tab"]
    title = app["title"]
    # click_tag is a real engine tag matched against event.sub_tag, so it has to be
    # unique per tile; the tab name already is.
    # margin, not just padding: padding is INSIDE the panel, so tiles drawn with
    # padding alone have their backgrounds touching and read as one block.
    # EMPTY click_text, not absent. The tile already shows its title, so flashing the
    # same word back while the finger is down says nothing - but a SUB-SECTION emits its
    # whole click region only when `click_text is not None` (`Layout._post_present`), so
    # dropping the property would make every tile decoration. `""` keeps the region and
    # draws no words. (A Column is different: it also emits on `click_tag` alone, which
    # is why the status slot in the strip can leave click_text unset.)
    style = (f"background: {PANEL};"
             f"click_tag: epadd-app-{tab};"
             f"click_text: ;"
             f"click_background: {PANEL_HI};"
             f"margin: 0, 0, {TILE_GAP}, {TILE_GAP};"
             f"padding: 14px, 10px, 14px, 10px;")
    tile = gui_sub_section(style=style)
    with tile:
        gui_row("row-height: content;")
        if app.get("icon"):
            # No icon name means no icon column and the title spans the row. An
            # unknown NAME is different: gui_icon_name draws nothing and says so
            # once, which is what lets an app be registered before its art exists.
            gui_icon_name(app["icon"], color=ACCENT, style="col-width: content;")
        # shrink, not wrap: a tile whose title takes two lines is a different
        # height from every other tile, and the engine does not clip - the second
        # line draws over the description.
        gui_text(f"$text:{_esc(title)};font:gui-4;overflow:shrink;")
        badge = gui_app_badge(app)
        if badge:
            gui_text(f"$text:{_esc(badge)};font:gui-1;color:{ACCENT};",
                     style="col-width: content;")
        if not dense and app.get("description"):
            gui_row("row-height: content;")
            gui_text(f"$text:{_esc(app['description'])};font:gui-1;color:{DIM};")

    # The callback MUST check the tag itself. Layout.on_message calls on_message_cb
    # for every event delivered to the item during the page's walk of the layout
    # tree, not only ones aimed at it - a listbox filters first, a plain section does
    # not. Unfiltered, any click anywhere on the PADD would open an app, and which
    # one would depend on tree order.
    click_tag = f"epadd-app-{tab}"
    item = getattr(tile, "sub_section", tile)

    def _open(event, sender, _tab=tab, _tag=click_tag):
        if getattr(event, "sub_tag", None) != _tag:
            return
        gui_app_open(_tab)

    gui_message_callback(item, _open)
    return tile


def _columns_for(client_id, dense):
    """How many tiles fit across THIS client's screen.

    The layout is in percent, so four columns is four columns whether the console is
    1920 or 1024 wide - and at 1024 that is a ~230px tile with ~174px left for the
    title, where a two-word name wraps and that one tile stops matching its
    neighbours. Ask the client how wide it actually is.
    """
    want = TILE_COLUMNS_DENSE if dense else TILE_COLUMNS
    if client_id is None:
        return want
    try:
        from ...gui import get_client_aspect_ratio
        width = getattr(get_client_aspect_ratio(client_id), "x", 0) or 0
    except Exception:
        return want                      # no client to ask (tests, server-side build)
    if width <= 0:
        return want
    return max(1, min(want, int(width // MIN_TILE_PX)))


def _grid_fits(client_id, groups, columns, dense):
    """Whether the tiles fit on this screen without anything being cut off.

    There is no scrolling in a grid, and the engine does NOT clip - a band that runs
    out of room draws over whatever is under it. So the grid is for the case where
    everything fits, and the list below is for the case where it does not.

    A client that has not reported its size yet answers 1024x768 with z=99, and that
    assumption is deliberately kept rather than special-cased: assuming the SMALLEST
    common console is the safe direction, because a list that scrolls is never broken
    while a grid that overflows draws over itself. The page rebuilds once the real
    size arrives.
    """
    if client_id is None:
        return True
    try:
        from ...gui import get_client_aspect_ratio
        height = getattr(get_client_aspect_ratio(client_id), "y", 0) or 0
    except Exception:
        return True
    if height <= 0:
        return True
    available = height - BODY_TOP_PX - BAR_PX - len(groups) * HEADING_PX
    rows = sum(-(-len(apps) // max(1, columns)) for _, apps in groups)
    return rows * (TILE_PX_DENSE if dense else TILE_PX) <= available


def _app_row(item):
    """One row of the list the PADD falls back to. Sizes its ROW and returns None -
    a listbox only calls resize_to_content() when the template returns nothing, and an
    item section that keeps a returned size is degenerate, which kills the click
    region along with the selection."""
    from .row import gui_row
    from .text import gui_text
    from .icon import gui_icon_name
    from .listbox import gui_list_box_is_header
    if gui_list_box_is_header(item):
        return                      # the listbox draws its own headers
    gui_row("row-height: 1.6em;")
    if item.get("icon"):
        gui_icon_name(item["icon"], color=ACCENT, style="col-width: content;")
    gui_text(f"$text:{_esc(item['title'])};font:gui-3;overflow:shrink;")
    if item.get("description"):
        gui_text(f"$text:{_esc(item['description'])};font:gui-1;color:{DIM};")


def _app_list(groups):
    """The PADD's app sheet as a scrolling list, for when the tiles do not fit.

    A listbox brings the two things the grid has no answer for: it scrolls, and its
    headers collapse - so the groups survive rather than being flattened away.
    """
    from .row import gui_row
    from .listbox import (gui_list_box, gui_list_box_header, gui_list_box_is_header)
    from .message import gui_message_callback

    items = []
    for name, apps in groups:
        items.append(gui_list_box_header(name.upper()))
        items.extend(apps)

    gui_row("padding: 24px, 10px, 24px, 10px;")
    lb = gui_list_box(items, "item-gap: 0.2em;", item_template=_app_row,
                      select=True, collapsible=True, reveal=True)

    def _pick(event, sender):
        item = lb.get_value()
        if item is None or gui_list_box_is_header(item):
            return
        gui_app_open(item["tab"])

    gui_message_callback(lb, _pick)
    return lb


def gui_app_home(ship_name=None, columns=None, title="ePADD"):
    """Draw the PADD home screen for this console.

    Called from the `//gui/tab/epadd` route's screen label, which then sits in
    `await gui()` - so the tile handlers belong to a task that stays alive.

    Args:
        ship_name (str, optional): shown beside the wordmark.
        columns (int, optional): tiles per row. Defaults to 4, or 6 once the console
            carries more than twelve apps, where the descriptions are dropped too.
        title (str, optional): the wordmark.
    """
    from .section import gui_section
    from .row import gui_row
    from .text import gui_text
    from .blank import gui_blank
    from .grid import gui_grid

    page = FrameContext.page
    console = epadd_console_name(_console_identity())
    groups = gui_app_groups(console)
    total = sum(len(apps) for _, apps in groups)
    dense = total > DENSE_AFTER
    if columns is None:
        columns = _columns_for(getattr(page, "client_id", None), dense)

    # The body below the strip. 45px is where every console's content starts - the
    # strip is 35px on a 3% layout, and LM has drawn from 45px since.
    gui_section(style="area: 0, 45px, 100, 100;")

    gui_row(f"row-height: {BAR_HEIGHT}; background: {PANEL_HEAD};")
    # HOME HAS A BACK TOO, and at home it is what leaves the PADD - the bottom of the
    # history. Same control, same place, on every screen inside the PADD: a bar whose
    # first button moves depending on where you are is a bar you have to read.
    from .button import gui_button
    gui_button("$text:<;", style="col-width: content;",
               on_press=lambda *_a: gui_app_go_back())
    gui_text(f"$text:{_esc(title)};font:gui-4;", style="col-width: content;")
    if ship_name:
        gui_text(f"$text:{_esc(ship_name)};font:gui-1;color:{DIM};",
                 style="col-width: content;")
    gui_blank()
    if console:
        gui_text(f"$text:{_esc(console.upper())};font:gui-1;color:{DIM};",
                 style="col-width: content;")

    if not groups:
        gui_row("row-height: content; padding: 24px, 16px, 24px, 0;")
        gui_text(f"$text:No apps on this console.;font:gui-2;color:{DIM};")
        return

    # A grid does not scroll and the engine does not clip, so a sheet that overflows
    # draws over itself. Past what fits, the same apps become a scrolling list with
    # collapsible group headers - nothing is hidden either way.
    if not _grid_fits(getattr(page, "client_id", None), groups, columns, dense):
        _app_list(groups)
        return

    for name, apps in groups:
        gui_row("row-height: content; padding: 24px, 14px, 24px, 4px;")
        gui_text(f"$text:{_esc(name.upper())};font:gui-1;color:{ACCENT};")
        with gui_grid(columns, row_style=TILE_ROW):
            for app in apps:
                _tile(app, dense)


# --- the badge that is there without opening anything ---------------------------------
#
# Playtest: people liked the PADD and wanted two things it could not give them - to see
# the crew member they are playing, and to know there was something waiting without
# opening it to find out. Both want the same thing: one small readout that is always on
# screen.
#
# WHERE. The hard part was a spot that is the same on every console, and the engine's own
# `data/guiboxdata.txt` answers it: `ship_data` sits at `3, 5, 27, 47` on helm, weapons,
# engineering, science AND comms - identical. The band directly above it is free on all
# five (on science it must stop at x=27, where `radar_zoom_ctrl` at `27,0,68,6` begins).
# Engine `y=0` is the BOTTOM of the topbar, not the top of the screen.
#
# It gets its OWN background rather than sitting on the ship-data art that overhangs
# there, because the icon at the left collapses that panel: borrowed art would leave the
# badge as text over the radar exactly when the screen is busiest. For the same reason it
# does not collapse with the panel - a readout you have to un-hide is not a readout.
#
# Not part of the info panel itself, which was worth wanting and is not available:
# `ship_data` is an ENGINE widget the library can only send a rect to (see
# `gui_panel_ship_data_show`), never put a row inside. The engine owns its collapse too,
# so nothing here would be told when it fired.


def gui_app_identity_text(client_id=None, console=None):
    """What the badge says: who you are, and how much is waiting.

    None when there is nothing worth a line - then no badge is drawn at all, rather
    than an empty box on every console of a mission that uses none of this.
    """
    who = _identity_name(client_id)
    waiting = gui_app_waiting(console=console, client_id=client_id)
    if not who and not waiting:
        return None
    if not waiting:
        return who
    # ASCII only - this is drawn by the engine.
    return f"{who} ({waiting})" if who else f"ePADD ({waiting})"


def _identity_name(client_id):
    """The person at this console: their away character first, then their crew post.

    The away character wins because it is who they are RIGHT NOW - a crew member on the
    surface is playing that body, and the badge saying their bridge name there would be
    the stranger problem all over again.
    """
    try:
        from .away_gui import away_who, away_label
        active = away_who(client_id)
        if active is not None:
            return away_label(active)[0]
    except Exception:
        pass
    try:
        from ..crew import crew_post_of
        post = crew_post_of(client_id)
    except Exception:
        return ""
    if post is None:
        return ""
    name = getattr(post, "name", "") or ""
    rank = getattr(post, "rank", "") or ""
    return f"{rank} {name}".strip() if rank and name else name


def gui_app_waiting(console=None, client_id=None):
    """How many apps have something to say - the count the badge carries.

    Apps, not messages. Unread mail is only one of the things a badge reports, and the
    number a crew member cannot get any other way is "how many of these should I open".
    """
    total = 0
    try:
        apps = gui_app_list(console=console, client_id=client_id)
    except Exception:
        return 0
    for app in apps:
        if gui_app_badge(app):
            total += 1
    return total
