from sbs_utils.procedural.gui.gui import ButtonPromise
def camera_anchor (x, y, z, name='', roles='camera_anchor'):
    """Spawn an invisible camera post and return its id.
    
    The detached-camera pattern LM's Game Master already uses: a player-family object with the
    'invisible' art, with ``__player__`` removed so it is not a player ship. It has to be
    player-family rather than terrain because a client can be ASSIGNED to it, and it is
    invisible so it never appears in the shot it exists to frame.
    
    Args:
        x, y, z (float): where to put it.
        name (str, optional): display name; usually empty for a camera post.
        roles (str, optional): extra roles, comma separated.
    
    Returns:
        int: the anchor's id, or 0 if it could not be spawned."""
def camera_assign (to, obj, consoles=None):
    """Assign consoles to a space object - their identity, not their lens.
    
    The engine needs this before a cinematic camera means anything. It is normally called ONCE
    per console (typically onto a `camera_anchor`), and then the lens is moved freely with
    `camera_track`. Re-assigning per shot changes what the console *is* - which also changes
    what it can see, since view culling follows the assigned object, not the camera.
    
    Args:
        to: audience - a client id, a ship, a side, or a set/role query (see ``consoles_of``).
        obj: the space object (id or object) to assign them to.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were assigned."""
def camera_assignment (to=None, consoles=None):
    """What each console is riding right now: ``{client_id: ship_id}``.
    
    Taken BEFORE a cutscene so it can be given back afterwards. `camera_track` ASSIGNS a
    console to the object the lens rides, and assignment is identity, not framing: it
    decides what that console can see and what the engine director follows once the
    camera is released. So a shot that rode a station leaves the mainscreen watching
    that station, and `camera_auto` alone does not undo it - it hands control back to a
    director that dutifully keeps following the wrong ship.
    
    Captured per console rather than assumed to be "the player ship", because it is not
    always one: a Game Master or Admiral console rides a detached camera object, and
    putting it back on a player ship would be a worse bug than the one being fixed.
    
    Returns:
        dict: client id -> the ship id it was assigned to. Ids that read back as 0 are
        omitted; there is nothing to restore and re-assigning to 0 would detach it."""
def camera_auto (to=None, consoles=None):
    """Hand the camera back to the engine's own director (it follows the assigned ship).
    
    The release path for anything `camera_track` took over - end a cutscene with this.
    
    Args:
        to: audience (see ``consoles_of``); ``None`` is the current console.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were released."""
def camera_chase (to, subject, distance, height=0.0, seconds=30.0, consoles=None):
    """Third person: hold the lens BEHIND the subject as it turns.
    
    The one move whose lens is a function of the subject's HEADING rather than of time, so it
    ignores the eased progress and reads the world each tick. That is the whole trick, and it
    is only possible because `_drive` calls `lens_at` per tick rather than sampling a path up
    front.
    
    WHY THIS IS NOT A TRACTOR. The intuitive way to chase is to attach the camera to the
    target and let the engine drag it. There is nothing to attach: the dolly and the target
    must be the SAME object or the frame is black, so the lens already rides the subject - a
    tractored camera object would be dragged along with nothing looking through it. Following
    IS re-aiming, and the engine has no interpolation to do it for us.
    
    WHY IT MUST RUN ON THE TICK. Re-aiming from a mission loop at a few hertz reads as a
    stutter, not as a saving - the same note `_drive` carries. A chase driven from a 0.5s
    mission tick flickers; the same maths on the dispatcher does not.
    
    A world-space offset does NOT rotate with the dolly, which is why the offset is rebuilt
    from `forward_vector()` every tick instead of being computed once. A subject with no usable
    heading (a rock, or an engine object that will not answer) falls back to a fixed offset
    rather than raising - a chase that is merely not behind the ship still shows the ship.
    
    Args:
        distance (float): how far BEHIND the subject to sit.
        height (float): how far above it. A little is usually better than none.
        seconds (float): how long this leg runs. Re-issue it to keep chasing - the same way
            an orbit is re-issued lap by lap.
    
    Returns:
        Promise: resolves when the leg ends, or when the subject goes."""
def camera_dolly (to, subject, from_distance, to_distance, yaw=0.0, pitch=12.0, seconds=20.0, ease='in_out', consoles=None):
    """Push the lens in (or pull it out) along a fixed angle, FOLLOWING the subject.
    
    `camera_move` interpolates between two fixed WORLD points, which is right for a
    station and wrong for a ship under way: the shot is left behind, and what began as a
    push-in ends as a fly-past. This holds the ANGLE and changes only the distance,
    recomputing from wherever the subject is each tick - the same trick `camera_orbit`
    uses, and for the same reason.
    
    Args:
        from_distance / to_distance (float): radius at the start and the end. Give a
            larger ``from`` for a push in, a larger ``to`` for a pull out.
        yaw (float): degrees around the subject to sit at.
        pitch (float): degrees above it. Slightly down reads better than dead level.
    
    Returns:
        Promise: resolves when the push ends."""
def camera_lens (to=None, consoles=None):
    """Where the lens is right now on the first of these consoles, or None.
    
    The mover records it, so a rack or a follow-on move can start from where the
    last one finished instead of the caller having to remember."""
def camera_move (to, subject, lens_from, lens_to, seconds, ease='in_out', consoles=None):
    """Glide the lens from one world position to another, looking at `subject`.
    
    Args:
        to: audience (see ``consoles_of``).
        subject: what the shot looks at - and, necessarily, what the lens rides.
        lens_from (Vec3 | tuple): world position to start at.
        lens_to (Vec3 | tuple): world position to end at.
        seconds (float): duration.
        ease (str): ``in_out`` (default), ``in``, ``out`` or ``linear``. Ours - the
            engine interpolates nothing.
    
    Returns:
        Promise: resolves with the final lens position when the move ends.
    
    Example:
        await camera_move(role("mainscreen"), hero, Vec3(0,900,-4000), Vec3(0,300,-900), 6)"""
def camera_move_stop (to=None, consoles=None):
    """Stop any running move on these consoles, leaving the lens where it is.
    
    Called for you by every move below: two drivers re-aiming the same console
    would fight tick by tick, and the symptom (a camera that jitters between two
    paths) reads as an engine bug rather than a second caller."""
def camera_orbit (to, subject, distance, from_yaw=0.0, to_yaw=360.0, seconds=10.0, pitch=15.0, ease='linear', consoles=None):
    """Swing the lens around `subject` at a fixed distance.
    
    Because offsets are world-space, this is the Game Master's move: recompute
    ``camera_orbit_lens`` each tick and re-aim. It follows a moving subject for free,
    since the offset is applied to wherever the subject is at the time.
    
    Args:
        distance (float): radius of the orbit.
        from_yaw / to_yaw (float): degrees to sweep between. Give ``to_yaw`` less
            than ``from_yaw`` to swing the other way.
        pitch (float): degrees above the subject. Default 15 looks down slightly,
            which reads better than dead level.
        ease (str): ``linear`` by default - an orbit that eases looks like a mistake.
    
    Returns:
        Promise: resolves when the sweep ends."""
def camera_orbit_lens (distance, yaw=0.0, pitch=0.0):
    """The offset for a shot ``distance`` away at a given angle, as a world-space Vec3.
    
    This is LM's Game Master formula, which is the reference implementation of an orbit here:
    take a vector straight back and rotate it. Because the engine does not rotate offsets into
    the dolly's frame, orbiting means recomputing this and calling `camera_track` again - which
    is exactly what the GM does when you drag its orbit slider.
    
    Args:
        distance (float): how far from the subject.
        yaw (float, optional): degrees around the subject.
        pitch (float, optional): degrees above (positive) or below it.
    
    Returns:
        Vec3: the offset to pass as ``lens``.
    
    Example:
        camera_track(role("mainscreen"), cam, lens=camera_orbit_lens(1800, yaw=35, pitch=20),
                     target=hero_ship)"""
def camera_rack (to, subject, consoles=None):
    """Look at something else WITHOUT moving the lens - a rack focus.
    
    Holds the current world position and re-aims at ``subject``. Any running move is
    stopped first: a rack during a move is a new intent, not a modifier on the old one.
    
    Returns:
        int: how many consoles were re-aimed."""
def camera_restore (assignments):
    """Put each console back on the object it was riding, and release the camera.
    
    The counterpart to `camera_assignment`, and the general rule for ending a cutscene:
    give the console back its own ship, THEN hand the camera to the engine director. In
    that order - releasing first leaves the director following the shot subject for the
    frames in between.
    
    Args:
        assignments (dict): what `camera_assignment` returned.
    
    Returns:
        int: how many consoles were put back."""
def camera_shot (to, subject, lens_world, consoles=None):
    """Put the lens at an ABSOLUTE world position, looking at `subject`.
    
    The natural way to write a shot - "camera over here, pointed at that" - is to pass two
    different objects as dolly and target. That shape does not render (see
    DESIGN_RECORD.md s7); what renders is one object named twice, with the lens offset away from it,
    which is what the Game Master does.
    
    That constraint costs nothing, because the offsets are WORLD-space: any camera position is
    reachable as `wanted - subject.pos`. So this composes the shot you meant out of the shape
    the engine accepts, and it keeps working as the subject moves, since the offset is
    recomputed from wherever it is at the time.
    
    Args:
        to: audience (see ``consoles_of``).
        subject: the object to look at - and, necessarily, the one the lens rides.
        lens_world (Vec3 | tuple): where the camera should BE, in world coordinates.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were pointed.
    
    Example:
        camera_shot(role("mainscreen"), hero_ship, Vec3(0, 900, -2600))"""
def camera_track (to, dolly, lens=None, target=None, look=None, consoles=None):
    """Point one or more consoles' cinematic camera at a subject.
    
    Camera sits at ``dolly`` + ``lens``; it looks at ``target`` + ``look``. Both offsets are
    WORLD-space (see the module docstring), so an offset does not rotate as the dolly turns -
    use `camera_orbit_lens` to place a shot by angle, and recompute it when you want the angle
    to change.
    
    ``target`` defaults to ``dolly``: a single-subject shot pins both ids to that object, which
    is the shape the engine expects.
    
    ASSIGNS each console to `dolly` before pointing, because the engine only honors the change
    when they match (see the module docstring). `camera_assign` remains for the rare case of
    setting a console's object without touching its camera.
    
    Note the consequence: moving the camera to an object CHANGES what that console can see,
    since view culling follows the assigned object. That is the engine's model, not a choice
    this wrapper makes.
    
    Args:
        to: audience - a client id, a ship, a side, or a set/role query (see ``consoles_of``).
        dolly: the object the camera rides (id or object). Prefer a `camera_anchor`; pinning a
            SHIP with no ``lens`` offset puts the lens inside its hull.
        lens (Vec3 | tuple, optional): offset from the dolly. Defaults to no offset.
        target (optional): what to look at. Defaults to the dolly.
        look (Vec3 | tuple, optional): offset from the target. Defaults to no offset.
        consoles (str, optional): narrow to consoles carrying these roles.
    
    Returns:
        int: how many consoles were pointed.
    
    Example:
        cam = camera_anchor(0, 900, -2600)
        camera_assign(role("mainscreen"), cam)
        camera_track(role("mainscreen"), cam, target=hero_ship)"""
def consoles_of (to, consoles=None):
    """Resolve an audience expression to a set of console client ids.
    
    Args:
        to: ``None`` (the current console), a client id, a ship id/object, a side
            key or side agent, or a set/list mixing any of those.
        consoles (str, optional): narrow to consoles with these roles, e.g.
            ``"mainscreen"`` or ``"science, comms"``.
    
    Returns:
        set[int]: console client ids (possibly empty)."""
def cutscene_define (name, shots, letterbox=True, skippable=True, bar=4, release=True):
    """Register a cutscene under ``name``.
    
    Args:
        name (str): what ``cutscene_play`` will look up.
        shots (list[dict]): in order. Per shot:
            ``subject`` (required) - what the shot looks at, and necessarily what
            the lens rides; ``framing`` (``close``/``medium``/``wide``, or a two-item
            list for a move) OR ``lens`` (world position) OR ``move`` ([from, to]);
            ``seconds`` (default 4); ``ease``; ``yaw``/``pitch``; ``overlay``
            ({"kind": ..., plus that kind's fields}).
            Prefer ``framing``: it scales to the subject's hull, so one shot frames a
            runabout and a starbase alike. ``lens``/``move`` are world POSITIONS and
            so also depend on where the subject is parked.
        letterbox (bool): black bars for the duration.
        skippable (bool): whether ``cutscene_skip`` ends it.
        bar (float): letterbox bar height in em.
        release (bool): at the end, put each console back on the object it was riding
            and hand the camera to the engine's director.
            Leave it True unless the next thing the story does is set its own shot -
            a cutscene that ends still holding a dolly will drop to the engine
            default the moment that object is deleted.
    
    Returns:
        dict: the stored cutscene."""
def cutscene_framing (subject, size='medium'):
    """How far the lens sits for a named shot size, scaled to the subject's own hull.
    
    A DISTANCE TYPED BY HAND FRAMES EXACTLY ONE SHIP. The subjects a mission points a
    camera at are not one size: across the TNG pack a B'Rel is 25 units of hull radius
    and Deep Space Nine is 220, and a planet is 10,000. One coordinate triple makes the
    big one overflow the frame and the small one a speck, which is precisely the report
    this exists to answer.
    
    So the distance is read off the subject instead. `viewscreen_framing` already does
    that arithmetic - 6 hull radii at the closest, 16 at the widest, floored at 250 so
    the engine reporting a tiny hull cannot put the lens inside it - and the Director
    has framed its shots that way since it deleted its own distance sliders, on the
    grounds that "a fixed number framed a starbase and a fighter equally badly".
    
    `medium` is the midpoint rather than a fourth constant, so there is still exactly
    one place these numbers are written down.
    
    Args:
        subject: the object the shot looks at.
        size (str): ``close``, ``medium`` or ``wide``. Anything else is treated as
            ``medium`` - a misspelled size should give a usable shot, not no shot.
    
    Returns:
        float: distance from the subject, in world units."""
def cutscene_get (name):
    """The stored cutscene, or None."""
def cutscene_play (name_or_shots, to=None, consoles=None, **overrides):
    """Play a cutscene and return a Promise that resolves when it ends.
    
    Args:
        name_or_shots: a name from ``cutscene_define``, or a list of shots to play
            without registering one.
        to: audience (see ``consoles_of``).
        **overrides: any ``cutscene_define`` field, for this run only.
    
    Returns:
        Promise: resolves with ``{"skipped": bool, "shots": int, "name": str}``."""
def cutscene_playing (to=None, consoles=None):
    """Whether a cutscene is running on any of these consoles."""
def cutscene_skip (to=None, consoles=None):
    """Skip a running cutscene. Returns how many consoles were skipped.
    
    A no-op on a cutscene defined as unskippable, so a global skip button can be
    wired once and left alone."""
def cutscene_stop (to=None, consoles=None):
    """Stop a running cutscene without honouring ``skippable`` - the teardown path.
    
    Resolves its promise as skipped, so a story awaiting it still continues."""
def gui (buttons=None, timeout=None):
    """Present the GUI layout that has been queued up for the current client.
    
    Suspends execution until the player presses a button or the timeout fires.
    GUI elements (text, images, sections, etc.) must be queued with ``gui_*``
    calls before ``await gui()``; they are rendered when the promise activates.
    
    Args:
        buttons (dict, optional): Extra buttons to add, mapping label text to
            jump target label name. e.g. ``{"Start": "start_label"}``.
            Defaults to None.
        timeout (Promise, optional): A promise (e.g. ``timeout_sim(30)``) that
            cancels the GUI when it resolves. Defaults to None.
    
    Returns:
        Promise: Resolves when a button is pressed or timeout fires.
    
    Example:
        gui_text("Choose your mission")
        await gui():
            + "Patrol":
                jump patrol_mission
            + "Escort":
                jump escort_mission"""
