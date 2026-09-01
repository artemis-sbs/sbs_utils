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
MODE_KEY = "epadd_mode"
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
    """Turn the ePADD strip on for this client. Off is the default and is unchanged
    behaviour - the full tab strip, exactly as it draws today.

    Args:
        on (bool): True for the two-button ePADD strip, False for the classic strip.
    """
    set_inventory_value(_client_id(), MODE_KEY, bool(on))


def gui_app_mode_is_on(client_id=None):
    """Whether this client draws the ePADD strip."""
    if client_id is None:
        client_id = _client_id()
    return bool(get_inventory_value(client_id, MODE_KEY, False))


# --- registration -----------------------------------------------------------------

def gui_app_register(tab, title=None, icon=None, consoles="*", group=None, sort=100,
                     description=None):
    """Present an existing `//gui/tab/<tab>` route as an ePADD app.

    The route is not touched and keeps its own `if` condition, which is still what
    decides whether the app is offered at all.

    Args:
        tab (str): the `//gui/tab/` path this app opens.
        title (str, optional): the tile's name. Defaults to the tab path, title-cased.
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

def gui_app_adopt_record(tabs, back_tab=None):
    """Remember what THIS console enabled, so unregistered tabs still reach the PADD.

    Called by the page as it draws the ePADD strip, with the tab set it was about to
    draw. Recording it is what lets an addon that knows nothing about ePADD keep
    working: its `gui_tab_enable` in the console's activation hook still decides where
    its panel appears, and the PADD picks it up from here.

    Unlike `console_tabs`, this is NOT consumed by drawing - the home screen is a
    different build from the console's, so it has to survive one.
    """
    keep = set()
    for tab in (tabs or ()):
        tab = str(tab).strip().lower()
        if not tab or tab in NEVER_AN_APP:
            continue
        if back_tab is not None and tab == str(back_tab).strip().lower():
            continue    # the console you came from is the back button, not an app
        keep.add(tab)
    set_inventory_value(_client_id(), ADOPTED_KEY, keep)


def gui_app_adopted(client_id=None):
    """The tab names this console enabled, as last recorded."""
    if client_id is None:
        client_id = _client_id()
    return set(get_inventory_value(client_id, ADOPTED_KEY, set()) or set())


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
