from sbs_utils.helpers import FrameContext
def _act_app (client_id):
    """The scene's line, and what this character can do about it.
    
    ONE PRESS PER CHOICE. The old panel made you select a row of text and then press a
    separate ACT button - a settings screen's interaction on a thing held in one hand,
    and reported as exactly that. The listbox's own selection IS the commitment here, the
    way the PADD's fallback app list works.
    
    A LISTBOX, not a stack of rows: a fixed row is never scaled down, so a scene with
    more choices than fit would spill its buttons out over the map. That is not
    hypothetical - it is the bug the first version of this screen shipped with."""
def _act_badge ():
    """How many choices are waiting. This is what makes a beat findable without the
    device taking the screen - and the auto-open is what makes it findable anyway."""
def _apps_for (surface):
    ...
def _area (value, fallback=None):
    """A descriptor's area: a style string, or a callable returning one."""
def _arm (client_id, setting):
    ...
def _at_style (client_id, at):
    """Where you are - REPLACED BY THE WEAPON when it is live.
    
    The bar is the only band on screen in every state, the tile sheet included, so it is
    the only place an armed weapon can be seen from everywhere. An app you have navigated
    away from cannot tell you anything."""
def _auto_open (client_id, surface='boarding'):
    """The surface's own auto-open, if it has one."""
def _bar_styles (client_id, surface='boarding'):
    """The bar's three STYLE strings, or None when this surface has no bar.
    
    Styles rather than the raw text, because comparing them is how the tick decides the
    bar moved - and the third slot's style is itself a signal on the handheld, where it
    turns red the moment the weapon is live."""
def _boarding_auto_open (client_id):
    """A new beat OPENS the ACT app, on every console at the site.
    
    Nobody should have to notice a badge to be in the scene - a beat that nobody answers
    because nobody looked is a scene that did not happen.
    
    Two rules that are the whole of it:
    
    * **The seq is recorded even when the app is not opened**, or a beat somebody
      dismissed pops straight back on the next tick and cannot be got rid of.
    * **Never while armed.** Yanking a crew member off a live weapon screen is the exact
      accident the safety rules exist to prevent, and it would happen at the worst
      possible moment - the one where something just started happening."""
def _boarding_home_text (client_id):
    ...
def _boarding_revision (client_id):
    """The handheld's own half of the revision - see :func:`xess_revision`."""
def _caller_detail (client_id, item):
    """The last thing this caller said, and what can be said back.
    
    ONE ENTRY AND A COUNT, never a thread - the thread is what the ePADD is for, and it
    is what keeps this device off a scrollbar."""
def _caller_detail_text (item, last):
    """The Crew detail as text-area markdown - see :func:`_caller_detail`.
    
    A person's line leads with their face (two text lines tall); the ship and "Everyone"
    have no face and lead with nothing. Values are made safe for a table cell and a
    lead line: a `|` would split the row, a `]` or `)` would end the face reference."""
def _caller_row (item, **kwargs):
    """One caller as a list row. Returns None - see :func:`_choice_row`."""
def _callers (client_id):
    """Everyone this console can reach, the ship first.
    
    The SHIP IS A ROW, and it is the row that carries BEAM UP: the ship is what beams you
    up, so leaving lives with the thing that does it rather than under every screen."""
def _choice_row (item, **kwargs):
    """One choice as a list row. Returns None, so the listbox sizes the item itself.
    
    NEVER return a size from an item template: the listbox only calls
    `resize_to_content()` when the template returns None, and an item section starts at
    zero height - returning one leaves it degenerate, which kills selection and the click
    region along with it."""
def _choice_text (item):
    """A choice's label, with who it is really for when that is not obvious.
    
    The attribute is `forwarded` - the guard text `boarding_orphan_choices` puts on a
    choice nobody present qualifies for, which the duty console is shown so a crew member
    can see they are covering. This read `covering` for its whole life, which nothing has
    ever set, so the mark has never once appeared on this screen."""
def _client (client_id=None):
    ...
def _condition (room):
    """How a node is doing: its condition as a colored pip and a word, then its wear
    as a gauge. Text-area markdown - the same text is filed to the survey log, so the
    ePADD Survey entry draws the same readout."""
