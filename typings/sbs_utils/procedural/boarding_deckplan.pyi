from collections import deque
def _boarded_on_signal (name, data):
    """The visit ended - a choice, the mission, the game - so the deck comes down. Here
    and not on the next tick: the results screen pauses the sim, and a paused sim ticks
    nothing."""
def _boarded_over ():
    """The party is off the ship: the role comes off, the deck comes down. Idempotent."""
def _boarded_tick (t=None):
    """One look at the boarded ship. NEVER RAISES - a raising interval pauses the sim."""
def _deck_art (tileset):
    """Dress the deck's tileset from the ``station`` set. Never loads a set twice: a set
    loaded again goes back on top of the sets loaded after it."""
def _deck_say (message, once=None):
    """Tell the author - in the engine's debug.log and on the console - without failing
    a headless run: a hull with no brig is not a mistake in anybody's files."""
def _end_an_empty_landing ():
    """End a TILE visit that is not a boarded ship's deck when nobody of its party is on
    the ground. True when one was ended.
    
    Not a text visit: it has no ground to be off, and it ends itself when its scene
    closes. Not a deck: a party aboard a ship is that ship's business
    (``boarding_deck_target``), ended by one of its three endings."""
def _entry (cells, region, names, kinds, cell_tiles, W, H):
    """The airlock's first cell; else the hallway cell nearest the middle of the ship;
    else the middle-most room cell. Its floor tiles."""
def _gangways (cells):
    """Join a plan that comes in pieces (a starbase's modules, a bio-ship's pods) with
    hallway across the gaps, nearest pieces first, so the deck is one walk. Returns the
    cells to add as hallway."""
def _grid_state (ship):
    """``[(grid object id, x, y, damaged, damcon, hp)]`` for a ship's interior now. The
    seam the tests replace."""
def _hold (target):
    """Keep a boarded ship where it is: no course, no target, no throttle. Asked again
    every second, because whatever flies it may ask otherwise."""
def _keeps_the_way (floor, start, blockers, cell, blocks, base):
    """THE RULE for standing anything on a deck: nothing seals a room, and nothing is
    walled in. Whether ``cell`` can take something - one that blocks or one that does
    not - given the cells that already block and ``base``, what can be walked from
    ``start`` round them today.
    
    - something that does not block must stand where a party can walk;
    - something that blocks must leave every other tile walkable that was, must itself
      have a tile beside it to be walked up to, and must not take the last such tile
      from anything already standing.
    
    One rule for a writer's records (``boarding_deck_settle``) and for the ship's own
    crew (``boarding_deck_crew``), checked by walking the real floor from the entry
    every time - so it holds whatever the hull, the kinds of room and the order of the
    records, and an unrelated record can change WHERE something stands but never
    WHETHER it can be reached."""
def _marks_of (area):
    ...
def _neighbours (t):
    ...
def _pieces (cells):
    """The plan's separate pieces - cells joined four-ways - biggest first."""
def _reach (floor, blocked, start):
    """The tiles of ``floor`` that can be walked to from ``start`` round ``blocked``."""
def _regions (cells):
    """{cell: region id} - same-named cells joined four-ways - and each region's name."""
def _stop (task):
    ...
def _words (text):
    ...
def boarding_deck_animate (area, seconds=0.25):
    """Keep a deck alive - doors, sparks, fire (``boarding_deck_animate_step``) - every
    `seconds`, until it is cleared. Started by ``boarding_deck_watch``; call it yourself
    for a deck with no ship behind it. Returns the tick task."""
def boarding_deck_animate_step (area):
    """One beat of a deck's life: doors slide open for anyone beside them and shut
    behind them, and flickering things (sparks, fire) flip frame every other beat.
    Returns how many things changed. ``boarding_deck_animate`` runs it for you."""
def boarding_deck_art_ready ():
    """True when the art a deck is drawn with (the ``station`` set) is installed - in
    the mission, or in a media pack pinned in its story.json."""
def boarding_deck_boarders ():
    """The ship the party aboard came from (its id), or None."""
