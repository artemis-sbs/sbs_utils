# Standby culling

Park distant objects out of the engine network by player proximity, without
losing their script state.

## Overview

`sbs.push_to_standby_list_id` removes an object from the engine sim and network
replication while its py-side Agent (roles, links, inventory) persists — so
distant, irrelevant objects stop costing the network without losing script state.
This module drives that by **player proximity**: call `standby_cull_step` (or
`standby_cull_fleets`) each tick, and any candidate with no `__player__` within a
radius is **parked**; it's **retrieved** the moment a player comes near.

A parked self-brained NPC has its **brain paused** while parked (and resumed on
retrieve), so a non-simulated object isn't still being steered — which makes
terrain *and* self-brained NPCs/POIs safe to cull. Fleets park as a **unit**: all
of a fleet's ships and its one brain go dark together when no player is near any
of them.

Side-agnostic — proximity is measured to *every* player. Extracted from the Open
Universe's culler so any large-world mission can reuse it.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == cull_loop ==
    --- tick
        await delay_sim(1)
        standby_cull_step(role("__npc__") | role("terrain"), 30000)
        standby_cull_fleets("fleet", 30000)
        jump tick
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.standby import (
        standby_cull_step, standby_cull_fleets, standby_cull_clear)

    # each tick: park loose objects and whole fleets past 30k units from all players
    standby_cull_step(candidates, 30000)
    standby_cull_fleets("fleet", 30000)
    ```

!!! warning "Clear before you despawn"
    Before clearing a system (e.g. on a jump), call `standby_cull_clear()` first.
    Delete-by-box only sees objects in **normal space**, not standby — so parked
    objects must be retrieved before the region is cleared, or they leak.

## API

::: sbs_utils.procedural.standby
