# The behavior tree system

Composable behavior tree nodes for NPC AI using MAST labels as leaf nodes.

## Overview

The behavior tree functions provide a higher-level alternative to the brain system for structuring NPC logic. Each function schedules a set of MAST labels as parallel tasks and returns a promise that resolves based on the tree's semantics:

| Node type | Resolves when |
|---|---|
| `bt_seq` (Sequence) | **All** children succeed in order — fails as soon as any child fails |
| `bt_sel` (Select) | **First** child to succeed — tries next on failure |
| `bt_invert` | Inverts the child's result |
| `bt_until_success` | Repeats the child label until it returns `BT_SUCCESS` |
| `bt_until_fail` | Repeats the child label until it returns `BT_FAIL` |
| `bt_repeat` | Repeats the child label indefinitely |

These are designed to be composed with `await` in MAST. Within a behavior tree label, use `BT_SUCCESS` or `BT_FAIL` to signal the outcome.

`bt_get_variable` / `bt_set_variable` read and write from the behavior tree's shared blackboard data so child labels can communicate without task-scope coupling.

## Quick example

=== ":mast-icon: {{ab.m}}"
    ```
    == npc_ai ==
    await bt_sel(attack_if_close, patrol)

    == attack_if_close ==
    enemies = broad_test_around(get_pos(BRAIN_AGENT_ID), 1000) & role("enemy")
    if len(enemies) == 0: BT_FAIL
    target(BRAIN_AGENT_ID, closest(BRAIN_AGENT_ID, enemies))
    BT_SUCCESS
    == patrol ==
    target_pos(BRAIN_AGENT_ID, waypoint_x, 0, waypoint_z)
    BT_SUCCESS
    ```

=== ":simple-python: {{ab.pm}}"
    ```python
    from sbs_utils.procedural.behavior import bt_seq, bt_sel, bt_invert, bt_until_success

    # Sequence: do A then B (fails if A fails)
    await bt_seq(move_to_target, fire_weapons)

    # Select: try A, fall back to B
    await bt_sel(attack_label, patrol_label)

    # Repeat until the patrol label returns BT_SUCCESS
    await bt_until_success(patrol_label)
    ```

## Return values in BT labels

Within a behavior tree leaf label, end with one of:

```
BT_SUCCESS   # this node succeeded
BT_FAIL      # this node failed
OK_IDLE      # still running (yield and retry next tick)
```

## API

::: sbs_utils.procedural.behavior
