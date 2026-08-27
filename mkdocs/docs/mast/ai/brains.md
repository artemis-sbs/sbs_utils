# Brains

Brains are a lightweight behavior tree system used by {{ab.m}} labels.

In practice, a brain:

- picks one or more labels to run every tick
- interprets each label result as success or fail
- combines child results with selector or sequence rules
- stores useful blackboard-style values in agent inventory

If you are familiar with behavior trees:

- SEL is a selector (first child success wins)
- SEQ is a sequence (all children must succeed)
- a normal label is a leaf node


## Mental model

Each agent can have one root brain object in inventory key __BRAIN__.

The root is usually a selector:

- SEL root
	- child 1 (leaf or composite)
	- child 2 (leaf or composite)
	- ...

Each tick:

1. The brain system visits every agent that has __BRAIN__.
2. The root brain runs.
3. Composite nodes execute children.
4. Leaf nodes execute a {{ab.m}} label and return a poll result.

Brains do not have a permanent done state. They are evaluated repeatedly.


## How results drive behavior

Brains use success/fail-style outcomes:

- PollResults.BT_SUCCESS
- PollResults.BT_FAIL
- PollResults.OK_IDLE (used as reset/neutral state internally)

Composite behavior:

- Selector (SEL):
	- starts as fail
	- runs children in order
	- first child that succeeds makes selector succeed
	- if none succeed, selector fails
- Sequence (SEQ):
	- runs children in order
	- first child that fails makes sequence fail
	- if all succeed, sequence succeeds

!!! danger "`fail` means opposite things in the two composites, and one of them is silent"
    Inside a **Selector**, `yield fail` is how a leaf declines its turn: the next sibling
    gets a go. That is the whole point of a priority list.

    Inside a **Sequence**, `yield fail` *returns immediately* — **every sibling after it is
    skipped for that pass.** Nothing reports this. There is no error, nothing in the log,
    and coverage looks healthy, because the leaf that failed did run; it is the ones after
    it that quietly did not.

    It shipped exactly once and cost a real bug: a science node yielded `fail` when no
    hostile was in scan range — which is precisely the situation when a ship is off at a
    wreck — so the comms, weapons and engineering nodes after it never ran, and the ship
    sat there holding no weapons target and never fired. The helm looked perfect
    throughout, because the helm was a Selector.

    **A node with nothing to do has succeeded at doing nothing.** Under a Sequence, say
    `yield success`. Reserve `fail` for Selector children and for "the whole sequence
    should stop here".

### Result modifiers

The runtime also supports modifier flags on a brain node:

- Invert
- AlwayFail
- AlwaySuccess

These flags alter the final node result after execution.


## Leaf label execution rules

A simple brain node points at one major label.

When a leaf runs:

1. On first run only, if sub label enter exists, it is executed once.
2. If sub label test exists, that sub label is executed for result.
3. Otherwise, execution starts at location 0 of the major label.

Runtime variables injected for the label task:

- BRAIN: current brain object
- BRAIN_AGENT: object form of the agent id
- BRAIN_AGENT_ID: raw agent id

This is why most brain labels read/write inventory through BRAIN_AGENT.

!!! danger "A leaf must never `await`"
    A leaf is **one synchronous pass** that ends in `yield success` or `yield fail`. Those
    resolve to results that mark the task done, and the scheduler disposes of it.

    Anything else — an `await`, or `yield idle` — leaves a **live task** on the scheduler,
    while the brain starts a fresh one next pass. That is one immortal task per pass, for
    the life of the mission, all running the same body. It also reads as not-success, so a
    Selector falls through to the next sibling and the leaf appears to do nothing at all
    while quietly multiplying.

    The library now ends such a leaf and warns once, rather than leaking, but the leaf
    still has to be written correctly to *mean* anything.

    **Work that takes time goes in a `task_schedule`d label, gated by a flag**, with a node
    that holds the tree until it finishes. `fleets/elite_abilities.mast` in
    LegendaryMissions is the worked example: `elite_bt_activate` schedules the ability and
    stashes the handle; `elite_bt_gate` yields `fail` until `elite_task.done()`.


## How often a brain runs

Every brain re-evaluates its whole tree on a heartbeat set by `BRAIN_PASS_SECONDS`
(default **3**). Brains are not all run in the same frame: a `RollingSlicer` hands back a
few each tick so a full pass over every brain in the mission completes in exactly that
period, whether there are three brains or three hundred. That keeps a big NPC count from
becoming a periodic frame spike.

**Design your leaves around that period, not around the tick.** A leaf sees the world as
it was when its pass came round, so a decision holds for up to `BRAIN_PASS_SECONDS`
before it can be revisited. That is fine for "who do I attack" and wrong for anything
needing a tight loop — steering corrections, or a throttle that should track a closing
distance. Work that needs to be smooth belongs in the engine's own steering
(`target`/`target_pos` set a destination the engine tracks every frame) rather than in
repeated leaf decisions.

!!! warning "This period was silently double until v1.4.0"
    The slice used to be sized **per call**, on the assumption that the host called it 30
    times a sim-second. Measured against a live 1.3.7 engine it really calls it **15**, so
    every pass took **twice** its declared time — `BRAIN_PASS_SECONDS = 3` meant six. The
    headless mock calls it about **6** a second, so the same tree ran on a **15-second**
    pass there, and the two hosts disagreed with each other by 2.5x.

    Nothing reported it, and nothing could: a brain running at half speed is
    indistinguishable from a brain whose leaves keep declining. It surfaced only because a
    brain-driven player ship almost never warped while identical logic written as a
    `delay_sim(1)` loop warped constantly — it was re-checking its speed every fifteen
    seconds instead of every three.

    The slice is now sized by the **elapsed tick count**, the way `TickTask` has always
    measured its own delay, so the period is honest and identical in both hosts. If you
    tuned a mission's feel against the old behavior, the equivalent is
    `BRAIN_PASS_SECONDS = 6`.