def gui_activate_console (console):
    """Set the current page's active console name.
    
    Marks the page as running a specific console type, which affects which
    console-specific routes and widgets respond to this client.
    
    Args:
        console (str): Console name, e.g. ``"helm"``, ``"weapons"``,
            ``"science"``.
    
    Example:
        gui_activate_console("helm")"""
def gui_add_console_type (path, display_name, description, label):
    """adds a tab definition
    
    Args:
        id_or_obj (agent): agent id or object
        console (str): Console name
        tab_name (str): Tab name
        label (label): Label to run when tab selected"""
def gui_blank (count=1, style=None):
    """Add one or more empty columns to the current layout row.
    
    Blanks occupy column space without rendering anything visible. Use them
    to push elements right, add padding, or center icons.
    
    Args:
        count (int, optional): Number of blank columns to insert. Defaults to
            1.
        style (str, optional): CSS-like style overrides applied to each blank.
            Defaults to None.
    
    Returns:
        Blank: The last blank layout item created.
    
    Example:
        gui_blank()
        gui_icon("icons/shield")
        gui_blank()"""
def gui_button (props, style=None, data=None, on_press=None, is_sub_task=None):
    """Add a button to the current GUI layout outside of an ``await gui()`` block.
    
    Unlike buttons declared with ``*`` or ``+`` inside ``await gui()``, this
    button is placed directly in the layout at the current position and fires
    its handler without ending the surrounding ``await gui()``. Use it for
    action buttons embedded in panels, listboxes, or info panels.
    
    Args:
        props (str): Button label text, optionally as a property string
            (e.g. ``"$text:Fire!;color:red;"``). Supports ``{var}``
            interpolation.
        style (str, optional): Additional CSS-like style overrides.
            End each property with a semicolon, e.g. ``"col-width:20%;"``.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the handler.
            Available as ``__ITEM__`` and (if a dict) as individual variables.
            Defaults to None.
        on_press (label | callable | Promise, optional): What to do when the
            button is pressed. A label is jumped to; a callable is called; a
            Promise has its result set. Defaults to None.
        is_sub_task (bool, optional): How an ``on_press`` **label** runs.
            ``True`` runs it as a sub-task: safe to press repeatedly, and it
            should end with ``->END``. ``False`` jumps the task that built the
            widget, so the press takes that task over and the handler must hand
            the console back -- this is the historical behavior and is
            **deprecated**. Defaults to None, meaning the library decides; a
            handler that paints a screen and reaches ``await gui()`` sends the
            GUI task there either way, so you should not need this.
    
    Valid Styles:
        area:
            Format as `top, left, bottom, right`.
            Just numbers indicates percentage of the section or page to cover.
            Can also use `px` (pixels) or `em` (1em = height of text font).
            Can combine different units, e.g. `5+5px, 3em, 100-10em, 50px;` is a valid area.
        color:
            The color of the text
        background-color:
            The background color of the button
        padding:
            A gap inside the element (makes the button smaller, but the background still is there.)
        margin:
            The gap outside the element (makes the button smaller).
        col-width:
            The width of the button
        justify:
            Where the text is placed inside the button. `left`, `center`, or `right`
        font:
            The font to use. Overrides the font in prefernces.json
    
    
    
    Returns:
        layout object: The Layout object created"""
def gui_change (code, label):
    """Register a per-tick change watch on a Python expression.
    
    Evaluates ``code`` each tick and executes ``label`` when its value differs
    from the previous tick. Python equivalent of the MAST ``on change``
    construct. The trigger is attached to the current task and runs for as long
    as the task is active.
    
    Args:
        code (str): Python expression to evaluate each tick, e.g.
            ``"ship_speed > 100"``.
        label: MAST label or inline block to execute when the value changes.
    
    Example:
        gui_change("shield_level", shield_warning)
        ///shield_warning
            gui_text("Shields changed!")"""
def gui_checkbox (msg, style=None, var=None, data=None):
    """Add a checkbox to the current GUI layout.
    
    The current value of ``var`` (expected to be a bool) sets the initial
    checked state. When the player toggles the checkbox, ``var`` is updated.
    
    Args:
        msg (str): Label text or property string shown next to the checkbox,
            e.g. ``"Enable shields"`` or ``"$text:Active;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial checked state
            from and update on toggle. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Checkbox: The layout item created.
    
    Example:
        gui_checkbox("Enable auto-fire", var="auto_fire_on")"""
def gui_cinematic_auto (client_id):
    """Switch a client to cinematic view, automatically tracking its assigned ship.
    
    Sets the client's view mode to ``"3dview/front/cinematic"`` with automatic
    camera control. The tracked ship must expose excitement values; player ships
    have these set automatically.
    
    Args:
        client_id (int): The client to switch to cinematic view.
    
    Example:
        gui_cinematic_auto(CLIENT_ID)"""
def gui_cinematic_full_control (client_id, camera_id, camera_offset, tracked_id, tracked_offset):
    """Switch a client to cinematic view with explicit camera and target control.
    
    Sets the view mode to ``"3dview/front/cinematic"`` and hands full camera
    control to the caller. Both offset vectors are converted to engine
    ``vec3`` objects before being passed to ``cinematic_control``.
    
    Args:
        client_id (int): The client to switch to cinematic view.
        camera_id (int): Object ID to use as the camera position anchor.
        camera_offset (Vec3 | None): Offset from ``camera_id`` in world units.
            Pass ``None`` to use the object's origin.
        tracked_id (int): Object ID for the camera to look at.
        tracked_offset (Vec3 | None): Offset from ``tracked_id`` to look at.
            Pass ``None`` to use the object's origin.
    
    Example:
        gui_cinematic_full_control(CLIENT_ID, camera_ship_id, Vec3(0,50,0), target_id, None)"""
def gui_click (name_or_layout_item=None, label=None):
    """Register a click handler for a named element or layout item.
    
    Attaches a ``ClickableTrigger`` to the current task. When the element is
    clicked, sets ``__CLICKED__`` to the click tag and runs ``label`` inline
    (or as a sub-task if a different label is specified).
    
    Args:
        name_or_layout_item (str | layout object | None, optional): A click-tag
            string, a layout item exposing ``click_tag``, or ``None`` to match
            any click. Defaults to None.
        label (optional): MAST label to run on click. Defaults to the currently
            active label.
    
    Returns:
        ClickableTrigger: The registered trigger.
    
    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_click(btn, on_fire_pressed)
        ///on_fire_pressed
            ~~ fire_torpedo(SHIP_ID) ~~"""
def gui_client_id ():
    """Return the client ID for the currently executing GUI task.
    
    Shortcut for ``FrameContext.client_id``. Returns ``0`` when running on
    the server.
    
    Returns:
        int: Current client ID, or ``0`` for the server.
    
    Example:
        id = gui_client_id()
        gui_text("Your client ID is {id}")"""
def gui_clipboard_copy (s):
    """Write a text string to the Windows clipboard.
    
    Windows-only. Replaces whatever is currently on the clipboard.
    ``gui_clipboard_copy`` is an alias for this function.
    
    Args:
        s (str): The text to place on the clipboard.
    
    Example:
        gui_clipboard_put("TSN Artemis — Mission Report")"""
def gui_clipboard_get ():
    """Read the current text content of the Windows clipboard.
    
    Windows-only. Returns ``None`` if the clipboard is empty or contains
    non-text data.
    
    Returns:
        str | None: The clipboard text, or ``None`` if unavailable.
    
    Example:
        text = gui_clipboard_get()
        if text is not None:
            gui_text("Pasted: {text}")"""
def gui_clipboard_put (s):
    """Write a text string to the Windows clipboard.
    
    Windows-only. Replaces whatever is currently on the clipboard.
    ``gui_clipboard_copy`` is an alias for this function.
    
    Args:
        s (str): The text to place on the clipboard.
    
    Example:
        gui_clipboard_put("TSN Artemis — Mission Report")"""
def gui_console (console, is_jump=False):
    """Activate a standard console with its default engine widget layout.
    
    Sets the engine widget list for the named console using the built-in
    configuration. Supported values: ``"helm"``, ``"weapons"``,
    ``"science"``, ``"engineering"``, ``"comms"``, ``"cinematic"``,
    ``"mainscreen"``, ``"cockpit"``.
    
    Args:
        console (str): Console name (case-insensitive).
        is_jump (bool, optional): For ``"helm"`` only — include jump-drive
            controls in the widget list. Defaults to ``False``.
    
    Example:
        gui_console("helm")
        gui_console("helm", is_jump=True)"""
def gui_console_clients (path, for_ships=None):
    """Return the set of client IDs that have a specific console type.
    
    Searches all player ships (or the given ship set) for linked console
    clients whose role matches ``console,{path}``.
    
    Args:
        path (str): Console path to match, e.g. ``"helm"`` or ``"science"``.
        for_ships (object | None, optional): Agent ID, object, or set of ships
            to search. Defaults to all ``__player__`` ships.
    
    Returns:
        set: Client IDs that have a console matching ``path``.
    
    Example:
        helm_clients = gui_console_clients("helm")"""
def gui_console_enter (client_id, console_type, ship=None):
    """THE ONE DOOR. Call this FIRST whenever a console becomes something else.
    
    A console that arrives somewhere carrying the last screen's furniture is the
    single most common transition bug in this codebase, and every mission used to
    have to remember seven separate pieces of trivia to avoid it. This is those
    seven, in the order that works.
    
    **It fires on a CHANGE of console type, not on a repaint.** A screen is
    re-entered every time it repaints - LegendaryMissions' main screen jumps back
    to itself on the viewscreen signal - so clearing on every reroute would tear
    down the furniture the screen just raised. Passing the type it already is
    is a no-op, so putting this at the top of a console label costs nothing.
    
    In order, and each step is here because it bit somebody:
    
    1. **Overlays.** They belong to the CONSOLE, not the page, and the page object
       survives a reroute - so ``present_all`` re-draws whatever the slots still
       hold, and the catch-up ticker re-delivers any live record it finds an empty
       slot for. ``overlay_clear_console`` defeats both.
    2. **The viewscreen claim.** A console that was driving its ship's main screen
       gives it back rather than holding it from a station that no longer has the
       control. Leaving a story claim held by a console nobody is sitting at parks
       every later crew request forever.
    3. **The camera.** A shot ASSIGNS its console to the object the lens rides, so
       a console leaving mid-shot is still riding an enemy ship.
    4. **Every console role, stripped** - or a screen that used to be a main screen
       keeps answering as one.
    5. **The role AND ``CONSOLE_TYPE``, both.** Role without ``CONSOLE_TYPE`` means
       main-screen view routes never find it; ``CONSOLE_TYPE`` without the role
       means overlays, ``announce()`` and comms drop the message in SILENCE,
       because every audience narrows through ``any_role``.
    6. **The crew seat.** A seat is believed only while the client's own
       ``CONSOLE_TYPE`` still agrees with it, so changing console frees it as a side
       effect and the player's name and face vanish. Re-asserted with an explicit
       pick, which is deterministic where letting it re-resolve is not.
    7. **The engine widget list.** A console leaves its native widgets behind and
       the page underneath draws through them.
    
    Args:
        client_id (int): the console.
        console_type (str): what it is becoming - ``"helm"``, ``"mainscreen"``, a
            mission's own console name.
        ship (optional): the ship it belongs to. Defaults to its home ship.
    
    Returns:
        bool: True if the console actually changed, False if it already was this."""
def gui_content (content, style=None, var=None):
    """Place a Python widget object into the layout system.
    
    Wraps a pre-built Python widget (e.g. a ship picker, custom control) in a
    ``GuiControl`` so it participates in the normal layout flow.
    
    Args:
        content (widget): A Python GUI widget object.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to bind the widget's value to.
            The current value of ``var`` is pushed into the widget and updates
            flow back when the widget changes. Defaults to None.
    
    Returns:
        GuiControl: The layout wrapper object.
    
    Example:
        picker = ShipPicker(0, 0, "mast", "Your Ship")
        gui_content(picker, var="selected_ship")"""
def gui_drop_down (props, style=None, var=None, data=None):
    """Add a drop-down list to the current GUI layout.
    
    When the player selects an item, ``var`` is updated. ``var`` is written, not
    read: the INITIAL selection comes from ``text:`` in ``props``, so interpolate
    the variable there yourself -- ``f"text:{speed};list:Slow,Medium,Fast;"`` --
    or set it afterwards with ``.value``.
    
    Args:
        props (str): Semicolon-separated properties. The options go in ``list:``
            (comma separated) and the closed-state label in ``text:``, e.g.
            ``"text:Red;list:Red,Green,Blue"``. NOT ``items:`` - a dropdown with no
            ``list:`` has nothing to render and the engine dies allocating for it
            (``MemoryError: bad allocation``), which reads as anything but a typo.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to write the selection to when it
            changes. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Dropdown: The layout item created.
    
    Example:
        speed = gui_drop_down("text:Medium;list:Slow,Medium,Fast;", var="speed_setting")
        speed.value = "Fast"      # move the selection from script"""
def gui_face (face, style=None):
    """Add a character face portrait to the current GUI layout.
    
    Renders the named face asset, typically used in comms panels to show the
    speaker's portrait.
    
    Args:
        face (str): Face asset name or property string, e.g. ``"crew/captain"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Face: The layout item created.
    
    Example:
        gui_face("crew/captain")"""
def gui_get_console_type (key):
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_get_console_type_list ():
    """Get the list of consoles defined by @console decorator labels
    path is added as a value"""
def gui_get_console_types ():
    """Get the list of consoles defined by @console decorator labels
    
        """
def gui_grid (columns=1):
    """Lay the GUI items you add next out as a grid, as a context manager.
    
    Inside the ``with`` block, items flow left-to-right and wrap to a new row
    every ``columns`` items — no manual ``gui_row()`` needed. The short final
    row is padded so columns stay aligned. Because it only starts standard rows,
    it adds no new rendering path.
    
    Args:
        columns (int): Number of columns (cells per row). Minimum 1.
    
    Returns:
        PageGrid: Context manager. Use with ``with``.
    
    Example:
        with gui_grid(3):
            gui_text("Name")
            gui_text("Side")
            gui_text("Status")
            for ship in ships:
                gui_text(ship.name)
                gui_text(ship.side)
                gui_text(ship.status)"""
def gui_hide (layout_item):
    """Hide a visible layout item.
    
    For sections, recalculates the layout after hiding. For individual items
    or rows, hides the element but does not re-layout — pair with
    ``gui_represent`` on the parent section if the layout needs updating.
    
    Args:
        layout_item: The layout object to hide. No-op if already hidden or
            ``None``.
    
    Example:
        gui_hide(warning_row)
        gui_represent(my_section)"""
def gui_hide_choice ():
    """Hide the button that was just pressed during its handler block.
    
    Call this from inside a button's handler block to remove the button
    from the layout immediately after it is clicked, without waiting for
    the ``await gui()`` to complete. Has no effect if called outside of
    a running button handler.
    
    Example:
        await gui():
            + "Launch Missile":
                gui_hide_choice()
                ~~ fire_torpedo(SHIP_ID) ~~"""
def gui_history_back ():
    """Jump back to the previous navigation history entry.
    
    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no history.
    
    Example:
        * "Back"
            gui_history_back()"""
def gui_history_clear ():
    """Clear the navigation history for the current page.
    
    Removes all back and forward history entries. Call this when entering a
    top-level screen where back-navigation should not be available.
    
    Example:
        gui_history_clear()"""
def gui_history_forward ():
    """Jump forward to the next navigation history entry.
    
    Restores any variables stored with the entry and jumps to its label.
    No-op if there is no forward history.
    
    Example:
        * "Forward"
            gui_history_forward()"""
