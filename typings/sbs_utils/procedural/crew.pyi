def _as_roster (roster_spec):
    ...
def _complement_key (ship_id=None, slot=None):
    """A STABLE identity for the ship whose complement this is.
    
    Never the raw engine id. A player ship can be respawned mid-mission and come back with a
    new one, and the crew must not change when it does - the same reason `crew_bind_ship`
    binds by NAME rather than by id.
    
    In order: the player-roster SLOT, which is what a console actually binds to and cannot
    dangle; then the ship's name; then the hull key. ``slot`` is passed EXPLICITLY rather than
    read out of ``ship_id``, because a ship id is an int too and there is nothing in the value
    to tell the two apart. A live player ship resolves to its own slot anyway, so a seat
    previewed by slot and then resolved by ship is the same seat."""
def _hull_race (ship_or_key):
    """The race a hull belongs to, for a fallback face. "" when it cannot be told.
    
    Takes a ship id/object OR a bare hull KEY. The key form is what lets a console picker
    ask this during setup without resolving an engine object at all - the answer only ever
    depended on the hull, never on the ship wearing it."""
def _member_by_pick (pick):
    """Resolve a persisted ``"<roster>:<member>"`` pick, or None.
    
    An unresolvable pick is IGNORED rather than an error: the pick persists on the player's
    machine and the roster that gave it meaning belongs to one mod, so joining a game that
    does not load that mod must simply fall through to the next tier."""
def _member_face (roster, member):
    """This member's face, DERIVED ONCE AND KEPT.
    
    A member with no ``Face:`` of their own gets one from the roster's ``Race:`` - but
    `face_resolve` rolls a fresh random face every call, so asking twice gave Data two
    different faces and every repaint changed his appearance. The derived face is cached back
    onto the member record, which also fixes the ordering problem a declare-time derivation
    would have: a mod registers its faces from its own `__init__`, which may run after the
    roster is declared."""
def _member_post (roster, member, source):
    """Build a post from a roster member, filling its blanks from the roster's fence."""
def _name_of (ship_or_name):
    ...
def _no_braces (text):
    """Braces out. The packed value is READ BACK INTO A MAST VARIABLE, and a MAST assignment
    re-runs a string through f-string formatting - so a brace anywhere in it is a SyntaxError
    reported against the console picker rather than against whatever put it there. Nothing
    legitimate carries one: a face string is `alias #color col row;`, a portrait is a path,
    and a pick is `roster:key`."""
def _norm (text):
    """Fold a ship name or hull key for comparison: stripped, lowered, spaces collapsed."""
def _own_over (post, own_name=None, own_face=None, own_portrait=None):
    """Lay what the player chose over the identity the ship had for them.
    
    FIELD BY FIELD. The three are separate answers to separate questions - what am I called,
    what do I look like, is that a photograph - and a player edits one at a time. Replacing
    the whole post the moment any one of them was set is what made editing destructive: a
    face built for an automatically named officer arrived with `own_name` empty, so the post
    came back nameless and the console read as unmanned.
    
    A PORTRAIT AND A FACE still displace each other, because they answer the same question
    and nothing could resolve having both.
    
    Everything they did not answer - the rank, the roster key, the seat - stays, so a player
    who renames themselves is still the person the ship put at that station."""
def _plain (text):
    """Braces and backticks out of anything bound for a MAST string or a style.
    
    A name reaches `gui_text` and f-string formatting, so a person genuinely called
    ``Foo{bar}`` would be a syntax error reported against the widget rather than against the
    roster that named them. Same guard the Director puts on its own screen labels."""
def _post (name, rank='', face='', portrait='', key='', roster='', source='unmanned', roles=''):
    ...
def _register_portraits (roster):
    """Cut a roster's ``Sheet:`` into named cells, once, at declare time.
    
    Reuses the image atlas wholesale: each member's ``At:`` cell is registered as
    ``crew:<roster>:<member>`` and that key IS the member's portrait, so a roster sheet
    behaves exactly like an icon sheet and there is no new image machinery to maintain."""
def _seat_is_live (client_id, console):
    """Is this client still actually sitting at this console?
    
    SELF-HEALING OCCUPANCY. Rather than hooking disconnects and console changes - two events
    that can be missed, and a missed one leaks a seat for the rest of the mission - a seat is
    simply believed only while the client's own CONSOLE_TYPE still agrees with it. A client
    that left, changed station or vanished stops matching and its seat frees itself."""
