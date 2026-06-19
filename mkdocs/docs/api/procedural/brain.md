# The brain system

Behavior-tree AI for NPCs, evaluated every tick via the objective system.

## Overview

A brain is a tree of `Brain` nodes attached to an agent's `__BRAIN__` inventory slot. The root is always a **Select** node — it runs each child in order and stops at the first success. Children can be plain labels (**Simple** nodes), or composite **Sequence** / **Select** nodes built from structured dicts.

Each tick, `brains_run_all` iterates all agents that have a `__BRAIN__` entry and calls `brain.run()`. A Simple node runs its MAST label synchronously in a temporary task; the label result (`BT_SUCCESS` / `BT_FAIL`) propagates up the tree.

`brain_add` is the main entry point. Call it once per behavior you want to add; the root Select node grows with each call. Use structured dicts for composite nodes:

- `{"SEL_name": [child1, child2]}` — Select composite
- `{"SEQ_name": [child1, child2]}` — Sequence composite

Within a brain label you have access to `BRAIN`, `BRAIN_AGENT`, and `BRAIN_AGENT_ID` task variables.

!!! note
    The brain system piggybacks on the objective tick. Call `brain_schedule()` (or `brain_add()`, which calls it automatically) to register the tick handler.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == setup ==
        brain_add(enemy_id, patrol_label)
        brain_add(enemy_id, attack_label)
        ->END

    == patrol_label ==
        ///test
        if get_pos(BRAIN_AGENT_ID).distance(target_pos) > 500: BT_FAIL
        BT_SUCCESS

    == attack_label ==
        target(BRAIN_AGENT_ID, player_id)
        BT_SUCCESS
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.brain import brain_add, brain_clear

    # Simple behavior list — Select runs them in order
    brain_add(enemy_id, patrol_label)
    brain_add(enemy_id, attack_label)

    # Nested composite example
    brain_add(enemy_id, {
        "SEL_combat": [attack_label, evade_label]
    })

    # Remove the brain entirely
    brain_clear(enemy_id)
    ```

## Behavior tree result values

| Return | Meaning |
|---|---|
| `BT_SUCCESS` | This node succeeded |
| `BT_FAIL` | This node failed |
| `OK_IDLE` | Still running (not yet resolved) |

## API

::: sbs_utils.procedural.brain
