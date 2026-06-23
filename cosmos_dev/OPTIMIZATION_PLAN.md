# cosmos_dev Physics & Radar Optimization Plan

## Why this work

Large missions (theta_quadrant, Infinite_Cosmos) spawn 2,000+ terrain objects (asteroids,
nebulae) plus 100–500 active objects (NPCs, players).  At the current 2 Hz physics rate, the
O(n²) collision loop processes 2.4 M sphere-pair checks every tick.  That blocks the MAST tick
(5 Hz) and GUI event drain (60 Hz loop) for the entire duration.  Additionally, the radar
snapshot serializes every object every 2 ticks and the browser redraws every object with a
`createRadialGradient` on every animation frame.

The real engine is single-threaded (Python embedded via Pybind11).  **The mock has no such
constraint.**  All changes below are `cosmos_dev/`-only and never affect `.sbslib` or real
mission logic.

---

## Architecture overview after changes

```
Main thread (60 Hz loop)
  ├─ GUI event drain       ← always immediate
  ├─ MAST tick (5 Hz)
  ├─ Client connect/disconnect
  └─ Physics-event drain   ← queue.Queue, thread-safe

Physics thread (2 Hz, daemon)
  ├─ acquire sim._lock
  ├─ behavior dispatch      ← active objects only
  ├─ rotation + translation ← active objects only
  ├─ spatial-hash collision ← active-active + active-terrain only
  ├─ passive systems        ← active objects only
  ├─ release sim._lock
  └─ _push_radar()          ← no lock needed (eventual consistency OK)

WebSocket server process (existing)
  ├─ drain gui_queue        ← batch all pending commands into ONE frame
  └─ broadcast to clients
```

---

## Change 1 — Physics threading (mission_runner.py + mock/sbs.py)

### Problem
`physics_tick()` runs synchronously in the main loop every 30 ticks (2 Hz).  For large
missions it can take tens of milliseconds, delaying GUI events and MAST ticks.

### Fix — dedicated physics thread

**`cosmos_dev/mock/sbs.py`**

Add `threading.Lock` to the `simulation` class:

```python
import threading

class simulation:
    def __init__(self):
        ...
        self._lock = threading.Lock()
```

Wrap every **mutation** of `space_objects`, `_terrain_ids`, or `_active_ids` with `self._lock`:
- `simulation.create_space_object`
- `delete_object`
- `push_to_standby_list_id` / `retrieve_from_standby_list_id`
- `simulation.reposition_space_object`

Change `_pending_physics_events` from a `list` to a `queue.Queue` (thread-safe):

```python
import queue
_pending_physics_events: queue.Queue = queue.Queue()
```

In `physics_tick`, acquire the lock around all computation, then release before `_push_radar`:

```python
def physics_tick(dt=0.5):
    if sim is None or sim._paused:
        return
    with sim._lock:
        # behavior dispatch, integration, collision, passive systems
    _push_radar()   # no lock — eventual consistency acceptable for radar display
```

**`cosmos_dev/mission_runner.py`**

Replace the `_physics_counter` logic with a background daemon thread:

```python
import threading

def _physics_worker(sbs_module, stop_event):
    while not stop_event.is_set():
        if sbs_module.sim is not None and not sbs_module.sim._paused:
            sbs_module.physics_tick(dt=0.5)
        stop_event.wait(timeout=0.5)   # 2 Hz; responsive to stop signal

_stop_physics = threading.Event()
_physics_thread = threading.Thread(
    target=_physics_worker,
    args=(sbs, _stop_physics),
    daemon=True,
    name="sbs-physics",
)
_physics_thread.start()
```

In the `finally` block: `_stop_physics.set(); _physics_thread.join(timeout=1)`.

The main loop drains the physics-events Queue each iteration instead of calling `physics_tick`:

```python
while not _base_mock._pending_physics_events.empty():
    tag, sub_tag, origin_id, selected_id = _base_mock._pending_physics_events.get_nowait()
    ev = FakeEvent(...)
    cosmos_event_handler(sbs.sim, ev)
```

### GIL note
Python's GIL prevents true CPU parallelism for pure-Python math.  The benefit here is
**decoupling**: MAST ticks and GUI events are never delayed by a slow physics sweep.  The GIL
is released during `queue.Queue.put()` and `time.sleep()`, so those operations do run in
genuine parallel with the main thread.

---

## Change 2 — Object classification by abits (mock/sbs.py)

### Problem
`physics_tick` iterates all objects for behavior dispatch, integration, and passive systems,
even though terrain objects (asteroids, nebulae) are completely static.

### abits bitmask
```
TERRAIN = 0x0f   (bits 0–3 set; NPC/PLAYER bits 4–5 clear)
NPC     = 0x10
PLAYER  = 0x20
```

