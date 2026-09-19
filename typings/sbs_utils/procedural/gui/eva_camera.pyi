def camera_auto (to=None, consoles=None):
    """Hand the camera back to the engine's own director (it follows the assigned ship).
    
    The release path for anything `camera_track` took over - end a cutscene with this.
    
    Args:
        to: audience (see ``consoles_of``); ``None`` is the current console.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were released."""
def camera_follow (to, subject, distance, height=0.0, yaw=0.0, pitch=0.0, lens_filter=None, consoles=None):
    """Aim a third-person lens behind a subject, ONCE, from live geometry.
    
    `camera_chase` is the same idea as a timed move: it takes the dispatcher, runs for a
    leg, and has to be re-issued. This is the single aim underneath it, so a caller with
    its own tick - a console driving a camera every frame while it flies - re-aims without
    starting and stopping a driver each time. That is what the Game Master does, and it is
    what the engine wants: there is no interpolation, so following IS re-aiming.
    
    Two things it adds over `camera_chase`, and each is why this exists:
    
    * **``yaw`` and ``pitch``** orbit the lens around the subject's own heading, so a
      console can look round its craft without losing the chase.
    * **``lens_filter(base, want) -> lens``** gets the last word on where the camera
      actually sits. Handed the subject's position and the lens the angles asked for, it
      may return something nearer. A ship in open space has no use for it; a suit inside a
      relic does, because a chase lens `distance` behind it in a 380-unit shaft is in the
      rock, and the engine's own chase mode has no way to say so.
    
    Args:
        distance (float): how far BEHIND the subject to sit.
        height (float): how far above it. A little is usually better than none.
        yaw (float): degrees around the subject from dead astern.
        pitch (float): degrees above (positive) or below it.
        lens_filter (callable, optional): `(base, want) -> lens`, both world positions.
    
    Returns:
        The world position the lens was put at, or None if the subject is not resolvable.
    
    A subject whose heading cannot be read falls back to a fixed offset rather than
    raising - a chase that is merely not behind the ship still shows the ship."""
def eva_camera_aim (client_id, suit=None, volume=None):
    """Re-aim ONE console's camera. Returns where the lens went, or None.
    
    Called every tick by `eva_camera_tick`. Cheap on purpose: one `camera_follow`, one
    depth read for the distance, and at most eight `volume_inside` tests for the clamp -
    all of which the autopilot is paying for anyway."""
def eva_camera_clamp (volume):
    """A `lens_filter` for `camera_follow` that keeps the lens inside `volume`.
    
    Walks the lens back along its own sightline toward the subject until it is inside -
    a bisection, because the subject is known inside and the wanted lens may not be, so
    the crossing is somewhere between them and eight halvings find it to under a unit.
    
    THE ONE THING THE ENGINE'S CHASE CANNOT DO. A relic has no collision at all, so
    nothing stops a camera ending up in the rock; and once it is there the frame is the
    inside of a wall, which reads as the console being broken rather than as the camera
    being wrong."""
def eva_camera_distance (client_id, suit=None, volume=None):
    """How far back the lens should sit right now.
    
    Manual wins outright. Otherwise: as far back as the room allows, then closer again the
    faster the suit is going."""
def eva_camera_dolly (client_id, amount=30.0):
    """Push the lens in or pull it out, and hold it there.
    
    Taking manual control of the distance turns OFF the automatic framing - a console that
    asked for a distance should get it, not have the clearance rule quietly argue with it.
    `eva_camera_recenter` gives the automatic framing back."""
def eva_camera_mode (mode=None):
    """Read or set the EVA camera mode - re-exported from `eva_console` so a caller does
    not have to know which file owns which half."""
def eva_camera_orbit (client_id, degrees=24.0):
    """Turn the lens around the suit. Marks the view as deliberately placed, so it stops
    washing back to dead astern on its own."""
def eva_camera_recenter (client_id):
    """Put the lens back behind the suit and hand the framing back to the automatic rule.
    
    One control, because "the camera is somewhere odd" is one problem however it got
    there - a stray orbit, a dolly left in, or both."""
def eva_camera_release (client_id):
    """Give the camera back to the engine's own director and forget this console's view.
    
    Called when a suit is put away. Without it a console that came back aboard would keep
    a script-driven lens pointed at a ship it is no longer flying."""
def eva_camera_state (client_id):
    """``(yaw, pitch, distance_or_None, free)`` for one console."""
def eva_camera_tick (t=None):
    """Re-aim every console flying a suit. ONE shared pass, not a task per console.
    
    The same idiom `eva_tick` and `volume_containment_tick` use, and for the same reason:
    six consoles is six of everything otherwise, and the work per console is small enough
    that the scheduling would cost more than the aiming."""
def eva_camera_tilt (client_id, degrees=8.0):
    """Raise or lower the lens. Clamped short of straight up or down, where a chase has no
    usable horizon and the shot reads as a map."""
def eva_camera_unwatch ():
    """Stop the camera pass."""
def eva_camera_watch (seconds=0.0):
    """Start the camera pass. Idempotent - asking twice watches once."""
def eva_camera_watching ():
    """Reset-ledger probe. Must NOT create anything by asking."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def volume_depth (volume, pos):
    """Signed distance to the wall: NEGATIVE inside, positive outside.
    
    The number the graded response is built on - scrape near zero, govern the
    throttle further out, clamp as the backstop."""
def volume_inside (volume, pos, margin=0.0):
    """Whether `pos` is inside by at least `margin` - `depth(pos) <= -margin`, without
    measuring how far.
    
    The cheap half of `volume_depth`, and the right question for anything that only needs
    a yes or no: a visibility sample, a camera looking for somewhere it fits. The first
    primitive that swallows the point settles it, where `depth` has to scan them all."""
def volume_nearest_inside (volume, pos, margin=0.0):
    """Closest point inside by at least `margin`; the position itself if already so."""
