from ..helpers import FrameContext
from .query import to_id, to_object

def hex_to_rgb(hex_color:str) -> tuple:
    """
    Convert a hexidecimal string representation of a color to a tuple of red, green, and blue.
    Args:
        hex_color (str): The hexidecimal color code.
    Returns:
        tuple: The tuple (red, green, blue)
    """
    # Remove the '#' if present
    hex_color = hex_color.strip().lstrip('#')
    # Convert to integers for R, G, B
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def dmx_run_for_ship(player_ship, dmx_function):
    """
    Run a dmx function for all clients on a player ship.
    Args:
        player_ship (int | Agent): The player ship agent or ID.
        dmx_function (callable)
    """
    if not dmx_function:
        return
    if not callable(dmx_function):
        print("DMX function not callable")
        return
    if to_object(player_ship) is None:
        return
    ship_id = to_id(player_ship)
    clients = FrameContext.context.sbs.get_client_ID_list()
    for client in clients:
        if FrameContext.context.sbs.get_ship_of_client(client) == ship_id:
            dmx_function(client)

def dmx_set_color(client, color:str, dmx_behavior, speed):
    """
    Set the RGB colors based on the color stylestring.
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

        speed (int): The speed at which the channel blinks or pulses, if applicable. Default is 0.
    """
    r,g,b = hex_to_rgb(color)
    print(r)
    dmx_set_channel(client, 0, dmx_behavior, speed, 0, r*16)
    dmx_set_channel(client, 1, dmx_behavior, speed, 0, g*16)
    dmx_set_channel(client, 2, dmx_behavior, speed, 0, b*16)


# The only real reasons for this function are 
# A) Better documentation, and
# B) speed, low, and high are optional.
def dmx_set_channel(client, dmx_channel, dmx_behavior, speed=0, low=0, high=255):
    """
    Set the DMX channel information for a client.
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
        high (int, optional): 0-255 allowed. The highest intensity the channel should emit. Default is 255.
    """
    FrameContext.context.sbs.set_dmx_channel(client, dmx_channel, dmx_behavior, speed, low, high)


