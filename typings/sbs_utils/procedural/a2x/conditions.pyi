def _distance_between (obj1, obj2):
    """Distance between two objects, or ``None`` if either is missing/destroyed.
    
    ``sbs.distance_id`` errors ("was sent None") for an id that is None or refers to
    a deleted object, and ``to_id`` passes both straight through -- so resolve to live
    objects first. Callers turn ``None`` into a False condition."""
def distance_greater (obj1, obj2, radius):
    """2.8 ``if_distance`` (GREATER) as a live boolean for polling loops.
    
    Also False when either object is missing or destroyed: a destroyed object is
    not "infinitely far away", it is untestable, so the condition should not fire."""
def distance_less (obj1, obj2, radius):
    """2.8 ``if_distance`` (LESS) as a live boolean for polling loops.
    
    False when either object is missing or destroyed -- a 2.8 condition about an
    object that does not exist simply never fires."""
def in_box (obj, least_x, least_z, most_x, most_z, inside=True):
    """2.8 ``if_inside_box`` / ``if_outside_box`` (an XZ rectangle).
    
    The corners are converted from 2.8 to Cosmos coordinates (the 180-degree XZ
    mirror), so the test is correct in Cosmos space. Returns ``inside`` semantics
    by default; pass ``inside=False`` for the outside test."""
def is_docked (ship, station=None):
    """2.8 ``if_docked``: True if ``ship`` is currently docked.
    
    The engine stores ``dock_state`` as ``"undocked"`` when not docked (otherwise a
    docked marker / station). ``station`` is accepted for call-site parity with 2.8
    but not matched -- Cosmos dock state is effectively boolean here."""
def pos (x, y, z):
    """Convert a 2.8 corner-origin position to a Cosmos :class:`Vec3`.
    
    Mirrors x and z about the map centre (y unchanged). Unpack into a spawn call::
    
        npc_spawn(*a2x_pos(50000, 2, 59000), name, side, art, behave)
    
    Args:
        x, y, z (float): a position in Artemis 2.8 coordinates.
    
    Returns:
        Vec3: the equivalent Cosmos position."""
def within (obj, x, y, z, radius):
    """True if ``obj`` is within ``radius`` of a 2.8-coord point (flipped internally).
    
    A boolean for polling loops (2.8 if_distance-to-point / if_inside_sphere)."""
