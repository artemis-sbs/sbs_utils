from sbs_utils.mast_sbs.story_nodes.define_format import DefineFormat
from sbs_utils.mast.mast_node import DescribableNode
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
def STRING_REGEX_NAMED (name):
    ...
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
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
def role (role: str):
    """Return the set of agent IDs that currently hold a given role.
    
    Args:
        role (str): The role name.
    
    Returns:
        set[int]: IDs of all agents with that role."""
def scan_results (message, target=None, tab=None):
    """Set the scan results for the current scan. This should be called when the scan is completed.
       This is typically called as part of a scan()
       This could also be called in response to a routed science message.
       When paired with a scan() the target and tab are not needed.
       Tab is the variable __SCAN_TAB__, target is track
    
    Args:
        message (str): Scan text for a scan that is in progress.
        target (Any, optional): Not currently used. Default is None.
        tab (str, optional): Scan tab for a scan that is in progress. Default is None."""
class CommsMessageStart(DescribableNode):
    """class CommsMessageStart"""
    def __init__ (self, mtype, title, q=None, var=None, format=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __str__ (self):
        """Return str(self)."""
    def create_end_node (self, loc, dedent_obj, compile_info):
        ...
    def is_indentable (self):
        ...
    def parse (lines):
        ...
    def post_dedent (self, compile_info):
        ...
class CommsMessageStartRuntimeNode(MastRuntimeNode):
    """class CommsMessageStartRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast_sbs.story_nodes.comms_message.CommsMessageStart):
        ...