def gui_history_jump (to_label, back_name=None, back_label=None, back_data=None):
    """Jump to a new GUI label and record the current position in navigation history.
    
    Appends the current position to the back-stack (clearing any forward
    history) then jumps to ``to_label``. Call ``gui_history_back`` to return.
    
    Args:
        to_label (label): Label to navigate to.
        back_name (str | None, optional): Display name for the back entry.
            Defaults to ``"BACK"``.
        back_label (label | None, optional): Label to return to. Defaults to
            the currently active label.
        back_data (dict | None, optional): Variables to restore when returning
            back. Defaults to None.
    
    Returns:
        PollResults: Result of the jump.
    
    Example:
        gui_history_jump(ship_detail_screen, back_name="Ship List")"""
def gui_history_redirect (back_name=None, back_label=None, back_data=None):
    """Append to navigation history without jumping forward.
    
    Adds a history entry so the current location can be returned to via
    ``gui_history_back``, but does not change the active label. Use when you
    need to update the back-stack from within a label that was jumped to
    externally (e.g. from a route).
    
    Args:
        back_name (str | None, optional): Display name for the history entry.
            Defaults to ``"BACK"``.
        back_label (label | None, optional): Label to return to. Defaults to
            the currently active label.
        back_data (dict | None, optional): Variables to restore when returning
            back. Defaults to None."""
def gui_history_store (back_text, back_label=None):
    """Record the current label as a history entry (back destination).
    
    Stores the active label (or ``back_label``) so that ``gui_history_back``
    can return to it later. Use ``gui_history_jump`` instead when also
    navigating forward.
    
    Args:
        back_text (str): Display name for this history entry (shown in back
            buttons or breadcrumbs).
        back_label (label, optional): Label to return to. Defaults to the
            currently active label."""
def gui_hole (count=1, style=None):
    """Reserve empty column space that the next layout item expands to fill.
    
    Unlike ``gui_blank``, a hole is consumed by the following item as extra
    width. Use it to make a single element span multiple column slots.
    
    Args:
        count (int, optional): Number of extra column slots to reserve.
            Defaults to 1.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Hole: The last hole layout item created.
    
    Example:
        gui_hole(2)
        gui_text("This text spans 3 columns")"""
def gui_icon (props, style=None, data=None):
    """Add an icon image to the current GUI layout.
    
    Renders an icon from the atlas or media path. It is not clickable on its
    own, but a ``click_tag:`` in the style makes it so - which is why it can
    carry ``data`` like any other widget.
    
    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/torpedo"`` or ``"image:icons/torpedo;color:yellow;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        data (object, optional): Arbitrary data carried by the widget, read
            back in a handler as ``__ITEM__.data`` and - when it is a dict -
            unpacked into the handler's variables. Defaults to None.
    
    Returns:
        Icon: The layout item created.
    
    Example:
        gui_icon("icons/shield")
        gui_text("{shield_pct}%")"""
def gui_icon_add_atlas (name, image, left=None, top=None, right=None, bottom=None, color=None):
    """Claim an icon NAME for a cell of your own sheet.
    
        gui_icon_add_atlas("wanted", media_shared("icons/quest-sheet"), 0, 0, 64, 64)
    
    From then on every `gui_icon_name("quest.job")` draws your art - the meaning points
    at the look `wanted`, and this claims that look. Nothing that draws it changes.
    
    This is `gui_image_add_atlas(..., domain="icon")`. The domain is what separates a
    deliberate re-skin from an image that happens to be called `square`."""
def gui_icon_add_atlas_grid (image, cols, rows=None, names=None, cell=None, color=None, start=0):
    """Claim a whole sheet of icon names at once - `gui_image_add_atlas_grid` in the icon
    domain. Names are laid out row-major; a `None` entry skips a cell."""
def gui_icon_button (props, style=None, data=None, on_press=None, is_sub_task=None):
    """Add a clickable icon button to the current GUI layout.
    
    Like ``gui_icon`` but the rendered item accepts click events. Takes
    ``data`` and ``on_press`` exactly as ``gui_button`` does, so a row of icon
    buttons built in a loop can each say which row they belong to (LM #708).
    
    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/fire"`` or ``"image:icons/fire;color:red;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        data (object, optional): Arbitrary data carried by the widget. The
            handler reads it as ``__ITEM__.data``; a dict is also unpacked
            into the handler's variables. Defaults to None.
        on_press (label | callable | Promise, optional): What to do when the
            icon is pressed. A label is jumped to; a callable is called; a
            Promise has its result set. Defaults to None - attach the handler
            with ``gui_message`` / ``gui_click`` instead.
        is_sub_task (bool, optional): How an ``on_press`` **label** runs.
            ``True`` runs it as a sub-task: safe to press repeatedly, and it
            should end with ``->END``. ``False`` jumps the task that built the
            widget, so the press takes that task over and the handler must hand
            the console back -- this is the historical behavior and is
            **deprecated**. Defaults to None, meaning the library decides; a
            handler that paints a screen and reaches ``await gui()`` sends the
            GUI task there either way, so you should not need this.
    
    Returns:
        IconButton: The layout item created.
    
    Example:
        btn = gui_icon_button("icons/fire", data={"slot": i})
        gui_message(btn, on_fire_clicked)
        ///on_fire_clicked
            fire_torpedo(SHIP_ID, slot)"""
def gui_icon_name (name, color=None, style=None, props=None):
    """Draw an icon by NAME rather than by sheet index.
    
        gui_icon_name("quest.job", color="#cc0")
    
    The name is resolved by `icon_names.icon_resolve`: a meaning (`quest.job`) follows
    its alias to a look, and a look is either a cell of the built-in sheet or - when a
    mission has registered that name with `gui_image_add_atlas` - a cell of its own
    sheet. The caller says what it wants; where the art comes from is not its business,
    which is what lets a consumer be written before the art exists and lets a mission
    re-skin every screen that draws it.
    
    An unknown name draws NOTHING and says so once, rather than falling back to some
    arbitrary glyph: a wrong icon is worse than a missing one, because it looks
    deliberate.
    
    Args:
        name (str): a meaning or a look - see `icon_names.icon_names()`.
        color (str, optional): tint. The built-in glyphs are white on transparent, so
            one glyph serves every state.
        style (str, optional): layout style, as for `gui_icon`.
        props (str, optional): extra icon properties appended verbatim.
    
    Returns:
        Icon | Image | None"""
def gui_icon_recolor (widget, color):
    """Tint an icon that is already on screen, whatever `gui_icon_name` gave back.
    
    That function returns an Icon for a built-in glyph and an Image for a name a
    mission has re-skinned, and the two carry their color in different places - so a
    caller that recolored by hand would work until someone registered their own sheet,
    which is the one thing the name indirection exists to survive. Recolor, never
    rebuild: the widget keeps its tag, so the engine re-sends one glyph instead of the
    console rebuilding a row that may be under the pilot's cursor.
    
    Args:
        widget: the layout item from `gui_icon_name` (None is a no-op).
        color (str): the new tint.
    
    Returns:
        bool: whether the tint was applied."""
def gui_image (props, style=None, fit=0, color=None):
    """Add an image to the current GUI layout.
    
    Resolves the image via the atlas, mission directory, and engine graphics
    path in that order. Prefer the named wrappers (``gui_image_stretch``,
    ``gui_image_absolute``, etc.) over calling this directly.
    
    Args:
        props (str): Image filename (without extension), a registered atlas
            key (see ``gui_image_add_atlas``), or an image property string
            like ``"image:media/logo;color:white;"``. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
        fit (int, optional): Scaling mode — 0=stretch, 1=absolute pixels,
            2=keep aspect ratio (top-left), 3=keep aspect ratio (centered).
        color (str, optional): Tint for this use only, overriding the atlas's own
            color. Lets one registered cell serve every state.
            Defaults to 0.
    
    Returns:
        Image: The layout item created."""
def gui_image_absolute (props, style=None):
    """Add an image to the layout at its native pixel dimensions.
    
    The image is drawn at 1:1 pixel size relative to the client's screen
    resolution, anchored at the top-left of the layout area.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_absolute("media/icons/torpedo")"""
def gui_image_add_atlas (key, image, left=None, top=None, right=None, bottom=None, color=None, domain=None):
    """The image atlas allows a key name to be used to assign to a set of image properties.
    This key can be used instead of image properties in any command that expect image properties.
    
    The image file passed will be used to search for the file. It will first check the mission directory followed by data/graphics folder.
    In the future this could be modified to account for mods, e.g. a common media folders.
    The image atlas takes care of supplying the correct path for the engine to use.
    
    By specifying the rect (left,top, right, bottom) the image key can reference a part of an image.
    
    
    Add a key to reference a full image
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image_add_atlas("test", "media/LegendaryMissions/operator")
    ```
    
    Add a key to reference a full image
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image_add_atlas("test2", "media/LegendaryMissions/operator", 645,570, 950,820)
    ```
    
    Once the atlas is added the key can be used anywhere images can be used.
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    gui_image("test")
    ```
    
    :mast-icon: MAST / :simple-python: python
    
    ``` python
    # Text area also use the image atlas for images
    gui_text_area("![](image://test2?scale=0.5&fill=center)")
    ```
    
    
    
    Args:
        key (str): the key to define in the image atlas
        image (str): The file of the image. This can also be a image property string do not include the extension. Only PNG files are valid.
        left (float, optional): The pixel location of the left. Defaults to None.
        top (float, optional): The pixel location of the top. Defaults to None.
        right (float, optional): The pixel location of the right. Defaults to None.
        bottom (float, optional): The pixel location of the bottom. Defaults to None.
        color (str, optional): default tint for this key. A drawing call may override it.
        domain (str, optional): a namespace for the key. `ImageAtlas.all` is one
            process-wide dict, so two addons registering `card_back` collide silently and
            the last one loaded wins. A domain scopes the claim - and something that
            RESOLVES through a domain (icons do) will only honor a deliberate registration.
    
    Returns:
        ImageAtlas: The image Atlas object. This is a low level object typically used by the system """
def gui_image_add_atlas_grid (image, cols, rows=None, names=None, cell=None, color=None, domain=None, start=0):
    """Register a whole sheet of evenly spaced cells in one call.
    
    Cutting a sheet up by hand is the same four lines of arithmetic every time, and
    getting one of them wrong shows up as art that is off by a cell rather than as an
    error (`casino_media.py` hand-loops exactly this).
    
        gui_image_add_atlas_grid("media/icons/quest-sheet", 8, 8,
                                 ["job", "beat", "arc"], cell=64, domain="icon")
    
    Args:
        image (str): the sheet, without the extension.
        cols (int): cells across.
        rows (int, optional): cells down. Needed only to measure a cell from the file.
        names (list | dict, optional): a list is laid out ROW-MAJOR from `start`, and a
            `None` entry skips that cell; a dict is `{name: (col, row)}` for a sparse
            sheet. Omit to register nothing and just get the cell size back.
        cell (int | tuple, optional): cell size in PIXELS. Measured from the file
            (`width / cols`) when omitted, which requires the file to be readable.
        color (str, optional): default tint for every cell.
        domain (str, optional): namespace for the keys - see ``gui_image_add_atlas``.
        start (int, optional): index of the first name in row-major order.
    
    Returns:
        dict: {name: ImageAtlas} for everything registered."""
def gui_image_get_atlas (text, domain=None):
    """The atlas registered under a key, or one built from the text as a file name.
    
    Args:
        text (str): a registered key, or an image path / property string.
        domain (str, optional): look only in this domain (see ``gui_image_add_atlas``)."""
def gui_image_keep_aspect_ratio (props, style=None):
    """Add an image scaled to fit the area while preserving aspect ratio.
    
    Scales the image as large as possible without cropping, anchored
    top-left. Leaves empty space if the area's aspect ratio differs from
    the image's.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_keep_aspect_ratio("media/ship/artemis")"""
def gui_image_keep_aspect_ratio_center (props, style=None):
    """Add an image scaled to fit the area while preserving aspect ratio, centered.
    
    Like ``gui_image_keep_aspect_ratio`` but centers the image in the
    remaining space when the aspect ratios differ.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_keep_aspect_ratio_center("media/crew/captain")"""
def gui_image_size (file):
    """Return the pixel dimensions of an image file or atlas entry.
    
    Checks the atlas first, then reads the PNG header directly. Results are
    cached so repeated calls are free after the first read.
    
    Args:
        file (str): Atlas key or image path (without ``.png`` extension).
    
    Returns:
        tuple[int, int]: ``(width, height)`` in pixels, or ``(-1, -1)`` if
            the file cannot be read.
    
    Example:
        w, h = gui_image_size("media/backgrounds/nebula")"""
def gui_image_stretch (props, style=None):
    """Add an image to the layout, stretched to fill its area.
    
    Args:
        props (str): Image filename (without extension), atlas key, or image
            property string e.g. ``"image:media/logo;color:white;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Image: The layout item created.
    
    Example:
        gui_image_stretch("media/backgrounds/nebula")"""
def gui_info_panel (tab=0, tab_location=0, icon_size=0, var=None):
    """Create the standard info panel with a built-in ship-data tab.
    
    Initialises a ``TabbedPanel`` pre-loaded with a "hide" tab (icon 121) and
    a "ship_data" tab (icon 140). Additional tabs can be appended with
    ``gui_info_panel_add``. The panel object is stored in the GUI task under
    ``var`` so it can be retrieved and updated later.
    
    Args:
        tab (int, optional): Initially active tab index. Defaults to 0.
        tab_location (int, optional): Edge where tabs appear (0=left). Defaults to 0.
        icon_size (int, optional): Icon size in pixels. Defaults to 0 (auto).
        var (str, optional): Task variable name used to store the panel.
            Defaults to ``"__INFO_PANEL__"``.
    
    Returns:
        TabbedPanel: The info panel layout object.
    
    Example:
        tp = gui_info_panel()
        gui_info_panel_add("comms", 130, show_comms_tab)"""
def gui_info_panel_add (path, icon_index, show, hide=None, tick=None, var=None):
    """Add a tab to an existing info panel.
    
    If the panel is currently displayed, it is re-represented immediately.
    
    Args:
        path (str): Route name for this tab, used to switch to it programmatically.
        icon_index (int): Icon index displayed on the tab button.
        show (callable): ``show(cid, left, top, width, height)`` called when
            the tab becomes active.
        hide (callable, optional): Called when the tab is deactivated.
            Defaults to None.
        tick (callable, optional): Called each tick while the tab is active.
            Defaults to None.
        var (str, optional): Task variable holding the panel (set by
            ``gui_info_panel``). Defaults to ``"__INFO_PANEL__"``.
    
    Returns:
        TabbedPanel | None: The panel, or ``None`` if not found.
    
    Example:
        gui_info_panel_add("crew", 155, show_crew_tab, hide_crew_tab)"""
def gui_info_panel_remove (path, var=None):
    """Remove a tab from an info panel by its path name.
    
    If the panel is currently displayed and the tab was actually present,
    the panel is re-represented immediately.
    
    Args:
        path (str): Route name of the tab to remove (as passed to
            ``gui_info_panel_add``).
        var (str, optional): Task variable holding the panel. Defaults to
            ``"__INFO_PANEL__"``.
    
    Returns:
        TabbedPanel | None: The panel, or ``None`` if not found.
    
    Example:
        gui_info_panel_remove("crew")"""
