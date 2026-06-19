from sbs_utils.agent import Agent
from sbs_utils.mast_sbs.story_nodes.button import Button
from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.mast.mastscheduler import ChangeRuntimeNode
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.garbagecollector import GarbageCollector
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.mast.pollresults import PollResults
from sbs_utils.futures import Promise
def AWAIT (promise: sbs_utils.futures.Promise) -> sbs_utils.futures.PromiseWaiter:
    """Wrap a promise in a non-blocking waiter.
    
    Returns a ``PromiseWaiter`` whose ``done()`` method can be polled each tick
    without suspending the current task.
    
    Args:
        promise (Promise): The promise to wait on.
    
    Returns:
        PromiseWaiter: A waiter that reports completion without blocking."""
def _comms_get_colors (to_obj, from_obj, is_receive, title_color, color):
    ...
def _comms_get_origin_id () -> int:
    ...
def _comms_get_selected_id () -> int:
    ...
def awaitable (func):
    ...
def comms (path=None, buttons=None, timeout=None) -> sbs_utils.procedural.comms.CommsPromise:
    """Suspend the current task and present comms buttons, waiting for a choice.
    
    Must be called from a server task (``client_id == 0``). The task resumes
    when a comms button is pressed or ``timeout`` resolves. The
    ``//comms/path`` route hierarchy controls which buttons appear.
    
    Args:
        path (str | None, optional): Initial comms path. Defaults to
            ``"comms"`` (root).
        buttons (dict | None, optional): Inline button definitions as
            ``{"button label": label_to_run, ...}``. Buttons are sticky
            (equivalent to ``+`` buttons in MAST). Defaults to None.
        timeout (Promise | None, optional): A promise that ends the comms
            interaction when it resolves (e.g. from ``delay_promise``).
            Defaults to None (no timeout).
    
    Returns:
        CommsPromise: Resolves when a button is selected or timeout fires.
    
    Example:
        await comms()
        await comms(timeout=delay_promise(seconds=30))"""
def comms_add_button (message, label=None, color=None, data=None, path=None) -> None:
    """Add a button to the currently active comms panel at runtime.
    
    Injects a sticky button into the comms button list of whichever
    ``ButtonPromise`` is currently navigating. Call this from inside a
    ``//comms/`` route to add dynamic buttons beyond those defined statically.
    
    Args:
        message (str): Button label text.
        label (label | None, optional): MAST label to run when pressed.
            Defaults to None.
        color (str | None, optional): Button text color. Defaults to None
            (inherits the comms default).
        data (dict | None, optional): Variables passed to the button handler.
            Defaults to None.
        path (str | None, optional): Comms sub-path to restrict the button
            to. Defaults to None (shown at the current path).
    
    Example:
        //comms/patrol
            comms_add_button("Retreat", retreat_label, color="yellow")"""
def comms_broadcast (ids_or_obj, msg, color=None) -> None:
    """Send a text message to the text waterfall of one or more targets.
    
    Accepts player ship IDs or client/console IDs. Ship IDs use
    ``send_message_to_player_ship``; client IDs use
    ``send_message_to_client``.
    
    Args:
        ids_or_obj: Agent ID, client ID, or set/list of either to send to.
            Pass ``None`` to send to the event's ``parent_id``.
        msg (str): The message text. Supports ``{var}`` interpolation.
        color (str, optional): Text color as a name or hex string, e.g.
            ``"red"`` or ``"#3ff"``. Defaults to ``"#fff"``.
    
    Example:
        comms_broadcast(SHIP_ID, "Red alert!", color="red")"""
def comms_info (name, face=None, color=None) -> None:
    """Update the comms selection info panel with a name and portrait.
    
    Sets the name and face shown in the comms console's selection panel for
    the current origin/selected ship pair. Use this from a ``//comms/`` route
    to customise what the player sees before pressing buttons.
    
    Args:
        name (str): Display name to show in the info panel.
        face (str, optional): Face asset string for the portrait. Defaults to
            the face registered for the selected object.
        color (str, optional): Text color. Defaults to ``"white"``.
    
    Example:
        comms_info("Commander Karn", face="crew/karn", color="red")"""