def boarding_deck_build (plan, key, title=None, scale=3, tileset='deck', furnish=True):
    """Build a boarding area from a plan: the tiles, a mark per room, and the furniture
    as scenery props. Declares the tileset first if nothing has. Returns the area key,
    or None when the plan has no open cell.
    
    Room marks are ``room:<name>`` (``room:hallway`` for hallways), plus ``entry`` and
    ``door`` - and a mark per KIND of room (``brig``, ``cargo``, ``hallway``) holding
    the floor of that kind nothing stands on. The prop keys are ``<area>_kit_<n>``.
    
    Built under ``DECK_AREA`` it is the deck `Area: deck` records are waiting for, and
    they are stood aboard (``boarding_deck_settle``)."""
def boarding_deck_built (area='deck'):
    """True while a generated deck stands under this key."""
def boarding_deck_clear ():
    """The per-mission reset. Emits nothing and moves nobody."""
def boarding_deck_count ():
    """For the reset ledger."""
def boarding_deck_crew (area, ship=None, boarders=None, hostile=None, count=None, talk_scene=None, seed=None):
    """Put a boarded ship's own crew aboard its deck, drawn as its race, as boarding
    hostiles (``boarding_combat``) - some who fight, some who do not:
    
    - aboard a ship at war with the boarders, about three in five are GUARDS, walking the
      hallways between two points and fighting whoever they notice; the rest are HANDS,
      calm, in the cabins and messes, who only fight back when provoked;
    - aboard any other ship everyone is a hand.
    
    NOBODY SEALS A ROOM. They stand still and they block, so each is stood only where
    the whole deck can still be walked from the entry and everything already aboard - a
    writer's `Area: deck` records, the crew stood before them - can still be walked up
    to (``_keeps_the_way``). A cell that fails is passed over for the next; on a hull
    with nowhere left, that one of the crew is not aboard.
    
    Args:
        area: the deck (``boarding_deck_build`` / ``boarding_deck_for``).
        ship, boarders: the boarded ship and the boarders' ship; ``side_are_enemies`` of
            the two decides the stance unless ``hostile`` does.
        hostile (bool): force the stance.
        count (int): how many; by default one per ten cells of the plan, 2 to 12.
        talk_scene (str): a scene key the hands can be talked to with (the mission's own
            dialogue); without one they cannot be talked to.
        seed: for a repeatable crew; the area's name by default.
    
    Returns:
        list: the hostile keys, ``<area>_crew_<n>``. Placed at once."""
def boarding_deck_crew_sprites (ship_key):
    """The figures a hull's crew is drawn as."""
def boarding_deck_for (ship, title=None, watch=True, tileset='deck'):
    """The boarding deck of a live ship: built the first time it is asked for, then kept
    in step with the ship (``boarding_deck_watch``). Returns the area key - hand it to
    ``boarding_invite(..., area=...)`` to put a party aboard - or None when the hull has
    no interior plan.
    
        deck = boarding_deck_for(enemy_id, title="Kralien cruiser")
        boarding_invite(player_ship, [], title="Boarding", area=deck)"""
def boarding_deck_has_plan (ship):
    """True when this ship's hull has an interior plan to draw a deck from. Cheap - one
    lookup - so a comms route can ask it of whatever is selected."""
def boarding_deck_kinds ():
    """The tile kinds generated decks use: every look the kits name is a kind of the same
    name, walls and hull closed - ``{kind: {walk, see, look}}``."""
def boarding_deck_kit (kind, floor=None, furniture=None, system=None):
    """Change what one kind of room looks like, for this mission. ``kind`` is a kit name
    (``cargo``, ``warp``, ``quarters``...) or a new one, which rooms whose roles or name
    contain that word will then use. Returns the kit as it now stands."""
def boarding_deck_kit_for (kind):
    """The kit of one kind of room, with this mission's changes."""