def gui_info_panel_send_message (client_id, message=None, message_color=None, path=None, title=None, title_color=None, banner=None, banner_color=None, face=None, icon_index=None, icon_color=None, button=None, history=True, time=-1, notify=None):
    """Send a message card to a client's info panel.
    
    Every card is filed in the tab's **log** (readable any time on the log tab)
    unless ``history=False``. A card only *interrupts* - taking over the panel's
    tab and auto-dismissing - when it needs an answer or the caller asks:
    
    - a card with a ``button`` ALWAYS interrupts. It is a progression gate: a
      mission awaiting the press deadlocks if the player never sees it.
    - otherwise pass ``notify=True`` to interrupt. The default is ``False``:
      the card goes to the log and does not steal the tab, because the attention
      half of a notification belongs to an overlay now (see ``announce``).
    
    Args:
        client_id (int | set): Client(s) to receive the message.
        message (str, optional): Main body text.
        message_color (str, optional): CSS color for the body text.
        path (str, optional): Tab path to place the message in. Defaults to
            ``"message"``.
        title (str, optional): Bold header line above the message.
        title_color (str, optional): CSS color for the title.
        banner (str, optional): Larger banner text shown above the title.
        banner_color (str, optional): CSS color for the banner.
        face (str, optional): Face/portrait key to display alongside the message.
        icon_index (int, optional): Icon index to display alongside the message.
        icon_color (str, optional): CSS color for the icon.
        button (str | list, optional): Button label(s) to show. When set the
            function returns an awaitable Promise that resolves on button press.
        history (bool, optional): File the card in the tab's log. Defaults to True.
        time (int, optional): Auto-dismiss after this many seconds if no button
            is configured. Defaults to -1 (use panel default of 10 s).
        notify (bool, optional): Interrupt - show the card live and switch the
            panel to its tab. Defaults to None, meaning "only if it has a
            button". Pass True for a card that must be seen now.
    
    Returns:
        Promise | None: Resolves when the button is pressed, or None if no
            button was specified.
    
    Example:
        await gui_info_panel_send_message(CLIENT_ID,
            title="New Orders",
            message="Report to DS1 immediately.",
            face="captain")"""
def gui_input (props, style=None, var=None, data=None):
    """Add a text input field to the current GUI layout.
    
    The current value of ``var`` is pre-filled as the input text. When the
    player edits and submits, ``var`` is updated with the new value.
    
    Args:
        props (str): Property string for input configuration, e.g.
            ``"hint:Enter name;"`` or ``""`` for defaults.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to pre-fill and update on submit.
            Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        TextInput: The layout item created.
    
    Example:
        gui_input("", var="ship_name", style="col-width:50%;")"""
def gui_int_slider (msg, style=None, var=None, data=None):
    """Add an integer-only slider control to the current GUI layout.
    
    Convenience wrapper for ``gui_slider(..., is_int=True)``.
    
    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"low:1;high:10;text:int;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        Slider: The layout item created.
    
    Example:
        gui_int_slider("low:1;high:5;text:int;", var="torp_count")"""
def gui_layout_widget (widget, style=None):
    """Place a specific engine widget at a fixed position in the layout.
    
    Adds the named engine widget to the console widget list AND places a
    ``ConsoleWidget`` placeholder in the layout at the current position so the
    engine widget renders inside the defined area.
    
    Args:
        widget (str): Engine widget name, e.g. ``"2dview"`` or
            ``"helm_movement"``.
        style (str, optional): Layout style for the PLACEHOLDER, as for any other
            widget - most usefully ``col-width``. Defaults to None (the whole row).
    
    DO NOT SHARE A ROW WITH MAST CONTROLS. The placeholder lays out correctly - measured:
    `red_alert` beside three checkboxes computes four clean quarters, and every rect is
    sent - but the ENGINE draws its widget at its own size, over the top of whatever MAST
    put beside it, so the controls simply vanish. Give an engine widget its own row (or
    its own section). ``col-width`` still shapes the rect the engine is GIVEN, which is
    worth having on its own; it just cannot stop the engine painting outside it.
    
    Returns:
        ConsoleWidget: The layout placeholder item.
    
    Example:
        gui_section(style="area:0,0,70,100;")
        gui_layout_widget("2dview")
        # sharing one row with a checkbox:
        gui_checkbox("Follow", "col-width:90px;", var="follow_tag")
        gui_layout_widget("red_alert", "col-width:1fr;")"""
def gui_list (items, style='', select=False, multi=False, title=None, read_only=False, row_height='1.6em'):
    """Data-bound listbox: the ``with`` block is the per-row template.
    
    Args:
        items: The rows to render. The ``as`` name (and ``item``) is bound to
            each one while the block runs.
        style (str, optional): listbox container style. Defaults to "".
        select (bool, optional): allow row selection. Defaults to False.
        multi (bool, optional): allow multiple selection. Defaults to False.
        title (str, optional): a title row for the listbox. Defaults to None.
        read_only (bool, optional): prevent modification. Defaults to False.
        row_height (str, optional): height of each row (e.g. "1.6em", "3em").
            A roomier value gives cells more breathing room. Defaults to "1.6em".
    
    Returns:
        PageList: A row-template context manager. Use with ``with``.
    
    Example:
        with gui_list(ships, select=True) as ship:
            gui_text("{ship.name}")
            gui_text("{ship.hull}%")"""
def gui_list_box (items, style, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False, reveal=False, hint=None):
    """Add a listbox to the current GUI layout.
    
    Args:
        items (list): Items to display. Plain strings render as text rows;
            ``LayoutListBoxHeader`` objects (from ``gui_list_box_header``)
            render as collapsible section dividers.
        style (str): CSS-like style overrides for the listbox container.
    
            ``row-height`` is the height of ONE item row, and a FLOOR - a template
            that needs more grows past it. It also sizes the box each item is measured
            and drawn in, so a template whose rows declare no height fills the item
            rather than collapsing, and the item's CLICK REGION is never smaller than
            the row you can see.
    
            ``item-gap`` is the spacing BETWEEN items. This is what ``row-height``
            used to mean here, which made a list declaring the height its template
            already used render at twice the pitch.
    
            Declare neither and an item is exactly as tall as its template's rows,
            with items flush - unchanged from before either key existed.
        item_template (callable | None, optional): Called per item to build
            its row layout. Defaults to None (built-in text row).
        title_template (str | callable | None, optional): Title for the
            listbox. A string is used as-is; a callable is invoked to build
            the title row. Defaults to None.
        section_style (str | None, optional): Style overrides applied to each
            item row section. Defaults to None.
        title_section_style (str | None, optional): Style overrides applied to
            the title section. Defaults to None.
        select (bool, optional): Allow item selection. Defaults to ``False``.
        multi (bool, optional): Allow multiple simultaneous selections. Only
            used when ``select=True``. Defaults to ``False``.
        carousel (bool, optional): Use carousel styling (e.g. ship-type
            selection). Defaults to ``False``.
        collapsible (bool, optional): Clicking a header collapses items until
            the next header. Defaults to ``False``.
        read_only (bool, optional): Prevent item modification. Defaults to
            ``False``.
        reveal (bool, optional): Scroll so the selected row is visible. A
            repaint rebuilds the listbox and the view starts at the top, so a
            restored selection can be held but off screen. Opt-in: this widget
            is load-bearing, and defaulting it on would move every list in every
            mission. Defaults to ``False``.
        hint (object, optional): An opaque token from the previous listbox's
            ``get_selection_hint()``. A repaint builds a DIFFERENT listbox whose
            view starts at the top, so without this the row under the user's
            mouse moves. Do not inspect it; pass it along.
    
    Returns:
        LayoutListbox: The layout object created.
    
    Example:
        gui_list_box(items, style="area:0,0,100,100;", select=True)"""
def gui_list_box_header (label, collapse=False, indent=0, selectable=False, data=None, visual_indent=None):
    """Create a collapsible section header for use in a listbox.
    
    When ``collapsible=True`` is set on the listbox, clicking a header toggles
    the visibility of items that follow it until the next header.
    
    Args:
        label (str): Header label text.
        collapse (bool, optional): Start in collapsed state. Defaults to
            ``False``.
        indent (int, optional): Logical indent level for tree structures.
            Defaults to 0.
        selectable (bool, optional): Whether clicking the header fires a
            selection event in addition to toggling collapse. Defaults to
            ``False``.
        data (object, optional): Arbitrary data attached to the header item.
            Defaults to None.
        visual_indent (int | None, optional): Override indent level for
            rendering only. Defaults to None (uses ``indent``).
    
    Returns:
        LayoutListBoxHeader: The header item."""
def gui_list_box_is_header (item):
    """Return whether a listbox item is a collapsible header.
    
    Args:
        item: Any item from a listbox items list.
    
    Returns:
        bool: ``True`` if the item is a ``LayoutListBoxHeader``.
    
    Example:
        for item in items:
            if gui_list_box_is_header(item):
                ~~ print("header:", item.label) ~~"""
def gui_listbox_items_convert_headers (items):
    """Convert a flat string list into a listbox-ready list with collapsible headers.
    
    Items prefixed with ``>>`` become ``LayoutListBoxHeader`` objects; all
    others pass through as plain strings. Pass the result to ``gui_list_box``
    with ``collapsible=True`` to enable collapse on header click.
    
    Args:
        items (list[str]): Flat list of strings. Prefix a string with ``>>``
            to make it a collapsible header, e.g. ``">>Section A"``.
    
    Returns:
        list[str | LayoutListBoxHeader]: Mixed list ready for ``gui_list_box``.
    
    Example:
        items = gui_listbox_items_convert_headers(
            [">>Section A", "Item 1", "Item 2", ">>Section B", "Item 3"]
        )
        gui_list_box(items, style="", select=True, collapsible=True)"""
def gui_log_tail (count=None, background=None, tab='log', style=None):
    """The last few log lines, drawn where a console's text waterfall used to be.
    
    The engine waterfall cannot be styled from script - its background is fixed, and too
    dark. This is the same content in a MAST text area, so the console owns its own look.
    
    It is the AMBIENT half of the log: always visible, no interaction, the last line or
    two. The history - filtered, scrollable, categorised - is the info-panel tab. Keeping
    both is deliberate: a crew reading ship data should still catch traffic going past
    without opening anything, and that is exactly what the tab cannot do.
    
    Args:
        count (int, optional): how many lines. Defaults to LOG_TAIL_LINES (2).
        background (str, optional): the strip's colour. Defaults to LOG_TAIL_BACKGROUND.
        tab (str, optional): which stream to tail. Defaults to everything.
        style (str, optional): extra style for the text area."""
def gui_map_picker (maps=None, properties=True, title=None, start_text='Start', list_style='item-gap: 7em;'):
    """Build a map carousel plus a Start button; return an awaitable resolving to the choice.
    
    Pairs with ``map_start``: this one only CHOOSES, so a mission can do something else with
    the answer, or start a map it picked some other way.
    
        chosen = await gui_map_picker()
        map_start(chosen)
    
    Args:
        maps (list | None): Map labels to offer. Defaults to ``maps_get_list()``, which
            already hides maps whose ``if`` condition is false.
        properties (bool): Render the selected map's ``Properties:`` panel. On by default -
            it is two calls, and without it a map expecting ``PLAYER_COUNT`` starts with it
            unset, which is a silent wrong-behaviour trap rather than a missing feature.
        title (str | None): Listbox title. Defaults to a count of the maps.
        start_text (str): Label for the start button.
        list_style (str): Style string for the carousel.
    
    Returns:
        Promise: Resolves with the chosen map Label when Start is pressed. A story with no
        maps draws a message and returns a promise that never resolves, rather than raising."""
def gui_message (layout_item, label=None):
    """Register a MAST label to run when a layout element receives a GUI event.
    
    Attaches a ``MessageTrigger`` to the current task so that when the engine
    fires a ``gui_message`` event matching ``layout_item``'s tag, the given
    label is pushed and executed inline. Used to respond to clicks on custom
    layout items (sections, regions, etc.) that are not plain buttons.
    
    Args:
        layout_item: The layout object whose tag to watch. Must expose
            ``is_message_for(event)`` (all standard layout items do).
        label (optional): MAST label or inline block to run on the event.
            Defaults to the current active label.
    
    Returns:
        MessageTrigger: The registered trigger object.
    
    Example:
        region = gui_region(style="area:10,10,50,50;")
        gui_message(region, on_region_click)
        ///on_region_click
            gui_text("Region clicked!")"""
def gui_message_callback (layout_item, cb):
    """Set a Python callable to invoke when a layout element receives a GUI event.
    
    Attaches a callback directly to the layout item's ``on_message_cb``
    attribute. The callback is called with the event and the layout item when
    the engine fires a ``gui_message`` event matching the item's tag.
    Use this for pure-Python handlers; use ``gui_message`` for MAST label
    handlers.
    
    Args:
        layout_item: The layout object to attach the callback to.
        cb (callable): Function called as ``cb(event, layout_item)`` on event.
    
    Example:
        btn = gui_button("Fire!", on_press=None)
        gui_message_callback(btn, lambda e, item: fire_torpedo(SHIP_ID))"""
def gui_message_clear (layout_item):
    """Drop EVERY gui_message handler attached to a widget, on both channels.
    
    Handlers accumulate now (LM #614), so replacing rather than adding takes an
    explicit step: clear, then register. Before #614 a plain re-registration
    did this implicitly, by throwing the previous handler away.
    
    Args:
        layout_item: the widget to detach every handler from.
    
    Returns:
        int: how many registrations were removed."""
def gui_message_label (layout_item, label):
    """Schedule a MAST label as a sub-task when a layout element receives a GUI event.
    
    Similar to ``gui_message_callback`` but wraps the label in a
    ``gui_sub_task_schedule`` call, running it as an independent sub-task
    rather than inline in the current task.
    
    Args:
        layout_item: The layout object to attach the handler to.
        label: MAST label to schedule as a sub-task on event.
    
    Example:
        section = gui_sub_section(style="col-width:30%;")
        gui_message_label(section, handle_section_click)"""
def gui_options_button (transparent=True, client_id=None):
    """Make the engine Options button transparent (or normal) for a client, and
    keep it that way across page rebuilds.
    
    Prefer this over calling ``sbs.transparent_options_button`` directly: the raw
    call is undone by the next page build.
    
    Args:
        transparent (bool, optional): ``True`` to make the button transparent,
            ``False`` to restore it. Defaults to ``True``.
        client_id (int, optional): The client to set it for. Defaults to the
            client of the current frame.
    
    Example:
        gui_options_button()            # this console's button, transparent
        gui_options_button(False)       # put it back"""
def gui_options_button_clear (client_id=None):
    """Forget the recorded intent (all clients when client_id is None), so the
    button returns to the default on the next rebuild. For a client that
    disconnected, and for tests."""
def gui_options_button_flag (client_id):
    """The flag a mission last asked for on this client, or 0 if it never did.
    
    Used by StoryPage.on_new_gui to restore the button to what the mission
    wanted rather than to a hardcoded 0."""
def gui_panel_console_message (cid, left, top, width, height):
    ...
def gui_panel_console_message_list (cid, left, top, width, height):
    ...
def gui_panel_console_message_tick (info_panel):
    ...
def gui_panel_log (cid, left, top, width, height, tab='log'):
    """Info-panel tab body: the ship's log, newest at the bottom.
    
    Oldest-first with the newest at the BOTTOM, which is what the waterfall did and what
    a running log should do - the text area follows the tail unless the reader has
    scrolled back (see TextArea.follow_tail)."""
def gui_panel_log_mission (cid, left, top, width, height):
    """Info-panel tab: objective and quest beats."""
def gui_panel_log_ship (cid, left, top, width, height):
    """Info-panel tab: damage, systems, docking - Engineering's own feed."""
def gui_panel_log_tick (info_panel):
    """Redraw the log tab only when the log has actually grown.
    
    The panel's tick contract is 0 = done, 1 = stay, 2 = redraw. **Never 0 here**: 0
    means "this tab has nothing important" and sends the console back to its DEFAULT
    tab, which for a log the player deliberately opened would be a surface that closes
    itself.
    
    Comparing the newest ``seq`` rather than redrawing every tick keeps an idle log at
    zero render cost - this widget wraps every line on recalc, so a 1 Hz re-present of a
    500-line log would be real work for no change."""
def gui_panel_upgrade_list (cid, left, top, width, height):
    ...