def comms_info_face_override (face=None) -> None:
    """Override the face portrait shown in the comms panel for this interaction.
    
    Sets a one-time face override on the current ``ButtonPromise``. The
    override applies until the player selects a different comms target or the
    interaction ends.
    
    Args:
        face (str | None, optional): Face asset string to show, or ``None``
            to clear any existing override and revert to the default.
    
    Example:
        comms_info_face_override("crew/commander")"""
def comms_message (msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color=None, title_color=None, is_receive=True, from_name=None) -> None:
    """Send a comms message with explicit sender and receiver control.
    
    Lower-level function used by ``comms_transmit`` and ``comms_receive``.
    Handles lifeforms, side colors, ``CommsOverride``, and emits the
    ``comms_message`` signal. Prefer ``comms_transmit`` or ``comms_receive``
    unless you need direct sender/receiver control.
    
    Args:
        msg (str): The message body text. Supports ``{var}`` interpolation.
        from_ids_or_obj: Sender agent ID(s) or object(s).
        to_ids_or_obj: Receiver agent ID(s) or object(s). Pass ``None`` to
            send the message to the sender (internal communication).
        title (str, optional): Title bar text. Defaults to the sender's
            comms ID.
        face (str, optional): Face asset string for the sender portrait.
            Defaults to the face registered for the sender.
        color (str, optional): Body text color. Defaults to ``"#fff"``.
        title_color (str, optional): Title text color. Defaults to the
            sender's side color.
        is_receive (bool, optional): ``True`` = message is received (``< <``
            prefix); ``False`` = message is sent (``> >`` prefix). Defaults
            to ``True``.
        from_name (str, optional): Override the display name of the sender.
            Defaults to None (uses the sender object's ``comms_id``).
    
    Example:
        comms_message("Incoming!", ENEMY_ID, SHIP_ID, title="Commander")"""
def comms_navigate (path, face=None, comms_badge=None) -> None:
    """Navigate the current comms interaction to a different button path.
    
    Changes which ``//comms/`` route sub-path is active, updating the buttons
    shown to the player. Call this from inside a comms button handler to
    implement multi-level comms menus.
    
    Args:
        path (str): Target comms sub-path, e.g. ``"patrol"`` (expanded to
            ``//comms/patrol``). Pass ``None`` or ``""`` to reset to the root.
        face (str | None, optional): Face override to apply when navigating.
            Defaults to None (keep current face).
        comms_badge (object | None, optional): Lifeform or ID to associate
            as the comms badge on the new path. Defaults to None.
    
    Example:
        //comms
            + "Talk to Commander"
                comms_navigate("commander")
        //comms/commander
            + "Order attack"
                comms_receive("Attack formation!", title="Commander")"""
def comms_navigate_override (ids_or_obj, sel_ids_or_obj, path=None, path_must_match=True) -> None:
    """Navigate a comms interaction from outside the comms task.
    
    Refreshes the buttons shown for the specified origin/selected pair. Use
    this when the story needs to update comms buttons from a non-comms task
    (e.g. a timer or event handler). If the pair is currently selected, the
    new buttons appear immediately.
    
    Args:
        ids_or_obj: Player ship ID(s) or object(s) (origin side).
        sel_ids_or_obj: Target ID(s) or object(s) (selected side).
        path (str | None, optional): Comms sub-path to navigate to. Defaults
            to None (reuses the current path of the active interaction).
        path_must_match (bool, optional): Only navigate if the active path
            already matches ``path``, avoiding disorienting mid-menu jumps.
            Defaults to ``True``.
    
    Example:
        comms_navigate_override(SHIP_ID, ENEMY_ID, "commander/angry")"""
