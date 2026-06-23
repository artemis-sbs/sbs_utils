# Debugging Missions Outside Cosmos

The `cosmos_dev` package lets you run and debug MAST missions in a normal Python
process — no Cosmos install required.  You get a browser-based GUI that mirrors
the real engine's widget protocol, full VS Code debugpy support, and a plain
`print()`/`log()` console.

## Components

| Component | Location | Purpose |
|---|---|---|
| `cosmos_dev/mock/sbs.py` | in-process | Lightweight engine stub; no GUI; used by unit tests |
| `cosmos_dev/mockgui/sbs.py` | in-process + subprocess | Engine stub **plus** a WebSocket GUI bridge |
| `cosmos_dev/mockgui/server.py` | subprocess | Stdlib WebSocket server that sends widget commands to the browser |
| `cosmos_dev/mockgui/client.html` | browser | Renders widgets; routes click/change events back to the runner |
| `cosmos_dev/mission_runner.py` | runner | Tick loop, auto-start, event dispatch |

---

## Quick Start — CLI

The `sbs debug` command (from `sbs.pyz`) is the simplest way to launch a mission.
Run it from the `missions/` folder next to `sbs.pyz`:

```sh
# Auto-start the first @map/ label with GUI
sbs debug ../LegendaryMissions --map 0 --gui

# Auto-start a map by name
sbs debug ../SecretMeeting --map "Secret Meeting" --gui

# Headless — no browser needed (useful for smoke-testing)
sbs debug ../LegendaryMissions --map 0

# Custom port
sbs debug . --gui --port 9000
```

Options:

| Option | Default | Description |
|---|---|---|
| `mission_path` | `.` | Path to the mission folder |
| `--gui` | off | Start the WebSocket GUI server; open `http://localhost:8765/` in a browser |
| `--map` | *(none)* | Index (int) or label path to auto-start; omit to show the GUI picker |
| `--port` | `8765` | WebSocket server port |
| `--tick-rate` | `60` | Engine ticks per second |
| `--mast` | `story.mast` | Override the entry `.mast` file (e.g. `debug.mast`) |
| `--cosmos-dir` | auto | Cosmos install root for serving texture images |

---

## Quick Start — Python Module

You can invoke the runner directly without `sbs.pyz`:

```sh
# from inside missions/sbs_utils/
python -m cosmos_dev.mission_runner ../LegendaryMissions --map 0 --gui
python -m cosmos_dev.mission_runner ../SecretMeeting --map "Secret Meeting"
python -m cosmos_dev.mission_runner ../MyLib --mast debug.mast
```

---

## VS Code Integration

A `.vscode/launch.json` inside the mission folder wires up debugpy.  The
`.env` file sets `PYTHONPATH` so the runner can find `sbs_utils` without
`sbs.pyz` on the path.

**`.env`** (already present in LegendaryMissions):
```ini
PYTHONPATH=../sbs_utils;${PYTHONPATH};../../../PyAddons
```

