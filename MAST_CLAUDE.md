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
    await signal_next("start")
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

**Top-level `shared` statements run only once.** After first execution they are converted to no-ops so subsequent clients don't re-run them. Because the server client runs first, top-level `shared` assignments are effectively server-initialized.

### `default shared`

Combines both: cross-task scope, only set if not already set.

```
default shared GAME_STARTED = False
default shared PLAYER_COUNT = 2
default shared SETTINGS = settings_get_defaults()
```

### `shared`, `assigned`, `client`, `temp` are SCOPE KEYWORDS - never variable names

The Assign rule is `(shared|assigned|client|temp)\s+<lhs> = <expr>`, so a variable with
one of those names is parsed as **a scope with an empty target**:

```
assigned = sbs.get_ship_of_client(client_id)   # assigns to NOTHING. No error.
ok = assigned == foe_id                        # NameError: 'assigned' is not defined
```

**The failure is reported against the line that READS it**, not the line that assigned
it, so it reads as "this variable vanished". `client_id` and `shared_state` are fine -
the keyword only matches with whitespace after it.

### Variable naming conventions

- **CAPS_STYLE** (`SHIP_ID`, `COMMS_ORIGIN_ID`, `DAMAGE_TARGET_ID`) — system-defined context variables injected by the engine or route system. Don't use this style for script-defined variables.
- **snake_case** (`ship_id`, `enemy_id`, `fleet_obj`) — script-defined variables. Follow Python conventions since most evaluation runs through Python `eval`/`exec`.

### Scope rules

- Variables are scoped to the **task**, not the label.
- A variable set in `== setup ==` is accessible after `jump main` in the same task.
- `shared` variables are accessible from any task in the story.
- Scope is more nuanced than this — treat as a topic to expand.

### Assigning a string re-formats it as an f-string

Every assignment whose value is a **string** gets run through f-string formatting
(`core_nodes/assign.py` → `compile_and_format_string`). That is the feature behind
`greeting = "Hello {name}"`, but it applies to a **function's return value** too:

```
cost = recipe_inputs_text(recipe)   # returns "{'salvage': 5}" -> RUNTIME ERROR
```

A `{` in returned text the author never sees is a `SyntaxError: f-string: expecting
'}'` at the assignment line, reported against your code, not the function's. So a
helper that formats text for display must not emit braces — and if data *might*
contain them, hold it somewhere other than a bare MAST assignment (pass it straight
to the widget, or keep it in a dict/list). Applies only to strings: a dict, list, or
number assigns untouched.

---

## `await`

Suspends the current task until a condition is met, then resumes at the next line.

```
== main ==
    await delay_sim(5)
    await delay_app(2)                              # real-world seconds
    await distance_less(phoenix_id, amb_id, 400)
    await signal_next("enemy_destroyed")           # one-shot: resume on next emit (data = result)
    await task_schedule(spawn_players)              # wait for spawned task to finish
    await is_timer_finished(id, "WARMUP")
    ->END
```

`await signal_next(name)` is a one-shot wait for the **next** `signal_emit(name)`;
its result is the emitted data. Loop it to react repeatedly, or use a
`//signal/<name>` route for persistent reaction. Composes with `promise_any`
(`await promise_any(signal_next("docked"), delay_sim(30))`) or takes a `timeout`.

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

Metadata is a data section embedded in a label. Its values are **injected as task
variables** when a task enters the label — seeded at task creation for spawned
tasks (brains/objectives/prefabs) and injected on a jump/reroute into the label
(e.g. a GUI route). Systems can also read metadata off the label **before** it
executes (`get_inventory_value`). Metadata values are **defaults**: a variable
already in scope (passed schedule/spawn data, live state) wins.

**Fence indentation (this bites):** the `metadata:` line, the top-level YAML keys,
and the **closing ` ``` ` fence must be at column 0** — the parser's rule ends in
`\n``` ` with no leading whitespace. Indent the whole block and you get
"Unrecognized syntax". The label's *code* is indented as usual; YAML-internal
nesting is indented per YAML. (Metadata works on any label type, including `@`
decorator labels and `//` routes.)

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

### Prefix every function an addon defines

Every top-level `def` in an addon's `.py` becomes a **MAST global in one flat,
mission-wide namespace**, and `MastGlobals.register_mission_functions` assigns into it
**unconditionally** - no warning, last loaded wins. Two addons that both define
`market_sell_price` therefore compile clean and blow up at **runtime**, in whichever
addon *lost*, with a signature error against a line that looks correct. Load order is
non-deterministic, so it is intermittent.

