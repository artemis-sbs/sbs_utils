from sbs_utils.helpers import FrameContext
def marker_area (x, y, z, size_x, size_z=None, text='', color='#0cf4'):
    """A labelled REGION on the map, centered on (x, z) - the shape a job means by "the
    shipping lane" or "the asteroid field". Returns its navarea id.
    
    `size_x`/`size_z` are the FULL width and depth, not half-extents, so they match the
    scatter box a job spawns its targets into: pass the same numbers and the marker
    covers exactly what was placed inside it.
    
    The four corners are given in the order the engine expects; the y coordinate is
    unused (a navarea is a ground-plane quad) and is accepted only so the call site can
    pass the same centre it spawned around."""
def marker_delete (handle):
    """Remove a marker: the id from marker_point/marker_area, or what marker_object
    returned. Safe to call twice, and safe on either kind.
    
    A navpoint id and an agent id are both plain ints, so this tries the navpoint
    registry first and falls through to the object - guessing from the type would delete
    the wrong thing exactly when a mission holds both."""
def marker_delete_role (role_name):
    """Remove every marker OBJECT carrying `role_name` - how a job clears its own
    markers when it completes. Navpoints are not roles and are removed by id."""
def marker_object (x, y, z, text, roles='', color='gold'):
    """A SELECTABLE marker - a real object the crew can click, scan or hail.
    
    Built the way the nebula cluster marker is (terrain.py): `behav_selection` so it can
    be selected, `elite_main_scn_invis` so it does not hang in space on the main screen,
    and a radar color so it reads as map furniture rather than as a contact.
    
    `roles` are added on top of `map,marker` - a job marks its own with its own role so
    it can find and remove them later."""
def marker_point (x, y, z, text, color='#0cf'):
    """A labelled dot on the map. Returns its navpoint id."""
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