def _crew_app (client_id):
    """Who is out here - the ship included - what each last said, and BEAM UP.
    
    HAIL AND PARTY WERE THE SAME APP. One held three abstract audience tokens
    (SHIP / PARTY / ALL) and the other held the actual people; an audience picker and a
    roster are one list. Merged, the roster IS the inbox, grouped by who said it, which
    costs nothing because every message already carries a `from`.
    
    A list and a detail, which is the house pattern for anything repeating (the quest
    log, the hangar board, Messages, Status). The list scrolls; the detail holds the
    actions, so a row is never two buttons wide."""
def _crew_badge ():
    ...
def _crew_health (lifeform):
    """(hp, max_hp) for a party member, read off the BODY they walk around in - the
    figure on the grid carries the HP, not the person. (None, None) when they have no
    body on this interior, so nothing is shown rather than a made-up full bar."""
def _dim_style (text):
    """The third slot, for a surface that has nothing special to say with it.
    
    SHRINK, NEVER WRAP. The bar is two rows by construction, so a slot that wraps leaves
    the bar and draws over the app beneath it - the engine does not clip. Boarding's
    third slot is a room name or "ARMED - BEAM" and never had the problem; the Admiral's
    is a status line written by a mission ("No extractors yet - build an Extractor on a
    worldlet to produce ore and gas."), and a mission's sentence is not ours to keep
    short. Seen in the engine, 2026-09-19."""
def _draw_app (client_id, surface='boarding'):
    """The open app, or the tile sheet when none is."""
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _file (client_id, room):
    """Scanning files the entry - there is no Record button, so the party's record fills
    in as they explore and nobody has to remember to keep it.
    
    A no-op until the store lands in pass 2. Deliberately called anyway: the seam is the
    thing that is hard to add later."""
def _fire_app (client_id):
    """Arm, and choose what the shot is.
    
    THREE SETTINGS, AND THEY ARE A LADDER: stop a person, open a thing, destroy it. The
    third exists so that killing somebody is a NAMED CHOICE rather than something that
    falls out of pointing a cutting tool at them - the same argument that puts the
    setting ahead of the target.
    
    Each setting says what it does BEFORE it is armed. A setting whose effect you have to
    guess is the same problem as inferring it from what you hit."""
def _fire_badge ():
    ...
def _fire_row (item, **kwargs):
    """One reach target. Colored by whether the held tool can do anything with it.
    
    Returns None so the listbox sizes it - see `_choice_row` for why returning a size
    kills selection."""
def _home (client_id, surface='boarding'):
    """The tile sheet: what is happening, then the tools.
    
    The scene's line is here AS WELL AS inside ACT, so the device always has something to
    say when you glance at it and you are never answering a question you scrolled past.
    A surface with no `home_text` simply has tiles."""
def _identity (client_id):
    ...
def _in_a_suit (client_id):
    """NAV needs a suit to fly. On a grid interior there is nothing for it to do."""
def _in_a_suit_with_tools (client_id):
    ...
def _job_style (job):
    ...
def _key (base, surface):
    """A per-surface client-inventory key.
    
    Boarding keeps the bare name it has always written, so nothing on a live client's
    inventory moves and an upgrade mid-mission cannot lose a crew member's open app."""
def _last_from (item):
    """The newest message from this caller. For the party row, the newest from anyone."""
def _leave (client_id):
    """The way home, and it has to match the way out.
    
    A console that suited up has a SHIP to delete and a different console type to restore;
    `boarding_go_up` knows about neither, so sending an EVA console through it would leave
    the suit drifting in the ruin and the console on a dead 3D view. One branch, shared
    with the PADD's button."""
def _leave_label (client_id):
    """What the way home is CALLED. You do not beam up out of a suit, you fly back."""
def _name_style (name):
    ...
def _nav_app (client_id):
    """Where you can go in this relic, and the way to stop going there."""
def _nav_badge ():
    """Where you are heading, and roughly how far.
    
    THE DISTANCE IS IN HERE ON PURPOSE. `gui_xess_tick` only rebuilds when
    `xess_revision` changes, and a suit crossing a chamber changes nothing else in that
    tuple - so without a badge that moves, the Nav screen would freeze the moment you
    pressed a destination and never show you arriving. Coarse, so it is a repaint every
    hundred units rather than every tick."""
