# sbs_utils — Library Reference for Claude

@MAST_CLAUDE.md
@MAST_MISSION_CLAUDE.md

## Environment

Runs inside **Artemis Cosmos** — a space ship bridge simulator. Python 3.11 embedded via Pybind11.

**Hard constraints:**
- No pip-installable packages (bundled `yaml/` is the exception)
- No threading, no asyncio

**Cosmos ≠ old SBS** — the old game used XML scripts; Cosmos uses MAST (Python-based). Never reference XML scripting.

---

## Engine Entry Point

Cosmos calls `script.py` at startup, then drives everything through one event handler (`sbs_utils/handlerhooks.py`):

```python
cosmos_event_handler(sim, event)
```

- **`sim`** — `sbs.simulation` instance
- **`sbs`** — Pybind11 API module (`import sbs` inside the handler)
- **`event`** — fields: `client_id`, `tag`, `sub_tag`, `origin_id`, `selected_id`, `parent_id`, `value_tag`, `extra_tag`, `extra_extra_tag`, `sub_float`, `source_point`, `event_time`
- **`client_id == 0`** = server. Client IDs > 0 = connected player consoles.

`cosmos_event_handler` dispatches `event.tag` to the appropriate dispatcher, then calls `tick_the_rest(event)` → `TickDispatcher` + `Gui.present`, then `GarbageCollector.collect()` and `Dirty.represent_dirty()`. See `handlerhooks.py` for the full dispatch table.

---

## Core Abstractions

**`FrameContext`** (`helpers.py`) — metaclass-based per-frame global:
- `.context` — `Context(sim, sbs, event)` for the current event
- `.client_id`, `.sim`, `.sim_seconds`, `.page`, `.task`, `.server_page`, `.client_page`
- Use `FrameContextOverride` to temporarily override task/page/event.

**`Agent`** (`agent.py`) — base class for all game objects:
- **Roles** — named sets of IDs: `add_role("enemy")`, `has_role("enemy")`
- **Links** — uni-directional associations: `add_link("target", other)`
- **Inventory** — key→value store: `set_inventory_value("hp", 100)`, `get_inventory_value("hp")`
- `Agent.all` — class-level dict of all live agents; `Agent.SHARED` — global singleton; `Agent.get(id)`

**`SpaceObject`** (`spaceobject.py`) — extends `Agent` with `tick_type` (`PASSIVE`/`TERRAIN`, `ACTIVE`/`NPC`, `PLAYER`), `is_player`, `is_npc`, `is_terrain`, etc.

**`MastDataObject`** (`mast/mast_node.py`) — dict-to-object shim. Stores values as **attributes**, not dict items.
- Use `obj.get(key, default)` to read → calls `getattr`
- Use `setattr(obj, key, value)` to write — **`obj[key] = value` raises `TypeError`**

---

## MAST Scripting

Two-layer structure:
- **`mast/`** — generic language core (compiler, scheduler, core node types)
- **`mast_sbs/`** — Cosmos-specific extensions (mission scheduler, story page, GUI/comms/science nodes)

### Execution model
- Linear flow like BASIC; control via `jump`/`label`
- Tasks can `yield`, suspending until the next tick
- MAST calls Python freely via `eval`/`exec`; procedural functions bridge the two
- `.mast` files → distributed as `.mastlib` zips (added to `sys.path` at runtime)
- Every mission starts at `== main ==`. The compiler creates an **implicit** `main` label — declaring `== main ==` explicitly causes "Duplicate label" unless you use `==replace: main ==`

### Key syntax
```
== label_name ==          # label (2+ equals signs)
jump label_name           # jump
x = 42                    # variable
shared x = 42             # shared across all tasks in story
~~ expr ~~                # inline python (expression or statement)
await delay_sim(seconds=5)
* "one-shot button"       # consumed after click
+ "sticky button"         # stays visible
"narration text"

# Route decorator labels
//spawn
//comms/path
//signal/name
//shared/signal/name
//damage/object  /destroy  /killed  /internal  /heat
//collision/passive  /interactive
//dock/hangar
//launch/missile  /drone
//focus/comms  /science  /weapons  /normal  /grid
//select/...  //point/...
//console/change  //object/grid
//gui/tab/Name

///inline_route            # named entry point within a label
@map/path/name "Display"  # discoverable map label
@media/kind/path "Display" # discoverable media label
```

