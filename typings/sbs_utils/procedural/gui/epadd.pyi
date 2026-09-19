from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def _app_link (tab):
    """One screen this one can reach, drawn as a TAB - not as a button.
    
    A `gui_button` is the wrong widget here for two reasons the playtest saw at once:
    the engine draws it with its own bevelled chrome, and it renders the backticks that
    `_esc` adds for quoting as literal characters. The tab strip's own buttons are not
    buttons either - `TabControl` subclasses Text - which is exactly why they are flat.
    
    So this is a Text with a background, a fixed slot and a click tag, built the same way
    `MastStoryPage._button` builds one. It gets the flat look, the same 256px slot, black
    on the light fill the console's own back button uses, and a hit region the width of
    the whole slot rather than the width of the word.
    
    `_esc` is safe here: a Text widget resolves the quoting, which is why the bar's title
    has always drawn clean while these did not.
    
    Uses the app's registered title when it has one and its raw name when it does not: a
    sub-app is an app route nobody registered, so there is no registration to ask."""
def _app_list (groups):
    """The PADD's app sheet as a scrolling list, for when the tiles do not fit.
    
    A listbox brings the two things the grid has no answer for: it scrolls, and its
    headers collapse - so the groups survive rather than being flattened away."""
def _app_row (item):
    """One row of the list the PADD falls back to. Sizes its ROW and returns None -
    a listbox only calls resize_to_content() when the template returns nothing, and an
    item section that keeps a returned size is degenerate, which kills the click
    region along with the selection."""
def _apps ():
    ...
def _apps_count ():
    """Reset-ledger probe. `Agent.SHARED` is rebuilt by `clear_shared()` on every
    mission reset, so this should always report 0 after one - it is registered so that
    a future move off SHARED cannot go unnoticed."""
def _client_id ():
    """Whose PADD this is: the PAGE's client, not the current event's.
    
    Same rule, and the same reason, as `console_tab._tab_client_id` - a page that
    rebuilds because something else emitted a signal runs under the EMITTER's event
    while `FrameContext.page` is correctly the console's."""
def _columns_for (client_id, dense):
    """How many tiles fit across THIS client's screen.
    
    The layout is in percent, so four columns is four columns whether the console is
    1920 or 1024 wide - and at 1024 that is a ~230px tile with ~174px left for the
    title, where a two-word name wraps and that one tile stops matching its
    neighbours. Ask the client how wide it actually is."""
def _console_identity (client_id=None):
    """Which console this client is on, for scoping the app list.
    
    The BUILD's own declaration first, the door's record as the fallback - the same
    precedence `MastStoryPage._console_identity` uses, and for the same reason.
    
    Reading `page.console` alone is what broke here: it is per BUILD and reset to "" at
    every swap, and the PADD's own screens declare no console at all. So once a player
    opened the PADD, `_scoped_here` saw "" and dropped every app scoped to a console -
    Cargo and Fabricate on engineering, Airwing and Casino on the hangar - and
    `gui_app_revision` moved for the same reason, re-entering home once on its own. The
    guard existed in the page and had been applied in one place only."""
def _console_set (consoles):
    """"engineering, hangar" -> {"engineering", "hangar"}; "*" -> None, meaning any."""
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _grid_fits (client_id, groups, columns, dense):
    """Whether the tiles fit on this screen without anything being cut off.
    
    There is no scrolling in a grid, and the engine does NOT clip - a band that runs
    out of room draws over whatever is under it. So the grid is for the case where
    everything fits, and the list below is for the case where it does not.
    
    A client that has not reported its size yet answers 1024x768 with z=99, and that
    assumption is deliberately kept rather than special-cased: assuming the SMALLEST
    common console is the safe direction, because a list that scrolls is never broken
    while a grid that overflows draws over itself. The page rebuilds once the real
    size arrives."""
def _group_rank (group):
    """GROUP_ORDER first in the order given, then anything else alphabetically."""
def _identity_name (client_id, console=None):
    """The person at this console: boarding character, then callsign in a cockpit, then crew post.
    
    The boarding character wins because it is who they are RIGHT NOW - a crew member on the
    surface is playing that body, and the badge saying their bridge name there would be
    the stranger problem all over again.
    
    A CALLSIGN wins on a flight console for the same reason one step down: in a cockpit the
    callsign IS what the rest of the flight calls you, and it is what every other readout the
    hangar draws already uses. It REPLACES the crew name rather than joining it because the
    badge shares a narrow strip with the waiting count - see the placement note above - and a
    name plus a callsign plus a count does not fit any of them."""
def _save (apps):
    ...
