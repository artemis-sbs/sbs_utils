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

The `sbs debug` command is the simplest way to launch a mission.  Run it from
the `missions/` folder next to `sbs.pyz`:

```sh
# Show the GUI map picker (opens http://localhost:8765/)
sbs debug ../LegendaryMissions

# Auto-start the first @map/ label, no browser needed
sbs debug ../LegendaryMissions --map 0 --no-gui

# Auto-start a map by name
sbs debug ../SecretMeeting --map "Secret Meeting"

# Custom port
sbs debug . --port 9000
```

Options:

| Option | Default | Description |
|---|---|---|
| `mission_path` | `.` | Path to the mission folder |
| `--map` | *(none)* | Index (int) or label path to auto-start; omit to show the GUI picker |
| `--no-gui` | off | Headless — no WebSocket server, no browser needed |
| `--port` | `8765` | WebSocket server port |
| `--tick-rate` | `60` | Engine ticks per second |

---

## Quick Start — Python Module

You can invoke the runner directly without `sbs.pyz`:

```sh
# from inside missions/sbs_utils/
python -m cosmos_dev.mission_runner ../LegendaryMissions --gui
python -m cosmos_dev.mission_runner ../LegendaryMissions --map 0
```

---

## VS Code Integration

A `.vscode/launch.json` inside the mission folder wires up debugpy.  The
`.env` file sets `PYTHONPATH` so the runner can find `sbs_utils` without
`sbs.pyz` on the path.

**`.env`** (already present in LegendaryMissions):
```ini
PYTHONPATH=../sbs_utils;../sbs_utils/mock;${PYTHONPATH};../../../PyAddons
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

## Browser GUI — "Send As" Trick

Open `http://localhost:8765/` in a browser after starting with `--gui`.

The topbar shows a **send as** field (default `0`).  The browser normally acts
as client `1` (the first connected player console).  Set **send as** to `0` to
impersonate the server and interact with server-side GUI pages (e.g. the map
picker or a GM console).

You can also pass `?id=0` in the URL to pre-set the field:

```
http://localhost:8765/?id=0    # open as server
http://localhost:8765/?id=2    # open as client 2
```

Multiple browser tabs can connect simultaneously, each with a different client
ID.

---

## GUI Event Field Mapping

The browser sends JSON objects; the runner converts them to `FakeEvent` before
calling `cosmos_event_handler`.

| Browser field | `FakeEvent` field | Notes |
|---|---|---|
| `clientID` | `client_id` | Effective ID after "send as" override |
| `tag` (numeric string) | `sub_tag` | Widget tag; always `event.tag = "gui_message"` |
| `value` (number) | `sub_float` | Sliders and numeric inputs |
| `value` (string) | `value_tag` | Dropdowns, text inputs |
| `sub_tag` (string) | `sub_tag` | Icon `click_tag` value (type = `"click"`) |

---

## Headless / CI Use

Omit `--gui` (or pass `--no-gui`) to run entirely in-process with no WebSocket
server.  Combine with `--map 0` to auto-start and exercise server-side logic
without any browser:

```sh
sbs debug ../MyMission --no-gui --map 0
```

This is useful for smoke-testing mission startup in CI before running the full
unit-test suite.