Objectives (`OBJECTIVE_PASS_SECONDS`, also 3) and urges (`URGE_PASS_SECONDS`, 30) share
the same slicer and were affected the same way.


## Defining brains declaratively

Brains can be assembled from Python-friendly structures.

Supported structures:

- string: label name
- MastNode: direct label node
- list: add each item as child
- dict:
	- single key starting with SEL -> selector composite
	- single key starting with SEQ -> sequence composite
	- otherwise use keys label and data

Common pattern:

```yaml
brain:
	SEQ:
		- ai_fleet_init_blackboard
		- SEL:
			- ai_fleet_chase_best_anger
			- label: ai_fleet_chase_roles
				data:
					test_roles: station
			- label: ai_fleet_chase_roles
				data:
					test_roles: __player__
		- ai_fleet_calc_forward_vector
		- ai_fleet_scatter_formation
```

!!! tip "The ROOT is a Selector unless you ask otherwise"
    `brain_add` creates a Selector root, which stops at the first child that succeeds.
    That is right for a priority list of behaviours and wrong for a set of independent
    jobs — the first success starves every one after it, permanently and silently.

    Pass `root_type=BrainType.Sequence` when every child should run each pass. It applies
    only when the call CREATES the root, so a later `brain_add` can never re-type an
    agent's existing tree.

    A tree that needs both — a priority helm plus several independent consoles — nests a
    `SEL:` inside a `SEQ:` root, as the example above does.

!!! warning "Declare the tree as YAML, never as a MAST dict literal"
    MAST parses line by line, so a `{...}` spanning lines is an unclosed brace that
    desyncs the compiler for the rest of the file — and a story that does not compile runs
    **zero labels while still reporting PASS**. The `brain:` metadata block has no such
    problem, which is why every prefab uses it.

Notes:

- Child order matters for SEL and SEQ.
- data on a node is passed into the task context for that label.
- metadata defaults in the label and runtime data overrides are often used together.


## Quick start: attach a brain

Brains are typically attached from Python when spawning/configuring an NPC or fleet controller.

```py
from sbs_utils.procedural.brain import brain_add

brain_add(
	agent_id,
	{
		"SEQ main": [
			"ai_fleet_init_blackboard",
			{
				"SEL choose_target": [
					"ai_fleet_chase_best_anger",
					{"label": "ai_fleet_chase_roles", "data": {"test_roles": "station"}},
					{"label": "ai_fleet_chase_roles", "data": {"test_roles": "__player__"}},
				]
			},
			"ai_fleet_calc_forward_vector",
			"ai_fleet_scatter_formation",
		]
	},
	client_id=0,
)
```

The first call creates a default selector root if needed, then inserts your tree.


## Metadata and per-node data

A brain label often declares defaults in metadata.

Example:

```mast
=== ai_fleet_chase_roles
metadata: yaml
	type: brain/npc
	use_arena: True
	test_roles: station
	exclude_roles: raider
		...
```

Then a brain node can provide data overrides:

```yaml
label: ai_fleet_chase_roles
data:
	test_roles: __player__
```

This allows one label to be reused with different behavior.


## Active brain status text

The runtime tracks active text for debugging/UI use.

For a leaf node:

- active: label name
- active_desc:
	- desc inventory value if present
	- optionally random choice if desc is a list
	- then DisplayName inventory value if present
	- otherwise label name

For a selector, when one child succeeds:

- that child becomes active
- brain_active inventory is set to child active_desc


## Worked example: fleet brain

Using your fleet script shape:

1. ai_fleet_init_blackboard
	- resets target data
	- computes lead ship and local arena
2. SEL target choice
	- try ai_fleet_chase_best_anger first
	- if that fails, try role-based targeting variants
3. ai_fleet_calc_forward_vector
	- computes destination and throttle
4. ai_fleet_scatter_formation
	- issues per-ship target positions

This creates robust fallback logic:

- preferred tactical behavior first
- deterministic fallbacks second
- movement only after a valid target exists


## Minimal authoring checklist

When writing a new brain label:

1. Add metadata defaults for tunables (distance, roles, stop_dist, etc.).
2. Use BRAIN_AGENT inventory as your blackboard.
3. Return early with yield fail when prerequisites are missing.
4. Set outputs (target, target_position, throttle, etc.).
5. End with yield success.

When composing a tree:

1. Use SEQ for required steps.
2. Use SEL for fallback options.
3. Put cheap/high-confidence options earlier.
4. Keep each label focused on one responsibility.


## Debugging tips

- If a brain seems idle, verify the agent has __BRAIN__ assigned.
- If a label never runs, confirm the label name resolves correctly.
- If selector never succeeds, inspect each child for missing prerequisites.
- If targeting stalls, verify blackboard keys are populated in init step.
- Track brain_active to see which child is currently winning selection.


## API touchpoints

Core procedural calls:

- brain_add(...)
- brain_clear(...)
- brains_run_all(...)

These are defined in:

- sbs_utils/procedural/brain.py

Example mission labels:

- fleets/brain_fleet.mast

Together they provide a full pattern for authoring reusable NPC decision logic.
