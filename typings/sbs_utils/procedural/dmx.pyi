from sbs_utils.helpers import FrameContext
def dmx_run_for_ship (player_ship, dmx_function):
    """Call a DMX function for every client connected to a player ship.
    
    Args:
        player_ship (int | Agent): The player ship agent or ID.
        dmx_function (callable): A callable that accepts a single ``client``
            int argument."""
def dmx_set_channel (client, dmx_channel, dmx_behavior, speed=0, low=0, high=255):
    """Set a single DMX channel's behavior and intensity range for a client.
    
    Args:
        client (int): The client ID.
        dmx_channel (int): Channel number 0–255. Typically 0 = Red, 1 = Green,
            2 = Blue.
        dmx_behavior (int): Channel behavior (0 = OFF, 1 = ON, 2 = BLINK,
            3 = PULSE, 4 = RAMPUP, 5 = RAMPDN, 6 = RANDOM).
        speed (int, optional): Blink/pulse speed. Defaults to 0.
        low (int, optional): Minimum intensity 0–255. Defaults to 0.
        high (int, optional): Maximum intensity 0–255. Defaults to 255."""
def dmx_set_color (client, color: str, dmx_behavior, speed):
    """Set DMX channels 0–2 (R/G/B) from a hex color string.
    
    Args:
        client (int): The client ID.
        color (str): Hex color string, e.g. ``"#1a2b3c"``.
        dmx_behavior (int): Channel behavior (0 = OFF, 1 = ON, 2 = BLINK,
            3 = PULSE, 4 = RAMPUP, 5 = RAMPDN, 6 = RANDOM).
        speed (int): Blink/pulse speed; ``0`` means no animation."""
def hex_to_rgb (hex_color: str) -> tuple:
    """Convert a hex color string to an ``(r, g, b)`` integer tuple.
    
    Args:
        hex_color (str): Hex color code, with or without a leading ``#``
            (e.g. ``"#1a2b3c"`` or ``"1a2b3c"``).
    
    Returns:
        tuple[int, int, int]: ``(red, green, blue)`` each in the range 0–255."""
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