**`.vscode/launch.json`**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Dbg w/Gui",
      "type": "debugpy",
      "request": "launch",
      "module": "cosmos_dev.mission_runner",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/../LegendaryMissions",
      "envFile": "${workspaceFolder}/../LegendaryMissions/.env",
      "args": [".", "--gui"],
      "subProcess": false
    },
    {
      "name": "Dbg no Gui",
      "type": "debugpy",
      "request": "launch",
      "module": "cosmos_dev.mission_runner",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/../LegendaryMissions",
      "envFile": "${workspaceFolder}/../LegendaryMissions/.env",
      "args": [".", "--map", "0"],
      "subProcess": false
    }
  ]
}
```

!!! note
    `"subProcess": false` prevents VS Code from tracking the WebSocket server
    subprocess.  Without it, stopping the debugger can leave the process
    running and hold the port.

---

## How Auto-Start Works

When `--map` is given, the runner polls `maps_get_list()` each tick until
`@map/` labels are registered by the story (they appear after a few ticks of
MAST initialisation).  Once labels are available the runner:

1. Picks the requested map by index or name.
2. Calls `task_schedule_server(map_label, defer=True)` — deferred so it fires
   on the *next* tick, after the current `cosmos_event_handler` returns.
3. Sets the shared variable `GAME_STARTED = True` and emits `game_started`.
4. Calls `sbs.resume_sim()`.

No `extern_debug.mast` or per-mission wrapper file is needed.

---

## Browser GUI — URL Paths

Open a browser after starting with `--gui`.  Which URL you open controls what
role the browser plays:

| URL | Behaviour |
|---|---|
| `http://localhost:8765/server` | Connects as the server console (`clientID=0`). No `client_connect` event is fired — the server page is already running. Replays the server frame. |
| `http://localhost:8765/client` | Connects as a new client with a unique `clientID`. Fires `client_connect` so the MAST client page starts. Replays server frame then client frame. |
| `http://localhost:8765/` | Same as `/client` (default). |

Multiple browser tabs can connect simultaneously, each with a different client
ID.  Server-page widgets (rendered with `clientID=0`) automatically fire events
as the server; client-page widgets fire as the browser's assigned ID.

!!! note "Client ID range"
    The mockgui server assigns client IDs starting at `0x8080000000000001`
    (the real engine uses `0x8000000000000001`).  These 64-bit values exceed
    JavaScript's `Number.MAX_SAFE_INTEGER`, so all `clientID` fields are
    transmitted as **JSON strings** and parsed back to `int` on arrival.
    Python internally always uses integer client IDs.

---

## GUI Event Field Mapping

The browser sends JSON objects; the runner converts them to `FakeEvent` before
calling `cosmos_event_handler`.  All browser events arrive with
`event.tag = "gui_message"`.  Widget tags are **strings** (from
`page.get_tag()` which returns `str(int)`).

Browser event `type` values:

| `type` | Trigger |
|---|---|
| `gui_message` | Pure click/activation — button, clickregion, iconbutton, rawiconbutton |
| `change` | Value-bearing change — checkbox `checked`, dropdown `value`, slider `value`, typein `value` |
| `submit` | Typein Enter key (same fields as `change`) |

Field mapping per widget:

| Widget | `sub_tag` | `value_tag` | `sub_float` |
|---|---|---|---|
| Button / Checkbox | widget tag (string) | — | — |
| Dropdown | widget tag (string) | selected string | index |
| Slider | widget tag (string) | — | raw float |
| Icon (`click_tag`) | click_tag string | — | — |
| TextInput | widget tag (string) | cumulative string | — |

---

## In-Place Widget Updates (Dirty System)

Widgets mark themselves dirty when their value changes; the engine re-renders
them automatically each tick without a full `clear`/`complete` cycle.
`gui_represent(widget)` is **deprecated** — calling it is safe but redundant.

The mockgui browser mirrors this: `send_gui_*` commands arriving outside a
rebuild find the existing element by tag in the live front buffer and replace
it in-place (`replaceChild`).  The widget's position is preserved; only the
content changes.

---

## Headless / CI Use

Omit `--gui` to run entirely in-process with no WebSocket server.  Combine
with `--map` to auto-start and exercise server-side logic without any browser:

```sh
sbs debug ../MyMission --map 0
python -m cosmos_dev.mission_runner ../MyMission --map 0
```

This is useful for smoke-testing mission startup in CI before running the full
unit-test suite.

---

## Font Measurement Tool

The browser topbar has a **Measure** button that measures the actual Goldman
font line heights and per-character pixel widths using DOM
`getBoundingClientRect()` and `canvas.measureText()`.  Click it after the
page loads to produce ready-to-paste Python constants for
`cosmos_dev/mock/sbs.py`.

Use this whenever the fonts are updated or the mock text measurement functions
need re-calibration.
