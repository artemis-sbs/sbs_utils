# MAST Language Reference for Claude

Working knowledge of MAST — the scripting language used in Artemis Cosmos.
Update this file as new things are confirmed or corrected by the user.

Items marked **[TBC]** are not yet confirmed.

---

## What MAST Is

MAST is a linear scripting language embedded in Python. Think "choose your own adventure" or BASIC line numbers — not functions with return values. Execution flows forward, jumps to labels, and runs until it ends. New tasks can be scheduled and events awaited, but nested label calls like function calls are not the norm.

**Never write `== main ==` in scripts or examples.** The main label is implicit — the top-level code in every MAST file is automatically combined into one shared main. `shared` variables at the top level only run once across all files. Use descriptive named labels (`== setup ==`, `== patrol_logic ==`) for everything else.

---

## Label Types

### Top-level labels (`==`)

```
== label_name ==
    code here
    code here
```

- Any number of `=` signs (2+). Trailing delimiter is **optional**.
- Always start at **column 0**.
- Commands under the label are **indented** (required for `if`/`for` blocks; conventional elsewhere).
- **Fallthrough by default** — execution continues into the next label unless stopped.
- To end the task: `->END`
- To jump: `jump label_name` or `-> label_name`

```
== setup ==           # all equivalent
=== setup
==== setup ===
```

### Inline labels (`---`)

```
== outer ==
    do_setup()
---loop
    await delay_sim(1)
    if still_running:
        jump loop
    ->END
```

- Start at **column 0** (same as top-level labels).
- Trailing `---` is optional; `----` (4 dashes) also works.
- **Name is only valid within the parent `==` label's scope** — local jump targets only.
- Used for loops and re-entry points within a label.
- Also fallthrough into the next label unless stopped.

### Routes (`//`)

```
//signal/enemy_spotted
    log("Enemy spotted", "combat")
    signal_emit("response_needed")
    ->END
```

- Start at **column 0**.
- **Do NOT fallthrough.**
- End implicitly at the next non-inline label (`==` or `//`) or end of file.
- Triggered by engine events — not by normal execution flow.
- Can have conditions: `//route/path if condition`
- Commands indented under the route.

### Inline routes (`///`)

Sub-entry points within a `//` route (e.g. `///enable`, `///docked` inside `//dock/hangar`).
**Not mature — avoid in examples for now.**

---

## Flow Control

### `->END`

Ends the current task entirely.

```
== setup ==
    spawn_object("enemy", ...)
    ->END
```

- **Must be uppercase.**
- No space preferred (`->END`), but `-> END` is legal.
- Indented like the surrounding code.
- Conditional form: `->END if obj is None`

### `jump` and `->`

`->` is a shortcut for `jump`, mostly used with `->END`.

```
jump main                           # jump to label "main"
-> main                             # equivalent
jump meeting_loop if not done       # conditional jump
->END                               # end the task
->END if obj is None                # conditional end
```

### Fallthrough pattern

A label that intentionally falls through into the next is a valid pattern:

```
== setup ==
    init_enemies()
    # falls through into main
== main ==
    await signal_wait("start")
    begin_mission()
    ->END
```

---

## `yield`

Used primarily in brain (AI) and objective labels to return a result. In some conditions `yield` also implies `->END` (ends that execution path).

```
yield success           # task succeeded (may also end task)
yield fail              # task failed
yield idle              # still running — check again next tick (behavior tree)
yield result obj        # return a value to the caller

# Conditional forms
yield success if condition
yield fail if obj is None
yield idle if not is_timer_finished(id, "timer")
yield result ship.id
```

**Brain tree pattern:**
```
=== ai_chase_target
    target_id = BRAIN_AGENT.get_inventory_value("blackboard:target")
    yield fail if target_id == 0
    yield fail if to_object(target_id) is None
    target(BRAIN_AGENT_ID, target_id, True, 1.0)
    yield success
```

---

## Variables and Scope

### `default`

