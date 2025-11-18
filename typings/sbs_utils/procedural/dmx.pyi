from sbs_utils.helpers import FrameContext
def dmx_run_for_ship (player_ship, dmx_function):
    """Run a dmx function for all clients on a player ship.
    Args:
        player_ship (int | Agent): The player ship agent or ID.
        dmx_function (callable)"""
def dmx_set_channel (client, dmx_channel, dmx_behavior, speed=0, low=0, high=255):
    """Set the DMX channel information for a client.
    Args:
        client (int): The client ID
        dmx_channel (int): 0-255 allowed. Usually:
            * 0 = Red
            * 1 = Green
            * 2 = Blue
    
        dmx_behavior (int): The behavior of the channel:
            * 0 = DMX_BEHAV_OFF    - the channel is always set to zero
            * 1 = DMX_BEHAV_ON     - the channel is always set to the high value
            * 2 = DMX_BEHAV_BLINK  - the channel blinks between the low and high values
            * 3 = DMX_BEHAV_PULSE  - the channel pulses between the low and high values
            * 4 = DMX_BEHAV_RAMPUP - the channel ramps between the low and high values
            * 5 = DMX_BEHAV_RAMPDN - the channel ramps between the low and high values
            * 6 = DMX_BEHAV_RANDOM - the channel jumps randomly around, somewhere between the low and high values
    
        speed (int, optional): The speed at which the channel blinks or pulses, if applicable. Default is 0.
        low (int, optional): 0-255 allowed. The lowest intensity the channel should emit. Default is 0.
        high (int, optional): 0-255 allowed. The highest intensity the channel should emit. Default is 255."""
def dmx_set_color (client, color: str, dmx_behavior, speed):
    """Set the RGB colors based on the color stylestring.
    Args:
        client (int): The client ID
        color (str): The color stylestring (e.g #123abc)
        dmx_behavior (int): The behavior of the dmx channels
            * 0 = DMX_BEHAV_OFF    - the channel is always set to zero
            * 1 = DMX_BEHAV_ON     - the channel is always set to the high value
            * 2 = DMX_BEHAV_BLINK  - the channel blinks between the low and high values
            * 3 = DMX_BEHAV_PULSE  - the channel pulses between the low and high values
            * 4 = DMX_BEHAV_RAMPUP - the channel ramps between the low and high values
            * 5 = DMX_BEHAV_RAMPDN - the channel ramps between the low and high values
            * 6 = DMX_BEHAV_RANDOM - the channel jumps randomly around, somewhere between the low and high values
    
        speed (int): The speed at which the channel blinks or pulses, if applicable. Default is 0."""
def hex_to_rgb (hex_color: str) -> tuple:
    """Convert a hexidecimal string representation of a color to a tuple of red, green, and blue.
    Args:
        hex_color (str): The hexidecimal color code.
    Returns:
        tuple: The tuple (red, green, blue)"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts item passed to an agent id
    Args:
        other (Agent | CloseData | int): The agent
    Returns:
        int: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Converts the item passed to an agent
    ??? note
    * Return of None could mean the agent no longer exists
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    Returns:
        Agent | None: The agent or None"""