def _seat_occupant_index (client_id, seat_key, console):
    """WHICH person at this seat this client is - 0 unless somebody else is already there.
    
    Pruned the same way `_taken_members` prunes seats: a recorded occupant is believed only
    while its client's own CONSOLE_TYPE still agrees, so a client that disconnected or moved
    station frees its place without any event having to be caught."""
def _seat_person (ship, console, occupant=0, race=None, slot=None):
    """(name, face) for a seat, allocated on first ask and remembered after.
    
    The FACE is allocated with the name and kept with it. Rolling a fresh `random_face` on
    every resolve would give the picker a different person each time it previewed the same
    station, and the console a different one again on arrival."""
def _seat_pick (roster, ship_id, console, client_id=None):
    """Who this roster puts at this console, or None.
    
    A ``By: person`` roster NEVER auto-assigns, and that is the point of it rather than an
    omission: its members are real people who choose themselves. Handing Doug's face to
    whoever happened to open helm first is exactly what it exists to avoid."""
def _take (name):
    """Claim a name for this run, or None if somebody already has it."""
def _taken_members (ship_id, exclude_client=None):
    """Member keys currently occupied on this ship, pruning any seat that went stale.
    
    `exclude_client` frees that client's own seat first, so re-resolving a console the same
    person is already sitting at gives them back the same member rather than the next one."""
def console_display_name (client_id):
    """What to CALL this console in a list of consoles.
    
    A person's name when there is one, else the screen's own name. The Director names its
    output windows PROG01 / PRE01 / DIR01 - those used to live in ``CREW_NAME`` too, and
    anything listing consoles by crew name showed them for free. They have their own key
    now, so the two have to be put back together here rather than at every call site."""
def crew_assign (client_id, ship_id, console, own_name=None, own_face=None, own_portrait=None, own_pick=None, hull=None, slot=None):
    """Resolve this console's crew and PUBLISH it. Returns the post.
    
    Writes on the client agent:
    
    ``CREW_NAME``
        Unchanged in name and meaning, so ``director_overlays._tok_crew_name`` and the
        Gamemaster's message list keep working with no edit at all. This is the whole reason
        the feature drops into the existing seam rather than replacing it.
    ``CREW_RANK`` / ``CREW_FACE`` / ``CREW_PORTRAIT`` / ``CREW_KEY`` / ``CREW_ROSTER`` /
    ``CREW_SOURCE``
        Additive. ``CREW_SOURCE`` is kept because it is the only way to answer "why is this
        console called that" after the fact.
    
    It also takes the seat, so a second client opening the same station on the same ship gets
    the NEXT person rather than the same one.
    
    Writes no client string. See the module docstring for why that would be unfixable."""
def crew_autoname_enabled ():
    """Whether a console nobody named gets one automatically. `CREW_AUTONAME`, default on."""
def crew_avatar_race (ship_id=None):
    """A race the slider-based avatar editor can actually BUILD, for this ship.
    
    The editor drives `faces.FACE_FEATURES`, which describes the six stock races and nothing
    else. A hull belonging to a mod race has no features to slide - its faces are whole drawn
    busts, one per atlas cell - so asking the editor for one lands on its "unknown race"
    screen. Falls back to terran, which is always buildable.
    
    A mod race wants :func:`crew_face_gallery` and a pick-one-of-these screen instead."""
def crew_bind_hull (hull_key, roster_spec):
    """Bind a roster to a shipData HULL KEY - the tier a mod uses. True when it took.
    
    The hull KEY, never ``artfileroot``: the two differ on about half the TNG hulls, so a
    roster keyed on art would silently attach to the wrong ships."""
def crew_bind_ship (ship_or_name, roster_spec):
    """Bind a roster to a ship BY NAME. Returns True when it took.
    
    By name rather than by id on purpose: a mission binds its crews before the ships exist,
    and a player ship can be respawned across a mission's life while keeping its name."""
def crew_callsign (client_id):
    """The pilot callsign this client flies under, or "".
    
    A DIFFERENT identity from the crew name and deliberately so: a callsign belongs to whoever
    is in the cockpit, is assigned by the hangar rather than by a roster, and is what the rest
    of the flight calls you. The hangar addon owns the value; this is the library's one named
    place to read it, so a console badge or a message list does not have to know the key."""