Sets the variable **only if it does not already exist**. If the variable was already set (e.g. passed in by the schedule call), `default` leaves it unchanged.

```
default the_message = "You forgot to set the_message"
default name = name_random_hostile(side_value)
default ship_art = None
default shared DIFFICULTY = 5
```

### `shared`

Makes a variable accessible across all tasks in the story.

```
shared phoenix_id = None
shared game_stats = {"destroyed": 0}
shared admiral = lifeform_spawn("Admiral Harkin", ...)
```

**Top-level `shared` statements run only once.** After first execution they are converted to no-ops so subsequent clients don't re-run them. Because the server client runs first, top-level `shared` assignments are effectively server-initialised.

### `default shared`

Combines both: cross-task scope, only set if not already set.

```
default shared GAME_STARTED = False
default shared PLAYER_COUNT = 2
default shared SETTINGS = settings_get_defaults()
```

### Variable naming conventions

- **CAPS_STYLE** (`SHIP_ID`, `COMMS_ORIGIN_ID`, `DAMAGE_TARGET_ID`) — system-defined context variables injected by the engine or route system. Don't use this style for script-defined variables.
- **snake_case** (`ship_id`, `enemy_id`, `fleet_obj`) — script-defined variables. Follow Python conventions since most evaluation runs through Python `eval`/`exec`.

### Scope rules

- Variables are scoped to the **task**, not the label.
- A variable set in `== setup ==` is accessible after `jump main` in the same task.
- `shared` variables are accessible from any task in the story.
- Scope is more nuanced than this — treat as a topic to expand.

---

## `await`

Suspends the current task until a condition is met, then resumes at the next line.

```
== main ==
    await delay_sim(5)
    await delay_app(2)                              # real-world seconds
    await distance_less(phoenix_id, amb_id, 400)
    await signal_wait("enemy_destroyed")
    await task_schedule(spawn_players)              # wait for spawned task to finish
    await is_timer_finished(id, "WARMUP")
    ->END
```

### `await gui()`

Suspends the task waiting for user GUI interaction. Should always run within the same task. Each client should have exactly one main GUI task.

```
@console/helm !0 ^5 "Helm"
    gui_console("helm")
    await gui()
```

### `promise_any(p1, p2, ...)`

Races multiple promises; resolves with whichever finishes first. Classic use: button OR timeout.

```
choice = gui_button("Confirm")
result = await promise_any(choice, delay_sim(10))
# result is whichever promise resolved — check it to know which won
```

---

## Task Spawning

### `task_schedule(label, data)` — fire and forget

Spawns a background task without waiting. The spawned task gets its own scope; data dict becomes variables in that task.

```
task_schedule(spawn_wave)
task_schedule(send_admiral_message, {"the_message": "Enemy incoming!"})
```

### `await task_schedule(label, data)` — wait for completion

Pauses the current task until the spawned task ends.

```
await task_schedule(spawn_players)
await task_schedule(docking_standard_player_station)
```

### `sub_task_schedule(label, data, var)` — sub-tasks

Schedules under the **current task** (`FrameContext.task`). Sub-tasks share the parent task's lifecycle — if the parent ends, sub-tasks end too.

```
sub_task_schedule(brain_scan_update)
await sub_task_schedule(brain_scan_update_text)
```

### `gui_sub_task_schedule(label, data, var)` — GUI sub-tasks

Same as `sub_task_schedule` but tagged `end_on_new_gui` — automatically cancelled when a new GUI page is presented to the client.

**Spawn scope**: A spawned task gets its own variable scope. Data passed via the dict becomes variables in the child task. `shared` variables are still accessible.

### `gui_task_jump("label")` — redirect the GUI task

From within a sub-task, redirects the parent console's GUI task to a label. Used in the watch/repaint pattern: the watcher detects a change and forces the panel to repaint.

```
--- watch
    await delay_sim(1)
    ->END if not object_exists(ship_id)
    alert_state = get_data_set_value(ship_id, "red_alert", 0)
    if alert_state != prev_alert_state:
        gui_task_jump("repaint")    # redirect GUI task, not this sub-task
    jump watch
```