def comms_override (origin_id=None, selected_id=None, face=None, from_name=None):
    """Create a context manager to override comms sender/receiver fields.
    
    Use as a ``with`` block to temporarily redirect comms calls
    (``comms_transmit``, ``comms_receive``, etc.) to specific IDs or a fixed
    face/name without changing the underlying event.
    
    Args:
        origin_id (int | None, optional): Override the origin (player ship)
            ID. Accepts any form accepted by ``to_set``. Defaults to None.
        selected_id (int | None, optional): Override the selected (target) ID.
            Defaults to None.
        face (str | None, optional): Override the face asset string. Defaults
            to None.
        from_name (str | None, optional): Override the sender display name.
            Defaults to None.
    
    Returns:
        CommsOverride: A context manager; use with ``with``.
    
    Example:
        with comms_override(origin_id=SHIP_ID, selected_id=ENEMY_ID):
            comms_receive("Surrender or be destroyed.", title="Klingon")"""
def comms_receive (msg, title=None, face=None, color=None, title_color=None) -> None:
    """Receive a comms message on a player ship from the selected target.
    
    Reads origin and selected IDs from the current event context (or
    ``COMMS_ORIGIN_ID``/``COMMS_SELECTED_ID`` task variables). Sends the
    message with a ``< <`` prefix indicating an incoming transmission.
    
    Args:
        msg (str): The message body text. Supports ``{var}`` interpolation.
        title (str, optional): Title bar text. Defaults to the sender's
            comms ID.
        face (str, optional): Face asset string for the portrait. Defaults to
            the face registered for the sender.
        color (str, optional): Body text color. Defaults to ``"#fff"``.
        title_color (str, optional): Title text color. Defaults to the
            sender's side color.
    
    Example:
        comms_receive("Docking clearance granted.", title="Station")"""
def comms_receive_internal (msg, ids_or_obj=None, from_name=None, title=None, face=None, color=None, title_color=None) -> None:
    """Receive an internal crew comms message (ship talking to itself).
    
    Sends a message where both sender and receiver are the same ship, used for
    incoming internal crew messages (e.g. engineering to bridge). The ship is
    read from the event context or from ``ids_or_obj``.
    
    Args:
        msg (str): The message body text. Supports ``{var}`` interpolation.
        ids_or_obj: Agent ID(s) or object(s) of the receiving ship. Defaults
            to the origin ship from the current event context.
        from_name (str, optional): Name of the internal sender (e.g.
            ``"Engineering"``). Used to look up a registered face via
            ``face_Engineering`` inventory key. Defaults to the ship's name.
        title (str, optional): Title bar text. Defaults to None.
        face (str, optional): Face asset string for the portrait. Defaults to
            the face registered for ``from_name``.
        color (str, optional): Body text color. Defaults to ``"#fff"``.
        title_color (str, optional): Title text color. Defaults to None.
    
    Example:
        comms_receive_internal("Power restored.", from_name="Engineering")"""
def comms_set_2dview_focus (client_id, focus_id=0, EVENT=None):
    """Set the 2D radar view to follow an alternate ship for a comms client.
    
    Stores ``focus_id`` as the alternate ship to track on the 2D radar for
    both the client and its assigned ship. The view only actually updates if
    the ``2d_follow`` inventory flag is set on the client.
    
    Args:
        client_id (int): The client whose radar should be updated.
        focus_id (int, optional): ID of the ship to track, or ``0`` to reset
            to the client's own ship. Defaults to 0.
        EVENT: Unused; present for route-handler compatibility.
    
    Example:
        comms_set_2dview_focus(CLIENT_ID, ENEMY_ID)"""
def comms_speech_bubble (msg, seconds=3, color=None, client_id=None, selected_id=None) -> None:
    """Display a speech bubble attached to the currently selected space object.
    
    Attaches a timed text bubble to the selected object on the client's 2D
    radar. The client and selected object are read from the current event
    context — ``client_id`` and ``selected_id`` parameters are accepted but
    currently overridden by the event.
    
    Args:
        msg (str): Text to display in the speech bubble.
        seconds (float, optional): Duration the bubble is shown. Pass ``0``
            for a permanent bubble. Defaults to 3.
        color (str, optional): Text color as a name or hex string. Defaults
            to ``"#fff"``.
        client_id (int | None, optional): Currently unused; read from event.
        selected_id (int | None, optional): Currently unused; read from event.
    
    Example:
        comms_speech_bubble("Curse you, Terran!", seconds=5)"""