`active` ↔ `(abits & 0x30) != 0`.  Terrain ↔ `(abits & 0x30) == 0`.

### Fix

Add two sets to `simulation.__init__`:

```python
self._terrain_ids: set = set()   # static — never dispatched or integrated
self._active_ids:  set = set()   # NPCs + players — full physics
```

Classify at spawn in `create_space_object`:

```python
if abits & 0x30:
    self._active_ids.add(id)
else:
    self._terrain_ids.add(id)
```

Remove from the correct set in `delete_object`, `push_to_standby_list_id`,
`retrieve_from_standby_list_id`.

**Behavior dispatch, integration, and passive systems** now loop over `_active_ids` only.
Terrain objects are never touched.

**Terrain rotation** (cosmetic `steer_yaw` on asteroids) is intentionally ignored — the mock
does not need visual spin.  Ships can still collide with terrain (see Change 3).

---

## Change 3 — Spatial-hash collision detection (mock/sbs.py)

### Problem
Sphere-pair collision is O((N+T)²).  At 200 active + 2000 terrain: 2.4 M pairs per tick.
Target: ~50 k pairs.

### Rules
- **terrain vs terrain**: always skip (terrain never moves; static objects cannot collide)
- **active vs active**: check
- **active vs terrain**: check (ships must still collide with asteroids etc.)

### Fix — uniform grid spatial hash

Cell size is **auto-tuned** each tick:

```python
max_er   = max((sim.space_objects[id]._exclusion_radius for id in active_ids), default=0)
cell_sz  = max(max_er * 2.0, 500.0)
```

Build two grids once per tick:

```python
def _cell(x, z, sz):
    return (int(x / sz), int(z / sz))

active_grid  = {}   # cell → [(id, obj), ...]
terrain_grid = {}   # cell → [(id, obj), ...]

for id in sim._active_ids:
    obj = sim.space_objects.get(id)
    if obj: active_grid.setdefault(_cell(obj._pos.x, obj._pos.z, cell_sz), []).append((id, obj))

for id in sim._terrain_ids:
    obj = sim.space_objects.get(id)
    if obj and obj._exclusion_radius > 0:
        terrain_grid.setdefault(_cell(obj._pos.x, obj._pos.z, cell_sz), []).append((id, obj))
```

**Active vs active** — 9-cell neighborhood, upper-triangle dedup via a `visited` set:

```python
visited = set()
for (cx, cz), cell_list in active_grid.items():
    neighbors = []
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            neighbors.extend(active_grid.get((cx+dx, cz+dz), []))
    for aid, a in cell_list:
        ra = a._exclusion_radius
        if ra <= 0: continue
        for bid, b in neighbors:
            if bid <= aid: continue
            pair = (aid, bid)
            if pair in visited: continue
            visited.add(pair)
            ...sphere test...
```

**Active vs terrain** — no dedup needed (terrain never appears in active_grid):

```python
for (cx, cz), cell_list in active_grid.items():
    for aid, a in cell_list:
        ra = a._exclusion_radius
        if ra <= 0: continue
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                for tid, t in terrain_grid.get((cx+dx, cz+dz), []):
                    ...sphere test...
```

Expected pair-check counts for 200 active + 2000 terrain, assuming 4 neighbors per cell:

| Check type | Before | After |
|---|---|---|
| active–active | 19 900 | ~800 |
| active–terrain | 400 000 | ~8 000 |
| terrain–terrain | 2 000 000 | 0 |
| **Total** | **~2.4 M** | **~9 k** |

---

## Change 4 — Delta radar protocol (mockgui/sbs.py)

### Problem
`_push_radar()` serializes **all** space objects every 2 physics ticks.  For a tile-map
mission this is 2 200 objects × ~100 bytes each = ~220 KB per push.

### Fix — two-channel protocol

**Channel 1: `"radar_terrain"`** — sent only when the terrain set changes (object spawned or
deleted).  Includes: `id`, `x`, `z`, `side`.  Terrain never moves, so this is a one-time cost
per spawn/delete event.

**Channel 2: `"radar"` (dynamic delta)** — sent every radar tick, active objects only.  Format:

```json
{
  "cmd": "radar",
  "removed": ["<id>", ...],
  "changed": [
    {"id": "<id>", "x": 100.0, "z": -500.0, "fx": 0.9, "fz": 0.4, "new": true, "side": "tsn", "tick_type": "PLAYER", "name": "Artemis"},
    {"id": "<id>", "x": 200.0, "z": -600.0, "fx": 0.8, "fz": 0.6}
  ],
  "client_focus": {"<cid>": {"x": ..., "z": ...}}
}
```

`"new": true` on objects not seen before (full fields).  Subsequent updates send only
`id`, `x`, `z`, `fx`, `fz`.