Different from `mast_task.jump()` — `gui_task_jump` targets the console's GUI task specifically.

---

## Metadata Blocks

Metadata is a data section embedded in a label that ends up as variables when the label executes. Systems can read metadata **before** the label executes — used to describe brain/prefab configuration. Metadata values represent defaults that can be overridden by the schedule/spawn call.

```
=== ai_chase_target
    metadata: ``` yaml
    type: brain/npc
    distance: 5000
    throttle: 1.0
    stop_dist: 500
    force_shoot: false
    ```
    
    # Code follows — "distance", "throttle" etc. are now variables
    yield fail if sbs.distance_id(BRAIN_AGENT_ID, target_id) > distance
    target(BRAIN_AGENT_ID, target_id, force_shoot, throttle, stop_dist=stop_dist)
    yield success
```

---

## Addons (`__init__.mast`)

LegendaryMissions-style addons are folders discovered by the presence of `__init__.mast`. The `__init__.mast` is the entry point; it uses `import` to load other files in the folder.

```
# prefabs/__init__.mast
import basic_enemy.mast
import basic_civilian.mast
import station_prefabs.mast
import terrain_prefabs.mast
```

`import filename.mast` looks for that file relative to the addon folder.

---

## Decorator Labels (`@`)

### Map labels

```
@map/secretmeeting "Secret Meeting"
    " The ambassadors are meeting secretly at starbase Phoenix.
    metadata: ``` yaml
    Properties:
        Player Ships: 'gui_int_slider("$text:int;low: 1.0;high:8.0;", var= "PLAYER_COUNT")'
        Difficulty: 'gui_int_slider("$text:int;low: 1.0;high:11.0;", var= "DIFFICULTY")'
    ```
    
    station_object = npc_spawn(0,0,0, "Starbase Phoenix", "tsn, station", ...)
    await task_schedule(spawn_players)
    ->END
```

### Media labels

```
@media/music/default "Cosmos Default Music"
@media/skybox/sky-bored-alice "borealis"
```

### Console labels

```
@console/helm !0 ^5 "Helm" if HELM_CONSOLE_ENABLED
    " Pilot the ship
    gui_console("helm")
    await gui()
```

Format: `@console/name !priority ^sort_order "Display Name" if condition`

---

## Comms System

### Initiation

Comms fires automatically when a player selects an entity in the Cosmos engine, which routes a comms-select event. The procedural comms system (`procedural/comms`) calls all matching `//enable/comms` routes once to check eligibility, then routes to the appropriate `//comms` label based on the state of the comms tree. Scripts don't manually open comms.

### Route structure

```
//comms if has_roles(COMMS_ORIGIN_ID, "__player__")
    + "Hail":
        << [green] "Hail"
            % Greetings, commander.
            % How can I help you?
    + "Send Message" //comms/ship_to_ship
    + "Attack!" if side_are_enemies(COMMS_ORIGIN_ID, COMMS_SELECTED_ID):
        >> "Prepare to be boarded."

//comms/ship_to_ship
    default prop_message = ""
    + "Back" //comms
    + "Send":
        comms_transmit(prop_message)
```

### Dialogue MAST syntax

`<<` = receive (incoming, NPC speaking). `>>` = transmit (outgoing, player speaking).

```
<< [green] "Title"
    % First possible line
    % Second possible line     # system picks one randomly
    % Third possible line

<< [$raider] "Hostile Hail"
    % Go climb a tree!
    % You can't win!

>> "Player response"
    % Understood, moving out.
```

`%` lines are random dialogue options — one is picked at random each time.

Other types: `<all>` (broadcast), `<scan>` (science scan result), `()` (speech bubble).

### Color style variables

`=$` declares a named color/style for use in comms dialogue:

```
=$ raider red, white
=$ friendly green

<< [$raider] "Hail"
    % Hostile message here
```