def _say (message):
    """Report an ePADD problem where somebody will actually see it.
    
    `log(msg, "epadd", "warning")` alone goes NOWHERE: a named category is a bare
    `logging.getLogger("epadd")`, and unless the mission happened to call
    `logger(name="epadd", file=...)` it has no handler at all. Every "the tile is simply
    not there" report so far has had a clean `mast.runtime.log` beside it for exactly
    that reason. So the named logger is kept - a mission that DOES attach one still gets
    its own file - and the same line also goes to `mast.runtime`, which is the log
    everybody reads."""
def _scoped_here (app, console):
    """Whether this app belongs on this console.
    
    `"*"` means every SHIP console. The crew console has to be named or opted into,
    because a landing party carrying the fabricator is not a scoping bug anybody would
    notice until it was on screen.
    
    An UNKNOWN console (None) gets only the `"*"` apps. A console-scoped app is a claim
    about who may use it, and a client with no console - the pick screen, the server's
    own screen - has not earned engineering's tools. (This used to fail OPEN, which is
    also how a broken console lookup stayed invisible: every tile still showed.
    `gui_app_why` names the unknown console instead.)"""
def _tile (app, dense):
    """One app tile: a clickable panel holding its icon, name and description.
    
    The WHOLE panel is the hit target, not just a button inside it - a sub-section
    with `click_text` emits a click region over its own bounds (Layout._post_present),
    which is the same mechanism the tab strip and the text area's links use."""
def epadd_console_allowed (console):
    """Whether the PADD belongs on this console (any name the engine or a script uses)."""
def epadd_console_name (console):
    """The name a script would use for a console, whatever the engine calls it."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def gui_app_badge (app):
    """An app's live badge, as text.
    
    Never raises: a provider that throws costs its own tile a badge and nothing else.
    
    RE-ENTRANT PROVIDERS ARE ANSWERED, NOT RE-ENTERED. A provider is free to ask what
    the other apps are reporting - LM's Status tile does exactly that, counting the apps
    with something to say - and `status_rows` computes a badge for EVERY app, the asking
    one included. That is a cycle: the provider was entered 332 times for one badge
    (measured), unwound only when Python's own recursion limit tripped, and the
    RecursionError caught below was logged as "status provider for 'status' raised" on
    every badge computation, several times a second. The badge still came out right,
    which is why it read as noise rather than as a bug."""
def gui_app_chrome (title, subtitle=None):
    """An app's title bar. OPTIONAL - an app draws it when a title helps orient.
    
    ITS OWN BAND, 45px..109px, from `design/epadd/Spec.src`. It used to be a bare
    `gui_row` with no section of its own, so it landed in the ambient full-screen section
    at y=0 and painted over the engine's Options button. Every caller already reserved
    `area: 0, 109px, 100, 100` for its body, so the bar was always MEANT to own this
    band - it just never claimed it.
    
    45px is the console body top, the LM convention every tab body already follows, so
    this clears the tab strip as well as Options.
    
    NO HOME BUTTON. The strip's status region opens the PADD home already; a HOME here
    was a second control for the same thing. And no back: the one Back in the game is
    the console's, on the tab bar, declared by every PADD screen with
    `gui_tab_back(CONSOLE_SELECT)`.
    
    NOT EVERY APP WANTS ONE. Upgrades and the other list/detail screens use their whole
    sheet and read better for it, so this is opt-in rather than something every screen
    must remember to draw.
    
    Args:
        title (str): the screen's name.
        subtitle (str, optional): a second, dimmer line. Leave it out unless it says
            something the screen below does not - a board captioned with the count of
            what it is already listing says nothing.
    
            Pass "" rather than None for a line that is EMPTY NOW but will have text
            later: the widget is created either way, so a live screen can update it in
            place instead of rebuilding the page to make one appear.
    
    Returns:
        Text | None: the subtitle widget, so a caller can keep it and update it."""
def gui_app_get_registered ():
    """Every registration, unfiltered - the raw table, for tools and tests."""
def gui_app_groups (console=None, client_id=None):
    """`gui_app_list` folded into (heading, apps) pairs, in drawing order.
    
    An empty group is not returned at all, which is why Helm - registering no ship
    apps - draws no "Ship" heading rather than an empty one."""
def gui_app_home (ship_name=None, columns=None, title='ePADD'):
    """Draw the PADD home screen for this console.
    
    Called from the `//gui/tab/epadd` route's screen label, which then sits in
    `await gui()` - so the tile handlers belong to a task that stays alive.
    
    Args:
        ship_name (str, optional): shown beside the wordmark.
        columns (int, optional): tiles per row. Defaults to 4, or 6 once the console
            carries more than twelve apps, where the descriptions are dropped too.
        title (str, optional): the wordmark."""
def gui_app_home_tick ():
    """Move the mission clock on, without rebuilding the home sheet.
    
    The screen calls this from an `on change mission_elapsed_text()` block, so it
    runs once a second - which means it has to be cheap, and it has to not care
    about being called when the home screen is no longer up:
    
        gui_app_home()
        on change mission_elapsed_text():
            gui_app_home_tick()
    
    Returns:
        bool: True when the clock was changed, False when there was nothing to do -
            no home screen on this page, or the same second again."""
def gui_app_identity_text (client_id=None, console=None):
    """What the badge says: who you are, and how much is waiting.
    
    None when there is nothing worth a line - then no badge is drawn at all, rather
    than an empty box on every console of a mission that uses none of this."""
def gui_app_is_registered (tab):
    ...
def gui_app_list (console=None, client_id=None):
    """The apps this console should offer, in the order they should be drawn.
    
    Registered apps scoped to `console`. An entry whose `//gui/app/` route does not
    exist, or whose route condition is false right now, is left out - the route's own
    `if` is still the authority on whether a panel is available. A MISSING route is
    reported by name; it is almost always a typo or an unmigrated `//gui/tab`.
    
    Returns:
        list[dict]: each with tab, title, icon, group, sort, description, label."""
def gui_app_open (tab):
    """Open an app: send the GUI task to that app's label.
    
    The same two lines `TabControl.on_message` runs when a tab button is clicked, so
    an app opened from the PADD arrives exactly as a tab would have.
    
    Returns:
        bool: False when the app has no route or there is no GUI task to send."""
def gui_app_register (tab, title=None, icon=None, consoles='*', group=None, sort=100, description=None, status=None, boarding=False):
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
        boarding (bool, optional): also offer this app to the crew console. `"*"` does NOT
            include it: a boarding party is not everywhere on the ship, it is somewhere
            else entirely, and a landing party has no use for the cargo hold. An app
            opts in, or names `consoles="crew"` to go there and nowhere else.
        group (str, optional): heading to file the tile under. Defaults to "Mission".
        sort (int, optional): order within the group, low first. Ties break on title.
        description (str, optional): the tile's second line."""