**Delta thresholds**:
- Position: skip update if |Δx|² + |Δz|² < 25 (5 units)
- Heading: skip if |Δfx| + |Δfz| < 0.05 rad (≈ 3°)

**New connection handling** — `_force_terrain_push()` resets both snapshots to force a
complete re-send on the next radar tick:

```python
def _force_terrain_push():
    global _last_terrain_snapshot, _last_dynamic_positions
    _last_terrain_snapshot   = set()
    _last_dynamic_positions  = {}
```

Called from `mission_runner.py` in the client-connect handler.

### Expected bandwidth reduction

| Mission type | Before | After |
|---|---|---|
| 50 objects, no terrain | ~5 KB/push | ~1 KB/push |
| 200 NPCs + 500 terrain | ~70 KB/push | ~5 KB/push (dynamic only) |
| 200 NPCs + 2 000 terrain | ~220 KB/push | ~5 KB/push |

---

## Change 5 — WebSocket command batching (mockgui/server.py)

### Problem
Each `send_gui_*` call puts one dict into `gui_queue`.  The server drains the queue and calls
`_ws_send()` once per item.  A MAST tick that rebuilds a complex page (50 widgets) = 50
WebSocket frames = 50 TCP writes.

### Fix

The server accumulates all items from `gui_queue` between two consecutive event-loop ticks into
a `"batch"` frame:

```python
msgs = []
while True:
    try:
        msgs.append(gui_queue.get_nowait())
    except queue.Empty:
        break

if msgs:
    if len(msgs) == 1:
        await _ws_send(writer, json.dumps(msgs[0]))
    else:
        await _ws_send(writer, json.dumps({"cmd": "batch", "items": msgs}))
```

Browser `dispatch()` handles `"batch"`:

```js
case 'batch':
    for (const item of msg.items) dispatch(item);
    break;
```

This reduces WebSocket frame count from O(widgets) to O(1) per MAST tick.

---

## Change 6 — Three.js GPU radar rendering (client.html)

### Problem
`_drawViewInRect` calls `createRadialGradient(px, py, 0, px, py, r*2.5)` for every object
every animation frame.  Gradient creation is CPU-computed even in GPU-accelerated browsers.
For 500 objects at 60 FPS: 30 000 gradient objects per second.

### Fix — dedicated Three.js WebGL renderer for radar

A second `WebGLRenderer` is created with its own non-displayed canvas (separate WebGL
context from `_threeRenderer` which handles image widgets and 3D ships).

```js
const _radarCanvas3d = document.createElement('canvas');
const _radarRenderer = new THREE.WebGLRenderer({ canvas: _radarCanvas3d, alpha: true });
const _radarScene    = new THREE.Scene();
const _radarCamera   = new THREE.OrthographicCamera(-1, 1, 1, -1, -1, 1);
_radarCamera.position.set(0, 0, 0);   // looking along -Z
```

Coordinate mapping: world `(x, z)` → Three.js `(x, z, 0)` (XY plane, camera top = world +Z).

### Two `THREE.Points` layers

Using `Points` instead of `InstancedMesh`: one draw call per layer, update Float32Arrays
in-place.

```js
// Terrain layer — updated only on radar_terrain message
const _terrainGeo = new THREE.BufferGeometry();
// setAttribute 'position' (Float32Array, 5000×3) and 'color' (Float32Array, 5000×3)
const _terrainPoints = new THREE.Points(_terrainGeo,
    new THREE.PointsMaterial({ size: 4, vertexColors: true, sizeAttenuation: false }));

// Dynamic layer — updated on every radar message
const _dynamicGeo = new THREE.BufferGeometry();
// setAttribute 'position' (Float32Array, 1000×3) and 'color' (Float32Array, 1000×3)
const _dynamicPoints = new THREE.Points(_dynamicGeo,
    new THREE.PointsMaterial({ size: 8, vertexColors: true, sizeAttenuation: false }));
```

### `cmdRadarTerrain(msg)` — new handler

Write terrain positions and side-hash colors to `_terrainPoints` arrays; set
`drawRange.count`; mark `needsUpdate = true`.  Runs only when terrain changes.

### `cmdRadar(msg)` — updated handler

Process `removed` + `changed` delta into `_dynamicPoints` arrays.  Maintain an
`id → array_index` map for O(1) updates and swap-with-last removals.

### Radar RAF loop (separate from `_start3dLoop`)

```
1. Resize _radarCanvas3d to match viewport
2. Update _radarCamera frustum from latest focus + span
3. _radarRenderer.render(_radarScene, _radarCamera)
4. Clear _radarCtx (visible overlay canvas)
5. Draw 2D chrome on _radarCtx:
   - Dark background per active view rect
   - Range rings + crosshair (cheap, static geometry)
   - drawImage(_radarCanvas3d, ...)    ← GPU blit of the dot layer
   - Navpoints + labels (few objects, 2D canvas)
   - Player heading arrows (≤8 ships, 2D canvas lines)
   - View border
```