### Button syntax

```
+ "Label"                                   # simple button, runs inline block
+ "Label" //comms/path                      # navigate to route
+ "Label" handler_label                     # jump to label
+ "Label" handler_label {"key": "value"}    # jump with data dict
+ "Label" if condition:                     # conditional button
    code_here()
+ !0 "Back" //comms                         # !0 = sort priority
+ "{variable_text}" handler_label           # dynamic button text
```

### Navigation

```
comms_navigate("//comms/ship_to_ship")   # go to submenu
comms_navigate("")                        # go back/up
```

---

## GUI System

GUI display is through the GUI system — not standalone quoted strings. Quoted strings (`"text"`) are only valid in specific page contexts (comms pages, story pages).

For general output: `print()` or `log(message, category)`.

### `on` handlers

`on` commands run and are checked while a GUI is on screen:

```
on change variable_name:
    # runs when variable_name changes
    selected = list_box.get_value()

on change update_ticker < get_counter_elapsed_seconds(client_id, "refresh"):
    update_ticker += 1

on change get_data_set_value(ship_id, "red_alert", 0):
    # runs when the red_alert data value changes — arbitrary expression, not just variables
    alert_state = get_data_set_value(ship_id, "red_alert", 0)
    on_screen.update(f"image:{get_mission_dir_filename(image)}")
    # gui_represent(on_screen)  # deprecated — dirty system handles re-render automatically

on gui_message(gui_button("Launch")):
    # runs when "Launch" button is pressed
    launch_fighter()

on signal signal_name:
    # runs when signal fires
    update_display()
```

### GUI layout

```
gui_section(style="area:0,0,100,100;")
gui_row("row-height:2em;")
gui_text("Display text")
gui_button("Button text")
gui_blank()                    # spacer
"""Inline text label"""        # triple-quoted string = GUI text in layout context
"""{variable} items loaded"""  # f-string style interpolation in triple-quoted text

# Named sub-section — fill it later with `with content:`
content = gui_sub_section()
with content:
    gui_text("Injected here")

# Reusable style
row_style = gui_style_def("row-height: 1.5em; padding: 6px, 0, 2px, 6px;")
gui_row(row_style)
```

### Widgets

```
# Dropdown — bound to a variable, displays current value
todo = gui_drop_down("text: {menu}; list: arc, line, box", var="menu")
on gui_message(todo):
    jump rebuild_gui

# List box — single or multi-select
lb = gui_list_box(items, "row-height: 1em;", item_template=my_template, select=True)
lb.set_selected_index(0, False)
selected = lb.get_value()
selected_list = lb.get_selected()   # multi=True
lb_index = lb.get_selected_index()

on change lb.value:
    item = lb.get_value()

# Checkbox
cb = gui_checkbox("text: {label}; state: {enabled}", style)
on gui_message(cb):
    enabled = not enabled

# Integer slider
sl = gui_int_slider("low: 0; high: 10;", style)
on gui_message(sl):
    val = sl.value

# Clickable icon
ib = gui_icon("icon_index: 137; color: white;", style="click_tag: menu; click_background: #6666")
on gui_click(ib):
    jump menu_label

# Face / avatar display
the_face = gui_face(face_string)
the_face.value = new_face_string
# gui_represent(the_face)  # deprecated — dirty system handles re-render automatically
```

### `on gui_click` vs `on gui_message`

- `on gui_message(element):` — fires when the element's **value changes**
- `on gui_click(element):` — fires when the element is **clicked** (for icons and elements with `click_tag`)

### Widget `data={}` and `__ITEM__`

Pass a `data={}` dict to inject local variables into the handler. `__ITEM__` is the widget that fired:

```
for i, widget in enumerate(widgets):
    sl = gui_int_slider("low: 0; high: {widget['max']};", style, data={"windex": i})
    on gui_message(sl):
        values[windex] = __ITEM__.value
```

### Updating without rebuilding