def comms_story_buttons (ids, sel_ids, buttons, path, nav_button=None) -> sbs_utils.procedural.comms.CommsChoiceButtonPromise:
    """Inject story-controlled buttons into active comms interactions and wait for a choice.
    
    Attaches a ``CommsChoiceButtonPromise`` to every active comms task that
    matches the given origin/selected pairs. The buttons appear at ``path``
    and disappear when one is pressed. An optional ``nav_button`` adds a
    navigation button at the parent path to enter this sub-menu.
    
    Args:
        ids: Player ship ID(s) or object(s) (origin side).
        sel_ids: Target ID(s) or object(s) (selected side).
        buttons (list[str]): Button label strings to present.
        path (str): Comms path where the buttons appear, e.g.
            ``"comms/rescue"``.
        nav_button (str | None, optional): Label for a navigation button
            shown at the parent path that leads to ``path``. Defaults to
            None (no nav button).
    
    Returns:
        CommsChoiceButtonPromise: Resolves with the pressed button label.
    
    Example:
        result = await comms_story_buttons(
            SHIP_ID, ENEMY_ID,
            ["Accept surrender", "Reject"],
            "comms/surrender",
            nav_button="Discuss surrender"
        )"""
def comms_transmit (msg, title=None, face=None, color=None, title_color=None) -> None:
    """Transmit a comms message from the player ship to the selected target.
    
    Reads origin and selected IDs from the current event context (or
    ``COMMS_ORIGIN_ID``/``COMMS_SELECTED_ID`` task variables). Sends the
    message with a ``> >`` prefix indicating an outgoing transmission.
    
    Args:
        msg (str): The message body text. Supports ``{var}`` interpolation.
        title (str, optional): Title bar text. Defaults to the sender's
            comms ID.
        face (str, optional): Face asset string for the portrait. Defaults to
            the face registered for the sender.
        color (str, optional): Body text color. Defaults to ``"#fff"``.
        title_color (str, optional): Title text color. Defaults to the
            sender's side color.
    
    Example:
        comms_transmit("Requesting docking clearance.", title="Artemis")"""
def comms_transmit_internal (msg, ids_or_obj=None, to_name=None, title=None, face=None, color=None, title_color=None) -> None:
    """Transmit an internal crew comms message (ship talking to itself).
    
    Sends a message where both sender and receiver are the same ship, used for
    internal crew communications (e.g. bridge to engineering). The origin ship
    is read from the current event context.
    
    Args:
        msg (str): The message body text. Supports ``{var}`` interpolation.
        ids_or_obj: Unused — origin ship is always read from the event.
        to_name (str, optional): Name of the internal recipient (e.g.
            ``"Engineering"``). Used to look up a registered face via
            ``face_Engineering`` inventory key. Defaults to the ship's name.
        title (str, optional): Title bar text. Defaults to None.
        face (str, optional): Face asset string for the portrait. Defaults to
            the face registered for ``to_name``.
        color (str, optional): Body text color. Defaults to ``"#fff"``.
        title_color (str, optional): Title text color. Defaults to None.
    
    Example:
        comms_transmit_internal("Shields holding.", to_name="Engineering")"""
def create_comms_label ():
    ...
def create_grid_comms_label ():
    ...
