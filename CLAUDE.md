# sbs_utils — Library Reference for Claude

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

`sbs_utils/mock/` provides a partial mock of the `sbs` Pybind11 API. Call `sbs.create_new_sim()` and set `FrameContext.context = Context(sbs.sim, sbs, FakeEvent())` in `setUp`. Call `SpaceObject.clear()` to reset all agent state between tests.

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
├── mock/           # sbs API mock for tests
├── yaml/           # Bundled pyyaml (no pip)
└── typings/        # .pyi stubs (generated, not source)

tests/              # Unit tests
mkdocs/             # MkDocs documentation source
```
