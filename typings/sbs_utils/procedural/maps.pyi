from sbs_utils.helpers import FrameContext
def map_get_properties (map):
    """Return the ``Properties`` inventory value of a map label.
    
    Checks ``"Properties"`` first, then ``"properties"`` as a fallback.
    
    Args:
        map (Label): The map label object.
    
    Returns:
        any: The properties value, or ``None`` if not set."""
def maps_get_init ():
    """Return the ``__overview__`` map label from the current MAST story, or ``None``.
    
    Returns:
        Label | None: The overview map label, or ``None`` if not defined."""
def maps_get_list ():
    """Return all ``@map`` labels defined in the current page's story.
    
    If only an ``__overview__`` label exists, it is returned as a single-item
    list. If no map labels are found at all, returns a placeholder list with a
    ``"No maps found"`` entry.
    
    Returns:
        list: ``@map`` Label objects, or a fallback list if none are defined."""