def crew_choices_for (ship_id, console=None, client_id=None, hull=None):
    """The people a picker may OFFER, in declaration order.
    
    ``console`` NARROWS a ``By: console`` roster to those who could take that exact seat.
    Pass None - which the console picker does - to offer everyone still free, because there
    the dropdown is an OVERRIDE beside a cast that already assigns itself by console: a
    player reaching for it is reaching past the automatic answer, and the automatic answer is
    the only thing the console was going to decide.
    
    Console is ignored outright for a ``By: person`` roster, where the seat is not what
    identifies anybody.
    
    ``hull`` is the shipData key, for a picker choosing one for a ship that does not exist
    yet - see :func:`crew_roster_for`.
    
    Returns [] when no roster staffs this ship, which is what keeps the picker looking
    exactly as it does today for a mission that declares none."""
def crew_clear ():
    """Drop every declared roster and every live seat - the per-mission reset."""
def crew_complement_count ():
    """Reset-ledger probe: how many automatic names are allocated to seats.
    
    A third probe rather than a bigger one, for the same reason `crew_seat_count` is separate:
    a complement that survives into the next mission is a DIFFERENT bug from a leaked seat -
    it shows up as run 2 naming its bridge after run 1's, or eventually as a pool with no free
    names left."""
def crew_count ():
    """Reset-ledger probe: how much DECLARED roster data is held."""
def crew_declare (records):
    """Register roster records. Returns ``{key: roster}`` for everything registered.
    
    Args:
        records: an iterable of roster records - what
            :func:`sbs_utils.procedural.amd_crew.crew_from_section` returns.
    
    A roster re-declared under a key that already exists REPLACES it, so an in-process
    recompile re-registering the same file is a no-op rather than a duplicate."""
def crew_declare_amd (node):
    """Declare every crew roster in an already-parsed AMD document or section.
    
    THE ADDON PATH. An addon's file lives inside its mastlib, which is a zip, so it must be
    read out and parsed by the addon itself::
    
        crew_declare_amd(amd_document(media_read_relative_file("crew_rosters.amd"),
                                      data_parser=amd_crew_data))"""
def crew_default_name (console, race=None):
    """An automatic name for a console, UNIQUE within this run, or "".
    
    Order: a pool somebody registered for this console and race, then that console's
    race-less pool, then the stock given-x-family names. A race with no pool falls back
    rather than returning nothing - asking for a Kralien helmsman should still get one.
    
    Uniqueness is per RUN because `_USED_NAMES` is cleared by the mission reset. Two consoles
    are never the same person, which matters most on a Director bridge wall where they are
    all on screen at once.
    
    Ask :func:`crew_name_gender` what face it should wear - the two are separate calls
    because a name is also handed to callers that draw no face at all."""
def crew_face_gallery (race, count=12):
    """Ready-made face strings for a race, for a PICK-one-of-these gallery.
    
    The avatar editor builds a face out of sliders, which only works for the six stock races
    whose features `faces.FACE_FEATURES` describes. A mod race is whole drawn busts, one per
    atlas cell, with nothing to slide - so it needs a gallery instead, and this is what fills
    it. Returns [] for a race nobody registered."""
def crew_find (spec):
    """Find one roster from a loose spec - an index, a key, a display name, or an
    unambiguous substring of either.
    
    Uses ``maps.label_find_by_spec``, the same matcher ``maps_find`` and ``media_find`` use,
    so a roster named in ``settings.yaml``, in a ``@map`` ``Defaults:``, on the command line
    and in a dropdown all resolve identically. An AMBIGUOUS spec returns None rather than
    guessing."""
def crew_get_list ():
    """The rosters a dropdown may OFFER - the USABLE ones, in declaration order.
    
    Usable means it has at least one member. An unusable roster stays in the registry, so
    ``crew_roster`` still finds it and lint can still complain about it, but it is never put
    in front of an operator - the ``media_get_list`` principle that a dropdown must never
    offer something selection would then refuse."""
