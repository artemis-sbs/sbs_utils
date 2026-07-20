"""
cosmos_dev/mockgui/sbs.py — GUI-capable drop-in replacement for the engine sbs module.

Inherits all simulation state (space objects, navpoints, sides, etc.) from
cosmos_dev.mock.sbs, then overrides the send_gui_* functions with real
WebSocket-based implementations that stream widget commands to a browser client.

Usage:
    import cosmos_dev.mockgui.sbs as sbs
    sbs.start_server()
    sbs.create_new_sim()
    # all simulation + GUI functions now available as 'sbs.*'

For unit tests that don't need live GUI, use the base mock directly:
    from cosmos_dev.mock import sbs
"""

import sys
import multiprocessing
from typing import Any

# Pull in all simulation state — space objects, navpoints, sides, diplomacy, etc.
import cosmos_dev.mock.sbs as _base_mock
from cosmos_dev.mock.sbs import *   # noqa: F401,F403

# Re-register this module as 'sbs' so engine scripts that do `import sbs` get
# the GUI-capable version instead of the base no-op mock.
sys.modules["sbs"] = sys.modules[__name__]


def create_new_sim():
    """Creates a new simulation and syncs the local sim reference."""
    global sim
    result = _base_mock.create_new_sim()
    sim = _base_mock.sim
    # Update FrameContext immediately so code running after sim_create() in the
    # same handler tick (e.g. npc_spawn) uses the new simulation object.
    try:
        from sbs_utils.helpers import FrameContext
        if FrameContext.context is not None:
            FrameContext.context.sim = sim
    except Exception:
        pass
    return result


# ---------------------------------------------------------------------------
# Shared queues  (initialised by start_server)
# ---------------------------------------------------------------------------
# Outbound GUI commands — script engine writes, server reads.
gui_queue: multiprocessing.Queue = None          # type: ignore[assignment]


# Inbound connection lifecycle events from the server.
# {"event": "connect"|"disconnect", "clientID": int}
client_event_queue: multiprocessing.Queue = None  # type: ignore[assignment]

# Inbound widget events from the browser.
# {"type": "click"|"change"|..., "tag": str, "clientID": int, ...}
gui_event_queue: multiprocessing.Queue = None    # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Server launcher
# ---------------------------------------------------------------------------
def start_server(
    host: str = "0.0.0.0",
    port: int = 8765,
    cosmos_dir: "str | None" = None,
) -> multiprocessing.Process:
    """Start the WebSocket bridge server in a child process.

    Creates multiprocessing.Queue instances for all three queues, assigns them
    to this module so send_gui_* calls work immediately, then spawns the server
    process and waits until it is ready to accept connections.  Returns the
    Process object.

    cosmos_dir: Cosmos install root (e.g. /path/to/Cosmos-1-3-0). Images are
    served from <cosmos_dir>/data/graphics/. Defaults to sbs_utils.fs.exe_dir.

    Requires only Python stdlib — no pip packages needed.
    """
    global gui_queue, client_event_queue, gui_event_queue

    if cosmos_dir is None:
        try:
            from sbs_utils import fs as _fs
            cosmos_dir = _fs.exe_dir
        except Exception:
            pass

    gui_queue          = multiprocessing.Queue()
    client_event_queue = multiprocessing.Queue()
    gui_event_queue    = multiprocessing.Queue()
    ready              = multiprocessing.Event()

    from cosmos_dev.mockgui import server as server_mod

    p = multiprocessing.Process(
        target=server_mod.run_server,
        args=(gui_queue, client_event_queue, gui_event_queue, ready, host, port, cosmos_dir),
        daemon=True,
        name="sbs-server",
    )
    p.start()

    if not ready.wait(timeout=10):
        p.terminate()
        raise RuntimeError(f"sbs server did not start within 10 s on {host}:{port}")
    return p


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------
def _send(clientID: int, cmd: str, **kwargs: Any) -> None:
    """Serialise a command and enqueue it."""
    payload = {"clientID": clientID, "cmd": cmd, **kwargs}
    gui_queue.put(payload)