**Prefix every module-level function with the addon's name** - the `hangar` addon is the
model: `hangar_get_stats`, `hangar_launch_craft`, private `_hangar_bump`. Reserve an
unprefixed concept name (`market_*`) for the ONE addon that owns that concept, and never
let two co-loaded addons share a prefix (`fleet_` was claimed by both LM `fleets` and OU
`admiral` until the latter became `admiralty_fleet_*`).

Three things that surprise people:

- **A leading underscore is not private.** `_dist` is exported exactly like `dist`.
- **Only functions are exported** - a module-level list/dict/constant is never a MAST
  global, so every `.mast` touchpoint must be an accessor function.
- **A re-export is not exported.** `from sbs_utils... import foo` keeps the library's
  `__module__`, so it is not registered - which also makes "delete the local copy and
  import the library one" the clean fix for a function that shadows a library global.

`sbs lint` enforces this (`namespace_lint.py`): `ns-duplicate-function` and
`ns-shadows-library` are errors, `ns-mast-var-collision` catches the
`Variable assignment to a keyword` compile error that silently empties a whole story,
and `ns-generic-name` warns on bare `get_`/`save_`/`build_` names. Suppress a
deliberate one with `# lint: allow ns-generic-name`.

### Addon dependencies (`provides` / `requires` / `suggests`)

Addons share one global MAST namespace and load in a **non-deterministic order**, so
"addon A uses a global/route from addon B" is fragile. Three top-level directives make
the contract explicit and checkable at **compile time**:

- **`provides <token>`** — this addon supplies a capability. Tokens are opaque strings
  (dotted by convention): `provides hangar`, `provides hangar.sortie_board`.
- **`requires <token>`** — HARD dependency. If no loaded addon provides the token, the
  story **fails to compile** (a clear error, surfaced by `sbs lint` / `--test` and as a
  runtime error screen).
- **`suggests <token>`** — SOFT dependency (optional augmentation). If unmet, a warning
  is logged and compilation continues.

Put them at the top of the addon's `__init__.mast` (column 0, like `import`); multiple
per line is fine (`provides casino, casino.bar`).

```
# hangar_sorties/__init__.mast — augments the hangar, but works standalone
provides hangar.sortie_board
suggests hangar             # warn (never fail) if the hangar isn't loaded

# gamemaster_comms/__init__.mast — meaningless without the GM console
requires gamemaster
```

Collection is **order-independent**: the compiler gathers every `provides` into a
story-level union as files compile, then validates `requires`/`suggests` once, after
the whole set has compiled — so it never matters which order addons load in. Use
`requires` for a hard coupling (you call the other addon's globals/routes, or your
feature is meaningless without it); use `suggests` for an optional augmentation (the
casino / hangar_sorties pattern, guarded with `default shared X = None` so it degrades
gracefully). These are compile-time only — no runtime effect. **Backward compatible:** a
line is a directive only when a token follows the keyword, so `requires = 5` is still an
assignment.

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
        <<[green] "Hail"
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
<<[green] "Title"
    % First possible line
    % Second possible line     # system picks one randomly
    % Third possible line

<<[$raider] "Hostile Hail"
    % Go climb a tree!
    % You can't win!

>> "Player response"
    % Understood, moving out.
```

`%` lines are random dialogue options — one is picked at random each time.

**Three syntax rules the examples above are easy to get wrong**, each measured against the
compiler rather than inferred:

- **No space between `<<`/`>>` and `[format]`.** `comms_message.py`'s `FORMAT_EXP` is
  `(\[(?P<format>...)\])?` with no leading whitespace, so `<< [green] "Hi"` matches only the
  bare `<<`, leaving `[green] "Hi"` to fail as *"Unrecognized syntax"* on its own line.
  Write `<<[green] "Hi"`.
- **No space after `=$`.** The rule is `\=\$(?P<name>\w+)`, so `=$ raider red, white` is
  `invalid syntax (<string>, line 1)`. Write `=$raider red, white`.
- **A `%` line cannot wrap.** MAST parses line by line, so an indented continuation of a long
  `%` line is an orphan and fails as *"Unrecognized syntax"* reported against the
  CONTINUATION, not against the `%`. Keep each `%` on one line however long it gets.

Other types: `<all>` (broadcast), `<scan>` (science scan result), `()` (speech bubble).

### Color style variables

`=$` declares a named color/style for use in comms dialogue:

```
=$raider red, white
=$friendly green