def crew_load_amd (file_path):
    """Load and declare crew rosters from a MISSION-relative ``.amd`` file.
    
    Mission-relative, so an ADDON CANNOT USE THIS - the same trap ``sides_load_amd`` has. Use
    :func:`crew_declare_amd` from an addon."""
def crew_name_gender (name):
    """The gender a name was declared with - "male", "female", "fluid" - or "".
    
    Looked up by the WHOLE name and then by the given name alone, so a roster that writes
    "Sana Okonjo" gets an answer from the stock pool's "Sana" without having to say. "" means
    nobody said, and a face rolled for that name is of either."""
def crew_name_list ():
    """Dropdown options string for a crew picker: ``'none, random, <Display>, ...'``.
    
    The map-Properties counterpart of :func:`crew_get_list`. Offers only USABLE rosters,
    for the same reason that function does - a dropdown must never offer something
    selection would then refuse."""
def crew_names_clear ():
    """Drop every registered name AND every name handed out this run.
    
    The allocated complement goes with them: it holds names that are only claimed while
    `_USED_NAMES` holds them, and keeping one without the other would leave seats named after
    people nothing believes are taken."""
def crew_pick_for (ship_id, name, client_id=None, hull=None):
    """The pick string for a person chosen BY DISPLAY NAME, or "" for none of them.
    
    The picker's dropdown is a list of names, and a MAST handler mapping one back to a member
    would be a loop inside a handler - the trap that captures the last iteration's value. So
    the mapping lives here, where it is one call."""
def crew_pick_value (roster_key, member_key):
    """The ``"<roster>:<member>"`` string a picker persists for a chosen person."""
def crew_post_of (client_id):
    """The post this client was last assigned, rebuilt from its inventory. None if unnamed."""
def crew_preview (pick):
    """The (name, face, portrait) a picked person shows, for a preview beside the picker.
    
    Returns ("", "", "") for an unresolvable pick, so a screen can bind all three without
    testing first."""
def crew_preview_markdown (face, portrait, height=88, align='center'):
    """A `gui_text_area` body that shows one crew member, or "" for nobody.
    
    ONE widget for both kinds of likeness, which is the point: a text area already speaks
    `face://` and `image://`, so a screen binds a single value and never has to swap widgets
    when a roster answers with a photograph instead of a face string. It also sidesteps the
    absolute-region ghost - a plain value update on an ordinary widget refreshes cleanly,
    where a child updated inside an absolute `gui_region` keeps the old draw underneath.
    
    A PORTRAIT BEATS A FACE, never both: a photograph is the stronger statement, and
    stacking them has no rule to resolve it."""
def crew_preview_post (client_id, ship_id, console, own_name=None, own_face=None, own_portrait=None, own_pick=None, hull=None, slot=None):
    """Who WOULD be at this console - the same answer, without taking anything.
    
    For a picker showing the player who they are about to be. It writes nothing and claims no
    seat, and because a seat's automatic name is allocated once and remembered
    (:func:`crew_seat_name`), what it shows IS what :func:`crew_assign` publishes - the two
    cannot drift apart. Clicking through every station on the picker costs the name pool one
    name per station looked at, and costs it that once."""
def crew_register_names (console, names, race=None, gender=None):
    """Declare fallback names for a console, optionally for one race.
    
    These fill seats a roster left empty - never seats nobody asked about. See
    :func:`crew_default_name`.
    
    ``gender`` says which face these names should wear - "male", "female", "fluid". Register
    a list per gender rather than one mixed list: a face is rolled for whoever ends up in
    the seat, and it has to agree with the name above it. Names registered without one get
    a face of either, exactly as before."""
def crew_release (client_id):
    """Give up whatever seat this client holds, on every ship.
    
    Called when a console changes ship or station. Occupancy is self-healing anyway, so this
    is an optimization rather than a correctness requirement - it frees the person for the
    next client in the same frame instead of on the next resolve."""