def gui_panel_widget_hide (cid, left, top, width, height, widget):
    ...
def gui_panel_widget_show (cid, left, top, width, height, widget):
    ...
def gui_percent_from_ems (client_id, ems, font):
    """Convert an em-based size to GUI percentage coordinates for a client's screen.
    
    An em is the width/height of the character "X" in the given font. Use this
    to size layout elements relative to text size rather than fixed pixels.
    
    Args:
        client_id (int): The client whose screen resolution to use.
        ems (float): The number of em units to convert.
        font (str): Font name used to measure one em (e.g. ``"hud_font"``).
    
    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).
    
    Example:
        pct = gui_percent_from_ems(CLIENT_ID, 2, "hud_font")
        gui_section(style="width:{pct.x}%;")"""
def gui_percent_from_pixels (client_id, pixels):
    """Convert a pixel size to GUI percentage coordinates for a client's screen.
    
    GUI layout positions are expressed as percentages (0–100) of the screen
    dimensions. Use this to convert a fixed pixel measurement to the equivalent
    percentage for a specific client's resolution.
    
    Args:
        client_id (int): The client whose screen resolution to use.
        pixels (float): The pixel size to convert.
    
    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).
    
    Example:
        pct = gui_percent_from_pixels(CLIENT_ID, 40)
        gui_section(style="height:{pct.y}%;")"""
def gui_properties_change (var, label):
    """Watch a MAST variable and run an inline block when its value changes.
    
    Registers a per-tick change detector on the current client's GUI task.
    When ``var`` changes value, the block at ``label`` is pushed and executed
    immediately within the current tick.
    
    Args:
        var (str): Name of the MAST variable to watch.
        label: The inline label or block to execute on change.
    
    Example:
        gui_properties_change("shield_level", shield_changed)
        ///shield_changed
            gui_text("Shields: {shield_level}")"""
def gui_properties_set (p=None, tag=None):
    """Update the data displayed in a property list box.
    
    Parses ``p`` (a dict or YAML string) into a flat list of label/control
    pairs and refreshes the list box stored under ``tag`` in the GUI task.
    Call this whenever the underlying data changes to redraw the panel.
    
    Args:
        p (dict | str, optional): Property data as a Python dict or a YAML
            string. Dict keys become labels; values are Python expressions
            evaluated to produce the control widget. Nested dicts become
            collapsible sections. Defaults to None (clears the list).
        tag (str, optional): Task inventory key holding the list box widget.
            Defaults to ``"__PROPS_LB__"``.
    
    Example:
        gui_properties_set({"Speed": "gui_text(str(ship_speed))", "Shields": "gui_slider(shield_pct)"})"""
def gui_property_list_box (name=None, tag=None, temp=<function _property_lb_item_template_one_line at 0x000002B55DAB5F30>):
    """Create a property list box with single-line label/control layout.
    
    Each property is rendered as a label on the left and its control widget
    on the right of the same row. Suitable for compact property panels.
    The widget is stored in the GUI task under ``tag`` so ``gui_properties_set``
    can refresh it later.
    
    Args:
        name (str, optional): Title shown in the list box header.
            Defaults to ``"Properties"``.
        tag (str, optional): Task inventory key used to store and retrieve
            the list box widget. Defaults to ``"__PROPS_LB__"``.
        temp (callable, optional): Item template function used to render each
            row. Defaults to the built-in one-line template.
    
    Returns:
        LayoutListBox: The list box widget.
    
    Example:
        gui_property_list_box("Navigation")
        gui_properties_set({"Heading": "gui_text(str(heading))", "Speed": "gui_text(str(speed))"})"""
def gui_property_list_box_stacked (name=None, tag=None):
    """Create a property list box with two-line stacked label/control layout.
    
    Each property is rendered as a label on one line and its control widget
    on the line below. Useful when controls are wide and need their own row.
    The widget is stored in the GUI task under ``tag`` so ``gui_properties_set``
    can refresh it later.
    
    Args:
        name (str, optional): Title shown in the list box header.
            Defaults to ``"Properties"``.
        tag (str, optional): Task inventory key used to store and retrieve
            the list box widget. Defaults to ``"__PROPS_LB__"``.
    
    Returns:
        LayoutListBox: The list box widget.
    
    Example:
        gui_property_list_box_stacked("Ship Systems")
        gui_properties_set({"Warp Core": "gui_slider(warp_pct)"})"""
def gui_radio (msg, style=None, var=None, data=None, vertical=False):
    """Add a radio button group to the current GUI layout.
    
    The current value of ``var`` sets the initially selected option. When the
    player selects a button, ``var`` is updated to the selected label.
    
    Args:
        msg (str): Comma-separated button labels or property string, e.g.
            ``"Alpha,Beta,Gamma"`` or ``"items:Slow,Fast;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on selection. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
        vertical (bool, optional): Stack buttons vertically. Defaults to
            ``False`` (horizontal).
    
    Returns:
        RadioButtonGroup: The layout item created.
    
    Example:
        gui_radio("Beam,Missile,Mine", var="weapon_type")"""
def gui_rebuild (region):
    """Mark a section or region to rebuild its layout on the next present.
    
    Clears the region's sub-layout so it is reconstructed from scratch the
    next time the region is rendered.
    
    Args:
        region: A section or region layout item.
    
    Returns:
        The same ``region`` object, for chaining.
    
    Example:
        gui_rebuild(my_region)
        gui_represent(my_region)"""
def gui_refresh (label):
    """Re-run an ``await gui()`` block at a given label on the current task.
    
    Causes any scheduler running ``label`` to rebuild its GUI from scratch on
    the next tick.
    
    Args:
        label: MAST label whose ``await gui()`` block should be refreshed.
            Pass ``None`` to refresh the current task's active label.
    
    Example:
        gui_refresh(status_panel)"""
def gui_region (style=None):
    """Create a re-representable GUI region pinned to an absolute screen area.
    
    Unlike ``gui_sub_section``, a region uses absolute positioning (the ``area``
    style property) and can be redrawn independently with ``region.represent()``.
    Use it for UI panels that update without redrawing the entire page.
    Also a context manager — content inside the ``with`` block is placed in
    the region.
    
    Args:
        style (str, optional): CSS-like style string. The ``area:`` property
            sets the absolute screen position (left, top, right, bottom %).
            Defaults to None.
    
    Returns:
        PageRegion: Context manager object with ``show()``, ``rebuild()``,
            and ``represent()`` methods.
    
    Example:
        hud = gui_region(style="area:0,0,100,10;")
        with hud:
            gui_text("HUD content here")
        ~~ hud.represent(event) ~~   # refresh just this region later"""
def gui_remove_console_type (path, display_name, label):
    """adds a tab definition
    
    Args:
        path (str): Console path
        display_name (str): Display name
        label (label): Label to run when tab selected"""
def gui_represent (layout_item):
    """Redraw a layout item on the client screen.
    
    For sections and regions, recalculates the entire sub-layout and redraws
    all children. For individual items or rows, redraws that element only.
    
    Args:
        layout_item: The layout object to redraw.
    
    Example:
        gui_represent(my_section)"""
def gui_request_client_string (client_id, key, timeout=None):
    """Request a text string from the player via a native OS input dialog.
    
    Sends a ``request_client_string`` call to the engine for the given client.
    The engine shows an OS-level text input and returns the typed value as a
    ``client_string`` event. Suspends until the player submits or the timeout
    fires.
    
    Args:
        client_id (int): Client to prompt.
        key (str): Tag used to identify the response event (``event.sub_tag``).
        timeout (Promise, optional): A promise that cancels the request if it
            resolves first. Defaults to None.
    
    Returns:
        Promise: Resolves with the typed string as its result.
    
    Example:
        result = await gui_request_client_string(CLIENT_ID, "ship_name")
        ~~ player_name = result.result ~~"""
def gui_reroute_client (client_id, label, data=None):
    """Jump a specific client's GUI task to a new label immediately.
    
    Finds the client's active page, optionally sets variables from ``data``,
    then jumps the page's GUI task to ``label`` and ticks it in the current
    frame context.
    
    Args:
        client_id (int): The client to reroute.
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_client(CLIENT_ID, briefing_screen)"""
def gui_reroute_clients (label, data=None, exclude=None):
    """Jump all connected client GUI tasks to a new label.
    
    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on each task before
            jumping. Defaults to None.
        exclude (set | None, optional): Set of client IDs to skip. Defaults
            to None (no exclusions).
    
    Example:
        gui_reroute_clients(mission_end_screen, exclude={spectator_id})"""
def gui_reroute_server (label, data=None):
    """Jump the server GUI task to a new label.
    
    Args:
        label: MAST label to jump to.
        data (dict | None, optional): Variables to set on the task before
            jumping. Defaults to None.
    
    Example:
        gui_reroute_server(server_status_page)"""
def gui_row (style=None):
    """Start a new layout row, pushing subsequent items to the next line.
    
    Call before adding items that should appear on a fresh row. Without
    explicit rows, items flow left-to-right across the current row.
    
    Args:
        style (str, optional): CSS-like style overrides for the row container.
            Defaults to None.
    
    Returns:
        Row: The row layout object.
    
    Example:
        gui_text("Name:")
        gui_row()
        gui_input("", var="ship_name")"""
def gui_screen_size (client_id):
    """Return the pixel dimensions of a client's screen.
    
    CAUTION: when the client has not reported its size yet, this returns a
    1024x768 PLACEHOLDER with ``z == 99`` rather than a real measurement, and a
    client that reconnects goes back to the placeholder until its next resize
    event. Branching on the width without checking validity silently builds the
    small-screen layout on a large display:
    
        ss = gui_screen_size(client_id)
        if ss.x < 1600:          # WRONG - 1024 placeholder also lands here
            ...
    
    Use ``gui_screen_size_known`` to tell "small" from "unknown".
    
    Args:
        client_id (int): The client whose screen to query.
    
    Returns:
        Vec3: Screen dimensions in pixels (x=width, y=height); z is
        ``GUI_SCREEN_SIZE_UNKNOWN_Z`` (99) when the size is not yet known.
    
    Example:
        size = gui_screen_size(CLIENT_ID)
        ~~ print(size.x, size.y) ~~"""
def gui_screen_size_known (client_id):
    """True when the client has actually reported its screen size.
    
    Pair with ``gui_screen_size`` before branching on the dimensions, so an
    unknown size can be handled deliberately (usually: assume the LARGER layout,
    which degrades better than cramming a wide screen into the narrow one).
    
    Args:
        client_id (int): The client whose screen to query.
    
    Returns:
        bool: False while the size is still the 1024x768 placeholder.
    
    Example:
        ss = gui_screen_size(client_id)
        if not gui_screen_size_known(client_id) or ss.x >= 1600:
            gui_row("row-height: 35px;col-width:45px;")
        else:
            gui_row("row-height: 35px;col-width:25px;")"""
def gui_screenshot (image_path):
    """Capture the full desktop and save it as a BMP file.
    
    Windows-only. Captures the entire desktop window (not just the Cosmos
    window) using GDI BitBlt. Useful for automated testing or recording
    mission state.
    
    Args:
        image_path (str): Absolute path to write the ``.bmp`` file.
    
    Example:
        ~~ gui_screenshot("C:/missions/debug/frame001.bmp") ~~"""
def gui_section (style=None):
    """Create a top-level GUI layout section at a specific screen area.
    
    Sections are the primary way to position content on screen. The ``area``
    style property sets the region (left, top, right, bottom as percentages).
    Content added after this call is placed inside the section until the next
    ``gui_section`` or the frame ends.
    
    Args:
        style (str, optional): CSS-like style string. Use ``area:`` to position
            the section, e.g. ``"area:10,10,90,90;"``. Defaults to None.
    
    Returns:
        Layout: The layout object for this section.
    
    Example:
        gui_section(style="area:5,5,95,50;")
        gui_text("Top half of screen")
        gui_section(style="area:5,50,95,95;")
        gui_text("Bottom half of screen")"""
def gui_set_style_def (name, style):
    """Parse a style string and register it under a named class.
    
    After registering, the name can be used as a CSS class reference in any
    style string (e.g. ``".my_style"``).
    
    Args:
        name (str): Class name to register (conventionally prefixed with
            ``"."``), e.g. ``".alert"``.
        style (str): CSS-like style string to associate with the name.
    
    Returns:
        StyleDefinition: The parsed and registered style object.
    
    Example:
        gui_set_style_def(".alert", "color:red;background:#400;")
        gui_text("Warning!", style=".alert")"""
def gui_ship (props, style=None):
    """Render a 3D ship model in the current GUI layout.
    
    Displays a real-time 3D render of the named ship type within the layout
    area. The ship type key must match one defined in the game data.
    
    Args:
        props (str): Ship type key or property string, e.g. ``"battleship"``
            or ``"$type:cruiser;angle:45;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Ship: The layout item created.
    
    Example:
        gui_ship("battleship", style="area:20,0,80,60;")"""
def gui_show (layout_item):
    """Make a hidden layout item visible.
    
    For sections, recalculates the layout after showing. For individual items
    or rows, shows the element but does not re-layout — pair with
    ``gui_represent`` on the parent section if the layout needs updating.
    
    Args:
        layout_item: The layout object to show. No-op if already visible or
            ``None``.
    
    Example:
        gui_show(warning_row)
        gui_represent(my_section)"""
def gui_slider (msg, style=None, var=None, data=None, is_int=False):
    """Add a slider control to the current GUI layout.
    
    The current value of ``var`` is used as the initial slider position. When
    the player adjusts the slider, ``var`` is updated.
    
    Args:
        msg (str): Property string defining the slider range and label, e.g.
            ``"low:0;high:100;text:float;"``
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial value from and
            update on change. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
        is_int (bool, optional): Restrict values to integers. Defaults to
            ``False``.
    
    Returns:
        Slider: The layout item created.
    
    Example:
        gui_slider("low:0;high:100;text:float;", var="speed_pct")"""
def gui_style_def (style):
    """Parse a CSS-like style string into a StyleDefinition object.
    
    Useful when you want to pre-parse a style string and inspect or reuse
    it without re-parsing each time.
    
    Args:
        style (str): CSS-like style string, e.g. ``"color:red;col-width:50%;"``.
    
    Returns:
        StyleDefinition: Parsed style object.
    
    Example:
        s = gui_style_def("color:green;font:hud_font;")"""
def gui_sub_section (style=None):
    """Create a nested layout sub-section, used as a context manager.
    
    Sub-sections let you group and style a subset of content within the current
    section. Use with Python's ``with`` statement in MAST via the ``with``
    keyword. The sub-section is added to the current layout when the ``with``
    block exits.
    
    The returned object can be hidden and restored after it is built, with
    ``gui_hide`` / ``gui_show`` or its own ``show()``. Hiding takes the whole
    sub-tree off screen, and its siblings reclaim the space on the next layout
    pass. Hold on to the object to do that - hiding one before its ``with``
    block has run is a no-op, since the layout it stands for does not exist yet.
    
    Args:
        style (str, optional): CSS-like style string controlling the column
            width, row height, background, etc. of the sub-section.
            Defaults to None.
    
    Returns:
        PageSubSection: Context manager object with ``show()`` and
            ``is_hidden``. Use with ``with``.
    
    Example:
        gui_row(style="row-height:3em;")
        with gui_sub_section(style="col-width:30%;"):
            gui_text("Left column")
        right = gui_sub_section()
        with right:
            gui_text("Right column")
        gui_hide(right)     # and gui_show(right) to bring it back"""