# ---------------------------------------------------------------------------
# Buffer control  (override base no-ops)
# ---------------------------------------------------------------------------
def send_gui_clear(clientID: int, tag: str) -> None:
    """Clears all GUI elements from screen on the targeted client."""
    _send(clientID, "clear", tag=tag)


def send_gui_complete(clientID: int, tag: str) -> None:
    """Flips the double-buffered display list on the targeted client."""
    _send(clientID, "complete", tag=tag)


# ---------------------------------------------------------------------------
# Widget helpers  (override base no-ops)
# ---------------------------------------------------------------------------
def _widget(cmd: str, clientID: int, parent: str, tag: str,
            style: str, left: float, top: float,
            right: float, bottom: float) -> None:
    _send(clientID, cmd,
          parent=parent, tag=tag, style=style,
          left=left, top=top, right=right, bottom=bottom)


def send_gui_button(clientID, parent, tag, style, left, top, right, bottom):
    _widget("button", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_checkbox(clientID, parent, tag, style, left, top, right, bottom):
    _widget("checkbox", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_clickregion(clientID, parent, tag, style, left, top, right, bottom):
    _widget("clickregion", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_colorbutton(clientID, parent, tag, style, left, top, right, bottom):
    _widget("colorbutton", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_colorcheckbox(clientID, parent, tag, style, left, top, right, bottom):
    _widget("colorcheckbox", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_dropdown(clientID, parent, tag, style, left, top, right, bottom):
    _widget("dropdown", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_icon(clientID, parent, tag, style, left, top, right, bottom):
    _widget("icon", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_iconbutton(clientID, parent, tag, style, left, top, right, bottom):
    _widget("iconbutton", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_iconcheckbox(clientID, parent, tag, style, left, top, right, bottom):
    _widget("iconcheckbox", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_image(clientID, parent, tag, style, left, top, right, bottom):
    _widget("image", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_rawiconbutton(clientID, parent, tag, style, left, top, right, bottom):
    _widget("rawiconbutton", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_sub_region(clientID, parent, tag, style, left, top, right, bottom):
    _widget("sub_region", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_text(clientID, parent, tag, style, left, top, right, bottom):
    _widget("text", clientID, parent, tag, style, left, top, right, bottom)

def send_gui_typein(clientID, parent, tag, style, left, top, right, bottom):
    _widget("typein", clientID, parent, tag, style, left, top, right, bottom)


# ---------------------------------------------------------------------------
# Widgets with extra parameters  (override base no-ops)
# ---------------------------------------------------------------------------
def send_gui_face(clientID: int, parent: str, tag: str, face_string: str,
                  left: float, top: float, right: float, bottom: float) -> None:
    _send(clientID, "face",
          parent=parent, tag=tag, face_string=face_string,
          left=left, top=top, right=right, bottom=bottom)

def send_gui_slider(clientID: int, parent: str, tag: str, current: float,
                    style: str, left: float, top: float,
                    right: float, bottom: float) -> None:
    _send(clientID, "slider",
          parent=parent, tag=tag, current=current, style=style,
          left=left, top=top, right=right, bottom=bottom)

def send_gui_hotkey(clientID: int, category: str, tag: str,
                    keyType: str, description: str) -> None:
    _send(clientID, "hotkey",
          category=category, tag=tag,
          keyType=keyType, description=description)


def send_gui_3dship(clientID: int, parent: str, tag: str, style: str,
                    left: float, top: float, right: float, bottom: float) -> None:
    # Extract hull_tag from the style string so Python can do the shipData lookup.
    hull_tag = ""
    for pair in style.split(";"):
        k, _, v = pair.partition(":")
        if k.strip() == "hull_tag":
            hull_tag = v.strip()
            break

    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        ship_info = get_ship_data_for(hull_tag) or {}
    except Exception:
        ship_info = {}

    artfileroot = ship_info.get("artfileroot", hull_tag)
    meshscale   = float(ship_info.get("meshscale", 1.0))

    _send(clientID, "3dship",
          parent=parent, tag=tag, style=style,
          left=left, top=top, right=right, bottom=bottom,
          artfileroot=artfileroot, meshscale=meshscale)


# ---------------------------------------------------------------------------
# 2D gameplay widget views
# ---------------------------------------------------------------------------
_2D_VIEW_WIDGETS = frozenset({"2dview", "science_2d_view", "comms_2d_view", "weapon_2d_view"})

# Per-client set of 2D-view widgets the script has explicitly sized this console
# epoch (via send_client_widget_rects / ConsoleWidget).  Latched so _push_2dview_rects
# never clobbers a script-set size with the default.  Reset on each widget-list change.
_explicit_2d_rects: dict = {}

# Per-client explicit 3dview rect (left, top, right, bottom in screen %), set when a
# script positions the 3D view via gui_layout_widget("3dview").  When absent the
# default below is used.  Reset on each widget-list change.
_view3d_rects: dict = {}
# Default 3D canvas rects (left, top, right, bottom in screen %).  The widget-driven
# 3dview (mainscreen/cockpit) uses a ~3% (~50px) top inset to clear the topbar,
# matching the 2D default in the browser; the cinematic cutscene view is full-bleed.
_DEFAULT_VIEW3D_RECT = (0.0, 3.0, 100.0, 100.0)
_DEFAULT_CINEMATIC_RECT = (0.0, 0.0, 100.0, 100.0)


def send_client_widget_rects(clientID: int, widgetName: str,
                              l1: float, t1: float, r1: float, b1: float,
                              l2: float, t2: float, r2: float, b2: float) -> None:
    """Forward gameplay view positions to the browser.  2D radar views become
    widget_rect commands; an explicit 3dview rect is stored for _push_cinematic to
    apply to the 3D canvas.  A non-degenerate rect latches as a script-set size so
    the per-tick defaults back off."""
    explicit = (r1 - l1) >= 1 and (b1 - t1) >= 1

    if widgetName == "3dview":
        # The 3D view is positioned by the cinematic command, not a widget_rect.
        if explicit:
            _view3d_rects[clientID] = (round(l1, 2), round(t1, 2), round(r1, 2), round(b1, 2))
        return

    if widgetName not in _2D_VIEW_WIDGETS or gui_queue is None:
        return
    # A real (non-degenerate) rect means the script positioned this view itself —
    # latch it so the per-tick default in _push_2dview_rects backs off.
    if explicit:
        _explicit_2d_rects.setdefault(clientID, set()).add(widgetName)
    try:
        gui_queue.put_nowait({
            "clientID": str(clientID),
            "cmd": "widget_rect",
            "widget": widgetName,
            "left":   round(l1, 2),
            "top":    round(t1, 2),
            "right":  round(r1, 2),
            "bottom": round(b1, 2),
        })
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Physics tick override — runs base physics then pushes a radar delta to the browser.
# ---------------------------------------------------------------------------
_radar_tick: int = 0
_RADAR_INTERVAL: int = 1    # push radar every physics tick (physics thread runs at 2 Hz)

CULL_RADIUS: float = 35_000.0  # only objects within this distance of a ship are sent

# Delta-radar state: reset by _force_terrain_push() when a new client connects.
_last_terrain_snapshot: frozenset = frozenset()  # frozenset of terrain IDs currently sent
_last_per_ship: dict = {}                        # ship_id_str → {obj_id → (x, z, fx, fz)}
_DYNAMIC_POS_THRESHOLD_SQ: float = 25.0          # 5 units²  — skip tiny drift
_DYNAMIC_HDG_THRESHOLD:    float = 0.05          # radians   — skip tiny rotations


def set_main_view_modes(clientID: int, main_screen_view: str, cam_angle: str, cam_mode: str) -> None:
    """Store the view mode (base behaviour) and tell the browser whether the
    cinematic 3dview should be shown for this client."""
    _base_mock.set_main_view_modes(clientID, main_screen_view, cam_angle, cam_mode)
    _send(clientID, "cinematic", active=(cam_mode == "cinematic"))


# Clients whose current console widget list contains a "3dview" gameplay widget
# (mainscreen forward view, cockpit, …).  Unlike the cinematic view, these consoles
# never call set_main_view_modes, so the browser's 3dview must be driven from the
# widget list here instead.
_view3d_widget_clients: set = set()

# Clients whose current widget list contains a 2D gameplay view (helm/weapons/
# science/comms radar, mainscreen LRS/tactical).  The standard gui_console() path
# sets the engine widget list but never calls send_client_widget_rects (the real
# engine lays the widgets out in C++), so without this the browser has no rect for
# the view and falls back to the tiny corner minimap.  clientID -> widget name.
_view2d_widget_clients: dict = {}


def send_client_widget_list(clientID: int, consoleType: str, widgetList: str) -> None:
    """Record the console type (base behaviour) and drive the browser's gameplay
    views from this client's widget list: activate the 3dview when a "3dview"
    widget is present, and register a 2D radar rect when a 2D-view widget is."""
    _base_mock.send_client_widget_list(clientID, consoleType, widgetList)
    widgets = (widgetList or "").split("^")

    # New console epoch: drop last epoch's explicit 3dview rect (re-sent on present
    # if the new layout sizes the view itself).
    _view3d_rects.pop(clientID, None)

    # 3dview (mainscreen forward view, cockpit) — _push_cinematic streams the camera.
    if "3dview" in widgets:
        _view3d_widget_clients.add(clientID)
    elif clientID in _view3d_widget_clients:
        _view3d_widget_clients.discard(clientID)
        _send(clientID, "cinematic", active=False)   # hide the browser 3dview

    # 2D gameplay view (radar) — _push_2dview_rects streams a default rect each
    # tick unless the script sizes the view itself (tracked in _explicit_2d_rects).
    # New console epoch: clear last epoch's explicit-size latch.
    _explicit_2d_rects.pop(clientID, None)
    view2d = next((w for w in widgets if w in _2D_VIEW_WIDGETS), None)
    if view2d is not None:
        _view2d_widget_clients[clientID] = view2d
    else:
        _view2d_widget_clients.pop(clientID, None)


def _push_2dview_rects() -> None:
    """Re-register the 2D radar rect each tick for clients whose console shows a
    2D-view widget.  Sends a degenerate rect so the browser applies its own
    full-panel _DEFAULT_2D_VIEW_RECT fallback (single source of truth for the
    default helm/radar layout).  Per-tick resend survives the _widgetRects.clear()
    that fires on every console rebuild."""
    if gui_queue is None:
        return
    for cid, widget in list(_view2d_widget_clients.items()):
        # Script already sized this view — don't overwrite it with the default.
        if widget in _explicit_2d_rects.get(cid, ()):
            continue
        try:
            gui_queue.put_nowait({
                "clientID": str(cid),
                "cmd": "widget_rect",
                "widget": widget,
                "left": 0, "top": 0, "right": 0, "bottom": 0,
            })
        except Exception:
            pass


def physics_tick(dt: float = 1.0 / 60.0) -> None:
    """Delegate to base physics then broadcast a radar delta to the browser."""
    global sim, _radar_tick
    _base_mock.physics_tick(dt)
    sim = _base_mock.sim   # keep local alias in sync (create_new_sim may have changed it)
    _radar_tick += 1
    if _radar_tick >= _RADAR_INTERVAL:
        _radar_tick = 0
        _push_radar()
        _push_cinematic()
        _push_2dview_rects()
        _push_skybox()


def _art_root_for(obj) -> str:
    """Resolve the 2D sprite art root for a space object, so the browser can load
    <root>256.png. Mirrors send_gui_3dship's lookup; falls back to the data tag."""
    tag = getattr(obj, "_data_tag", "") or ""
    if not tag:
        return ""
    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        info = get_ship_data_for(tag) or {}
        return info.get("artfileroot", tag)
    except Exception:
        return tag


def _nebula_info(obj):
    """If the object is a nebula, return its visual params for the 3dview's GPU
    point-sprite cloud, else None. Nebulae are volumetric (no OBJ mesh):

        radius   – cloud size (data_set "size")
        density  – particle count + opacity scale (~1.95..20)
        seed     – engine random_seed, for reproducible deterministic scatter
        color    – emission rgb (self-glow core), 0..1
        color2   – scattering rgb (second tint for two-tone particles), 0..1
        swirl    – animated swirl rotation amount
        warp     – per-particle positional wobble amount
    """
    if getattr(obj, "_data_tag", "") != "nebula":
        return None
    ds = obj.data_set
    def _f(key, default):
        v = ds.get(key)
        return float(v) if v is not None else default
    return {
        "radius":  round(_f("size", 2000.0), 1),
        "density": round(_f("density", 7.0), 2),
        "seed":    int(_f("random_seed", 1)),
        "color":   [round(_f("emission_red", 0.5), 3),
                    round(_f("emission_green", 0.5), 3),
                    round(_f("emission_blue", 0.8), 3)],
        "color2":  [round(_f("scattering_red", 0.5), 3),
                    round(_f("scattering_green", 0.5), 3),
                    round(_f("scattering_blue", 0.8), 3)],
        "swirl":   round(_f("swirl", 0.0), 3),
        "warp":    round(_f("domain_warp", 0.0), 3),
    }


def _quat_of(obj) -> list:
    """Object orientation as [w, x, y, z] for the 3dview (full yaw/pitch/roll).
    The mock uses the standard quaternion->basis convention (forward = +Z),
    which matches Three.js, so it can be applied directly browser-side."""
    q = obj._rot_quat
    return [round(q._w, 4), round(q._x, 4), round(q._y, 4), round(q._z, 4)]


def _mesh_scale_for(obj) -> float:
    """Resolve the engine meshscale (OBJ→world size factor) for a space object,
    so the 3dview sizes hull meshes correctly. Mirrors send_gui_3dship."""
    tag = getattr(obj, "_data_tag", "") or ""
    if not tag:
        return 1.0
    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        info = get_ship_data_for(tag) or {}
        return float(info.get("meshscale", 1.0))
    except Exception:
        return 1.0


# Last skybox name broadcast to browsers; reset on connect so late joiners get it.
_last_skybox_sent = "\0"   # sentinel != any real name (incl. None)


def _force_terrain_push() -> None:
    """Reset delta snapshots so the next physics tick sends a full terrain + dynamic state.

    Call this when a new browser client connects so they receive complete radar state
    immediately rather than waiting for the next incremental change.
    """
    global _last_terrain_snapshot, _last_per_ship, _last_skybox_sent
    _last_terrain_snapshot = frozenset()
    _last_per_ship = {}
    _last_skybox_sent = "\0"   # force the skybox to re-broadcast to the new client


def _push_skybox() -> None:
    """Broadcast the current skybox name to browsers when it changes (or after a
    connect-forced reset). The browser slices the cross PNG into a backdrop."""
    global _last_skybox_sent
    if gui_queue is None:
        return
    name = getattr(_base_mock, "_current_skybox", None)
    if name == _last_skybox_sent:
        return
    _last_skybox_sent = name
    try:
        gui_queue.put_nowait({"clientID": 0, "cmd": "skybox", "name": name})
    except Exception:
        pass


def _push_radar() -> None:
    """Two-channel per-ship radar push.

    Channel 1 — ``radar_terrain``: broadcast when terrain id-set changes.
    Channel 2 — ``radar``: one message per unique ship (tagged ``ship_id``).
    Each browser client filters by its own ship_id, so consoles sharing a
    ship (helm, weapons, science …) receive a single culled stream rather
    than per-client duplicates.  ship_id ``"0"`` = GM / unassigned view;
    sees all active objects with no distance culling.
    """
    global _last_terrain_snapshot, _last_per_ship
    if _base_mock.sim is None or gui_queue is None:
        return
    s = _base_mock.sim

    # --- Channel 1: terrain — only when the terrain id-set changes ---
    current_terrain_ids = frozenset(s._terrain_ids & s.space_objects.keys())
    if current_terrain_ids != _last_terrain_snapshot:
        _last_terrain_snapshot = current_terrain_ids
        terrain_objects = []
        for tid in current_terrain_ids:
            obj = s.space_objects[tid]
            rec = {
                "id":   str(obj._id),
                "x":    round(obj._pos.x, 1),
                "z":    round(obj._pos.z, 1),
                "side": obj._side,
                "y":    round(obj._pos.y, 1),
                "q":    _quat_of(obj),
            }
            neb = _nebula_info(obj)
            if neb is not None:
                rec["nebula"]    = True
                rec["art"]       = ""        # volumetric — drawn as a particle cloud, no OBJ
                rec["meshscale"] = 1.0
                rec.update(neb)
            else:
                rec["art"]       = _art_root_for(obj)
                rec["meshscale"] = _mesh_scale_for(obj)
            terrain_objects.append(rec)
        try:
            gui_queue.put_nowait({
                "clientID": 0,
                "cmd":      "radar_terrain",
                "objects":  terrain_objects,
            })
        except Exception:
            pass

    # --- Channel 2: per-ship delta ---
    active_ids = s._active_ids & s.space_objects.keys()
    r2 = CULL_RADIUS * CULL_RADIUS

    # Build navpoints + navareas + client_focus (sent in every per-ship message).
    navpts: list = []
    for name, nav in s.nav_points.items():
        navpts.append({"name": name, "x": round(nav._pos.x, 1), "z": round(nav._pos.z, 1)})

    # Navareas are navpoints (a subclass) kept in the ID registry, not the name
    # dict above — pull them out by type.
    navareas: list = []
    for nav in s.nav_points_by_id.values():
        if not isinstance(nav, _base_mock.navarea):
            continue
        navareas.append({
            "name":   nav._text,
            "color":  nav._color,
            "points": [[round(px, 1), round(pz, 1)] for (px, pz) in nav._points],
        })

    client_focus: dict = {}
    for cid, ship_id in s.client_ships.items():
        obj = s.space_objects.get(ship_id)
        if obj is not None:
            client_focus[str(cid)] = {
                "x":       round(obj._pos.x, 1),
                "z":       round(obj._pos.z, 1),
                "ship_id": str(ship_id),
            }

    # Unique ships with at least one connected client, plus the GM view (ship_id=0).
    ships: dict = {}          # ship_id (int) → space_object or None
    for sid in s.client_ships.values():
        if sid not in ships:
            ships[sid] = s.space_objects.get(sid)
    ships[0] = None           # GM / spectator / unassigned — no distance culling

    for ship_id, ship_obj in ships.items():
        sid_str = str(ship_id)
        last    = _last_per_ship.setdefault(sid_str, {})

        # Determine the visible set for this ship.
        if ship_obj is not None:
            sx, sz  = ship_obj._pos.x, ship_obj._pos.z
            in_view: set = set()
            for id_ in active_ids:
                obj = s.space_objects[id_]
                dx  = obj._pos.x - sx
                dz  = obj._pos.z - sz
                if dx * dx + dz * dz <= r2:
                    in_view.add(id_)
        else:
            in_view = set(active_ids)   # GM sees everything

        removed = [str(id_) for id_ in last if id_ not in in_view]
        changed: list = []
        new_snap: dict = {}

        for id_ in in_view:
            obj = s.space_objects[id_]
            fwd = obj.forward_vector()
            x   = round(obj._pos.x, 1)
            z   = round(obj._pos.z, 1)
            fx  = round(fwd.x, 3)
            fz  = round(fwd.z, 3)
            new_snap[id_] = (x, z, fx, fz)

            prev = last.get(id_)
            if prev is None:
                changed.append({
                    "id":        str(id_),
                    "x": x, "z": z, "fx": fx, "fz": fz,
                    "side":      obj._side,
                    "tick_type": obj._tick_type,
                    "name":      obj.data_set.get("name_tag") or obj.data_set.get("display_text") or "",
                    "art":       _art_root_for(obj),
                    "y":         round(obj._pos.y, 1),
                    "meshscale": _mesh_scale_for(obj),
                    "q":         _quat_of(obj),
                    "new":       True,
                })
            else:
                lx, lz, lfx, lfz = prev
                ddx, ddz = x - lx, z - lz
                dhdg = abs(fx - lfx) + abs(fz - lfz)
                if (ddx * ddx + ddz * ddz >= _DYNAMIC_POS_THRESHOLD_SQ
                        or dhdg >= _DYNAMIC_HDG_THRESHOLD):
                    changed.append({"id": str(id_), "x": x, "z": z, "fx": fx, "fz": fz,
                                    "q": _quat_of(obj)})

        _last_per_ship[sid_str] = new_snap

        if removed or changed or navpts or navareas or client_focus:
            try:
                gui_queue.put_nowait({
                    "clientID":     0,
                    "cmd":          "radar",
                    "ship_id":      sid_str,
                    "removed":      removed,
                    "changed":      changed,
                    "navpoints":    navpts,
                    "navareas":     navareas,
                    "client_focus": client_focus,
                })
            except Exception:
                pass


def _forward_view_camera(clientID: int):
    """Auto chase-cam (behind + above the ship, looking ahead) for a widget-driven
    3dview client.  Mirrors the base mock's cinematic auto-cam so the widget view
    matches the cinematic one.  Returns {"cam", "target"} or None."""
    sim_ = _base_mock.sim
    if sim_ is None:
        return None
    ship_id = sim_.client_ships.get(clientID, 0)
    o = sim_.space_objects.get(ship_id)
    if o is None:
        return None
    p = o._pos
    f = o.forward_vector()
    cam = (p.x - f.x * 500.0, p.y + 150.0, p.z - f.z * 500.0)
    tgt = (p.x + f.x * 200.0, p.y, p.z + f.z * 200.0)
    return {"cam": cam, "target": tgt}


def _emit_cinematic(cid, cam, mode: str, default_rect) -> None:
    """Enqueue one per-tick cinematic camera message for a client, including the
    3D canvas rect: script-set if present, else default_rect (full-bleed for the
    cinematic cutscene, topbar-inset for the widget-driven 3dview)."""
    c, t = cam["cam"], cam["target"]
    rect = _view3d_rects.get(cid, default_rect)
    try:
        gui_queue.put_nowait({
            "clientID": cid,
            "cmd":      "cinematic",
            "active":   True,
            "mode":     mode,
            "cam":      [round(c[0], 1), round(c[1], 1), round(c[2], 1)],
            "target":   [round(t[0], 1), round(t[1], 1), round(t[2], 1)],
            "rect":     [rect[0], rect[1], rect[2], rect[3]],
        })
    except Exception:
        pass


def _push_cinematic() -> None:
    """Stream the resolved 3dview camera each tick for every client showing a 3D
    view — both the cinematic main-screen view and the widget-driven forward view
    (mainscreen/cockpit).  One small message per client per tick; the browser
    reuses its radar object buffers (on the y=0 plane) for the scene.
    """
    if _base_mock.sim is None or gui_queue is None:
        return
    handled = set()
    # Cinematic main-screen view — explicit camera from cinematic_control / auto.
    for cid, modes in list(_base_mock._view_modes.items()):
        if modes[2] != "cinematic":
            continue
        cam = _base_mock.get_cinematic_camera(cid)
        if cam is None:
            continue
        _emit_cinematic(cid, cam, cam["mode"], _DEFAULT_CINEMATIC_RECT)
        handled.add(cid)

    # Widget-driven 3dview (mainscreen forward view, cockpit) — no cinematic camera
    # state, so synthesize an auto chase-cam tracking the client's ship.
    for cid in list(_view3d_widget_clients):
        if cid in handled:
            continue
        cam = _forward_view_camera(cid)
        if cam is None:
            continue
        _emit_cinematic(cid, cam, "auto", _DEFAULT_VIEW3D_RECT)
