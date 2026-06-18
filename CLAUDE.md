
# sbs_utils — Library Reference for Claude

## Operating Environment

This library runs inside **Artemis Cosmos** (referred to as "Cosmos"), a space ship bridge simulation game. Cosmos embeds Python 3.11 via Pybind11.

### Hard constraints (must be respected)
- No pip-installable packages
- No threading
- No asyncio

### Engine interaction

Cosmos calls `script.py` once at startup to bootstrap the embedded Python environment. All subsequent interaction is event-driven via a single entry point defined in `sbs_utils/handlerhooks.py`:

```python
cosmos_event_handler(sim, event)
```

**`sim`** — An `sbs.simulation` instance passed in by the engine. Provides access to simulation state.  
**`sbs`** — The Pybind11 API module, imported inside the handler (`import sbs`). Exposes callable functions to control the engine (e.g., `send_gui_*`, spawning objects, simulation control).  
**`event`** — The event object with fields: `client_id`, `tag`, `sub_tag`, `origin_id`, `selected_id`, `parent_id`, `value_tag`, `extra_tag`, `extra_extra_tag`, `sub_float`, `source_point`, `event_time`.

`client_id == 0` is always the server. Client IDs > 0 are connected player consoles.

---

## About Artemis Cosmos

Artemis Cosmos is a new version of "Artemis Spaceship Bridge Simulator" (abbreviated **SBS**). Key distinctions:

- **Artemis Cosmos** = the current game this library targets
- **SBS** = the old game; do not confuse the two
- **No XML scripting** — the old SBS used XML-based scripts; Cosmos does not. When discussing scripting, this always means MAST (below), never the old XML approach.

---

## Entry Point and Event Flow

`cosmos_event_handler` dispatches `event.tag` to the appropriate dispatcher(s), then calls `tick_the_rest(event)` (runs `TickDispatcher` + `Gui.present`) for most events, followed by `GarbageCollector.collect()` and `Dirty.represent_dirty()`.

### Key event tags

| `event.tag` | Dispatched to |
|---|---|
| `mission_tick` | `TickDispatcher`, `LifetimeDispatcher`, `Gui.present` |
| `damage` / `npc_killed` / `station_killed` | `DamageDispatcher` / `LifetimeDispatcher` |
| `gui_message` | `Gui.on_message` |
| `client_connect` / `client_change` | `Gui.add_client` / `Gui.on_event` |
| `screen_size` | `FrameContext.aspect_ratios`, `Gui.on_event` |
| `passive_collision_*` / `interactive_collision_*` / `within_range` | `CollisionDispatcher` |
| `select_space_object` / `hold_click` / `hold_button_pressed` / `science_scan_complete` | `ConsoleDispatcher` |
| `press_comms_button` | `ConsoleDispatcher` |
| `grid_object` / `grid_object_selection` / `press_grid_button` / `grid_point_selection` | `GridDispatcher`, `ConsoleDispatcher` |
| `player_launches_missile` / `ship_launches_drone` | `LaunchDispatcher` |
| `fighter_requests_dock` / `press_fighter_button` / `docking_change` | `LifetimeDispatcher`, signal/docking |
| `red_alert` | `signal_emit("red_alert_change", ...)` |
| `client_string` | `ClientStringDispatcher` |

---

## FrameContext

`FrameContext` (`sbs_utils/helpers.py`) is a metaclass-based per-frame global providing access to:

- `FrameContext.context` — `Context(sim, sbs, event)` for the current event
- `FrameContext.page` — the currently active GUI `Page`
- `FrameContext.task` — the currently ticking MAST task
- `FrameContext.client_id` — shortcut to `event.client_id`
- `FrameContext.sim` / `FrameContext.sim_seconds` — simulation access
- `FrameContext.server_page` / `FrameContext.client_page` — page for server (id=0) or current client

Use `FrameContextOverride` as a context manager to temporarily override task/page/event during execution.

---

## Agent and SpaceObject

`Agent` (`sbs_utils/agent.py`) is the base class for all game objects. It provides:

- **Roles** — named sets of object IDs: `add_role("enemy")`, `has_role("enemy")`, `get_role_objects("enemy")`
- **Links** — uni-directional named associations: `add_link("target", other)`, `get_link_objects("target")`
- **Inventory** — named key→value storage: `set_inventory_value("health", 100)`, `get_inventory_value("health")`
- `Agent.all` — class-level dict of all live agents keyed by ID
- `Agent.SHARED` — singleton agent for global shared state
- `Agent.get(id)` — look up any agent by ID