def _nav_far (client_id, pos):
    """That distance as a label. `--` when there is nothing to measure from."""
def _nav_gap (client_id, pos):
    """How far this console's suit is from a point, or None when it cannot be measured.
    
    NONE RATHER THAN ZERO, and that is the whole of a bridge report. `helm_position` only
    understood things with a `.x`, an authored place is a plain (x, y, z) TUPLE, so every
    measurement answered `inf` - which this function turned into 0.0 and the app printed
    beside every destination. "They all show 0 for the distance." A number that is wrong
    is worse than no number: it reads as a working readout saying you have arrived.
    (`helm_position` takes a tuple now, so this is belt and braces.)"""
def _nav_mark (item):
    """The prefix for one destination. Visited beats seen - arriving implies seeing.
    
    A nav row is ``(name, label, visited, seen, hint)``; anything shorter is a caller
    that predates the marks and draws a blank rather than raising. A lead beats a find,
    and both beat where the crew has been: they are about what is still to DO."""
def _nav_row (item, **kwargs):
    """One destination as a list row. Returns None, so the listbox sizes it - see
    `_choice_row` for why returning a size kills selection.
    
    A RUIN IS A MAP YOU ARE DRAWING. Without a mark, every room reads the same whether
    the crew cleared it an hour ago or have never been near it, and the only record of
    where they had been was in their heads. Visited is dimmed: it is done, and the row
    worth looking at is the one that is not."""
def _nav_speed_row (client_id):
    """How hard to fly: three named speeds, as three buttons.
    
    NOT A SLIDER. The choice a boarder makes is "pick through this" or "get there", and a
    continuous control invites fiddling with a number whose units mean nothing to anybody
    on a bridge. The chosen one is marked rather than removed, so the row never moves."""
def _nav_view_row (client_id):
    """Orbit and dolly, as four presses and a way back.
    
    ON NAV RATHER THAN AN APP OF ITS OWN. Looking round is part of flying, not a settings
    screen - and a tile costs a whole row of the device to say "the camera".
    
    The centre control is deliberately ONE button. "The camera is somewhere odd" is one
    problem however it got there - a stray orbit, a dolly left in, or both - and a console
    that has lost the view wants it back, not a menu."""
def _older_count (item):
    ...
def _pick_setting (client_id, setting):
    """Choose the verb WITHOUT arming. Picking a setting and firing must be two
    decisions, or changing your mind about the setting is a shot."""
def _register_builtins ():
    ...
def _report_once (key, exc, what):
    """SAID, NOT SWALLOWED - and said once. This runs per tile per build, so an unguarded
    log is several lines a second for the rest of the mission."""
def _safe (client_id):
    ...
def _say (text, to, by):
    ...
def _scan_app (client_id):
    """Read the room you are standing in.
    
    The readout is the library's own node description rather than a second one - LM
    already renders a grid node's condition, and two descriptions of the same thing
    drift apart."""
def _scan_available (client_id):
    """SCAN reads where a body IS - a floor, or a suit's place in a relic."""
def _scan_ground (client_id):
    """Scan on the ground: the place, and everything in sight worth a reading.
    
    Only what the crew can SEE - a scan that listed a hostile behind a rock would be the
    device leaking the map. Each reading is filed to the survey log once."""
def _scan_suit (client_id):
    """Scan from a suit: the room, the nearest named place, and the finds in reach.
    
    The words are the relic's `Scan:` fields - written for the PLAYER - and never a part's
    prose, which in a shipped relic is notes to the author. A find shows its picture (its
    ITEM `Sprite:`) and can be READ, which is a scan the mission hears as `eva_scanned`."""
def _ship_name (client_id):
    ...
def _standing_somewhere (client_id):
    """SCAN and FIRE need a body on a floor. A tile that cannot do anything is worse than
    no tile - it is a promise the device does not keep."""
def _surface_def (surface):
    ...
def _team_health ():
    """Every party member's HP, for the revision - a hit repaints the Crew app."""
def _tile (client_id, app, surface='boarding'):
    """One app tile: a clickable panel holding its icon, name, blurb and badge.
    
    The WHOLE panel is the hit target - a sub-section with `click_text` emits a click
    region over its own bounds, the same mechanism the PADD's tiles and the tab strip
    use. `click_text` must be EMPTY, not absent: a sub-section emits its region only when
    `click_text is not None`, so dropping the property turns every tile into decoration."""
