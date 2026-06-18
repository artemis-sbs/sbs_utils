# The comms system

Send messages to player consoles and manage the comms-tree route system.

## Overview

The comms module provides two related capabilities:

**Broadcast messages** — `comms_broadcast` sends a text message to the comms panel of a ship (or all ships). Messages appear as incoming transmissions on the comms console. Use `comms_broadcast` for NPC dialogue, status updates, and mission narration that the crew hears.

**Comms routes** — the `//comms/<path>` route system defines the interactive comms tree that players navigate using the comms console. Use `comms_route_to` from Python/MAST to programmatically navigate the tree, and `comms_select` to set which NPC a player is talking to.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    //comms/alien
        + "Greetings, humans." //comms/alien/greet

    //comms/alien/greet
        + "We come in peace.":
            signal_emit("alliance_offered")
        + "Stand down!":
            target(alien_id, player_ship_id)

    == patrol ==
        comms_broadcast(ship_id, "Enemy spotted at grid 7-Alpha!", "red")
        ->END
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.comms import comms_broadcast, comms_route_to

    comms_broadcast(ship_id, "Incoming transmission!", "yellow")
    comms_route_to(client_id, "alien/greet")
    ```

## API

::: sbs_utils.procedural.comms