<<[$raider] "Hail"
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

**Refreshing an open comms menu from OUTSIDE the comms task.** When game state
changes (a build finishes, a new option unlocks), an already-open comms menu is
stale. `comms_navigate_override(origin, selected, path=None)` re-runs the comms
routes for that origin/selected pair, so the new buttons appear immediately — and
it **no-ops if that pair isn't currently in a comms interaction**, so it's safe to
call broadly. Scope it to the right consoles (e.g. `role("admiral_cam") &
role(side)`), never all clients.

```
# from a build task, when a platform finishes:
comms_navigate_override(role("admiral_cam") & role(side), worldlet_id)
```

`follow_route_select_comms(origin, selected)` (procedural/routes) fires a comms
*selection* programmatically — as if the player clicked that object.

---

## GUI System

> **Invoke the `cosmos-gui` skill for GUI best practices & gotchas** — the dirty system / live
> updates, `.update()` replacing the whole style, listbox+detail pattern, the
> for-loop handler trap, engine-widget embedding, and the compiler-vs-mock traps.
> This section is the quick syntax; the skill is how to build GUIs well.

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

> **`//signal` vs `//shared/signal` — the #1 multiplayer footgun.** `//signal` runs its
> body **once per connected console** (plus the server); `//shared/signal` runs **only on
> the server, once**. Litmus test: *"with five consoles, do I want this five times?"* If the
> route **spawns, saves, rewards, applies a modifier, counts, ends the game, rolls random, or
> starts a server ticker → `//shared/signal`.** Only per-console **display** (a GUI screen /
> widget) stays `//signal`. `comms_broadcast`/`comms_message`/`info_card` are server sends —
> call them once. Need both? Split: `//shared/signal` does the work + `signal_emit`s a display
> signal a `//signal` route paints. Full rule + the split pattern: **`SIGNAL_ROUTING.md`**.
> `sbs lint` flags side-effects in a `//signal` route.

> **Second axis: how many times is it EMITTED?** `//shared/signal` is server-once **per
> emit** — it says nothing about how often the signal fires. Emit an init signal twice and
> the body runs twice (`create_default_player_ships` emitted from inside its own loop; a
> re-entered `start_server` took a session from 8 player ships to 33). **Prefer identity:**
> `player_ensure(slot, ...)` / `side_ensure(key)` create only what is missing, so an
> accidental re-emit is a no-op *and* a deliberate one (respawn, reset, late joiner,
> post-`sim_create` rebuild) still works. With no natural key, mark the route
> **`once`** — `//shared/signal/give_starting_cash once`, `//signal/show_intro once if X`
> — at most one run per mission; the `if` is tested first so a false condition keeps the
> shot; `signal_once_reset("name")` re-arms, and a mission reload re-arms automatically.
> **Never `once` a route that REPAIRS engine state** — `create_sides` must stay re-runnable
> because `sim_create()` leaves the sim handle stale for the rest of the frame. `sbs lint`
> adds `signal-init-unkeyed-spawn`, `signal-emit-in-loop`, `signal-multi-emit`.

| Route | Triggered by |
|---|---|
| `//spawn` | Object spawned |
| `//spawn/grid` | Grid object spawned |
| `//comms` | Comms opened (root menu) |
| `//comms/path` | Comms submenu |
| `//signal/name` | `signal_emit("name", ...)` — runs **once per connected console + server** |
| `//shared/signal/name` | `signal_emit("name", ...)` — runs **ONLY on the server** (once) |
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

**Never span a bare `{}`/dict across lines.** MAST parses **line by line**, so a
dict literal broken across lines — even as a normal function argument — makes the
first line an unclosed `{`:

```
# BROKEN — compiles to "'{' was never closed", then cascades:
prefab_spawn("prefab_fleet_raider", {
    "race": "skaraan",
    "fleet_difficulty": 4
})
```