def _unread_from (item):
    """How many unread messages this caller has sent. "" when none - the convention the
    PADD's own badge providers follow."""
def _view_key (surface):
    ...
def _work_app (client_id):
    """What is in reach, and the two things a suit can do about it."""
def _work_badge ():
    """What is in reach, and how far - and it has to MOVE.
    
    `gui_xess_tick` only rebuilds when `xess_revision` changes, and the badge is the part
    of that tuple a moving suit can shift. Without a number that changes, the whole screen
    freezes the moment the suit starts flying."""
def gui_xess (client_id=None):
    """Build the handheld. The boarding surface of :func:`gui_xess_panel`."""
def gui_xess_head (client_id, title, back=True, surface='boarding'):
    """An app's title line, with the way back to the tiles.
    
    Every app draws this, so Back is in the same place on all of them - which is the
    only reason a crew member can leave an app they have never seen before."""
def gui_xess_panel (client_id=None, surface='boarding', identity_area=None, app_area=None):
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
        dict: the held widgets, also stored on the page for :func:`gui_xess_tick`."""
def gui_xess_tick (surface='boarding'):
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
        bool: False when the screen is gone - a handler can outlive the page."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def xess_app_badge (app):
    """An app's live badge, as text, or None.
    
    Never raises: a provider that throws costs its own tile a badge and nothing else.
    A provider asking for its own badge is ANSWERED with None rather than re-entered."""
def xess_app_count (surface=None):
    """Reset-ledger probe: how many apps are registered. Every surface when none is named,
    so a mission's leftovers are counted too."""
def xess_apps (client_id=None, surface='boarding'):
    """The apps this console may open, in tile order.
    
    An `available` that raises drops its own tile and nothing else - the same bargain the
    badge makes. A device that goes blank because one mission app asked an awkward
    question is worse than a device missing one tile."""
def xess_clear ():
    """Forget every registration, on EVERY surface. The mission reset calls this; the
    built-ins re-register themselves immediately after, so a reset never leaves a device
    with no apps.
    
    A mission's own surface goes away entirely - its descriptor as well as its apps -
    because the next mission has no reason to carry it. A mission re-registers its
    surfaces when its console opens, which is why that call has to be idempotent."""
def xess_focus (client_id=None, surface='boarding'):
    """The row the open app is showing, for the apps that are a list and a detail."""
def xess_open (client_id, key=None, surface='boarding'):
    """Open an app on this console, or go home with ``None``.
    
    Leaving FIRE DISARMS. Walking away from a live weapon with the gun still up is
    exactly the accident the disarm-on-shot rule exists to prevent, one step earlier.
    That is the HANDHELD's rule, and the import that serves it lives inside the branch -
    a panel on some other console must not drag the boarding modules in to open a tile."""
def xess_opened (client_id=None, surface='boarding'):
    """The app this console has open on this surface, or None for the tile sheet."""
def xess_panel_revision (client_id=None, surface='boarding'):
    """What a panel's `on change` watches: the bar AND the app area.
    
    Two channels, deliberately. :func:`gui_xess_tick` updates the bar's three widgets in
    place and rebuilds the app region only when the app half moved, so a status line that
    ticks every second never rebuilds a listbox somebody is halfway through clicking."""
def xess_register (key, title=None, icon=None, blurb=None, sort=100, draw=None, badge=None, available=None, surface='boarding'):
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
        dict: the registration."""
def xess_registered (surface='boarding'):
    """Every app key on a surface. An accessor because MAST cannot see a module-level
    dict - only functions become MAST globals."""
def xess_revision (client_id=None, surface='boarding'):
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
    only when boarding is the surface being asked about."""
def xess_set_focus (client_id, value, surface='boarding'):
    ...
def xess_surface (surface, title=None, identity=None, revision=None, auto_open=None, home_text=None, identity_area=None, app_area=None, at_style=None):
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
        dict: the descriptor."""
def xess_surfaces ():
    """Every surface name the device knows. An accessor because MAST cannot see a dict."""
def xess_unregister (key, surface='boarding'):
    """Take an app off the device. True when there was one."""
