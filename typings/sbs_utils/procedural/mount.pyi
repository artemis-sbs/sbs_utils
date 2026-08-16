from sbs_utils.helpers import FrameContext
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.vec import Vec3
def _mount_all_mounted ():
    ...
def _mount_connect (host_id, mount_id, off):
    """The one place the raw engine call is made."""
def _mount_disconnect (host_id, mount_id):
    ...
def _mount_key (name):
    ...
def _mount_on_destroy (destroyed, damage_event=None):
    """Host destroyed -> release its mounts, honoring each one's delete_with_host.
    
    Registered with LifetimeDispatcher so it reacts in the same handler the destruction
    is routed in, rather than a tick later with a dangling weld."""
def _mount_sim ():
    ...
def _mount_vec3 (offset):
    """Accept a Vec3, an (x, y, z) tuple, or None -> origin."""
def add_role (set_holder, role):
    """Add a role to one or more agents.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Agent(s) to update.
        role (str): The role name to add."""
def delete_object (id_or_objs):
    """Delete one or more agents from the simulation.
    
    Args:
        id_or_objs (Agent | int | set[Agent | int]): Agent(s) to delete."""
def get_dedicated_link (so, link_name: str):
    """Return the single agent ID linked under a dedicated (1-to-1) link.
    
    A dedicated link stores exactly one target per source. Use ``link`` /
    ``set_dedicated_link`` for many-to-many or 1-to-1 links respectively.
    
    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        int | None: The linked agent ID, or ``None`` if not set."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def link (set_holder, link_name: str, set_to):
    """Create a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to link to."""
def linked_to (link_source, link_name: str):
    """Return the set of IDs that an agent links to under a given name.
    
    Args:
        link_source (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
    
    Returns:
        set[int]: IDs of all linked targets, or an empty set if none."""
def mount_attach (host, mount, offset=None, delete_with_host=True):
    """Weld an existing object into the host's body frame.
    
    Args:
        host (Agent | int): The object to ride on.
        mount (Agent | int): The object to attach.
        offset (Vec3 | tuple, optional): Position in the HOST's own frame -
            ``+z`` forward, ``+x`` right, ``+y`` up. Defaults to the host's center.
        delete_with_host (bool): Delete this mount when the host is destroyed
            (default). Pass False to leave it floating as debris - a blown-off
            turret that can be salvaged.
    
    Returns:
        int | None: The mount's id, or None if either object is missing or the
            engine refused the connection."""
def mount_clear_all ():
    """Release every mount without deleting anything.
    
    There is no module-level registry to clear - the relationships live on the agents
    themselves and are purged with them - so this is for tests, for a mid-mission clean
    slate, and for reset_mission_state to drop the ENGINE-side welds deliberately.
    
    Tolerates having no frame context: a reset can fire with none, and dropping our own
    state must never depend on the engine being there."""
def mount_count ():
    """How many welded mounts exist. Cheap probe for tests and diagnostics."""
def mount_detach (host, mount, delete=False):
    """Release a mount. Optionally delete it.
    
    Deletion goes through the procedural ``delete_object`` (deferred) rather than the
    engine call, which frees the C++ object synchronously and would leave anything still
    holding it pointing at freed memory."""
def mount_detach_all (host, delete=None):
    """Release every mount on a host.
    
    Args:
        delete (bool, optional): Force-delete (True) or force-keep (False) every mount.
            Defaults to None, meaning honor each mount's own ``delete_with_host``
            setting - which is what the host-destroyed path wants.
    
    Returns:
        list[int]: The mounts released."""
def mount_host_of (mount):
    """The host a mount rides on, or None.
    
    A host that no longer exists reads as None rather than a dangling id. The destroy
    dispatch cleans up ships killed in COMBAT, but a script can also just delete a ship
    outright, and that path fires no destroy event - so "my host is gone" has to be
    answerable from the link alone."""
def mount_is (obj):
    """Whether an object is currently mounted on something."""
def mount_list (host):
    """Every mount currently welded to a host, as a list of ids."""
def mount_offset (host, mount):
    """The body-frame offset a mount was welded at, as a Vec3."""
def mount_prune_orphans (delete=None):
    """Release mounts whose host is gone, honoring each one's ``delete_with_host``.
    
    The destroy dispatch covers a host killed in combat. This covers the other way a host
    vanishes - a script deleting it - which fires no destroy event and would otherwise
    leave armed objects welded to nothing.
    
    Returns:
        list[int]: The orphans dealt with."""
def mount_ring (host, ship_key, count, radius=None, y=0.0, **kwargs):
    """Spawn ``count`` mounts evenly spaced on a ring in the host's body XZ plane.
    
    The common case for bolting turrets onto a hull or a station. Because the offsets are
    body-frame, a station host and a maneuvering ship host behave identically.
    
    Args:
        radius (float, optional): Ring radius. Defaults to a little outside the host's
            exclusion radius so the mounts sit clear of the hull.
    
    Returns:
        list[int]: The ids created (may be shorter than ``count`` if any failed)."""
def mount_set_offset (host, mount, offset):
    """Move a mount to a new body-frame offset.
    
    The engine's connection carries its offset point from creation, so this deletes and
    re-adds it - cheap, and the only way to change where a mount rides."""
def mount_spawn (host, ship_key, offset=None, name='', side=None, behave_id='behav_station', delete_with_host=True):
    """Spawn a new object already welded to the host.
    
    Spawns at the host's position and lets the weld pull it into place, so the caller
    never has to compute a world position - that is the engine's job now.
    
    ``behav_station`` is the default because a mount must not steer: a ``behav_npcship``
    would fight the tractor with its own helm.
    
    Returns:
        int | None: The new mount's id, or None."""
def npc_spawn (x, y, z, name, side, ship_key, behave_id):
    """Spawn a non-player (NPC) ship into the simulation.
    
    Args:
        x (float): X spawn coordinate.
        y (float): Y spawn coordinate.
        z (float): Z spawn coordinate.
        name (str): Display name, or ``None``.
        side (str): Side the ship belongs to.
        ship_key (str): Ship template key from shipData.
        behave_id (str): Behavior type identifier.
    
    Returns:
        SpawnData: Spawn data for the new NPC."""
def object_exists (so_id):
    """Return whether an object currently exists in the simulation.
    
    Args:
        so_id (Agent | int): Agent ID or object.
    
    Returns:
        bool: ``True`` if the engine reports the object present."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def set_dedicated_link (so, link_name: str, to):
    """Set a dedicated (1-to-1) link from a source agent to a single target.
    
    Replaces any existing link under ``link_name`` with the new target. Pass
    ``to=None`` to clear the link entirely, so that ``get_dedicated_link``
    returns ``None`` again.
    
    Args:
        so (Agent | int): The source agent ID or object.
        link_name (str): The link key name.
        to (Agent | int | None): The target agent ID or object, or ``None`` to clear."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def unlink (set_holder, link_name: str, set_to):
    """Remove a named link from one or more source agents to one or more targets.
    
    Args:
        set_holder (Agent | int | set[Agent | int]): Source agent(s).
        link_name (str): The link key name.
        set_to (Agent | int | set[Agent | int]): Target agent(s) to unlink."""