**The failure is silent and cascading.** The unclosed-brace error desyncs the parser
for the rest of the file (spurious "Weighted text without start" / "Unrecognized
syntax" on the continuation lines), which can leave the **whole story's main task
empty** — the mission then runs with **0 labels executed, no output, and still
reports "PASS - no runtime errors"** (a headless `--test` shows `labels 0/N`). If a
mission mysteriously does nothing, suspect a multi-line literal first.

**`~~ … ~~` is a STATEMENT form, not a sub-expression.** Inline in a call argument
it is a compile error — `invalid syntax (<string>, line 1)`, reported against the
whole line:

```
# BROKEN:
gui_properties_set(~~{"Heading": "gui_text(str(h))"}~~)

# Bind it first:
props = ~~{"Heading": "gui_text(str(h))"}~~
gui_properties_set(props)
```

Two fixes — keep it on **one line**, or wrap the multi-line literal in `~~ … ~~`
(as the `avatar_widgets` example above; multi-line *is* fine inside `~~`):

```
# both compile:
fleet_data = ~~{"race": "skaraan", "fleet_difficulty": 4, "START_X": x, "START_Y": y, "START_Z": z}~~
prefab_spawn("prefab_fleet_raider", fleet_data)
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

## Detached command consoles (GM / Admiral pattern)

A console that oversees the whole system from a god's-eye 2D view (Game Master,
the OU Admiral) rides a **detached camera**, not a ship. The pattern (see LM
`gamemaster.mast` and OU `admiral.mast`):

```
# Per client: an invisible camera the console rides.
cam = to_object(player_spawn(0, 1000, 0, "", "#,admiral_cam,admiral,has_science_scan", "invisible"))
remove_role(cam, "__player__")                       # not a real player ship
link(cam.id, "extra_scan_source", any_role("__npc__,__player__"))  # sees everything
cam.side = "tsn"
cam.data_set.set("ship_base_scan_range", 40000, 0)   # see the whole system
sbs.assign_client_to_ship(client_id, cam.id)
gui_activate_console("gamemaster_overseer_comms")    # see naming note below
gui_layout_widget("comms_2d_view")                   # embed the engine 2D view
```

**Selection routing depends on the CONSOLE NAME** (`consoledispatcher.py`): a name
containing `"sci"` or `"admiral"` routes a 2D-view click to the **science**
selection; `"comm"` routes it to the **comms** selection (which the `//comms`
routes need). A `gamemaster_` **prefix** also gets the engine's optimized
detached-console network path. So `gamemaster_overseer_comms` = optimized network +
comms selection. (The console *name* is separate from the camera's *role* — the
GM/Admiral routes gate on the `gamemaster`/`admiral` role, not the name.)

**Comms won't OPEN on an object the side has no science data for.**
`science_set_scan_data(origin, target, tabs)` stores the scan **per the origin's
side** (side-wide, not per-console), so one pass marks a whole side's objects
"known". Scan the console's own theatre (its worldlets/platforms/fleets) once so
comms enables on the first click.

**Click-to-move the camera.** `//focus/comms` (and `//focus/science`) fire on a 2D
click carrying `EVENT.source_point` (the clicked point) and `EVENT.extra_extra_tag`
(`lmb`/`rmb`). Set the origin's `.pos` to pan: `COMMS_ORIGIN.pos =
Vec3(EVENT.source_point)`.

**Roles come from the ART too.** Spawning with a starbase art auto-adds the
`station` role from that art's ship_data — so `remove_role(obj, "station")` **after**
spawn if you don't want LM's default station comms (docking/market) on the object.

**IDE-linter false positive:** a `+ "label" handler_label` comms button (no data
dict) may flag *"Missing required argument(s): 'fields'"* in the editor — the real
MAST compiler accepts it. Verify with a headless `--test`, not the linter.

---

## Things NOT in MAST

- XML scripting (that was the old SBS game)
- `~~` around regular function calls
- Routes inside labels (routes are always top-level)
- Function-style return values from labels (use `yield result` or task data)
- Standalone quoted strings outside page contexts (use `log()` or `print()`)

**Tuple unpacking — now SUPPORTED** (2026-07-04). `a, b = expr` (Assign node) and
`for a, b in enumerate(xs):` (Loop node) both work for plain comma-separated names:
```
i, j = ship_cell(id)
for idx, ship in enumerate(to_object_list(role("__player__"))):
    ...
```
A tuple target carrying `.`/`[` (e.g. `a, obj.x = ...`) still falls through to the old
exec path; a length mismatch raises. (Before this, the assignment silently set a var
literally named `"a, b"`, and the `for` form **desynced the parser** — whole story
empty, `labels 0/N`, still "PASS". If you hit that on an OLDER sbslib, use the index
workaround: `c = ship_cell(id); a = c[0]; b = c[1]`.) Covered by
`sbs_utils/tests/test_tuple_unpack.py`.

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
