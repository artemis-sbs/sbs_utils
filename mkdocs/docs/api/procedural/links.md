# Links

Uni-directional named associations between agents.

## Overview

Links are a lightweight way to associate one agent with another under a named relationship. Unlike inventory values, a single agent can have many outgoing links under the same name, making links ideal for one-to-many relationships: a ship linked to all its console clients, a brain linked to all its child nodes, a ship linked to all its active upgrades.

Key functions:

- **`link(from_id, name, to_id)`** — add a link.
- **`unlink(from_id, name, to_id)`** — remove a specific link.
- **`linked_to(from_id, name)`** — get the set of agents linked under `name`.
- **`has_link_to(from_id, name, to_id)`** — check whether a specific link exists.

Links are uni-directional. `linked_to(ship_id, "consoles")` returns the consoles; nothing automatically tells a console which ships it belongs to.

## Quick example

=== "MAST"
    ```
    == setup ==
    ~~ link(SHIP_ID, "escort_targets", FREIGHTER_ID) ~~
    ~~ link(SHIP_ID, "escort_targets", TRANSPORT_ID) ~~

    == check ==
    ~~ targets = linked_to(SHIP_ID, "escort_targets") ~~
    ~~ alive = [t for t in targets if object_exists(t)] ~~
    ~~ if len(alive) == 0: jump mission_complete ~~
    ```

=== "Python"
    ```python
    from sbs_utils.procedural.links import link, unlink, linked_to, has_link_to

    # Associate a freighter with a ship
    link(SHIP_ID, "escort_targets", FREIGHTER_ID)
    link(SHIP_ID, "escort_targets", TRANSPORT_ID)

    # Get all linked targets
    targets = linked_to(SHIP_ID, "escort_targets")

    # Remove when destroyed
    unlink(SHIP_ID, "escort_targets", FREIGHTER_ID)

    # Check
    if has_link_to(SHIP_ID, "escort_targets", FREIGHTER_ID):
        print("still escorting the freighter")
    ```

## System link names

Several library modules use reserved link names:

| Link name | Used by |
|---|---|
| `"__UPGRADE__"` | Upgrade system |
| `"__BRAIN__"` (inventory, not link) | Brain system |
| `"consoles"` | Client console associations |
| `"grid_objects"` | Grid objects on a ship |
| `"damage"` | Damaged grid objects |
| `"work-order"` | Damcon repair assignments |

## API

::: sbs_utils.procedural.links