Terrain and dynamic dots are rendered by the GPU.  The 2D canvas is only used for the
chrome that cannot be instanced (text labels, thin lines, dashed rings).

---

## Summary of gains

| Metric | Before | After |
|---|---|---|
| Collision pairs (200 NPC + 2000 terrain) | 2.4 M / tick | ~9 k / tick |
| Terrain physics work | O(T) per tick | 0 |
| MAST / GUI latency under load | blocked by physics | decoupled (thread) |
| Radar bandwidth (tile-map mission) | ~220 KB / push | ~5 KB / push |
| WebSocket frames per MAST tick | O(widgets) | 1 batch frame |
| Browser radar draw calls | O(objects) CPU gradients | 2 GPU draw calls + cheap 2D chrome |

---

## File change list

| File | Changes |
|---|---|
| `cosmos_dev/mock/sbs.py` | `simulation._lock`, `_terrain_ids`, `_active_ids`; classify on spawn/delete/standby; `physics_tick` lock + active-only loops + spatial hash; `_pending_physics_events` → `queue.Queue` |
| `cosmos_dev/mission_runner.py` | Remove `_physics_counter`; start `_physics_thread`; drain Queue in main loop; call `sbs._force_terrain_push()` on client connect |
| `cosmos_dev/mockgui/sbs.py` | `_force_terrain_push()`; `_push_radar()` two-channel delta: `radar_terrain` + `radar` delta |
| `cosmos_dev/mockgui/server.py` | Batch `gui_queue` drain into single `"batch"` WebSocket frame |
| `cosmos_dev/mockgui/client.html` | `dispatch` handles `"batch"`; `cmdRadarTerrain`; updated `cmdRadar` (delta); Three.js `_radarRenderer` + `_terrainPoints` + `_dynamicPoints`; radar RAF loop |

---

## Implementation order

1. `mock/sbs.py` — abits classification + spatial hash (no threading yet; testable standalone)
2. `mock/sbs.py` + `mission_runner.py` — threading + queue.Queue
3. `mockgui/sbs.py` — delta radar protocol + `_force_terrain_push`
4. `mockgui/server.py` — WebSocket command batching
5. `client.html` — Three.js radar renderer + batch dispatch handler




## Why ship-centric wins
In Artemis, 6 consoles (helm, weapons, science, engineering, comms, main screen) share one ship. They all need identical radar — same position, same culling radius. Sending them separate per-client messages computes and serialises the same payload N times.

# Approach	Server compute	Messages generated	Wire bytes per tick
Full broadcast	O(1)	1	1 × all_objects
Per-client	O(N clients)	N	N × culled_objects
Per-ship broadcast	O(K ships)	K	K × culled_objects
With 2 player ships × 6 consoles each = 12 clients: per-client sends 12 messages; per-ship sends 2. Server CPU scales with unique ships (K ≈ 2–6), not consoles (N ≈ 12–24).

# How it works
Server (mockgui/sbs.py): group s.client_ships by shipID first, deduplicate. One culled radar message per unique ship, tagged "ship_id": str(ship_id). Server/GM view (clientID=0) gets a separate unculled message tagged "ship_id": "0".


# group clients by their assigned ship
ships_to_clients: dict = {}
for cid, sid in s.client_ships.items():
    ships_to_clients.setdefault(sid, []).append(cid)

for ship_id, client_ids in ships_to_clients.items():
    obj = s.space_objects.get(ship_id)
    cx, cz = (obj._pos.x, obj._pos.z) if obj else (0, 0)
    # cull changed/removed to CULL_RADIUS around (cx, cz)
    # send one message tagged ship_id — all 6 consoles share it
Client (client.html): store _myShipId (set once when the server assigns the client to a ship, via a new assign_ship init-time message or read from client_focus). In cmdRadar, skip the message if msg.ship_id !== _myShipId && msg.ship_id !== '0'.

No server.py routing changes needed — it stays a broadcast. Each browser tab receives K messages and ignores K-1 of them. For localhost that's free.

# Ship change handling
When a player is reassigned to a different ship, _myShipId updates and they start consuming the new ship's stream. The culling centre jumps (one large delta frame), then camera lerp (Change 2) smooths the visual transition. No special burst mitigation needed.

# One wrinkle: unassigned clients
Clients not yet assigned to a ship (lobby, spectator) have no _myShipId. They should fall back to the server/GM view (ship_id: "0") rather than seeing nothing.

Verdict: per-ship broadcast is the right design. It matches Artemis semantics, reduces server compute proportionally to consoles-per-ship (typically 6×), and requires no server.py routing changes. Want me to implement Changes 3 → 2 → 4 → 1 with this ship-centric model for Change 1?

