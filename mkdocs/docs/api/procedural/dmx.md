# DMX system

Control DMX lighting hardware connected to player consoles.

## Overview

Cosmos supports DMX512 lighting controllers connected to client PCs. The DMX module sends channel commands to clients to drive RGB lights, blinking effects, and animated behaviors synchronized with in-game events.

Each DMX channel maps to a light or group of lights. Channels 0–2 are conventionally Red, Green, Blue for RGB strips. Use `dmx_set_color` to drive all three channels from a single hex color string, or `dmx_set_channel` for per-channel control.

`dmx_run_for_ship` iterates every client connected to a player ship and calls your function once per client — use this to synchronize a whole bridge's lighting.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == red_alert ==
        dmx_run_for_ship(ship_id, lambda c: dmx_set_color(c, "#ff0000", 2, 10))
        ->END

    == all_clear ==
        dmx_run_for_ship(ship_id, lambda c: dmx_set_color(c, "#00ff00", 1, 0))
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.dmx import dmx_run_for_ship, dmx_set_color, dmx_set_channel

    dmx_run_for_ship(ship_id, lambda c: dmx_set_color(c, "#ff0000", 2, 10))
    dmx_set_color(client_id, "#00ff00", 1, 0)
    dmx_set_channel(client_id, 0, 3, speed=5, low=0, high=200)  # channel 0, PULSE
    ```

## DMX behavior values

| Value | Behavior |
|---|---|
| 0 | OFF |
| 1 | ON (solid) |
| 2 | BLINK |
| 3 | PULSE |
| 4 | RAMP UP |
| 5 | RAMP DOWN |
| 6 | RANDOM |

## API

::: sbs_utils.procedural.dmx