### Node registration — ordering pitfall
`@mast_node()` appends to the end (lower priority); `@mast_node(append=False)` inserts at the front (higher priority). The compiler takes the **first match** — wrong order silently matches the wrong node type. The `mast_sbs/story_nodes/__init__.py` comment warns about this. Always import `story_nodes` explicitly in tests (don't rely on test ordering).

### Backward compatibility
**MAST language changes must not break existing scripts.** This overrides almost all other refactoring instincts.

---

## Procedural API (`procedural/`)

Functions callable from both Python and MAST. Key modules: `space_objects`, `spawn`, `query`, `signal`, `inventory`, `ship_data`, `timers`, `roles`, `links`, `sides`, `quest`, `objective`, `routes`, `popup`, `science`, `terrain`, `torpedoes`, `upgrades`, `prefab`, `maps`, `media`, `modifiers`, `settings`, `style`, `lifeform`, `promise_functions`, `internal_damage`, `mission`, `gui/widgets`.

`signal_emit()` is safe to call when `FrameContext.mast is None` — it returns early with no side effects.

---

## Path / File System (`fs.py`)

**Do not use `__file__` in production `fs.py` functions.** Cosmos embeds Python and `script.py`'s `__file__` is unreliable at runtime. Path globals (`exe_dir`, `script_dir`) are set from `sys.path[0]` via engine bootstrapping.

`test_set_exe_dir()` is the **test-only** exception — it uses `__file__` from `fs.py` itself, which is reliable for library modules.

---

## Testing

Tests use **`unittest`**, not pytest. Run via:
```
python -m unittest discover -s tests
```

**Every test file that touches file paths or MAST compilation must call `test_set_exe_dir()` at module level** (before any class definitions). Without it, `get_script_dir()` caches `sys.path[0]` from discover mode (`tests/`), breaking all path resolution.

```python
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
```

`cosmos_dev/mock/sbs.py` provides a partial mock of the `sbs` Pybind11 API. Import it with `from cosmos_dev.mock import sbs`. Call `sbs.create_new_sim()` and set `FrameContext.context = Context(sbs.sim, sbs, FakeEvent())` in `setUp`. Call `SpaceObject.clear()` to reset all agent state between tests.

---

## Development / Debugging (`cosmos_dev/`)

`cosmos_dev/` is a **dev-only** package — it is never included in the `.sbslib` distributed to missions. It provides a full mission runner and browser-based GUI for debugging outside Cosmos.

### Running a mission for debugging

**VS Code** (`.vscode/launch.json` in the mission folder):
```json
{
    "module": "cosmos_dev.mission_runner",
    "envFile": ".env",
    "args": [".", "--gui"]
}
```
The `.env` file must have `PYTHONPATH=../sbs_utils` so Python can find `cosmos_dev`. Add `"subProcess": false` to prevent VS Code holding onto the spawned WebSocket server child process.

**CLI via `sbs.pyz`:**
```
sbs debug .                        # GUI, map selection screen (story.mast)
sbs debug . --map 0                # GUI, auto-start map at index 0
sbs debug . --map SecretMeeting    # GUI, auto-start by name
sbs debug . --no-gui --map 0       # headless
```

**Direct Python:**
```
python -m cosmos_dev.mission_runner <mission_path> --gui
python -m cosmos_dev.mission_runner <mission_path> --map 0
```

### How it works

- **`cosmos_dev/mock/sbs.py`** — in-process mock of the `sbs` Pybind11 API (no GUI); used by unit tests
- **`cosmos_dev/mockgui/sbs.py`** — extends the mock with real GUI via WebSocket; spawns `server.py` in a child process
- **`cosmos_dev/mockgui/server.py`** — stdlib-only WebSocket bridge; streams `send_gui_*` commands to `client.html`; puts browser events in a queue for the runner to consume
- **`cosmos_dev/mockgui/client.html`** — browser renderer; open `http://localhost:8765/`
- **`cosmos_dev/mission_runner.py`** — tick loop; drains browser event queues and fires `cosmos_event_handler`; auto-starts a map by index/name when `--map` is passed

### Map auto-start

When `--map` is given, `_try_auto_start_map()` polls `maps_get_list()` each tick until `@map/` labels are registered (story top-level code finishes), then calls `task_schedule_server(map_label, defer=True)`, sets `GAME_STARTED`, emits `game_started`, and calls `sbs.resume_sim()`. Without `--map`, the server GUI map-selection screen is shown.

### Browser URLs

| URL | Behaviour |
|---|---|
| `http://localhost:8765/server` | Connects as the server console (`clientID=0`). Replays the server frame. No `client_connect` event fired — server page is already running. |
| `http://localhost:8765/client` | Connects as a new client with a unique `clientID`. Fires `client_connect` so the MAST client page starts. Replays server frame then client frame. |
| `http://localhost:8765/` | Same as `/client` (default). |

Each widget fires events with the `clientID` of the frame that rendered it — server-page widgets (rendered with `clientID=0`) automatically fire as the server; client-page widgets fire as the browser's assigned ID. No manual override is needed.

**Client ID range**: The mockgui server assigns IDs starting at `0x8080000000000001` (vs the real engine's `0x8000000000000001`). These 64-bit values exceed JavaScript's `Number.MAX_SAFE_INTEGER`, so `server.py` transmits all `clientID` fields as **JSON strings** and parses them back to `int` when events arrive from the browser. Python internally always uses integer client IDs.

### GUI event field mapping (confirmed)

All browser events arrive as `event.tag = "gui_message"`. Widget tags are **strings** (from `page.get_tag()` which returns `str(int)`).

Browser event `type` values sent to the runner:
- `"gui_message"` — pure click/activation (button, clickregion, iconbutton, rawiconbutton)
- `"change"` — value-bearing change (checkbox `checked`, dropdown `value`, slider `value`, typein `value`)
- `"submit"` — typein Enter key (same fields as `change`)

| Widget | `sub_tag` | `value_tag` | `sub_float` |
|---|---|---|---|
| Button / Checkbox | widget tag (string) | — | — |
| Dropdown | widget tag (string) | selected string | index |
| Slider | widget tag (string) | — | raw float |
| Icon (`click_tag`) | click_tag string | — | — |
| TextInput | widget tag (string) | cumulative string | — |

### In-place widget updates (dirty system)

Widgets mark themselves dirty when their value changes; the engine re-renders them automatically each tick without a full `clear`/`complete` cycle. `gui_represent(widget)` is **deprecated** — calling it is safe but redundant. The mockgui browser mirrors this: `send_gui_*` commands arriving outside a rebuild find the element by tag in the front buffer and replace it in-place.

---

## Packaging

- **`.sbslib`** — zip of the `sbs_utils` package; built with the external `sbs.pyz` utility
- **`.mastlib`** — zip of `.mast` files; added to `sys.path` at runtime

---

## Folder Layout

```
sbs_utils/
├── mast/           # MAST core (generic)
│   └── core_nodes/ # Built-in node types
├── mast_sbs/       # Cosmos MAST extensions
│   └── story_nodes/# Cosmos node types
├── pages/          # GUI page system
│   ├── layout/     # Layout components
│   └── widgets/    # Composite widgets
├── procedural/     # Procedural API
│   └── gui/        # GUI procedural helpers
├── cards/          # Tilemap / ASCII map system
├── yaml/           # Bundled pyyaml (no pip)
└── typings/        # .pyi stubs (generated, not source)

cosmos_dev/         # Dev-only tooling (NOT in .sbslib)
├── mock/           # In-process sbs mock (no GUI) — used by unit tests
└── mockgui/        # WebSocket GUI bridge
    ├── sbs.py      # Extends mock with real send_gui_* → WebSocket
    ├── server.py   # stdlib WebSocket server (no pip)
    └── client.html # Browser renderer

tests/              # Unit tests
mkdocs/             # MkDocs documentation source
```