```
widget.value = new_value
# The dirty system automatically re-renders changed widgets — gui_represent() is deprecated (safe but redundant)
```

### Full GUI rebuild

```
gui_reroute_server(label)      # redirect all clients to a new label
gui_refresh("label_name")      # same, by string name
```

### Inline buttons inside `await gui()`

```
await gui():
    * "Apply":                 # * = consumed after click
        do_action()

jump next_label                # runs after button is pressed
```

### `match / case`

Python 3.10+ match syntax works in MAST:

```
match menu:
    case "arc":
        jump edit_arc
    case "sphere":
        jump edit_sphere
```

---

## Route Types

| Route | Triggered by |
|---|---|
| `//spawn` | Object spawned |
| `//spawn/grid` | Grid object spawned |
| `//comms` | Comms opened (root menu) |
| `//comms/path` | Comms submenu |
| `//signal/name` | `signal_emit("name", ...)` |
| `//shared/signal/name` | Signal, fires for all clients/tasks |
| `//damage/object` | Object takes damage |
| `//damage/destroy` | Object destroyed |
| `//damage/killed` | Object killed |
| `//damage/internal` | Internal damage |
| `//damage/heat` | Heat damage |
| `//collision/passive` | Passive collision |
| `//collision/interactive` | Interactive collision |
| `//dock/hangar` | Docking event |
| `//launch/missile` | Missile launched |
| `//launch/drone` | Drone launched |
| `//focus/comms` | Console focus changed |
| `//focus/science` | Science focus |
| `//focus/weapons` | Weapons focus |
| `//focus/normal` | Normal focus |
| `//focus/grid` | Grid focus |
| `//select/...` | Object selected |
| `//point/...` | Point interaction |
| `//console/change` | Console changed |
| `//object/grid` | Object on grid |
| `//gui/tab/Name` | GUI tab selected |

Routes can have conditions: `//route/path if condition`

---

## Built-in Context Variables

Set automatically by the engine before a route fires:

```
# Comms
COMMS_ORIGIN_ID, COMMS_ORIGIN
COMMS_SELECTED_ID, COMMS_SELECTED

# Spawn
SPAWNED_ID, SPAWNED
START_X, START_Y, START_Z

# Damage
DAMAGE_TARGET_ID, DAMAGE_ORIGIN_ID, DAMAGE_SOURCE_ID, DAMAGE_PARENT_ID
DESTROYED_ID  (for //damage/destroy)

# Brain / Objective
BRAIN_AGENT_ID, BRAIN_AGENT
OBJECTIVE_AGENT_ID, OBJECTIVE, OBJECTIVE_AGENT

# Science
SCIENCE_ORIGIN_ID, SCIENCE_SELECTED_ID
SCIENCE_ORIGIN, SCIENCE_SELECTED

# General
EVENT                   # event object (.parent_id, .sub_tag, etc.)
client_id               # client performing the action
```

---

## Python Inline (`~~`)

`~~ expr ~~` embeds Python the MAST parser cannot handle natively.

**Do NOT use `~~` for:** regular function calls, assignments, if statements, for loops.

**DO use `~~` for:** complex dict/set literals and other syntax the parser specifically fails on:

```
g = ~~ {"x": pos_x, "y": pos_y, "name": item_name} ~~

avatar_widgets = ~~{
    "terran": [{"label": "Eyes", "min": 0, "max": 9}],
    "skaraan": [{"label": "Eyes", "min": 0, "max": 4}]
}~~
```

---

## Common Idioms

### Early exit
```
->END if obj is None
->END if not has_role(SPAWNED_ID, "ship")
```

### Conditional jump / loop
```
jump loop if not is_timer_finished(id, "meeting_count")
```

### Inventory as blackboard
```
set_inventory_value(ship_id, "blackboard:target", target_id)
target_id = get_inventory_value(ship_id, "blackboard:target")
count = get_inventory_value(ship_id, "hp", 100)   # with default
```

