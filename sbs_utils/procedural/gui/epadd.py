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

OPT-IN, AND SILENT UNTIL ASKED. `gui_app_mode()` is per client and defaults OFF, so
a mission that never calls it draws the identical strip it draws today. Nothing about
the declare-every-build contract changes either: the page still consumes `console_tabs`
and `__back_tab__` at the end of every build.

NOTHING DISAPPEARS WHEN YOU TURN IT ON. A tab that no one registered as an app is
ADOPTED: it shows up under "Other" with its raw name. That is what makes the switch
safe to flip on a mission full of addons that have never heard of ePADD - and it is
why the adopted set comes from the CONSOLE's own `gui_tab_enable` calls rather than
from the route table. Walking the route table would surface every tab in the story on
every console, losing the per-console scoping four different LM addons already express
correctly; recording what the console actually enabled keeps all of it, for free.

`gui_app_adopt_record` is how that recording happens - `StoryPage` calls it as it
draws the ePADD strip, with the set it was about to draw.
"""
from ...agent import Agent
from ...helpers import FrameContext
from ..inventory import get_inventory_value, set_inventory_value


APPS_KEY = "__EPADD_APPS__"
MODE_KEY = "epadd_mode"            # per client
MODE_DEFAULT_KEY = "__EPADD_MODE__"  # mission-wide, on Agent.SHARED
ADOPTED_KEY = "epadd_adopted"

# Groups render in this order; anything else lands after them alphabetically, and
# "Other" - where adopted tabs go - is always last, because it is the leftovers.
GROUP_ORDER = ["Ship", "Mission", "Systems"]
ADOPTED_GROUP = "Other"

# ePADD's own furniture, never an app. Just the PADD itself: the console-switch tabs
# (helm/weapons/...) are deliberately NOT excluded, because a mission that turned
# ALLOW_CONSOLE_TABS on asked for them and adopting them keeps that working.
NEVER_AN_APP = {"epadd"}

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


# --- mode -------------------------------------------------------------------------

def gui_app_mode(on=True):
    """Turn the ePADD strip on for THIS client, overriding the mission default.

    Args:
        on (bool): True for the two-button ePADD strip, False for the classic strip.
    """
    set_inventory_value(_client_id(), MODE_KEY, bool(on))


def gui_app_mode_default(on=True):
    """Turn ePADD on for every console in the mission.

    This is the switch a mission actually throws - once, at the top level, off a
    setting. Doing it per client would mean a call in every console's activation
    path, and a console the mission does not own would never get one.

    A client that has called `gui_app_mode` keeps its own answer, so a single
    console can still be held back (or brought forward) on a mission-wide default.
    """
    Agent.SHARED.set_inventory_value(MODE_DEFAULT_KEY, bool(on))


def gui_app_mode_is_on(client_id=None):
    """Whether this client draws the ePADD strip: its own setting, else the
    mission default, else off - which is what every existing mission gets."""
    if client_id is None:
        client_id = _client_id()
    own = get_inventory_value(client_id, MODE_KEY, None)
    if own is not None:
        return bool(own)
    return bool(Agent.SHARED.get_inventory_value(MODE_DEFAULT_KEY, False))


# --- registration -----------------------------------------------------------------

def gui_app_register(tab, title=None, icon=None, consoles="*", group=None, sort=100,
                     description=None, status=None):
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
        consoles (str, optional): comma list of console names, or "*" for every
            console. Matched after `epadd_console_name`, so "engineering" matches the
            engine's `normal_engi`. Defaults to "*".
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
        "group": group if group else "Mission",
        "sort": sort,
        "description": description,
        "status": status,
        "adopted": False,
    }
    _save(apps)


def gui_app_unregister(tab):
    """Drop an app registration. The `//gui/tab/` route is untouched, so the tab is
    adopted from then on rather than vanishing."""
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


# --- adoption ---------------------------------------------------------------------

def gui_app_adopt_record(tabs, back_tab=None, client_id=None, console=None):
    """Remember what THIS console enabled, so unregistered tabs still reach the PADD.

    Called by the page as it draws the ePADD strip, with the tab set it was about to
    draw. Recording it is what lets an addon that knows nothing about ePADD keep
    working: its `gui_tab_enable` in the console's activation hook still decides where
    its panel appears, and the PADD picks it up from here.

    Unlike `console_tabs`, this is NOT consumed by drawing - the home screen is a
    different build from the console's, so it has to survive one.

    AN EMPTY SET DOES NOT OVERWRITE, and that is the whole subtlety. Opening the PADD
    is itself a build, and the home screen declares no apps - only its own back tab -
    so the very next strip after the console's would otherwise record nothing and the
    home screen would read an empty set and draw no adopted tiles. What DOES clear it
    is a different console: the record is stamped with the console it came from, so
    moving to another station replaces it rather than inheriting the last one's apps.
    """
    keep = set()
    for tab in (tabs or ()):
        tab = str(tab).strip().lower()
        if not tab or tab in NEVER_AN_APP:
            continue
        if back_tab is not None and tab == str(back_tab).strip().lower():
            continue    # the console you came from is the back button, not an app
        keep.add(tab)

    cid = _client_id() if client_id is None else client_id
    console = epadd_console_name(console)
    record = get_inventory_value(cid, ADOPTED_KEY, None)
    if isinstance(record, dict) and not keep and record.get("console") == console:
        return                      # a build that offered nothing; the last one stands
    set_inventory_value(cid, ADOPTED_KEY, {"console": console, "tabs": keep})


def gui_app_adopted(client_id=None):
    """The tab names this console enabled, as last recorded."""
    if client_id is None:
        client_id = _client_id()
    record = get_inventory_value(client_id, ADOPTED_KEY, None)
    if isinstance(record, dict):
        return set(record.get("tabs") or set())
    return set(record or set())     # tolerate a record written before the stamp


# --- the list the home screen draws ------------------------------------------------

def gui_app_list(console=None, client_id=None):
    """The apps this console should offer, in the order they should be drawn.

    Registered apps scoped to `console`, plus every adopted tab that no one
    registered. An entry whose `//gui/tab/` route does not exist, or whose route
    condition is false right now, is left out - the route's own `if` is still the
    authority on whether a panel is available.

    Returns:
        list[dict]: each with tab, title, icon, group, sort, description, adopted.
    """
    from ...mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel

    if console is None:
        page = FrameContext.page
        console = getattr(page, "console", None) if page is not None else None
    console = epadd_console_name(console)

    routes = GuiTabDecoratorLabel.all
    task = FrameContext.task
    apps = _apps()
    out = []
    seen = set()

    def route_ok(tab):
        label = routes.get(tab)
        if label is None:
            return None                     # nothing defines this tab
        if task is not None and isinstance(label, GuiTabDecoratorLabel):
            if not label.test(task):
                return None                 # its own `if` says no
        return label

    for tab, app in apps.items():
        if tab in NEVER_AN_APP:
            continue
        wanted = app.get("consoles")
        if wanted is not None and console is not None and console not in wanted:
            continue
        label = route_ok(tab)
        if label is None:
            continue
        entry = dict(app)
        entry["label"] = label
        out.append(entry)
        seen.add(tab)

    for tab in gui_app_adopted(client_id):
        if tab in seen or tab in NEVER_AN_APP:
            continue
        label = route_ok(tab)
        if label is None:
            continue
        out.append({
            "tab": tab,
            "title": tab.replace("_", " ").title(),
            "icon": None,
            "consoles": None,
            "group": ADOPTED_GROUP,
            "sort": 100,
            "description": None,
            "status": None,
            "adopted": True,
            "label": label,
        })
        seen.add(tab)

    out.sort(key=lambda a: (_group_rank(a["group"]), a["group"],
                            a["sort"], a["title"].lower()))
    return out


def _group_rank(group):
    """GROUP_ORDER first in the order given, then anything else alphabetically, then
    "Other" - the adopted leftovers - always last."""
    if group == ADOPTED_GROUP:
        return len(GROUP_ORDER) + 1
    try:
        return GROUP_ORDER.index(group)
    except ValueError:
        return len(GROUP_ORDER)


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
    """Open an app: send the GUI task to that tab's label.

    The same two lines `TabControl.on_message` runs when a tab button is clicked, so
    an app opened from the PADD arrives exactly as it would have from the strip.

    Returns:
        bool: False when the tab has no route or there is no GUI task to send.
    """
    from ...mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
    label = GuiTabDecoratorLabel.all.get(str(tab).strip().lower())
    if label is None:
        return False
    page = FrameContext.page
    task = getattr(page, "gui_task", None) if page is not None else None
    if task is None:
        return False
    task.jump(label)
    task.tick_in_context()
    return True


def _esc(text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
    from ...helpers import gui_text_escape
    return gui_text_escape("" if text is None else str(text))


def gui_app_chrome(title, subtitle=None, home_text="HOME", on_home=None):
    """The bar an app draws instead of `gui_tab_back(CONSOLE_SELECT)`.

    ePADD owns this row and nothing below it, so an app's own body is unchanged.

    Args:
        title (str): the app's name.
        subtitle (str, optional): a second, dimmer line of context.
        home_text (str, optional): the home button's label.
        on_home (callable | label, optional): what the home button does. Defaults to
            re-entering the PADD home through its own `//gui/tab/epadd` route, so an
            app does not need to know how the home screen is reached.
    """
    from .row import gui_row
    from .text import gui_text
    from .button import gui_button
    from .blank import gui_blank

    if on_home is None:
        on_home = lambda *_a: gui_app_open("epadd")

    gui_row(f"row-height: {BAR_HEIGHT}; background: {PANEL_HEAD};")
    gui_button(f"$text:{_esc(home_text)};", style="col-width: content;",
               on_press=on_home)
    gui_text(f"$text:{_esc(title)};font:gui-4;", style="col-width: content;")
    if subtitle:
        gui_text(f"$text:{_esc(subtitle)};font:gui-1;color:{DIM};")
    else:
        gui_blank()


def gui_app_badge(app):
    """An app's live badge, as text. Never raises: a provider that throws is reported
    once by the log and the tile draws without one."""
    provider = app.get("status")
    if provider is None:
        return None
    try:
        value = provider() if callable(provider) else provider
    except Exception:
        from ..execution import log
        log(f"status provider for {app.get('tab')!r} raised", "epadd", "warning")
        return None
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
    style = (f"background: {PANEL};"
             f"click_tag: epadd-app-{tab};"
             f"click_text: {_esc(title)};"
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
    console = epadd_console_name(getattr(page, "console", None) if page else None)
    groups = gui_app_groups(console)
    total = sum(len(apps) for _, apps in groups)
    dense = total > DENSE_AFTER
    if columns is None:
        columns = _columns_for(getattr(page, "client_id", None), dense)

    # The body below the strip. 45px is where every console's content starts - the
    # strip is 35px on a 3% layout, and LM has drawn from 45px since.
    gui_section(style="area: 0, 45px, 100, 100;")

    gui_row(f"row-height: {BAR_HEIGHT}; background: {PANEL_HEAD};")
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
