def _apply (client_id, fn, target):
    ...
def _beam (client_id, area):
    ...
def _beam_app (client_id):
    """The transporter: where the ship can put you, and whether it can right now."""
def _esc (text):
    """Free prose in a style string. A `:` or `;` in a title or description would
    otherwise be read as style properties and silently truncate the widget - the same
    trap `gui_map_picker` documents on its cards."""
def _exits (client_id):
    """[(exit mark, destination title)] for the area this console is standing in - only
    to places the party knows about."""
def _give (client_id, item, to):
    ...
def _go_exit (client_id, mark):
    """Walk to the nearest cell of an exit mark; stopping on it goes through."""
def _go_to (client_id, key):
    ...
def _in_a_suit (client_id):
    ...
def _in_sight (client_id):
    """What Scan lists - only while Scan is the open app, so walking with another app
    open does not rebuild it on every step."""
def _leads (client_id):
    """What the open quests point at, and where - a button walks there when it is in
    this area. A quest names its leads with `Leads to:`."""
def _look_app (client_id):
    ...
def _medkit (client_id, me, target):
    """The stock medkit: stand somebody back up, or patch a wound."""
def _near (client_id):
    """[(kind, key, name)] within reach: props, then talkable hostiles, then crew."""
def _nearby (client_id):
    ...
def _nearby_revision (client_id):
    """The Look and Tasks lists, without distances: a step that changes only how far
    something is does not rebuild the device; a new bearing, hint or thing does."""
def _on_ground (client_id):
    ...
def _own_quests (client_id):
    """The personal quests this console's crew member was handed (`For:`)."""
def _pack_app (client_id):
    ...
def _places ():
    """Where each crew member is standing, as the Crew app words it. A mark changes
    rarely, so this repaints on arriving somewhere, not on every step."""
def _suit_leads (client_id):
    """In a relic: the places the open quests point at, nearest first, and a press flies
    the suit there - the Nav app's own verb, so a lead is one press from a course."""
def _tasks_app (client_id):
    """This crew member's own quests, then the party's."""
def _tasks_available (client_id):
    """Tasks follow the crew member, on the ground or in a suit - a quest is theirs
    wherever they are standing.
    
    AND IN A PARTY WITH NOWHERE TO STAND, when they hold a quest of their own. A visit that
    is rooms only (no tile area, no suit) had Crew and Act and nothing else, so a quest
    handed to one person was on no screen at all: not on the handheld, and not on the
    ship's Quests list, which shows the ship's. The person it was written for never saw
    its name. Somebody with no quest of their own keeps the two-tile device."""
def _tasks_revision (client_id):
    ...
def _use (client_id, kind, key):
    ...
def gui_xess_head (client_id, title, back=True, surface='boarding'):
    """An app's title line, with the way back to the tiles.
    
    Every app draws this, so Back is in the same place on all of them - which is the
    only reason a crew member can leave an app they have never seen before."""
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
def xess_ground_register ():
    """Register the ground apps. At import, and again from `xess_clear` - the mission
    reset clears every registration and used to put back only the device's built-ins, so
    from the second run of a reused interpreter a landing party had no Look, Pack, Tasks
    or Beam at all."""
def xess_ground_revision (client_id):
    """What the ground apps show, for the device's revision."""
def xess_ground_use (item, fn, label='Use'):
    """Give an item a USE from the Pack: ``fn(client_id, lifeform, target)`` where
    ``target`` is a teammate beside you (or yourself). Return text for the device."""
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