def gui_tab_activate (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    This is general called automatically by //gui/tab and //console labels
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_add_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_back (tab_name: str):
    """Sets the back tab (left most) tab for the console tabs.
    The back tag is set by //gui/tab and //console labels
    This allows overriding
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_clear_top ():
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable (tab_name: str):
    """Enable a tab on the console tabs
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_enable_top ():
    ...
def gui_tab_get_active ():
    """returns the active tab
    
    Args:
        tab_name (str): The path of a //gui/tab"""
def gui_tab_get_list ():
    ...
def gui_tab_is_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tab_remove_top (tab_name: str):
    """Specify a tab by default to shown when the page is shown for standard consoles.
    
    Args:
        tab_name (str): A comma separated list of paths of a //gui//tab e.g. helm,weapons"""
def gui_tabbed_panel (items=None, style=None, tab=0, tab_location=0, icon_size=0):
    """Create a tabbed panel widget with icon-based tab navigation.
    
    Each tab is defined by a dict with ``path``, ``icon``, ``show``, and
    optionally ``hide`` and ``tick`` keys. The panel calls ``show`` when a tab
    is activated and ``hide`` when it is deactivated. Prefer ``gui_info_panel``
    for the standard info panel; use this directly only when building a custom
    panel layout.
    
    Args:
        items (list[dict], optional): Tab descriptors. Each dict has:
            ``path`` (str) — route name for this tab;
            ``icon`` (int) — icon index displayed on the tab button;
            ``show`` (callable) — ``show(cid, left, top, width, height)`` called
            when the tab becomes active;
            ``hide`` (callable, optional) — called when the tab is hidden;
            ``tick`` (callable, optional) — called each tick while the tab is
            active. Defaults to None.
        style (str, optional): CSS-like style string for the panel. Defaults to None.
        tab (int, optional): Index of the initially active tab. Defaults to 0.
        tab_location (int, optional): Edge where tabs appear (0=left). Defaults to 0.
        icon_size (int, optional): Icon size in pixels. Defaults to 0 (auto).
    
    Returns:
        TabbedPanel: The panel layout object.
    
    Example:
        panels = [
            {"path": "status", "icon": 140, "show": show_status, "hide": hide_status},
            {"path": "map",    "icon": 121, "show": show_map},
        ]
        tp = gui_tabbed_panel(panels, tab=0)"""
def gui_table (items, columns=None, style='row-height: 1.6em;', select=False, header=True, font='gui-2', on_cell_change=None, headers=None, **kwargs):
    """Add a table (a selectable/scrollable gui_list_box) to the layout.
    
    ``style`` is handed BOTH to the listbox and to each row's ``gui_row``. Under the
    old listbox semantics that meant a row of `row-height` and a GAP of the same, so
    every table rendered at twice its declared pitch; now both say the same thing and
    a table is as tall as it says.
    
    Two forms:
    
    **Block form** — author the row yourself, like the other containers::
    
        with gui_table(fleet, headers=["Ship", "Hull"], select=True) as ship:
            gui_text("{ship.name}")
            gui_text("{ship.hull}%")
    
    Each widget in the ``with`` block is a column; ``headers`` labels line up above
    them. (Used with ``with`` — pass no ``columns``.)
    
    **Declarative form** — pass column specs and it generates the row for you::
    
        gui_table(fleet, [{"key": "name", "label": "Ship"}, ...], select=True)
    
    Args:
        items: list of rows — dicts, MastDataObjects, or plain objects.
        columns: list of column specs (declarative form). Omit for the block form.
            Each spec is a dict:
            {"key": <field name>,
             "label": <header text>            (default: key),
             "align": "l" | "c" | "r"          (default: "l"),
             "width": <percent number> | "auto" (default: "auto"),
             "type": "text" | "checkbox" | "dropdown" | "input" | "button"
                                               (default: "text", read-only),
             "options": [...]                  (dropdown choices),
             "button_label": <text>}           (button cell label; default: label)
            Interactive cells write their new value back to the row and fire
            on_cell_change. 'auto' columns are sized to the widest cell (header +
            data) and share whatever percent the fixed columns leave.
        style: row style (row-height, padding, ...).
        select: allow row selection (default False).
        header: render the column-label header row (default True).
        font: cell/header font tag (default gui-2).
        on_cell_change: fn(item, key, value) called when a cell control changes
            (value is None for a button press). The row is already updated.
        **kwargs: forwarded to gui_list_box (multi, carousel, ...).
    
    Returns:
        The gui_list_box. Read the selected row with get_value()/get_selected().
    
    Example:
        gui_table(fleet, [
            {"key": "name",   "label": "Ship",    "align": "l"},
            {"key": "hull",   "label": "Hull",    "align": "c", "width": 20},
            {"key": "side",   "label": "Side",    "align": "r", "width": 20},
        ], select=True)"""
def gui_task_for_client (client_id):
    """Return the GUI task currently running for a client.
    
    Each connected client has a dedicated GUI task that drives its page layout.
    Returns ``None`` if the client has no active page.
    
    Args:
        client_id (int): The client to look up.
    
    Returns:
        MastAsyncTask | None: The client's GUI task, or ``None`` if unavailable.
    
    Example:
        task = gui_task_for_client(CLIENT_ID)
        if task is not None:
            ~~ task.set_variable("score", 10) ~~"""
def gui_text (props, style=None):
    """Add a text label to the current GUI layout.
    
    Args:
        props (str): Text content or property string, e.g. ``"Hello"`` or
            ``"$text:Hello;color:white;"``. Supports ``{var}`` interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Text: The layout item created.
    
    Example:
        gui_text("Hull: {hull_pct}%")
        gui_text("$text:WARNING;color:red;")"""
def gui_text_area (props, style=None, markdown=True, line_styles=None):
    """Add a rich text area to the current GUI layout.
    
    Supports Markdown-style formatting and inline image references
    (``![](image://key)``). Use for multi-line or formatted text blocks.
    
    Args:
        props (str): Text content or Markdown string. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
        markdown (bool, optional): Parse the mini-markdown. Pass ``False`` to
            render lines VERBATIM - the right choice for source code, a MAST
            error dump or a raw log, where the markup rules actively corrupt the
            content: ``#`` starts a heading (so every MAST comment becomes one),
            a leading ``-`` is consumed as a bullet (``->END``), any ``[...]``
            is read as a link reference and replaces the line, and ``^`` becomes
            a newline. ``{var}`` interpolation is also skipped, since a brace in
            code is a brace. Defaults to True.
        line_styles (list, optional): One style key per line, applied in order -
            how you colorize text that is no longer being parsed. Pairs with
            ``markdown=False``. Defaults to None.
    
    Returns:
        TextArea: The layout item created.
    
    Example:
        gui_text_area("## Status\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5) Mission active")
        gui_text_area(source, markdown=False, line_styles=per_line_keys)"""
def gui_text_escape (s):
    """Quote a dynamic value for safe inclusion as a ``$text:`` style value.
    
    Wraps ``s`` in backticks so any ``:`` or ``;`` it contains is treated as
    literal text by the style parser rather than a style property (issue #569).
    A literal backtick -- the quoting delimiter itself -- is stripped. An empty
    or ``None`` value returns ``""`` so the caller emits ``$text:;`` with no
    stray backtick in the box (issue #641).
    
    Use this ONLY on the dynamic value, e.g. ``f"$text:{gui_text_escape(name)};color:red;"``
    -- never on a whole authored props string, so the author's own ``:``/``;``
    styling is left untouched."""
def gui_update (tag, props, shared=False, test=None):
    """Update the property string of an existing GUI element by tag.
    
    Finds the element with the given tag on the current page (or all pages if
    ``shared=True``) and updates its properties in-place without rebuilding the
    full layout.
    
    The tag is a SCRIPT-SIDE name, not the string the engine knows the widget by.
    Set it with a ``tag:`` style (``gui_text("hi", style="tag:status;")``) and the
    page records it beside the engine's own tag, so naming a widget never disturbs
    the tag the engine, a listbox, or a click region depends on.
    
    A name set inside a listbox ``item_template`` resolves too, but note two things:
    only rows that are currently ON SCREEN exist, so a tag naming a scrolled-away row
    finds nothing; and the name must be unique per row (put the item in it, e.g.
    ``f"tag:row-{item};"``) or only the last row drawn is reachable.
    
    Args:
        tag (str): The element name to find and update.
        props (str): New property string for the element, e.g.
            ``"$text:Firing!;color:red;"``.
        shared (bool, optional): Apply the update to all client pages, not just
            the current one. Defaults to ``False``.
        test (dict | None, optional): Only apply the update when any variable
            in ``test`` has changed since the last update. Defaults to None
            (always update).
    
    Returns:
        bool: True when a widget was found and updated. False is not an error --
        an off-screen listbox row is the ordinary case -- but it lets a caller tell
        a miss from a hit. Always False for ``shared=True``, which fans out.
    
    Example:
        gui_update(status_tag, "$text:OK;color:green;")"""
def gui_update_shared (tag, props, test=None):
    """Update a GUI element by tag on all client pages.
    
    Convenience wrapper for ``gui_update(tag, props, shared=True, test=test)``.
    
    Args:
        tag (str): The element tag to find and update.
        props (str): New property string for the element.
        test (dict | None, optional): Only update when any variable in
            ``test`` has changed. Defaults to None.
    
    Example:
        gui_update_shared(alert_tag, "$text:ALERT;color:red;")"""
def gui_update_widget_list (add_widgets=None, remove_widgets=None):
    """Add or remove widgets from the current client's active widget list.
    
    Modifies the live widget list by taking the union of ``add_widgets`` and
    the current list, then subtracting ``remove_widgets``. View widgets
    (``2dview``, ``3dview``, etc.) are always placed first.
    
    Args:
        add_widgets (str | None, optional): ``^``-separated widget names to
            add. Defaults to None (no additions).
        remove_widgets (str | None, optional): ``^``-separated widget names to
            remove. Defaults to None (no removals).
    
    Example:
        gui_update_widget_list(add_widgets="shield_control", remove_widgets="radar_zoom_ctrl")"""
def gui_update_widgets (add_widgets, remove_widgets):
    """Stage widget list changes on the pending widget list without sending.
    
    Modifies ``page.pending_widgets`` rather than the live widget list. Changes
    are committed when the pending list is flushed to the engine.
    
    Args:
        add_widgets (str): ``^``-separated widget names to add.
        remove_widgets (str): ``^``-separated widget names to remove.
    
    Example:
        gui_update_widgets("shield_control", "radar_zoom_ctrl")"""
def gui_vradio (msg, style=None, var=None, data=None):
    """Add a vertical radio button group to the current GUI layout.
    
    Convenience wrapper for ``gui_radio(..., vertical=True)``.
    
    Args:
        msg (str): Comma-separated button labels or property string.
        style (str, optional): CSS-like style overrides. Defaults to None.
        var (str, optional): Variable name to read the initial selection from
            and update on selection. Defaults to None.
        data (object, optional): Arbitrary data passed to the event handler.
            Defaults to None.
    
    Returns:
        RadioButtonGroup: The layout item created.
    
    Example:
        gui_vradio("Alpha,Beta,Gamma", var="choice")"""
def gui_widget_list (console, widgets):
    """Set the engine console widget list for the current client.
    
    Sends a widget list string directly to the engine, replacing the current
    widget layout. Widgets are ``^``-separated engine widget names.
    
    Args:
        console (str): Console type name, e.g. ``"normal_helm"``.
        widgets (str): ``^``-separated list of engine widget names, e.g.
            ``"2dview^helm_movement^throttle"``.
    
    Example:
        gui_widget_list("normal_helm", "2dview^helm_movement^throttle")"""
def gui_widget_list_clear ():
    """Clear all engine widgets from the current client's console.
    
    Sends an empty widget list to the engine, removing all engine controls.
    The MAST GUI layout (sections, regions, etc.) is not affected.
    
    Example:
        gui_widget_list_clear()"""
def gui_widget_offscreen (widget, client_id=None):
    """Push an engine widget out of view.
    
    The ONLY reliable way to be rid of an engine widget. It cannot be un-declared: the
    console's widget list is what the engine draws from, and the engine keeps what it has
    been given, so simply not asking for it is not always enough on a console that has
    already shown it. gui_hide() does even less - it clears `_show` on the layout
    placeholder while the engine carries on rendering.
    
    So this does what `gui_panel_widget_hide` has always quietly done: sends the widget a
    rect at 100,100, off the visible area. Named, because "hide the waterfall" was
    attempted three different wrong ways before anyone found the one that works.
    
    Args:
        widget (str): engine widget name, e.g. ``"text_waterfall"``.
        client_id (int, optional): defaults to the current client."""
def hail_audio_checkbox (client_id=None, style=None):
    """`Audio` - ticked when hails may play their `Audio:`, which is the default.
    
    Ticked means SOUND, not mute: a scene that ships a sound file expects to be heard,
    and a box you have to tick to get the normal behaviour is a box people find only
    after wondering why it is quiet.
    
    Reads the SHIP's setting rather than remembering its own, so two comms consoles
    always agree - the same reason the placement dial is derived.
    
    Returns:
        the checkbox layout item, or None where a hail cannot be placed."""
def hail_band_clear (ship, to=None, consoles='mainscreen'):
    """Take the band down."""
def hail_band_show (ship, to=None, consoles='mainscreen'):
    """Put the current beat over a live orbit shot.
    
    Only meaningful for the `orbit` form - the other two draw inline, where a plain
    section is enough and an overlay would just be a second thing to keep in step."""
def hail_choice_strip (ship, client_id=None, style=None, row_style=None):
    """The hail list: waiting hails to answer, or the open conversation's replies.
    
    A LISTBOX rather than a row of buttons. Three things follow from that, and all three
    were problems with the buttons: the queue can be any length because the list
    scrolls; the heading says what the list IS, so no separate text row is needed; and
    there is ONE widget to rebuild rather than N, so a repaint cannot leave half a strip
    behind.
    
    Args:
        style (str, optional): the LISTBOX's own style - its item row height.
        row_style (str, optional): the layout ROW the listbox sits in. It opens its own
            row, because a listbox otherwise joins whatever row is currently open and
            lands beside the control above it.
    
    Returns:
        int: how many rows were drawn."""
def hail_list_title (ship):
    """The list's heading: who is talking, or what is waiting."""
def hail_panel_history (cid, left=0, top=0, width=0, height=0):
    """The comms info-panel tab: every conversation this ship has had, re-readable.
    
    Two states in one tab - the list, and one conversation being replayed. The info
    panel gives a builder no way to push a second tab, and a hail's history is one idea,
    so the state lives on the console (`HAIL_REPLAY`) and this reads it."""
def hail_panel_icon ():
    """The history tab's glyph.
    
    A FUNCTION, not a constant, and that is load-bearing: only functions become MAST
    globals, so a module-level `HAIL_PANEL_ICON` is invisible to every .mast file that
    tries to use it - and invisible in a way a headless run does not catch, because the
    console layout that would name it never renders there.
    
    Resolved by MEANING rather than by sheet index, so a mission that re-skins the icon
    sheet moves this with it and the console never carries a bare number it cannot
    explain. Falls back to the messages glyph if the name is ever retired."""
def hail_rows (ship, client_id=None):
    """What the hail list should show right now, as plain rows.
    
    Three states in one list, which is what lets a console draw it unconditionally:
    
    | ship state                | rows                                    |
    |---------------------------|-----------------------------------------|
    | nothing pending or active | none - the list is not drawn            |
    | hails waiting, none open  | one per waiting hail, best first        |
    | a hail open, still talking| a single `Continue`                     |
    | a hail open, beats done   | that scene's answers                    |
    
    Waiting hails are NOT capped here. A listbox scrolls, so the queue cannot outgrow
    the space - which was the whole reason the old button strip stopped at four and
    silently dropped the fifth. The ANSWERS are still capped, because four is an
    authored limit that `amd_lint_hails` enforces at write time."""
def hail_screen_clear (ship, to=None, consoles='mainscreen'):
    """Take the conversation off the main screen, restoring it untouched."""
def hail_screen_show (ship, to=None, consoles='mainscreen'):
    """Put the conversation over the main screen.
    
    Only for the forms that OWN the screen. An orbit shot keeps the live view and gets
    the smaller band instead."""
def hail_transcript_text (entry):
    """An archived conversation as markdown: every line in the order it was said, with
    the answers the crew gave marked as theirs.
    
    The answers are TEXT, deliberately. `hail_answer` refuses a replaying console, so a
    button here would be refused anyway - but the surest way not to rewrite history is
    not to draw a control that looks as though it could."""
def hail_view (ship, client_id=None, face_style=None):
    """Build the conversation into the CURRENT layout position.
    
    `portrait` and `still` draw here. `orbit` draws NOTHING here and returns its name
    anyway: the engine has the screen full-bleed and the band is an overlay, so a
    console that gets `"orbit"` back should simply leave its view alone.
    
    Args:
        face_style (str, optional): the layout row the portrait sits in. The default is
            sized for a bridge console's centre column and is a percentage of the
            SCREEN, so a panel shorter than that gets a face taller than itself and
            every row beneath it - the name, the line, the answers - is pushed out of
            the panel entirely. A small panel passes its own height here. Sizing it is
            the console's call because only the console knows how much room it gave.
    
    Returns:
        str | None: the form that was built, or None when no hail is open."""
def hail_where_checkbox (client_id=None, style=None, label='Hails'):
    """The placement dial reduced to Off/On, for a ship with ONE console.
    
    A fighter's cockpit is the whole bridge: there is no main screen to send a hail
    to and no second officer to disagree with, so three of the drop-down's four
    entries name places that do not exist. Ticked means "show incoming calls here",
    which is `console` placement - the same value the drop-down writes, through the
    same `hail_where_set`, so the two controls are interchangeable and a ship that
    grows a main screen later can swap back with no state to migrate.
    
    Returns:
        the checkbox layout item, or None when this console cannot place a hail."""
def hail_where_dropdown (client_id=None, style=None):
    """The placement dial: Off / This Console / Main Screen / Both.
    
    Deliberately the same shape as the science console's On-Screen drop-down, and it
    sits in the same place - beside that console's Follow checkbox. The whole dial is
    one call because the change handler lives here: a console that had to write its own
    `on change` would be a console that could disagree with the library about what the
    labels mean.
    
    Returns:
        the drop-down layout item, or None when this console cannot place a hail."""
def icon_names ():
    """Every name that resolves - the built-ins plus the meanings. For lint, for a
    picker, and for anyone wondering what they may ask for."""
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
def overlay_banner (text, color='#fd0', slot='top_banner', to=None, consoles=None, seconds=None, background='#000a', cycle=True, dwell=None, loop=None):
    """Full-width top strip (alert / countdown). Auto-dismiss after ``seconds`` if set.
    Re-call it to update in place (generation-guarded) - a countdown needs no new API.
    
    ``background`` fills the strip (translucent black by default) so the text reads
    over the live view; pass ``None`` for bare text on the view.
    
    **Text too long for the strip is shown in timed parts** rather than clipped:
    it is measured against that client's screen, split into segments that each fit,
    and advanced on a tick.
    
    Args:
        cycle (bool): split-and-cycle when the text does not fit. Default True;
            pass False to let a long line spill/clip as before.
        dwell (float, optional): seconds per part. Default: paced by word count
            (about 2.6 words/second, clamped to 2.5-7s).
        loop (bool, optional): repeat the sequence. Default: loop while the banner
            is sticky (no ``seconds``), play once when it has a lifetime."""
def overlay_choice (title, buttons, to=None, consoles=None, slot='center_hero'):
    """Show a modal choice card and return an awaitable that resolves when a button
    is pressed. Await it from a story/background task (not the target console's own
    gui task); the result's ``.data`` is the chosen label.
    
        result = await overlay_choice("Fire on the ambassador?", ["Yes", "No"], to=player)
        if result.data == "Yes":
            ..."""
def overlay_clear (slot=None, to=None, consoles=None):
    """Clear one slot (or all slots if ``slot`` is None) on the ``to`` targets.
    
    Taking a card down means taking it down, including for anyone who has not
    arrived yet - otherwise the catch-up would put it straight back. But only
    for the consoles actually named: a record the cleared consoles fully account
    for is retired, a wider one keeps running for everybody else."""
def overlay_clear_console (client_id):
    """Clear every overlay this ONE console is carrying - the transition door.
    
    A console that is becoming something else must not arrive with the previous
    screen's furniture still on it. Two things resurrect a leaked card and both
    are handled here: ``OverlayManager`` lives on the PAGE and the page survives
    a reroute, so ``present_all`` re-draws whatever the slots still hold; and the
    catch-up ticker re-shows any live record it finds an empty slot for -
    ``OverlayManager.clear`` sets ``content = None``, which is exactly the
    condition that ticker tests for.
    
    Iterates the page's OWN slots rather than the declared registry: that dict is
    lazily created, so it is precisely the set this console has ever used, where
    the registry carries slots nothing ever raises.
    
    Returns:
        int: how many slots were cleared."""
def overlay_credits (entries, title=None, slot='fullscreen', to=None, consoles=None, seconds=None, roll=None, window=8):
    """Opening/closing credits: a title + a list of lines. Static by default; pass
    ``roll`` (seconds per page) to auto-advance ``window`` lines at a time, clearing
    at the end."""
def overlay_debug_log (path=None):
    """Enable overlay command-stream logging to ``path`` (default: the mission's
    overlay_debug.log). Truncates the file. Pass None-path to disable."""
def overlay_flash (color='#f006', to=None, consoles=None, slot='fullscreen', seconds=0.4):
    """Full-screen color wash (hull hit, jump). Auto-dismisses fast (default 0.4s)."""
def overlay_hero (title, subtitle=None, image=None, face=None, ship=None, icon=None, slot='center_hero', to=None, consoles=None, seconds=None, background=None, letterbox=False, bar=4):
    """Show a big centered hero / chapter card with an optional visual above the
    title (first set wins): ``face`` (a face string), ``ship`` (a ship-type key),
    ``icon`` (an icon index), or ``image`` (an image key). Auto-dismiss after
    ``seconds`` if set.
    
    Args:
        background (str, optional): a colour laid under the card's rows - a scrim,
            so the text stays legible over a bright 3D view. Usually translucent
            (``"#000a"``).
        letterbox (bool | str): also drop cinematic bars on the full-screen slot,
            so one call gives a framed title card. Pass a string to use it as the
            line between the bars. Lifts together with the card when ``seconds``
            is set.
        bar (int): letterbox bar height in em."""
def overlay_hud (rows=None, controls=None, title=None, to=None, consoles=None, slot='hud'):
    """Show a sticky HUD (label/value rows + optional control buttons) over the
    live view. Stays until cleared. Update values with ``overlay_hud_update``.
    
    Args:
        rows: a dict or list of (label, value) pairs.
        controls: list of ``{"label":.., "action": <MAST label | callable>,
            "data":..}`` — rendered as persistent sub-task buttons."""
def overlay_hud_update (rows=None, title=None, to=None, consoles=None, slot='hud'):
    """Cheaply update a live HUD's rows (and/or title). Re-fills the slot region
    out-of-band — no page repaint. Watchers call this only when a displayed value
    actually changes."""
def overlay_kind (kind, to=None, consoles=None, slot=None, seconds=None, **fields):
    """Low-level front door: show any registered ``kind`` with its default slot.
    
    The escape hatch for callers that pick the kind at runtime (the quest driver's
    inline overlay directives, AMD records). Prefer the named wrappers when the
    kind is known at author time."""
def overlay_letterbox (line=None, bar=4, to=None, consoles=None, slot='fullscreen', seconds=None):
    """Cinematic letterbox: black bars top+bottom (``bar`` em each) with an optional
    centered line. Sticky by default; pass ``seconds`` to auto-lift."""
def overlay_lower_third (name, line, slot='lower_third', to=None, consoles=None, seconds=None, background='#000a', cycle=True, dwell=None, loop=None):
    """Bottom name-plate + subtitle line (someone speaking over the live view).
    
    ``background`` fills the strip (translucent black by default) so the text reads
    over whatever is behind it - the same scrim ``overlay_banner``, ``overlay_hero``
    and ``overlay_lower_third_portrait`` already carry. Pass ``None`` for no fill.
    
    A line too long for the plate is shown in **timed parts** rather than clipped -
    which is what subtitles want anyway: the speaker's line arrives in readable
    chunks while their audio plays. See ``overlay_banner`` for ``cycle`` / ``dwell``
    / ``loop``; a lower third defaults to playing through once (``loop=False``)
    because a repeating subtitle reads as a stutter."""
def overlay_lower_third_portrait (name, line, face=None, ship=None, icon=None, image=None, align='left', buttons=None, on_reply=None, slot=None, to=None, consoles=None, seconds=None, color='#8cf', background='#000a', cycle=True, dwell=None, loop=None):
    """Lower third carrying ONE square visual, on the left or the right of the line.
    
    Same strip as ``overlay_lower_third``, plus a portrait. **A conversation is
    this called repeatedly with ``align`` alternating** - the visual moving side
    to side is what reads as a back-and-forth, and only the speaker is on screen.
    
    The visual is always laid out **square** (an image keeps its aspect ratio
    inside that square box), which is what makes the four sources interchangeable:
    the strip, the gutter and the space left for the line do not move when you
    swap a face for a ship.
    
    Args:
        name (str): the speaker's name plate.
        line (str): what they say. Too long for the remaining width and it is
            played in **timed parts** (measured against the strip MINUS the
            square), like ``overlay_lower_third``.
        face (str, optional): a face string - ``get_face(id)`` or a lifeform face.
        ship (str, optional): a ship-type key (e.g. ``"tsn_battle_cruiser"``) -
            a live 3D render.
        icon (str, optional): an icon property string or key.
        image (str, optional): an image key - letterboxed inside the square.
        align (str): ``"left"`` (default) or ``"right"`` - which side the visual
            sits on. Named ``align`` and not ``side`` because a *side* in Cosmos
            is a faction; this is layout only.
        color (str): the name-plate color.
        background (str): fill behind the strip so it reads over the live view;
            pass ``None`` for bare content.
    
    The four are **first set wins**, in ``overlay_hero``'s order (face, ship,
    icon, image). With none set the column is still reserved, so a run of beats
    does not jump sideways when one speaker has no visual.
    
    **Replies are optional.** Pass ``buttons`` and the strip grows a row of them
    below the line, pushed toward the speaker's side, in a taller slot. It then
    returns an awaitable instead of the cycled flag::
    
        reply = await overlay_lower_third_portrait(
            "Harkin", "Do we fire?", face=f, buttons=["Fire", "Hold"], to=player)
        if reply.data == "Fire":
            ...
    
    Pass ``seconds`` and it is a TIMEOUT, not just a dismiss: the card clears and
    the reply resolves with ``data is None``, so an unanswered choice never
    deadlocks the task waiting on it. Without ``seconds`` it waits indefinitely,
    which is right for a beat the story cannot proceed past::
    
        reply = await overlay_lower_third_portrait(..., buttons=[...], seconds=25)
        answer = reply.data or "Hold"      # nobody answered -> the default
    
    From MAST, hold it in a variable if you like - `p = f()` then `r = await p`
    compiles. The one form that does not is a BARE `await p` with nothing
    assigned; assign the result, or await the call.
    
    ``reply.data`` is the label pressed and ``reply.client_id`` is who pressed it,
    which matters as soon as ``to`` covers more than one console: the FIRST press
    wins and the rest are ignored, so the answer is meaningless without knowing
    whose it was.
    
    ``on_reply`` names a signal emitted on the press as well, carrying
    ``{"reply": label, "client_id": id}`` - for a caller with nobody awaiting (a
    declarative AMD hook, a fire-and-forget beat). Handle it in a
    ``//shared/signal`` route if it changes anything: a plain ``//signal`` route
    runs once PER CONSOLE, so five consoles would advance the scene five times.
    
    A **label** handler is deliberately not offered. ``gui_button`` supports one,
    but it is dispatched as a jump on the task that BUILT the widget - which for
    an overlay is the client's own GUI task, so a reply would navigate whatever
    console the player happens to be sitting at. A signal route reaches any label
    without that.
    
    See ``overlay_banner`` for ``cycle`` / ``dwell`` / ``loop``."""
def overlay_register (kind, builder):
    """Register a content builder for an overlay ``kind``.
    
    Args:
        kind (str): the ``kind`` value callers pass to ``overlay_show``.
        builder (callable): ``builder(client_id, content)`` — content is the dict
            passed to ``overlay_show`` (with ``kind`` included). Build widgets with
            the normal ``gui_*`` functions."""
def overlay_register_label (kind, label):
    """Register a MAST **label** as the builder for ``kind`` — the MAST-native way to
    author a custom overlay card without a Python builder.
    
    The label builds the card with the usual ``gui_*`` verbs and ends (``->END``);
    the content fields passed to ``overlay_show`` arrive as task variables. It is
    re-run on every repaint, so keep it **build-only** (no ``await``, no state
    changes). Reference the label by name from top-level MAST::
    
        === my_hero_card
            gui_row("row-height: content;")
            gui_text(f"$text:{gui_text_escape(title)};justify:center;font:gui-6")
            ->END
    
        overlay_register_label("my_hero", my_hero_card)
        # then anywhere: overlay_show("center_hero", "my_hero", title="CHAPTER TWO")"""
def overlay_show (slot, kind, to=None, consoles=None, **content):
    """Show an overlay in ``slot`` using content builder ``kind``.
    
    Args:
        slot (str): a slot name (see ``OVERLAY_SLOTS``); unknown names use a
            centered default rect.
        kind (str): a registered builder (see ``overlay_register``).
        to: the audience — ``None`` = the current console; a client id; a **ship**
            (its consoles); a **side** key/agent (that side's consoles); or a set /
            role query mixing them. See ``consoles_of``.
        consoles (str, optional): narrow the audience to consoles with these roles,
            e.g. ``"mainscreen"``.
        **content: fields passed through to the builder.
    
    A console that joins the audience while this is still up gets it too — see
    the late-joiner note above. ``to=None`` means "the console calling", which has
    no audience to join, so it is not tracked."""
def overlay_signal_clear (to=None, slot=None):
    """Signal-route forwarder for clear."""
def overlay_signal_show (to, slot, kind, fields=None):
    """Signal-route forwarder: overlay_show with content supplied as a dict."""
def overlay_slot_define (slot, rect, draw_layer=28000, input='passthrough'):
    """Define or override a slot's default rect / draw_layer / input mode."""
def overlay_toast (text, icon=None, seconds=3, to=None, consoles=None, slot='corner_toast', color=None, category=None, severity=None):
    """Notify the crew. RETIRED as an overlay -- writes to the ship's log instead.
    
    The line appears immediately in the ambient strip on every console of the addressed
    ship, and stays in the log tab afterwards. ``icon``, ``seconds`` and ``slot`` are
    accepted and ignored: they described a transient corner card that no longer exists,
    and removing them would break every existing caller for no gain.
    
    Args:
        color (str, optional): line color; defaults to the category's.
        category (str, optional): which log tab -- ``ship`` or ``mission``. Everything
            shows in ``log`` regardless.
        severity (str, optional): ``tip`` | ``warning`` | ``danger``. A warning or danger
            line renders as a callout and raises the log tab."""
def rundown_add (name, subject, lens=None, move=None, seconds=4, ease='in_out', label=None, overlay=None, framing=None, yaw=None, pitch=None):
    """Add (or replace) a shot in the rundown.
    
    Args:
        name (str): how the director refers to it.
        subject: what the shot looks at - and necessarily what the lens rides.
        framing: a named size (``close``/``medium``/``wide``), or two for a move.
            PREFERRED over lens/move - the distance is taken from the subject own
            hull, so one shot frames a runabout and a starbase alike.
        lens: world position for a static shot.
        move: ``[from, to]`` world positions for a moving one.
        seconds (float): duration of a ``move`` (a static shot holds until punched away).
        label (str, optional): what the director's tile says. Defaults to ``name``.
        overlay (dict, optional): furniture to show with it, ``{"kind": ..., ...}``.
    
    Returns:
        dict: the stored shot."""
def rundown_clear ():
    """Empty the rundown and both desks."""
def rundown_excitement (name):
    """How interesting this shot's subject is right now.
    
    Reads the engine's own ``exciting`` value - the same notion its automatic
    cinematic camera follows - so a suggestion agrees with what the engine would
    have picked, rather than being a second opinion invented here."""
def rundown_get (name):
    ...
def rundown_live ():
    """The name of the shot on PROGRAM, or None. This is the tally."""
def rundown_preview (to=None, consoles=None):
    """Set (or read) the PREVIEW audience - the director's own console."""
def rundown_program (to=None, consoles=None):
    """Set (or read) the PROGRAM audience - the feed everyone sees.
    
    Naming the audience is also where each console's own ship is recorded, so the
    desk can give it back at release. Captured HERE rather than at the first punch
    because by then a shot has already reassigned somebody."""
def rundown_punch (name, flash=False):
    """Put a shot on PROGRAM. Returns True if it went live.
    
    A cut, because the engine only cuts. ``flash`` fakes a transition with a
    one-frame flash overlay - the only "effect" available, and it is honest about
    being a fake rather than pretending to dissolve."""
def rundown_release ():
    """Hand PROGRAM back to the engine's own director and clear the tally.
    
    The end-of-show path - and the one to call BEFORE deleting anything a shot was
    riding, since a deleted dolly drops the view to the engine default."""
def rundown_remove (name):
    """Drop a shot. If it was live, the tally is cleared - the feed does not change,
    because pulling a shot out of a list is not a directing decision."""
def rundown_shots ():
    """Every shot, in rundown order."""
def rundown_stage (name):
    """Line a shot up on PREVIEW without touching PROGRAM. Returns True if staged."""
def rundown_staged ():
    """The name of the shot on PREVIEW, or None."""
def rundown_suggest (exclude_live=True):
    """The shot worth punching to, or None. **Assist, never autopilot.**
    
    Args:
        exclude_live (bool): skip whatever is already live, since suggesting the
            shot the director is already on is noise."""
def rundown_take (flash=False):
    """Punch what is on PREVIEW. The broadcast take. Returns the name, or None."""
def rundown_tiles ():
    """Everything a director's console needs to draw the rundown.
    
    A list of ``{name, label, live, staged, suggested, excitement}`` in rundown
    order. Returned as DATA so the console is a mission's to design - this layer
    has no opinion about what a tile looks like."""
def viewscreen_apply (ship):
    """Make the engine match the recorded state. Safe to call repeatedly.
    
    This is the one place that touches cameras, so a console that connects late, a
    repaint, or a fresh ``viewscreen_set`` all arrive at the same behavior by calling it.
    
    Returns:
        int: how many consoles the shot is running on."""
def viewscreen_baseline (ship):
    """The ``(view, facing, mode)`` the crew had before anyone took the screen."""
def viewscreen_baseline_drop (ship):
    """Forget the baseline without restoring it.
    
    What a helm takeover does: helm's choice IS the new state, so there is nothing
    to go back to and leaving a stale baseline recorded would let a later,
    unrelated release put the crew's screen somewhere they left minutes ago."""
def viewscreen_bump (ship):
    """Advance the sequence. Call BEFORE the outcome, never after."""
def viewscreen_claim (ship, tier='console', owner=None, baseline=None, cids=None):
    """Record that ``owner`` holds this ship's main screen.
    
    Bookkeeping only - it does not move a camera or write a main-screen view. The
    caller (``viewscreen_set``, a cutscene, the Director) does that; this decides
    whether it is allowed to and remembers what to go back to.
    
    Args:
        ship: the player ship whose screen this is.
        tier (str): ``"console"`` or ``"story"``.
        owner (str, optional): the token from ``viewscreen_owner_token``. An
            unnamed claim is still a claim.
        baseline (tuple, optional): the ``(view, facing, mode)`` to record if this
            is the first claim. Captured by the caller because only it can read the
            engine state.
        cids (iterable, optional): the main screens whose home ship the caller has
            recorded, noted alongside the baseline on the first claim.
    
    Returns:
        bool: True if the claim was taken. False when a STORY claim holds and this
        is a console one - the caller should park its request rather than act."""
def viewscreen_claim_drop (ship, owner=None, keep_baseline=False):
    """Give up the claim. Bookkeeping only - see ``viewscreen_restore``.
    
    Args:
        owner (str, optional): refuse unless this token still holds it. ``None``
            forces, which is what a mission reset and the one-door console
            transition want.
        keep_baseline (bool): leave the baseline recorded. Only ``True`` while a
            caller is in the middle of applying it.
    
    Returns:
        bool: True if a claim was dropped."""
def viewscreen_claimed (ship):
    """Whether anything holds this ship's main screen."""
def viewscreen_clear (ship, owner=None):
    """Hand the screen back, restoring the view the crew had before it was taken.
    
    Args:
        owner (str, optional): refuse unless this token still holds the claim, so
            a console whose shot was replaced cannot take the screen off whoever
            replaced it. ``None`` forces.
    
    Returns:
        bool: True if a viewer was running."""
def viewscreen_consoles (ship):
    """The main-screen consoles of one ship - the audience every shot addresses.
    
    Narrowed to the SHIP's own screens, which is what keeps one bridge's viewer out of
    another's. Returns an empty set when no main screen is connected, which is normal
    and not an error."""
def viewscreen_effective_state (ship):
    """What this ship's main screen is ACTUALLY set to, after arbitration.
    
    ``handlerhooks`` writes the crew's triple, then asks
    ``viewscreen_helm_override`` what to do with it, and then fans a reroute out to
    the ship's main screens carrying the EVENT's values as task variables. When a
    story claim refused the press, those values are the rejected ones - so the
    reroute has to carry this instead, or a console reading the injected
    ``MAIN_SCREEN_VIEW`` sees a view the library declined to apply.
    
    LegendaryMissions reads the ship's inventory rather than the injected variable,
    so LM would not show this - which is exactly what makes it easy to ship broken."""
def viewscreen_framing (subject):
    """``(near, far)`` lens distances for a subject.
    
    Scaled off the hull's own size, so a starbase and a fighter both fill the frame
    rather than one being a speck and the other clipping the lens. ``exclusion_radius``
    is the only size the engine actually exposes; when it says nothing, a default that
    frames a mid-sized ship is better than a guess that frames nothing."""
def viewscreen_held (ship):
    """The crew request parked behind a story claim, or None."""
def viewscreen_helm_override (ship, view, facing, mode):
    """Helm or weapons touched the engine's main-screen control.
    
    Called from the ``main_screen_change`` handler with the triple the engine just
    reported. What happens next depends on WHO holds the screen:
    
    * **A console claim** - science's "on screen", weapons', docking's - stands
      down, and nothing is restored: helm's choice IS the new state, and putting a
      recorded "before" back over the top would undo the very change being handled.
      Any request parked behind a story beat is thrown away too; helm just spoke,
      and a stale drop-down pick firing later would override the officer who
      overrode it.
    * **A story claim** - a cutscene, a hail, a mission beat - does NOT stand down.
      The crew's press is PARKED and applied when the story releases, so it is
      honored a few seconds late rather than lost, and the story's own triple is
      written back so the engine and the record agree again.
    
    A triple identical to what the claim asked for is not a takeover either way: a
    console reconnecting replays the state it is already in.
    
    The triple is written here as well as by the caller. ``handlerhooks`` already
    records it (issue #595) and writing it twice is harmless - but a function whose
    postcondition depends on the caller having gone first is a trap for the next
    caller, so this one leaves the ship in the state it was told about either way.
    On the story path that means writing the story's triple BACK over what the
    caller just recorded, which is the whole point.
    
    Returns:
        bool: True if a claim was stood down. False for a story claim that held -
        see ``viewscreen_effective_state`` for what the screen is actually showing
        afterwards, which is what the reroute has to carry."""
def viewscreen_hold (ship, request):
    """Park a crew request that arrived while a story held the screen.
    
    ONE request, not a queue: the crew pressing three things during a cutscene
    means they want the last one, and replaying all three on release would walk the
    screen through states nobody asked to see."""
def viewscreen_hold_drop (ship):
    """Throw the parked request away.
    
    What helm's control does on a console-tier claim: helm just spoke, and a stale
    drop-down pick firing later would override the officer who overrode it."""
def viewscreen_hold_take (ship):
    """Take the parked request, clearing it. Returns None when there is none."""
def viewscreen_home_ship (client_id):
    """The ship a console BELONGS to, even while a shot has it assigned elsewhere.
    
    Anything that means "this console's own ship" must ask this rather than
    ``sbs.get_ship_of_client``, which during a shot answers with the subject."""
def viewscreen_hull_percent (subject):
    """Remaining hull as 0-100, summed over the four ship systems.
    
    NOTE: LM's ``results_helpers.py`` carries the same formula for the end-game screen.
    Two copies of "what does damaged mean" is one too many - when phase 5 touches LM,
    promote one of them and delete the other."""
def viewscreen_is_live (ship):
    """Whether a console is currently driving this ship's main screen."""
def viewscreen_label_for (mode):
    """The drop-down label for a mode, so a repaint re-selects what is running."""
def viewscreen_mode (ship):
    """The shot this ship's main screen is running, or ``"off"``."""
def viewscreen_mode_for (label):
    """The mode a drop-down label means. Unknown labels read as ``off`` - a console
    showing something we do not recognize must not leave the screen commandeered."""
def viewscreen_owner (ship):
    """Who holds this ship's main screen, or ``""``."""
def viewscreen_owner_token (kind, client_id=None):
    """The owner token for a claimant.
    
    Per-CONSOLE for anything a crew member drives (``science``, ``weapons``), bare
    for anything the ship has one of (``hail``, ``docking``). Two science consoles
    on one bridge are two different claimants; one bridge has only one docking."""
def viewscreen_owns (ship, owner):
    """Is ``owner``'s claim still the live one?
    
    The question a console should ask before acting on the screen it thinks it is
    driving. LegendaryMissions' weapons console hand-rolled this as a private
    ``WEAP_VIEWER_SUBJECT`` inventory value, and science never asked at all - which
    is why science re-pointing on a new selection used to yank a shot weapons had
    set up."""
def viewscreen_page_names ():
    """Every registered page name, in display order."""
def viewscreen_page_register (name, fn, order=50):
    """Register a data page.
    
    Args:
        name (str): identifies the page (``"vitals"``, ``"cargo"``, ...). Re-registering
            a name REPLACES it, which is how a mission overrides a built-in.
        fn (callable): ``fn(subject_id, ship_id)`` -> markdown, or None for "nothing to
            say about this subject".
        order (int): sort key. The built-ins leave gaps so a mission can slot between."""
def viewscreen_page_remove (name):
    """Drop a page (including a built-in a mission does not want)."""
def viewscreen_pages (subject, ship):
    """``[(name, markdown), ...]`` for this subject - empty pages dropped.
    
    A page that raises is skipped rather than taking the column down with it: one
    mission page with a bad key must not blank the whole viewer."""
def viewscreen_relative_bearing (subject, ship):
    """Bearing of ``subject`` from ``ship``: 0 is dead ahead, degrees clockwise.
    
    The convention is the engine's own, taken from the forward/right vectors rather
    than assumed from an axis - the same maths the damage-facing code uses. Returns
    None when either object (or its heading) is unavailable, because a bearing that is
    quietly 90 degrees out is worse than no bearing."""
def viewscreen_reset ():
    """Drop every running shot WITHOUT touching the engine - for mission reset.
    
    The tick tasks are already gone by then (``TickDispatcher.clear()``), and the
    clients these records name belong to a sim that is being torn down, so re-assigning
    their cameras is at best pointless. This just stops the records outliving the
    mission that made them."""
def viewscreen_restore (ship, owner=None):
    """THE DOOR HOME. Put this ship's main screen back the way the crew had it.
    
    Drops the claim, stops the shot, takes the viewer's own overlays down, gives
    every main screen its own ship back, restores the baseline view, and then -
    and only then - applies whatever crew request was parked behind a story beat.
    
    The ORDER is load-bearing, twice:
    
    * **Assignments before the triple.** The assignment decides what a console can
      SEE; the triple only decides its widget list. Restore the triple first and
      the main-screen label re-runs while the console is still riding the subject,
      so it picks its widgets from the SUBJECT's ``MAIN_SCREEN_VIEW`` - the hazard
      ``gui_console`` documents.
    * **The parked request last.** Applying it claims the screen again and
      captures a baseline; it has to capture the RESTORED one, not the story's.
    
    Args:
        owner (str, optional): refuse unless this token still holds the claim.
            ``None`` forces - what a console transition and a reset want.
    
    Returns:
        bool: True if anything was holding the screen."""
def viewscreen_roster (ship):
    """The main screens that have a home recorded for this claim.
    
    Held on the SHIP while the home VALUE is held on each console, and that split
    is deliberate: ``viewscreen_home_ship(client_id)`` has only a client id, so the
    value has to be reachable from one - but a restore has to reach consoles that
    have since stopped being this ship's main screens, so the membership has to
    live somewhere that outlives the role."""
def viewscreen_roster_add (ship, client_id):
    """Note that this console has a home recorded - the late-joiner path."""
def viewscreen_seq (ship):
    """The claim sequence, bumped on every claim and every release.
    
    Poll it to notice the screen changed hands. Bumped BEFORE the outcome runs, the
    same rule ``hail.py`` follows, so a second actor in the same frame is already
    carrying a stale value by the time it arrives."""
def viewscreen_set (ship, mode, subject=None, owner=None, tier='console'):
    """Point this ship's main screen at something.
    
    Args:
        ship (Agent | int): the player ship whose screen this is.
        mode (str): one of ``MODES``. ``"off"`` is the same as ``viewscreen_clear``.
        subject (Agent | int, optional): what the shot is about - normally the science
            selection. ``None`` means no subject.
        owner (str, optional): the claim token, from ``viewscreen_owner_token``.
            Without one the claim is anonymous - still a claim, but nothing can
            ask whether it is still theirs.
        tier (str): ``"console"`` (the default - a crew member's pick) or
            ``"story"`` (a cutscene, a hail, a mission beat).
    
    Returns:
        bool: True when the state changed.
    
    **False now means two things.** It has always meant "already showing exactly
    that"; it also means "a STORY claim holds the screen, so your request was
    PARKED and will be applied when the story releases". Ask
    ``viewscreen_owns(ship, owner)`` when you need to know which - that is the
    question a console actually has."""
def viewscreen_shot_props (current=None):
    """The whole property string for a shot drop-down.
    
    The list key is ``list:``, NOT ``items:`` - a dropdown built with the wrong key has
    no options to render and the engine dies allocating for it (`MemoryError: bad
    allocation`), which does not look like a typo from the outside. ``text:`` is the
    label shown while it is closed, so pass what is currently running."""
def viewscreen_subject (ship):
    """The id the shot is about, or 0."""
def viewscreen_take (ship, owner=None, tier='story'):
    """Claim this ship's main screen WITHOUT starting one of the viewer's own shots.
    
    For anything that drives the screen its own way and still has to be arbitrated:
    a cutscene, the Director, a mission beat pointing the camera by hand. It records
    the crew's view and every main screen's home ship the same way ``viewscreen_set``
    does, so ``viewscreen_restore`` puts the bridge back afterwards - which is what
    a cutscene played during a science shot could not do before, because the only
    thing that captured a baseline was a shot starting.
    
    Returns:
        bool: False when a story claim already holds the screen and this is a
        console-tier request."""
def viewscreen_tier (ship):
    """``"console"``, ``"story"``, or ``""`` when nothing holds the screen."""