def get_comms_selection (id_or_not):
    """Return the ID of the object currently selected on the comms console.
    
    Args:
        id_or_not (Agent | int): The player ship agent ID or object.
    
    Returns:
        int | None: The selected agent ID, or ``None`` if unavailable."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
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
def has_role (so, role):
    """Return whether an agent currently holds a given role.
    
    Args:
        so (Agent | int): Agent ID or object.
        role (str): The role name to test for.
    
    Returns:
        bool: ``True`` if the agent has the role."""
def labels_get_type (label_type):
    """Return all labels whose type or path starts with the given prefix.
    
    Walks every label in the current story, checking the ``type`` metadata key
    first, then the label ``path`` attribute, then the label name.
    
    Args:
        label_type (str): Prefix to match, e.g. ``"map/"`` or ``"media/"``.
    
    Returns:
        list[MastNode]: Matching label objects."""
def science_is_unknown (origin, target) -> bool:
    """Return ``True`` if the target has not been scanned by the scanning ship.
    
    Checks the ``"scan"`` tab. Use ``science_has_scan_data`` to check a
    different tab.
    
    Args:
        origin (int | Agent): The scanning player ship.
        target (int | Agent): The object to check.
    
    Returns:
        bool: ``True`` if the target is unscanned or shows default/empty data."""
def set_inventory_value (so, key: str, value):
    """Set an inventory value on one or more agents.
    
    If ``so`` is a set or collection, every member receives the value.
    
    Args:
        so (Agent | int | set[Agent | int]): The agent(s) to update.
        key (str): The inventory key.
        value (any): The value to store."""
def side_get_side_color (key_or_id, default='#0F0') -> str:
    """Return the icon color assigned to a side.
    
    Args:
        key_or_id (str | int | Agent): Side key, agent ID, or object.
        default (str, optional): Color to return if the side has no color set.
            Defaults to ``"#0F0"`` (green).
    
    Returns:
        str: The hex color code assigned to the side, or ``default``."""
def signal_emit (name, data=None):
    """Emit a named signal, running all registered ``//signal/<name>`` routes.
    
    Safe to call when no MAST context is active — returns immediately with no
    side effects.
    
    Args:
        name (str): The signal name.
        data (dict, optional): Arbitrary data passed to each signal handler.
            Defaults to None."""
def start_comms_common_selected (event, is_grid):
    ...
def start_comms_selected (event):
    ...
def start_grid_comms_selected (event):
    ...
def task_all (*args, **kwargs) -> sbs_utils.procedural.execution.TaskPromiseAllAny:
    """Schedule a task for each label and wait until all tasks complete.
    
    Args:
        *args (label): Labels to schedule as parallel tasks.
        data (dict, optional): Keyword argument passed as initial variables to
            every task. Defaults to None.
        sub_tasks (bool, optional): Run as sub-tasks instead of top-level
            tasks. Defaults to False.
    
    Returns:
        TaskPromiseAllAny: A promise that resolves when all tasks complete.
    
    Example:
        await task_all(patrol_alpha, patrol_beta, patrol_gamma)"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
def to_object_list (the_set):
    """Convert a set or list of IDs/agents to a list of Agent objects (excluding None).
    
    Args:
        the_set (set[Agent | int] | list[Agent | int]): IDs or agent objects.
    
    Returns:
        list[Agent]: Resolved Agent objects; items that cannot be resolved are
            excluded."""
class CommsChoiceButtonPromise(Promise):
    """class CommsChoiceButtonPromise"""
    def __init__ (self, buttons, path, nav_button):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def get_buttons (self, path):
        ...
    def set_result (self, result):
        ...
class CommsOverride(object):
    """class CommsOverride"""
    def __enter__ (self):
        ...
    def __exit__ (self, ex_type=None, ex_val=None, ex_tb=None):
        ...
    def __init__ (self, origin_id=None, selected_id=None, face=None, from_name=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def active ():
        ...
class CommsPromise(ButtonPromise):
    """class CommsPromise"""
    def __init__ (self, path, task, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def build_promise_buttons (self):
        ...
    def clear (self) -> None:
        ...
    def collect (self) -> bool:
        ...
    def handle_button_sub_task (self, sub_task):
        ...
    def initial_poll (self) -> None:
        ...
    def leave (self) -> None:
        ...
    def message (self, event) -> None:
        ...
    def poll (self):
        ...
    def post_button_run (self, button):
        ...
    def pre_button_run (self, button):
        ...
    def pressed_set_values (self, task) -> None:
        ...
    def pressed_test (self) -> bool:
        ...
    def process_on_change (self) -> None:
        ...
    def selected (self, event) -> None:
        ...
    def set_buttons (self, origin_id, selected_id) -> None:
        ...
    def set_comms_badge (self, comms_badge):
        ...
    def set_face_override (self, face):
        ...
    def set_path (self, path) -> None:
        ...
    def show_buttons (self) -> None:
        ...
