from ..helpers import FrameContext
from .query import to_id, to_object

def hex_to_rgb(hex_color:str) -> tuple:
    """Convert a hex color string to an ``(r, g, b)`` integer tuple.

    Args:
        hex_color (str): Hex color code, with or without a leading ``#``
            (e.g. ``"#1a2b3c"`` or ``"1a2b3c"``).

    Returns:
        tuple[int, int, int]: ``(red, green, blue)`` each in the range 0–255.
    """
    # Remove the '#' if present
    hex_color = hex_color.strip().lstrip('#')
    # Convert to integers for R, G, B
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def dmx_run_for_ship(player_ship, dmx_function):
    """Call a DMX function for every client connected to a player ship.

    Args:
        player_ship (int | Agent): The player ship agent or ID.
        dmx_function (callable): A callable that accepts a single ``client``
            int argument.
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
    """Set DMX channels 0–2 (R/G/B) from a hex color string.

    Args:
        client (int): The client ID.
        color (str): Hex color string, e.g. ``"#1a2b3c"``.
        dmx_behavior (int): Channel behavior (0 = OFF, 1 = ON, 2 = BLINK,
            3 = PULSE, 4 = RAMPUP, 5 = RAMPDN, 6 = RANDOM).
        speed (int): Blink/pulse speed; ``0`` means no animation.
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
    """Set a single DMX channel's behavior and intensity range for a client.

    Args:
        client (int): The client ID.
        dmx_channel (int): Channel number 0–255. Typically 0 = Red, 1 = Green,
            2 = Blue.
        dmx_behavior (int): Channel behavior (0 = OFF, 1 = ON, 2 = BLINK,
            3 = PULSE, 4 = RAMPUP, 5 = RAMPDN, 6 = RANDOM).
        speed (int, optional): Blink/pulse speed. Defaults to 0.
        low (int, optional): Minimum intensity 0–255. Defaults to 0.
        high (int, optional): Maximum intensity 0–255. Defaults to 255.
    """
    FrameContext.context.sbs.set_dmx_channel(client, dmx_channel, dmx_behavior, speed, low, high)