### Timer pattern
```
set_timer(id, "warmup", 25)
set_timer(id, "cooldown", minutes=2)
yield fail if not is_timer_finished(id, "warmup")
jump loop if not is_timer_finished(id, "meeting_count")
t = format_time_remaining(id, "warmup")
```

### Object existence check
```
->END if not object_exists(ship_id)    # guard before reading data from a ship
```

### Read a data_set value procedurally
```
alert_state = get_data_set_value(ship_id, "red_alert", 0)           # with default
dock_state  = get_data_set_value(ship_id, "dock_state", "undocked")
```

### Vec3 unpacking
```
npc_spawn(*Vec3(1000, 0, 1000), "Name", "tsn", "art", "behav_station")
# equivalent to: npc_spawn(1000, 0, 1000, ...)
```

### Set operations
```
role("ship") & role("friendly")          # intersection
role("enemy") - role("surrendered")      # subtraction
any_role("__player__,admiral")           # any of multiple roles
```

### Log

From `sbs_utils.procedural.execution`. Preferred over `print()`.

```python
# signature: log(message, name=None, level=None)
log("Game started")
log(f"{upgrade_name} spawned at {x},{y},{z}", "upgrades")
log("Spawn failed", "spawn", "warning")
```

---

## Additional Loop Forms

### `for x while condition:`

A loop with an inline exit condition — stops when condition is false rather than iterating a fixed count:

```
for x while d > 1000:
    await delay_sim(4)
    ->END if to_object(artemis_id) is None
    d = sbs.distance_id(artemis_id, target_id)
```

---

## Task Introspection

### `mast_task` — current task reference

Inside a label, `mast_task` is the current running task. Store it in a shared variable for debug access or external control:

```
shared main_story_task = mast_task   # in @map body

# From a debug comms route:
main_story_task.jump("scene_two")    # redirect the task to a different label
```

---

## Things NOT in MAST

- XML scripting (that was the old SBS game)
- `~~` around regular function calls
- Routes inside labels (routes are always top-level)
- Function-style return values from labels (use `yield result` or task data)
- Standalone quoted strings outside page contexts (use `log()` or `print()`)

---

## PyMAST — Python Generator Labels

An alternative to `.mast` files: Python generator functions decorated with `@label()`. Used in tool-style missions like `remote_mission_pick`.

```python
from sbs_utils.mast.label import label
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural.execution import AWAIT, jump, get_shared_variable, set_shared_variable
from sbs_utils.procedural.timers import timeout

@label()
def main_gui():
    # build GUI
    yield AWAIT(gui({"ok": confirm}))

@label()
def confirm():
    yield AWAIT(gui({"back": main_gui}, timeout=timeout(10)))
    yield jump(main_gui)

class SimpleAiPage(StoryPage):
    story = MastStory()       # empty story — no .mast file
    main_server = main_gui
    main_client = main_gui
```

### Translation table

| MAST | PyMAST |
|---|---|
| `await gui(...)` | `yield AWAIT(gui(...))` |
| `jump label_name` | `yield jump(label_fn)` |
| `await delay_sim(5)` | `yield AWAIT(delay_sim(5))` |
| `shared x = val` | `set_shared_variable("x", val)` |
| Read shared var | `get_shared_variable("x")` |

### GUI callbacks

`gui_message_callback(widget, fn)` registers a Python function for widget events (replaces MAST's `on gui_message`):

```python
lb = gui_list_box(items, "", item_template=render, select=True)
gui_message_callback(lb, lambda event, sender: handle_select(lb, items))
yield AWAIT(gui({"start": start_fn}))
```

### `MastDataObject`

Wraps a plain dict so keys are accessible as attributes. `obj.get("key", default)` reads safely:

```python
item = MastDataObject({"name": "Scout", "hp": 100})
item.name          # "Scout"
item.get("hp", 0)  # 100
# item["hp"] raises TypeError — always use .get() or attribute access
```

### Launching another mission

```python
sbs.run_next_mission(mission_folder_name)   # loads and starts a different mission
```