`SpaceObject` (`sbs_utils/spaceobject.py`) extends `Agent` with engine-specific properties:

- `tick_type` (`TickType` enum: `PASSIVE`/`TERRAIN`, `ACTIVE`/`NPC`, `PLAYER`)
- `is_player`, `is_npc`, `is_terrain`, `is_active`, `is_passive` properties
- `spawn_pos`, `_name`, `_side`, `_ship_data_key`

---

## MAST Scripting Language

MAST is the primary scripting language for Cosmos mission authors. It lives in two parts:

### `sbs_utils/mast/` — Core language (generic, not Cosmos-specific)

- **`mast.py`** — Compiler: regex-based parser that produces a list of `MastNode` objects from `.mast` files
- **`mast_node.py`** — `MastNode` base class; each node type declares a `rule` (regex) and optionally overrides `parse()`
- **`mastscheduler.py`** — `MastScheduler` (like a process), `MastAsyncTask` (pseudo-coroutine), `MastTicker` (runs MAST nodes), `PyTicker` (runs Python generator functions)
- **`maststory.py`** / **`maststorypage.py`** — Story-level orchestration
- **`core_nodes/`** — Built-in node types: `label`, `jump`, `assign`, `if`/conditional, `loop`, `await`, `yield`, `on_change`, `on_signal`, `with`, `import`, inline python, inline functions, decorator labels, signal route labels

### `sbs_utils/mast_sbs/` — Cosmos-specific MAST extensions

- **`mastmission.py`** — Mission-level scheduler
- **`maststoryscheduler.py`** — Story scheduler for Cosmos
- **`maststorypage.py`** — Cosmos GUI page driven by MAST story execution
- **`mast_sbs_procedural.py`** — Procedural functions exposed to MAST scripts
- **`story_nodes/`** — Cosmos-specific nodes: `button`, `text`, `media`, `comms_message`, `card_base`, `card_map` (`@map` — discoverable label pattern), `route_label` (`//` routes), `inline_route` (`///`), `weighted_text`, `define_format`, GUI decorator/console labels

### MAST execution model

- Execution flows linearly through nodes, like BASIC or assembly — control changes via `jump` to a `label`
- At any point execution can **yield**, suspending the task and allowing other tasks to run
- On the next tick, the task resumes exactly where it left off (similar to coroutines but not identical)
- MAST calls Python freely via `eval`/`exec`; procedural functions bridge Python↔MAST
- Script files use `.mast` extension and are distributed as `.mastlib` zip files (added to the Python path at runtime)
- Every mission (server and each client) starts execution at `== main ==`

### MAST syntax quick reference

```
# Comment

# Labels — enclose name in 2+ equals signs
== main ==
== SomeSectionName ==

# Variables
x = 42
name = "hello"
shared enemy_count = 20          # shared = all tasks in story see it

# Complex python values use "snakes" (2+ tildes)
data = ~~ [[1,2],[3,4]] ~~

# Inline python expression (evaluate and discard)
~~ some_function() ~~

# Jump
jump SomeSectionName

# Conditional
if x > 5:
    jump BigX

# Loop
for x while condition:
    ...

# Await (suspend until done)
await delay_sim(seconds=5)

# Buttons — * = one-shot (consumed after click), + = sticky (stays visible)
* "Button label"            # goes to next label on click
* "Button label" LabelName  # jumps to LabelName on click
* "Button label":           # inline block on click
    jump SomeLabel

# Text / narration
"Some text shown to players"

# Route decorator labels — wire up engine events
//spawn                      # handles object spawn
//comms/path                 # handles comms message matching path
//science                    # handles science scan
//gui/tab/TabName            # handles GUI tab
//signal/my_signal           # handles custom signal
//shared/signal/my_signal    # signal shared across tasks
//damage/object              # handles damage event
//damage/destroy             # handles object destroyed
//damage/killed              # handles npc/station killed
//damage/internal            # internal damage
//damage/heat                # heat damage
//collision/passive          # passive collision
//collision/interactive      # interactive collision
//dock/hangar                # docking event
//launch/missile             # missile launched
//launch/drone               # drone launched
//focus/comms                # comms console focused
//focus/science              # science console focused
//focus/weapons / //focus/normal / //focus/grid
//select/comms / //select/science / //select/weapons / //select/normal / //select/grid
//point/comms / //point/science / //point/weapons / //point/normal / //point/grid
//console/change             # console type changed
//object/grid                # grid object event

# Inline route — named entry point within a label (not a label itself)
///sub_route_name

# Discoverable decorator labels — the @ prefix marks labels that procedural code
# can enumerate and present as choices. Multiple in one script = multiple options.
# The selected one is then scheduled and runs like any other label.

@map/path/name "Display Name"      # card-based tilemap; picker shows available maps
@media/kind/path "Display Name"    # media asset (audio/video/image); picker by kind
```