def crew_resolve (client_id, ship_id, console, own_name=None, own_face=None, own_portrait=None, own_pick=None, hull=None, slot=None):
    """Who is at this console, and why. Returns a post - see the module docstring.
    
    Resolution runs strongest first, and the ``source`` on the returned post says which tier
    answered:
    
    ``own``
        What this human chose at the picker - a typed name, a built face, or a person they
        picked out of a ``By: person`` roster. Nothing outranks a person's own answer.
    
        PER FIELD, not wholesale. What they did not answer is still answered by the tier
        below, so naming yourself keeps the face the ship gave you and building a face keeps
        the name. It used to replace the whole identity, which meant editing one aspect blanked
        the others: opening the avatar editor on an automatically named officer and pressing
        Done left them with a face and NO NAME.
    ``ship`` / ``map`` / ``hull``
        A roster bound to this named ship, selected for this game, or declared by a mod for
        this hull. :func:`crew_roster_for` picks between them; :func:`_seat_pick` then
        chooses a member within it.
    ``library``
        A registered fallback name, filling a seat the roster left empty.
    ``unmanned``
        Nobody - which is exactly what a mission that does none of this gets, and why this is
        backward compatible.
    
    ``hull`` is the shipData key and ``slot`` the player-roster slot, for a caller that has
    those and no ship - the console picker is choosing a hull for a ship that does not exist
    yet. The hull reaches the roster lookup and the fallback face's race; the slot names the
    seat, and is what a live player ship resolves to anyway, so a station previewed by slot
    and then taken on the spawned ship is the same seat.
    
    Does NOT write anything. :func:`crew_assign` is the one that does."""
def crew_roster (key):
    """One roster by exact key, or None."""
def crew_roster_for (ship_id, hull=None):
    """Which roster staffs this ship, and WHY: ``(roster, source)``.
    
    Source is ``ship`` / ``map`` / ``hull`` / None, strongest first. It is returned rather
    than merely logged because "why is this console called that" is otherwise unanswerable
    from the outside - every tier looks identical once it has produced a name.
    
    ``hull`` is the shipData KEY, for a caller that has one and no object - the console picker
    is choosing a hull for a ship that does not exist yet. Without it the ``hull`` tier could
    never answer during setup, which is precisely the tier a mod's cast rides on. A ship_id
    given as a bare string is read as a ship NAME first and a hull key second, so either fact
    may be passed in either place."""
def crew_rosters ():
    """Every declared roster, in declaration order."""
def crew_seat_count ():
    """Reset-ledger probe: how many LIVE seats are held.
    
    Separate from :func:`crew_count` on purpose - declared rosters and occupied seats leak
    for different reasons, and one probe covering both cannot say which of them happened."""
def crew_seat_name (ship, console, occupant=0, race=None, slot=None):
    """The automatic name for a SEAT - allocated once, then the same answer forever.
    
    ``occupant`` is which person at that station: 0 is the station's own officer, 1 the second
    client to open it, and so on. Each is allocated on first ask, so a ship costs the pool only
    the seats somebody actually looked at.
    
    Public because a seat has a name whether or not anyone is sitting in it: a Director bridge
    wall listing stations wants "helm - Sana Okonjo" rather than "helm - unmanned" for a ship
    whose crew simply is not all on screen.
    
    Returns "" when automatic naming is off (``CREW_AUTONAME``) or the pool is exhausted."""
def crew_select (spec):
    """Resolve the roster a setting, a map or an operator ASKED for.
    
    Args:
        spec: ``""``/``None``/``"none"`` selects nothing - the deliberate default, see
            ``CREW_SELECT`` in settings; ``"random"`` picks from every usable roster;
            anything else goes through :func:`crew_find`.
    
    Returns:
        The roster record, or None.
    
    A spec that matches nothing WARNS BY NAME and selects nothing. Silence was the tempting
    choice and the wrong one: ``CREW_SELECT: Enterprize`` would leave every console unnamed,
    which is indistinguishable from never having asked."""
def crew_selected_name ():
    """The current CREW_SELECT, or ``"none"``.
    
    Reads the shared value first, then the setting, so a map's `default shared` seed cannot
    overwrite a choice a profile already made."""
def crew_self_pack (pick='', face='', portrait=''):
    """Pack this player's own choices into one client-string value."""
def crew_self_unpack (text):
    """(pick, face, portrait) out of a packed value. Always a 3-tuple, so a caller can
    unpack it without testing - an empty or malformed value reads as three blanks.
    
    Braces are stripped on the way OUT as well as in, because the value comes off the
    player's own disk and a hand-edited client_string_set.txt is not this file's to trust."""
def crew_unbind_ship (ship_or_name):
    """Drop a ship's binding, so it falls back to the map / hull / library tiers."""