def boarding_deck_layout (plan, scale=3):
    """Lay a plan out as tiles. Pure: no areas, no props. Returns a dict:
    
    - ``w``, ``h``, ``tiles``: the map, rows of LOOK names, None outside the ship;
    - ``rooms``: ``{mark: set(tiles)}``, a mark per room name (``room:cargo``) plus
      ``room:hallway``; ``doors``: the doorway tiles;
    - ``entry``: the arrival tiles; ``furniture``: ``[(sprite, x, y, system_cell)]``,
      ``system_cell`` being the plan cell a system's kit stands for (None for plain
      furniture);
    - ``cell_tiles``: ``{plan cell: its floor tiles}``;
    - ``kinds``: ``{kind: set(tiles)}``, the floor of each KIND of room that nothing
      stands on (``hallway`` included); ``floor``: every tile that can be walked."""
def boarding_deck_mark_words ():
    """The words `Mark:` takes on `Area: deck`, sorted: every kind of room the generator
    knows (and the words that mean one - ``cabin``, ``surgery``), ``entry`` and
    ``hallway``. What the linter checks a `Mark:` against."""
def boarding_deck_plan (ship, layout=None):
    """A plan for a ship: its interior layout (grid data), with the open cells of its
    hull map as hallway. ``ship`` is a live ship, or a shipData key - which has no hull
    map. None when the hull has no interior.
    
    WHERE THE HALLWAYS COME FROM is ``plan["source"]``, because only the engine can say
    whether a ship nobody flies has a hull map at all:
    
    - ``hull map``: the engine's own open cells for this ship;
    - ``grid text``: no hull map, so the hallways its `.grid` file drew
      (``grid_get_open_cells``);
    - ``rooms only``: neither - the rooms, joined by gangways.
    
    The rooms are the hull's interior when it has one, else a plan kept for reading
    (``grid_plan_ascii`` - how a hull nobody flies has a deck and no interior)."""
def boarding_deck_plan_ascii (text, ship_key=None):
    """A plan from an ASCII interior (`.grid`): ``{"ship", "w", "h", "cells"}`` where
    ``cells`` maps each open ``(x, y)`` to its room name, ``""`` for hallway."""
def boarding_deck_race (ship_key):
    """The race whose crew a hull carries, from its key: ``kralien_cruiser`` ->
    ``kralien``, ``starbase_torgoth`` -> ``torgoth``. ``human`` for anything not in
    ``RACE_CREWS``."""
def boarding_deck_ready (ship):
    """Can a party be sent aboard this ship and SEE it: the hull has a plan, and the
    deck art is installed. What the "Send a boarding party" button asks."""
def boarding_deck_release (area='deck'):
    """Take a generated deck down: its furniture, doors and crew are forgotten, anything
    dropped on it with them, and the area is unloaded. A writer's own `Area: deck`
    records are taken off the map and KEPT - `Mark: brig` again, waiting for the next
    ship - with whatever was opened, taken or put down still so.
    
    Returns:
        bool: True when there was a deck to take down."""
def boarding_deck_room_kind (name):
    """Which kit a room of this name uses: its roles, most specific first, then the
    words of its name. ``hallway`` for a hallway, ``room`` when nothing matches."""
def boarding_deck_settle (area='deck', place=True):
    """Stand a writer's records aboard a generated deck: every prop, person and hostile
    whose `Area:` is this deck gets a cell in a room of the KIND its `Mark:` names.
    
    - a cell nothing stands on, and each record a cell of its own: two things marked
      ``brig`` are two cells of the brig;
    - something that blocks (`Blocks: yes`, anybody `Calm: yes`) is never stood where
      it would cut the deck in two - a one-cell room with a way through it cannot take
      one, and that is the hallway too - and nothing is stood beside a doorway while
      there is anywhere else;
    - ``entry`` is beside where the party arrives; ``hallway`` is any hallway;
    - a hull with NO such room stands it in the hallway, and says so in ONE line for
      that kind (``debug.log``, and the console) - not an error: the same mission
      boards a cruiser that has a brig and a scout that has not.
    
    `At: x, y` is left as written (a cell means nothing on a deck nobody has seen, and
    the linter says so). What was taken, opened or put down stays so.
    
    Safe to call again: a record already standing is left where it is, and only what
    has been declared since is settled. ``boarding_deck_build`` calls it for
    ``DECK_AREA``, and ``boarding_ground_load`` does when a deck is already up.
    
    Returns:
        dict: ``{key: (x, y)}`` for the records this call settled."""