### Node registration — critical rule

New MAST node types are registered via the `@mast_node()` decorator which appends the class to `MastNode.nodes`. The compiler tries each rule in order and takes the **first match**.

- `@mast_node()` — appends to the end (lower priority, matched later)
- `@mast_node(append=False)` — inserts at the front (higher priority, matched first)

**Pitfall:** If a more-specific regex should win over a more-general one, the specific class must use `append=False` or be imported first. Wrong ordering causes the wrong node type to be silently matched, producing incorrect behavior with no error. The `mast_sbs/story_nodes/__init__.py` comment warns: "Order could matter due to mast_node placement."

Importing `mast_sbs` triggers node registration automatically via `story_nodes/__init__.py`.

### Backward compatibility rule
**Changes to the MAST language must rarely break existing scripts.** This is a primary constraint when modifying parsing or runtime behavior.

---

## Procedural API (`sbs_utils/procedural/`)

Functions callable from both Python and MAST scripts:

| Module | Purpose |
|---|---|
| `space_objects.py` | Create/manage space objects |
| `spawn.py` | Spawn objects into the simulation |
| `query.py` | Query objects by role, proximity, etc. |
| `signal.py` | `signal_emit()` — the pub/sub signal system |
| `inventory.py` | `get/set_inventory_value` wrappers |
| `ship_data.py` | Ship definitions and data lookup |
| `timers.py` | Timer management |
| `mission.py` | Mission-level helpers |
| `roles.py` | Role management helpers |
| `links.py` | Link management helpers |
| `objective.py` | Mission objectives |
| `quest.py` | Quest tracking |
| `routes.py` | Route handling |
| `popup.py` | Popup UI helpers |
| `science.py` | Science console helpers |
| `terrain.py` | Terrain object helpers |
| `torpedoes.py` | Torpedo management |
| `upgrades.py` | Ship upgrades |
| `prefab.py` | Prefab/template helpers |
| `gui/widgets.py` | GUI widget procedural helpers |
| `media.py` | Audio/video media |
| `maps.py` | Map helpers |
| `modifiers.py` | Object modifier helpers |
| `sides.py` | Side (faction) management |
| `settings.py` | Settings access |
| `style.py` | Style/theming |
| `lifeform.py` | Lifeform objects |
| `promise_functions.py` | Promise/async-style helpers |
| `internal_damage.py` | Internal damage system |

---

## GUI / Pages (`sbs_utils/pages/`)

Pages create GUIs for Cosmos clients by ultimately calling `sbs.send_gui_*` functions.

`Gui` (`sbs_utils/gui.py`) manages per-client GUI stacks — each client has a stack of `Page` objects; `Gui.push/pop` navigates between them.

- **`layout/`** — Layout-based components: `button`, `text`, `text_area`, `text_input`, `image`, `icon`, `icon_button`, `checkbox`, `radio_button`, `dropdown`, `slider`, `row`, `column`, `layout_page`, `clickable`, `face`, `ship`, `console_widget`, `blank`, `hole`
- **`widgets/`** — Higher-level composites: `tabbed_panel`, `layout_listbox`, `shippicker`
- **`avatar.py`** — Avatar display page
- **`start.py`** — Startup/mission selection page
- **`shippicker.py`** — Ship selection page

---

## Dispatcher System

Dispatchers route engine events to registered Python handlers:

| Dispatcher | File | Purpose |
|---|---|---|
| `TickDispatcher` | `tickdispatcher.py` | Per-tick callbacks |
| `LifetimeDispatcher` | `lifetimedispatcher.py` | Object spawn/destroy/dock events |
| `DamageDispatcher` | `damagedispatcher.py` | Damage, kills, heat, internal damage |
| `CollisionDispatcher` | `damagedispatcher.py` | Passive/interactive/range collisions |
| `ConsoleDispatcher` | `consoledispatcher.py` | Console selection, button presses, science scan |
| `GridDispatcher` | `griddispatcher.py` | Grid object events |
| `LaunchDispatcher` | `launchdispatcher.py` | Missile/drone launches |
| `GarbageCollector` | `garbagecollector.py` | Cleanup of destroyed objects |
| `HotkeyDispatcher` | `extra_dispatcher.py` | Hotkey events |
| `ClientStringDispatcher` | `extra_dispatcher.py` | Client string events |

---

## Other Key Files

| File | Purpose |
|---|---|
| `sbs_utils/helpers.py` | `FrameContext`, `Context`, `FakeEvent`, `FrameContextOverride`, `split_props`, `merge_props`, `format_exception` |
| `sbs_utils/vec.py` | `Vec3` 3D vector class |
| `sbs_utils/futures.py` | `Promise` and `Waiter` for async-style patterns |
| `sbs_utils/scatter.py` / `scattervec.py` | Scatter/distribution helpers |
| `sbs_utils/faces.py` | Face/portrait management |
| `sbs_utils/gridobject.py` | Grid object base class |
| `sbs_utils/map.py` | Map system |
| `sbs_utils/fs.py` | `get_mission_name`, `get_startup_mission_name` |
| `sbs_utils/gui.py` | `Gui` manager, `Page` base class |
| `sbs_utils/spaceobject.py` | `SpaceObject`, `TickType` |
| `sbs_utils/version__.py` | Library version |

---

## Folder Layout

```
sbs_utils/              # Root: entry point, dispatchers, core classes
├── mast/               # MAST language core (generic)
│   └── core_nodes/     # Built-in MAST node types
├── mast_sbs/           # Cosmos-specific MAST extensions
│   └── story_nodes/    # Cosmos MAST node types
├── pages/              # GUI page and layout system
│   ├── layout/         # Layout-based GUI components
│   └── widgets/        # Higher-level composite widgets
├── procedural/         # Procedural API (Python and MAST callable)
│   └── gui/            # GUI procedural helpers
├── cards/              # Deck/card system (tilemaps, ASCII maps)
├── mock/               # Partial mock of sbs pybind11 API (for tests)
├── proxies/            # Obsolete — ignore
├── yaml/               # Modified pyyaml copy (no pip available)
└── typings/            # Output: .pyi stubs for IDE support (not source)

tests/                  # Unit tests (pytest)
mkdocs/                 # Documentation source (MkDocs → GitHub Pages)
typings/                # Output: IDE typings (not source)
```

---

## Testing

```bash
pytest
```

Run from the repo root. Some test coverage exists but needs improvement. `sbs_utils/mock/` provides a partial mock of the `sbs` pybind11 API for tests that run without the engine.

---

## Packaging

The library is packaged as a `.sbslib` file — a zip of the `sbs_utils` package renamed to `.sbslib`. Use the `sbs.pyz` command-line utility (located outside this repo) to build it.

`.mastlib` files follow the same pattern: a zip of `.mast` script files, added to the Python path at runtime.

---

## Developer Tools

- **`auto_run.py`** — Windows-only helper that launches multiple Artemis Cosmos instances (Server, comms, weapons, science, engineering, cinematic) for local multi-client testing
- **`script.py`** / **`script_min.py`** — Entry script(s) called by Cosmos at startup to bootstrap Python
- **`demo.py`** — Scratch/demo file

---

## `sbs` Module Quick Reference (Pybind11 API)

The `sbs` module is exposed by Cosmos via Pybind11. Key categories:

- `sbs.send_gui_clear`, `send_gui_text`, `send_gui_button`, `send_gui_complete`, … — GUI rendering
- `sbs.send_comms_selection_info`, `send_grid_selection_info` — Console UI
- `sbs.get_ship_of_client(client_id)` — Map client to ship ID
- `sbs.run_next_mission(name)`, `pause_sim()`, `resume_sim()` — Simulation control
- `sbs.simulation` — The simulation instance type (what `sim` is in the event handler)

`sbs_utils/mock/` contains a partial implementation for testing. `typings/` contains `.pyi` stubs for IDE autocompletion.
