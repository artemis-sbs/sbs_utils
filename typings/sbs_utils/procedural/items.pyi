from sbs_utils.vec import Vec3
def _item_spawn_pool (categories):
    """(keys, weights) eligible to spawn in space, weighted by 1/tier."""
def item_get (key):
    """Return the item label whose metadata ``key`` matches, or ``None``."""
def item_keys ():
    """Return the list of all registered item keys."""
def item_meta (item, field, default=None):
    """Read a metadata field from an item (a label object or a key string)."""
def item_spawn (key, x, y, z, name=None, blink=None, yaw=None, qty=None):
    """Spawn a collectible pickup for an item ``key`` at ``(x, y, z)``.
    
    Art comes from the registry; the key is stored on the pickup as the
    ``item_key`` inventory value so the generic collision route can credit it
    without any per-item code.
    
    ``qty`` makes ONE pickup worth several units - a salvage cache, an ore seam. Without
    it a bulk resource has to spawn one object per unit, which is both object churn and a
    tedious pickup grind (a job needing 24 salvage would scatter 24 collectibles). The
    collection route reads it, defaulting to 1, so existing pickups are unaffected.
    
    An UNREGISTERED key is a mission bug, and a silent one: the art it falls back to
    decides both the mesh and -- via the art's shipData ``interactionradius`` -- whether
    ``//collision/interactive`` fires at all, so an unregistered pickup can look like a
    ``?`` and be uncollectable. Fall back to the key itself (item keys and art keys
    coincide by convention, so it is the best available guess) and log a warning, rather
    than quietly spawning the ``unknown`` placeholder, which has no interaction radius."""
def items_get_list ():
    """Return all registered item labels (metadata ``type: item/...``)."""
def items_of_category (category):
    """Return item labels whose ``type`` contains the given category segment.
    
    e.g. ``items_of_category("upgrade")`` or ``items_of_category("resource")``."""
def labels_get_type (label_type):
    """Return all labels whose type or path starts with the given prefix.
    
    Walks every label in the current story, checking the ``type`` metadata key
    first, then the label ``path`` attribute, then the label name.
    
    Args:
        label_type (str): Prefix to match, e.g. ``"map/"`` or ``"media/"``.
    
    Returns:
        list[MastNode]: Matching label objects."""
def log (message: str, name: str = None, level: str = None, use_mast_scope=False) -> None:
    """Emit a log message using Python's ``logging`` module.
    
    When ``use_mast_scope=True`` the message is formatted through the current
    MAST task's string formatter first (MAST exposes this as ``log``).
    
    Args:
        message (str): The message to log. May contain MAST format strings when
            ``use_mast_scope=True``.
        name (str, optional): Logger name. Defaults to None (``__base_logger__``).
        level (str, optional): Logging level string, e.g. ``"DEBUG"``, ``"INFO"``.
            Defaults to None (``DEBUG``).
        use_mast_scope (bool, optional): Format the message via the current
            MAST task. Defaults to False."""
def pickup_spawn (x, y, z, roles, blink=None, yaw=None, name=None, art_id=None):
    """Legacy shim: the old ``roles`` arg carried the upgrade key."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def terrain_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a passive terrain object into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the object belongs to, or ``None``.
        ship_key (str): Object template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new terrain object."""
def terrain_spawn_items (density, center=None, points=None, categories=None):
    """Scatter tier-weighted item pickups (default categories: upgrade+resource).
    
    ``density`` 1-4 controls how many spawn. If ``points`` is given they are
    sampled; otherwise a box scatter around ``center`` is used."""
def terrain_spawn_pickups (upgrade_value, center=None, points=None):
    """Legacy shim onto the registry-driven spawner."""
