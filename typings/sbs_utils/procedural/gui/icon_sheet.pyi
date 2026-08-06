def icon_names ():
    """Every name that resolves - the built-ins plus the meanings. For lint, for a
    picker, and for anyone wondering what they may ask for."""
def icon_props (name, color=None, extra=None):
    """(kind, props) for a DIRECT engine send: kind is "icon" or "image", props the style
    string to hand it.
    
    Widget code goes through `gui_icon_name`, but the low-level renderers call
    `send_gui_icon` themselves with a hand-written property string - which is where the
    remaining magic numbers live. This lets them name what they draw without giving up
    the direct send, and an atlas-backed name comes back as an IMAGE because the engine
    has no icon concept for art it did not ship.
    
    Never raises and never returns nothing: an unknown name falls back to the built-in
    look, because a renderer mid-frame is the worst place to discover a typo."""
def icon_resolve (name):
    """A name -> (icon_index, atlas_key). Exactly one of the two is set.
    
    Follows aliases first, so `quest.job` lands on whatever look it currently points at.
    An unknown name resolves to (None, None) and the caller draws nothing rather than
    guessing a glyph - a wrong icon is worse than a missing one.
    
    The atlas branch is what makes a custom sheet a drop-in later: register the look in
    the ICON DOMAIN (`gui_icon_add_atlas`, or `Kind: icon` in AMD) and it wins, with no
    change to anything that draws it.
    
    The domain is a GUARD, not ceremony. `ImageAtlas.all` is one process-wide dict, so
    without it any mission registering an image called `square` or `flag` - words no one
    would think twice about - would silently re-skin every icon meaning pointing there.
    Overriding a look has to be something you meant."""