def gui_app_revision (console=None, client_id=None):
    """What the HOME screen watches to know it must repaint.
    
    A signal does not wake `await gui()`, so the home screen polls - the same shape
    the inbox and the crew console use. Two things change under it: a badge (mail
    arrives, a build finishes) and the app LIST itself, because a route condition can
    turn an app on or off while the PADD is open. Without this the home screen was
    frozen at whatever it said when it was opened.
    
    Cheap: the badges are computed for the tiles anyway."""
def gui_app_subnav (apps):
    """The screens THIS app can reach, on the bar's own line.
    
    Called straight after `gui_app_chrome`, and deliberately opens NO row of its own -
    it appends to the bar's, so the sub-apps sit to the right of the title in the same
    45..109px band instead of eating a second one:
    
        gui_app_chrome("Debug")
        gui_app_subnav(["brain", "mast"])
    
        [ Debug ..................... [Brain] [MAST] ]
    
    The chrome's trailing blank is what puts them on the right: it takes the slack, so
    everything after it is pushed to the far end of the row.
    
    Its own call rather than a parameter on the bar, because exactly one app has
    sub-apps and folding that into the component every screen draws is how the bar
    accumulated the special cases that made it wrong.
    
    Replaces `gui_tab_enable("brain,mast")`, which put an app's sub-screens on the
    CONSOLE'S tab bar - the last place the PADD and the tab system still met.
    
    Args:
        apps (list[str]): app names. A sub-app has no registration, so a name with no
            registered title falls back to its own name."""
def gui_app_unregister (tab):
    """Drop an app registration. The `//gui/app/` route is untouched - it simply stops
    being offered on the PADD."""
def gui_app_waiting (console=None, client_id=None):
    """How many apps have something to say - the count the badge carries.
    
    Apps, not messages. Unread mail is only one of the things a badge reports, and the
    number a crew member cannot get any other way is "how many of these should I open"."""
def gui_app_why (tab, console=None, client_id=None):
    """Why a tile is, or is not, on this console's PADD. One line, in plain words.
    
    A missing tile has four causes and three of them are SILENT by design - the whole
    point of a route condition is that it hides things quietly - so "the app is just not
    there" has been costing a full archaeology session each time it is reported. Ask
    this instead, from a debug console or a comms route::
    
        log(gui_app_why("boarding_party"))
    
    Args:
        tab (str): the app, as `gui_app_register` was given it.
        console (str, optional): the console to ask about. Defaults to this client's.
        client_id (optional): the console's client. Defaults to the page's own.
    
    Returns:
        str: the reason, naming the thing to go and look at."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
