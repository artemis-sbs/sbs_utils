def _dist (a, b):
    ...
def _eva_haul (client_id, target, display):
    """Reel a find in and let the existing pickup path collect it.
    
    THE MASS RULE IS THE TRAP HERE. `grav_tether` silently REVERSES the engine pair when
    the target is twice the source's mass or more - the big thing pulls the small one -
    and a suit is the smallest thing in any relic. Left alone, a boarder tethering a
    cargo pod gets reeled into the pod. So the ratio is checked BEFORE the attach and a
    refusal is reported by name, rather than the crew watching a suit fly into the
    scenery with no explanation."""
def _eva_unlist (client_id, target):
    """Take a hauled find off the relic's destination list. Never raises."""
def _eva_work (client_id, target, verb, display):
    """Start a timed job on a barrier - a cut, or a haul on the blockage itself."""
def _pos (thing):
    ...
def _report (client_id, target, verb, result, detail=None):
    ...
def any_role (roles: str):
    """Return the set of agent IDs that hold at least one of the given roles.
    
    Args:
        roles (str): A single role name or a comma-separated list.
    
    Returns:
        set[int]: IDs of agents with any of the specified roles."""
def eva_abort (client_id):
    """Stop whatever this console had running."""
def eva_aim (client_id, target):
    """Point the suit at a target: lock its weapons and swing its 2D view to match.
    
    THE LOCK IS THE POINT. A hull's beams fire at whatever `weapon_target_UID` names, so
    without this the suit's beam - and `tsn_shuttle` has had one all along - never fires
    at anything. The 2D focus is so the console agrees with the handheld rather than
    showing a view the crew has to re-aim by hand."""
def eva_aimed (client_id):
    """What this suit's weapons are locked on, or None."""
def eva_arm (client_id, verb='beam'):
    """Hold a verb ready. Two decisions on purpose - choose, then use."""
def eva_armed (client_id):
    """Which verb this console is holding, or None."""
def eva_disarm (client_id):
    """Put it away."""
def eva_reach (client_id=None):
    """How far this console can reach. One number, for now - a hook for a mission that
    wants a longer arm on a better suit."""
def eva_selected_target (client_id):
    """The reach target matching the console's WEAPONS selection, or None.
    
    What makes a click on the 2D view and a row in the app the same act: whatever the
    crew selected, if it is something this suit can work on, is the target."""
def eva_target_object (client_id, target):
    """The SPACE OBJECT for a target key, or None.
    
    A haul target is already an object id. A barrier is a key naming a sphere in the rail
    web - and a sphere is not something a beam can hit, which is why it now carries an
    object standing in for it."""
def eva_target_verbs (client_id, target):
    """What may be done to one target, or `()` if it is not in reach."""
def eva_targets (client_id, reach=None):
    """``[(key, display, kind, distance, verbs)]`` - what this suit can work on.
    
    Nearest first, the same as `eva_points`, because the same hand is picking from it.
    
    `kind` is `"barrier"` or `"haul"`. `verbs` is what may be done to it: a barrier says
    so itself (`Clear with:`), and anything haulable takes a tether."""
def eva_tools_clear (client_id=None):
    """Put the tools away - one console's, or every one's."""
def eva_tools_tick (t=None):
    """Finish the jobs that are done. ONE shared pass, like the autopilot and the camera."""
def eva_tools_unwatch ():
    """Stop the jobs pass."""
def eva_tools_watch (seconds=0.25):
    """Start the jobs pass. Idempotent - asking twice watches once."""
def eva_tools_working ():
    """Reset-ledger probe: how many consoles have a job running. Must NOT create anything
    by asking."""
def eva_use (client_id, target, verb=None):
    """Use the held verb on a target. The one entry point the app calls.
    
    Returns True only when something actually started. **Every other outcome is reported
    too**, through `eva_worked` with a reason - a verb that fails silently is
    indistinguishable from a broken screen, and that has been reported from a bridge on
    the other body model already."""
def eva_working (client_id):
    """``(target, verb, seconds_left, display)`` while a job runs, else
    ``(None, None, 0.0, None)``."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
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
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