def boarding_deck_source (area='deck'):
    """Where a built deck's hallways came from: ``hull map`` (the engine's own open
    cells), ``grid text`` (the hull's `.grid` file - the engine gave this ship no hull
    map) or ``rooms only``. None when no deck stands under that key. The same word the
    "was planned from" line in debug.log ends with."""
def boarding_deck_sync (area, ship):
    """Show a ship's state on the deck built from it: a damaged node's kit goes dark
    with rubble beside it - sparks by a system, fire in any other room - a repaired one
    comes back, and each damage-control team
    stands - and walks - where Engineering has it. Call it when things change, or let
    ``boarding_deck_watch`` call it every second. Returns how many things changed."""
def boarding_deck_system_prop (area, cell):
    """The prop key of the kit standing for a system node, or None."""
def boarding_deck_target ():
    """The ship a party is aboard (its id), or None."""
def boarding_deck_text (layout, key, title=None, tileset='deck'):
    """The layout as a `.tiles` area file (kinds and the entry; room marks are added by
    ``boarding_deck_build``, so an author's copy stays readable)."""
def boarding_deck_tiles_of (area, cell):
    """The floor tiles a plan cell became - where a damaged node's sparks go."""
def boarding_deck_tileset (name='deck'):
    """Declare the tileset generated decks use (``boarding_deck_kinds``). Returns its
    name."""
def boarding_deck_visit (ship, target, scenes=None, title=None, stories=None):
    """Send a boarding party from ``ship`` aboard ``target``, on a deck drawn from the
    target's own interior plan. One call::
    
        boarding_deck_visit(COMMS_ORIGIN_ID, COMMS_SELECTED_ID, boarding_ground_scenes())
    
    What it does, in order: the target's plan becomes the tile area ``deck``
    (``DECK_AREA``), dressed from the ``station`` art; every `Area: deck` record is stood
    in a room of its kind (``boarding_deck_settle``); the target's own crew comes aboard
    as its race (``boarding_deck_crew`` - calm unless the two ships are at war); the
    target wears the role ``boarding_target`` and is held where it is; and a tile-map
    visit is opened (``boarding_visit``), kept under the ship's name.
    
    It ends as any tile visit does - ``boarding_visit_end()``, or the game ending - and
    also when the target is gone. However it ends, the deck is taken down
    (``boarding_deck_release``) and the role comes off.
    
    ONE DECK AT A TIME. A deck left from the last ship is taken down first.
    
    A LANDING PARTY THAT IS ALL HOME IS NO OBSTACLE. A tile-map visit somewhere else - a
    landing a mission opened, which nothing but the mission ever closes - is ENDED first
    when nobody of its party is on the ground (``boarding_visit_ended`` is sent for it,
    as for any visit). It is what "the last one home ends it" means for a place that has
    no hail to decline. With somebody still down there the answer is None, as it always
    was, and nothing is touched: nobody is pulled off a planet by a button on the bridge.
    Coming back, the mission opens its own site again, as it did the first time. A text
    visit (rooms and choices) and another ship's deck are never ended for this.
    
    Args:
        ship: the ship the party leaves from.
        target: the ship being boarded.
        scenes: what a prop's `Scene:` and a person's `Talk scene:` name -
            ``boarding_ground_scenes()``.
        title (str, optional): the name of the place; the target's name by default.
        stories (optional): as ``boarding_visit`` - quests for one person each.
    
    Returns:
        dict: the invitation - or None, with nothing built and nothing opened, when the
        target is gone or its hull has no plan, or a party is already out."""
def boarding_deck_watch (area, ship, seconds=1.0):
    """Keep a deck in step with its ship (``boarding_deck_sync``) every few seconds,
    until the deck is cleared or the ship is gone. Returns the tick task."""
def tilemap_sprite_cells (key):
    """The cells a sprite covers, as ``(dx, dy)`` offsets from its actor's own cell.
    
    Always holds ``(0, 0)``; a sprite with no ``base`` covers just that. Every other
    cell is covered when more than half of it is under the base, each way."""
