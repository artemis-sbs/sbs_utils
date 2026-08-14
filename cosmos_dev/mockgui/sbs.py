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

import os
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
    global sim, _last_fx_nonempty, _cinematic_tick, _reset_gen
    result = _base_mock.create_new_sim()
    sim = _base_mock.sim
    # New world: invalidate any push already in flight on the physics thread (see
    # _reset_gen). Bumped FIRST so nothing built against the old world can commit
    # a baseline or enqueue a message after the clears below.
    _reset_gen += 1
    # Push the camera on the FIRST tick after a (re)start (then ~15 Hz) so the 3D view
    # frames immediately instead of waiting a couple ticks.
    _cinematic_tick = _CINEMATIC_INTERVAL - 1
    # Update FrameContext immediately so code running after sim_create() in the
    # same handler tick (e.g. npc_spawn) uses the new simulation object.
    try:
        from sbs_utils.helpers import FrameContext
        if FrameContext.context is not None:
            FrameContext.context.sim = sim
    except Exception:
        pass
    # A new sim means a mission (re)start. Tell every browser to wipe leftover
    # 2D radar / 3D cinematic state from the previous mission, and reset our push
    # snapshots so the new world streams fresh on the next physics ticks. (Guarded:
    # this is also called once at startup before the queue/server exist.)
    if gui_queue is not None:
        # Stop re-registering the previous mission's 2D radar rect each tick FIRST:
        # _push_2dview_rects (physics thread) would otherwise enqueue a widget_rect
        # after world_reset and leave the 2D view stuck on screen.  Clearing before
        # the send guarantees no rect lands after world_reset in the FIFO queue.
        # The new console's widget list repopulates this when the next mission loads.
        _view2d_widget_clients.clear()
        _explicit_2d_rects.clear()
        # Same contract for the 3D view: the browser's world_reset hides the 3dview
        # canvas and waits for the next console to re-register, so holding the old
        # mission's registration here only streams cameras nobody is showing.
        _view3d_widget_clients.clear()
        _view3d_rects.clear()
        # Every registered engine widget, not a hand-kept subset: a client set left
        # populated here streams the previous mission's widgets into the next run.
        for _w in _ENGINE_WIDGETS.values():
            _w.clients.clear()
        _view_target_clients.clear()
        _hud_cache.clear()          # drop stale HUD diff baselines from the old mission
        _unknown_widgets_seen.clear()   # re-report unemulated widgets for the new run
        _reticle_sent.clear()           # else run 2 keeps run 1's selection reticle
        _force_terrain_push()
        _last_fx_nonempty = False
        # Tell every browser to wipe leftover 2D radar / 3D cinematic state.
        try:
            _send(0, "world_reset")
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
    static_roots: "list | None" = None,
) -> multiprocessing.Process:
    """Start the WebSocket bridge server in a child process.

    Creates multiprocessing.Queue instances for all three queues, assigns them
    to this module so send_gui_* calls work immediately, then spawns the server
    process and waits until it is ready to accept connections.  Returns the
    Process object.

    cosmos_dir: Cosmos install root (e.g. /path/to/Cosmos-1-3-0). Images are
    served from <cosmos_dir>/data/graphics/. Defaults to sbs_utils.fs.exe_dir.

    static_roots: extra directories the browser may fetch art from. Engine art
    lives under data/graphics, but a mission's OWN media/ and any pack it pins
    under shared_media: do not -- so without these, mission art 404s in the
    browser while drawing correctly in the engine. Defaults to the mission dir
    and the missions root (a shared pack is `../__lib__/media/<pack>/...`, which
    the browser normalises to `/__lib__/media/...`).

    Requires only Python stdlib — no pip packages needed.
    """
    global gui_queue, client_event_queue, gui_event_queue

    if cosmos_dir is None:
        try:
            from sbs_utils import fs as _fs
            cosmos_dir = _fs.exe_dir
        except Exception:
            pass

    # Deliberately NOT derived from fs.get_script_dir(): that is sys.path[0],
    # which _load_libs has just filled with the last-inserted mastlib, so it
    # points into __lib__/<some>.mastlib rather than at the mission. The caller
    # knows the real paths; it passes them.
    static_roots = list(static_roots or [])

    gui_queue          = multiprocessing.Queue()
    client_event_queue = multiprocessing.Queue()
    gui_event_queue    = multiprocessing.Queue()
    ready              = multiprocessing.Event()

    from cosmos_dev.mockgui import server as server_mod

    p = multiprocessing.Process(
        target=server_mod.run_server,
        args=(gui_queue, client_event_queue, gui_event_queue, ready, host, port,
              cosmos_dir, static_roots),
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

def send_story_dialog(clientID: int, title: str, text: str, face: str, color: str) -> None:
    """Stream a story dialog (title + text + composited face) to the client's
    browser. The engine renders this in C++; the base mock is a no-op, so this
    override is what makes admiral/comms narrative (and its face) visible in the
    browser mock. It is not part of a region rebuild — the browser shows it as a
    dismissable card until the player closes it."""
    _send(clientID, "story_dialog",
          title=title or "", text=text or "", face=face or "", color=color or "#444")

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


def send_message_to_client(clientID: int, colorDesc: str, text: str) -> None:
    """Append a colored line to the client's text waterfall (the engine renders
    this stream in C++)."""
    _send(clientID, "text_msg", color=colorDesc or "#fff", text=text or "")


def send_message_to_player_ship(playerID: int, colorDesc: str, text: str) -> None:
    """Append a colored line to the waterfall of every client controlling
    playerID (mirrors the engine routing ship messages to its consoles)."""
    # Mirror the engine's validation (see the base mock) so a non-space id - e.g.
    # the SHARED story agent - raises here instead of silently matching no client.
    _base_mock._require_space_object(playerID, "SendMessageToPlayerShip")
    if _base_mock.sim is None:
        return
    for cid, sid in list(_base_mock.sim.client_ships.items()):
        if sid == playerID:
            _send(cid, "text_msg", color=colorDesc or "#fff", text=text or "")


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

    # Every other engine widget the browser can draw is described in _ENGINE_WIDGETS,
    # which says how to forward its rect.  Mock HUD overlays ("hud") own a default
    # screen corner, so only a real (non-degenerate) rect moves them; the rest are
    # positioned entirely by the layout and take the rect as sent.
    w = _ENGINE_WIDGETS.get(widgetName)
    if w is not None and w.rect:
        if gui_queue is not None and (w.rect != "hud" or explicit):
            _send_rect(clientID, w, l1, t1, r1, b1)
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
_RADAR_INTERVAL: int = 1    # push radar every physics tick (physics thread runs at 30 Hz)
# Behaviours that render as grid icon 0 (blank) in the engine - selection/marker
# helpers. They must not draw anything on the 2D radar, so the mock simply omits them
# from the radar stream entirely (which also keeps their mesh out of the 3D view).
# NOTE: only the BLANK ones (no art / data tag) are helpers. behav_selection is ALSO the
# production behaviour for VISIBLE, selectable MAP markers (terrain.py nebula markers, the
# galaxy-theater board) - those carry a real art and MUST draw. So the hide is gated on
# "behav_selection AND no art" (see _is_hidden_marker), not the behaviour alone.
_RADAR_HIDDEN_BEHAVIORS = frozenset({"behav_selection"})


def _is_hidden_marker(obj) -> bool:
    """True if this object is an engine selection HELPER that must not draw: a hidden-
    behaviour object (behav_selection) with NO art. A behav_selection WITH an art is a real
    map marker (the production nebula markers + the galaxy-theater board spawn this way) and
    renders normally."""
    return (obj._tick_type in _RADAR_HIDDEN_BEHAVIORS
            and not getattr(obj, "_data_tag", ""))


def _is_invisible(obj) -> bool:
    """True for objects spawned with the 'invisible' art — the detached-command cambots
    (Admiral / GM / galaxy overseer cameras). They ride the camera centre and the engine
    never shows them, so they must NOT draw on the radar OR be hit-tested (otherwise the
    invisible cambot steals every 2D-view click from the object behind it). NOTE: this is
    about invisibility, not ownership — a visible own ship (e.g. a player selecting itself
    on comms) is a valid pick and is left alone."""
    return getattr(obj, "_data_tag", "") == "invisible"


def _not_selectable(obj) -> bool:
    """True if the object carries data_set selectable == 0 — VISIBLE but not clickable
    (asteroids, individual nebula). Streamed as `nosel` so the 2D-view pick skips it while
    it still DRAWS (unlike _is_invisible, which drops the object from the stream entirely)."""
    v = obj.data_set.get("selectable")
    if v is None:
        return False           # default: selectable
    try:
        return float(v) == 0.0
    except (TypeError, ValueError):
        return False


def _not_hittable(obj) -> bool:
    """Object must NOT be hit-tested on the 2D view — streamed as `nosel` so the pick skips
    it. Two cases, same rule: data_set selectable==0 (asteroids, nebula) or spawned invisible
    (the detached-command cambots)."""
    return _not_selectable(obj) or _is_invisible(obj)


def _drop_from_radar(obj) -> bool:
    """Object must not appear on the radar AT ALL (not drawn, not streamed). An INVISIBLE
    object is fully hidden UNLESS its BEHAVIOUR is behav_player: the detached-command cambot
    (invisible + behav_player) is the one invisible thing that still draws a faint dot at the
    camera. Every OTHER invisible object is dropped."""
    return _is_invisible(obj) and getattr(obj, "_tick_type", "") != "behav_player"
_cinematic_tick: int = 0
_CINEMATIC_INTERVAL: int = 2  # push the 3D camera every 2nd radar tick (~15 Hz) - the
                              # browser lerps the camera between updates, so 30 Hz is wasted

CULL_RADIUS: float = 35_000.0  # only objects within this distance of a ship are sent

# Delta-radar state: reset by _force_terrain_push() when a new client connects.
_last_terrain_snapshot: frozenset = frozenset()  # frozenset of terrain IDs currently sent
_last_per_ship: dict = {}                        # ship_id_str → {obj_id → (x, z, fx, fz)}
# World generation — bumped by create_new_sim(). The pushes below run on the 30 Hz
# PHYSICS thread while create_new_sim() clears the delta baselines from the MAIN
# thread, so a push that started before a mission reload could write its old-world
# snapshot back into the freshly-cleared baseline. Space-object ids RECYCLE across
# sim.__init__(), so a new NPC inheriting a stale baseline entry looks "already
# known": it is streamed as a delta only, never as a full record, and the browser
# (which will not invent identity from a delta) never draws it. That is the classic
# "enemies stop moving on the second run" bug. Each push captures the generation on
# entry and discards its writes if a reload landed mid-build.
_reset_gen: int = 0

# Stream health, sampled by the runner (--runs soak, /debug). `full` and `delta` are
# records ISSUED; `resync` counts full records re-issued because a browser reported a
# delta it could not place; `dropped_gen` counts pushes discarded by the generation
# guard. A healthy restart shows full > 0 in every run and resync ~0.
_stream_stats: dict = {"full": 0, "delta": 0, "resync": 0, "dropped_gen": 0}


def stream_stats() -> dict:
    """Snapshot of radar-stream health (see _stream_stats)."""
    return dict(_stream_stats)


def stream_stats_reset() -> None:
    for k in _stream_stats:
        _stream_stats[k] = 0


def _register_gui_reset_probes() -> None:
    """Declare the GUI push layer's per-mission snapshots with the reset ledger.

    These are the delta baselines and per-client view registrations. A stale entry
    here does not crash - it silently withholds the FULL record a browser needs to
    draw an object, which is exactly the "enemies frozen from run 2" symptom.
    """
    try:
        from sbs_utils.handlerhooks import register_reset_state
    except Exception:
        return
    register_reset_state("mockgui.last_per_ship",
                         lambda: sum(len(v) for v in _last_per_ship.values()))
    register_reset_state("mockgui.last_terrain_snapshot", lambda: len(_last_terrain_snapshot))
    register_reset_state("mockgui.hud_cache",            lambda: len(_hud_cache))
    register_reset_state("mockgui.view2d_widget_clients", lambda: len(_view2d_widget_clients))
    register_reset_state("mockgui.view3d_widget_clients", lambda: len(_view3d_widget_clients))
    register_reset_state("mockgui.explicit_2d_rects",     lambda: len(_explicit_2d_rects))


_register_gui_reset_probes()
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

# Clients whose console widget list contains a "ship_data" widget.  _push_ship_data
# streams the client's player-ship vitals (shields/energy/dock_state/...) each tick
# so the browser can render a live HUD — the engine renders this widget in C++, so
# without this the mock shows nothing for it.
_view_shipdata_clients: set = set()

# Clients on the main-screen console ("normal_main") - the only place the
# mock-only target_data HUD is shown.
_view_target_clients: set = set()

# Per-(client, panel) HUD send cache, so we only stream what CHANGED:
#   key -> {"gen": last data_set gen, "speed": last rounded speed, "payload": last sent}
# The data_set's change counter lets us skip clean objects without recomputing; the
# retained payload lets us send only the fields that differ. Browser merges partials.
_hud_cache: dict = {}

# Clients whose console widget list contains "text_waterfall". The waterfall is
# event-driven (only re-shows on a message), but the server rebuilds its GUI every
# tick and the root send_gui_clear hides it; _push_text_active re-asserts it each
# tick for these clients so it stays visible (like ship_data).
_view_text_clients: set = set()

# Clients whose console widget list declares the "red_alert" widget — i.e. the ones
# that show the red-alert TOGGLE BUTTON (the real engine widget, in comms). Pressing it
# toggles the ship's red_alert. The alert VIGNETTE is separate: it lights every console
# of a ship in red alert (helm/weapons/…), not just the button owners.
_view_redalert_clients: set = set()
# Last vignette state (bool) sent per client, so we only push on transitions.
_redalert_state: dict = {}
# Last button on-state (bool) sent per button-owner client.
_redalert_btn_state: dict = {}

# Clients whose console declares the "comms_control" widget — the comms action menu.
# The comms system emits the menu via send_comms_selection_info (header) +
# send_comms_button_info (each button), keyed by the comms ORIGIN (ship/cam); the mock
# maps that origin back to the viewing client(s) and streams a clickable panel.
_view_comms_control_clients: set = set()
# Clients whose console declares the "comms_face" widget — the selected target's portrait.
# The face string arrives in send_comms_selection_info (2nd arg); rendered via face.js.
_view_comms_face_clients: set = set()
# Clients whose console declares the "comms_waterfall" widget — the comms dialogue stream.
# Fed by send_comms_message_to_player_ship (comms_message/comms_transmit/comms_broadcast).
_view_comms_wf_clients: set = set()
# Clients whose console declares the "radar_zoom_ctrl" widget — a browser-local zoom slider
# bound to the 2D radar scale (no server state; the mock renders/handles it entirely).
_view_radar_zoom_clients: set = set()
# Clients whose console declares the "comms_sorted_list" widget — a scrollable list of comms
# targets. The engine builds this internally; the mock streams nearby sided ships each second.
_view_comms_list_clients: set = set()
_comms_list_tick: int = 0
_COMMS_LIST_INTERVAL: int = 15   # rebuild ~twice a second (physics thread is 30 Hz)
# DEV DEMO KNOB: MOCK_FORCE_RED_ALERT=1 forces the red-alert vignette ON for every
# client showing a 2D view, regardless of the mission's console layout or the ship's
# real red_alert value. Purely to eyeball the widget render (e.g. on the OU Admiral,
# whose console has no red_alert widget). Leave unset for normal behavior.
_FORCE_RED_ALERT = os.environ.get("MOCK_FORCE_RED_ALERT", "") not in ("", "0", "false", "False")

# Per-client console NAME (from send_client_widget_list's consoleType == page.console).
# Used to fill event.sub_tag on a radar-click selection so consoledispatcher routes it
# to the right console selection (a name with "comm" -> comms, "sci"/"admiral" -> science).
_console_name: dict = {}

# ---------------------------------------------------------------------------
# Engine (Family B) widget registry
# ---------------------------------------------------------------------------
# One descriptor per engine console widget the browser can draw.  Adding a widget
# is one entry here plus a `cmd<Name>` renderer in client.html.  Before this table
# the same facts were spread across three parallel if-cascades (widget list, widget
# rects, per-tick push) that had to be edited in lockstep - which is how they drifted.
#
#   cmd       browser command name.
#   clients   clientIDs whose console currently declares this widget.
#   rect      how a script layout rect is forwarded to the browser:
#               "op"     -> {op:"rect", left..bottom}    (the comms_* family)
#               "active" -> {active:True, left..bottom}  (the red_alert button)
#               "hud"    -> the shared hud_rect command  (ship_data, text_waterfall);
#                           forwarded only when the rect is non-degenerate
#   hide      how a removal is signalled: "op" -> {op:"hide"}, "active" -> {active:False}
#   defaults  fallback placement per console name for widgets the mission never lays
#             out, as (anchor, dx, dy, w, h) in CAPTURE pixels - see _CAPTURE_W/H and
#             _DEFAULT_RECTS below.  "*" applies to any console.
#   on_change per-client cleanup run when the widget is declared OR removed.
#
# Only helm and weapons need `defaults`: LM lays comms/science/engineering out with
# gui_layout_widget (so real rects already arrive), but leaves helm and weapons to the
# engine's internal C++ layout, which never reaches the mock.

# Reference resolution of the engine console captures the default rects were measured
# from.  The browser scales these by its own viewport height and anchors to the named
# edge, so the proportions hold at any window size instead of stretching.
_CAPTURE_W, _CAPTURE_H = 2552.0, 1355.0


class _EngineWidget:
    """A Family-B engine widget the browser mock knows how to draw."""
    __slots__ = ("name", "cmd", "rect", "hide", "defaults", "clients", "on_change")

    def __init__(self, name, cmd, rect=None, hide=None, defaults=None,
                 clients=None, on_change=None):
        self.name = name
        self.cmd = cmd
        self.rect = rect
        self.hide = hide
        self.defaults = defaults or {}
        self.clients = clients if clients is not None else set()
        self.on_change = on_change

    def default_for(self, console):
        """The fallback rect for this console, or None to leave placement to the script."""
        return self.defaults.get(console) or self.defaults.get("*")


_ENGINE_WIDGETS: dict = {}


def _register(w: _EngineWidget) -> _EngineWidget:
    _ENGINE_WIDGETS[w.name] = w
    return w


def _hide_widget(clientID: int, w: _EngineWidget) -> None:
    """Tell the browser this client's console no longer shows the widget."""
    if gui_queue is None or not w.hide:
        return
    if w.hide == "op":
        _send(clientID, w.cmd, op="hide")
    else:
        _send(clientID, w.cmd, active=False)


def _send_rect(clientID: int, w: _EngineWidget,
               l1: float, t1: float, r1: float, b1: float) -> None:
    """Forward a script-set layout rect (already resolved to screen percent)."""
    coords = dict(left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
    if w.rect == "op":
        _send(clientID, w.cmd, op="rect", **coords)
    elif w.rect == "active":
        _send(clientID, w.cmd, active=True, **coords)
    elif w.rect == "hud":
        # Mock-only HUD overlays share one reposition command keyed by widget name.
        _send(clientID, "hud_rect", widget=w.name, **coords)


def _send_default_rect(clientID: int, w: _EngineWidget, console: str) -> None:
    """Place a widget the mission never laid out, using the engine capture defaults.

    Sent in CAPTURE pixels plus the reference size; the browser scales by its own
    viewport and anchors to the named edge.  A later script rect simply overwrites
    it, so sending this unconditionally is safe."""
    d = w.default_for(console or "")
    if d is None or gui_queue is None or w.rect != "op":
        return
    anchor, dx, dy, ww, hh = d
    _send(clientID, w.cmd, op="defrect", anchor=anchor,
          dx=dx, dy=dy, w=ww, h=hh, refw=_CAPTURE_W, refh=_CAPTURE_H)


# --- the widgets the browser already draws -------------------------------------
# ship_data / text_waterfall are mock HUD overlays: they sit in a screen corner by
# default and only move when a script sizes them, so their rect is forwarded only
# when non-degenerate.
_register(_EngineWidget("ship_data", "ship_data", rect="hud", hide="active",
                        clients=_view_shipdata_clients))
_register(_EngineWidget("text_waterfall", "text_active", rect="hud", hide="active",
                        clients=_view_text_clients))
# The red-alert TOGGLE BUTTON (the vignette is driven separately, per ship).
_register(_EngineWidget("red_alert", "red_alert_btn", rect="active", hide="active",
                        clients=_view_redalert_clients,
                        on_change=lambda cid: _redalert_btn_state.pop(cid, None)))
_register(_EngineWidget("comms_control", "comms_control", rect="op", hide="op",
                        clients=_view_comms_control_clients))
_register(_EngineWidget("comms_face", "comms_face", rect="op", hide="op",
                        clients=_view_comms_face_clients))
_register(_EngineWidget("comms_waterfall", "comms_wf", rect="op", hide="op",
                        clients=_view_comms_wf_clients))
_register(_EngineWidget("radar_zoom_ctrl", "radar_zoom", rect="op", hide="op",
                        clients=_view_radar_zoom_clients))
_register(_EngineWidget("comms_sorted_list", "comms_list", rect="op", hide="op",
                        clients=_view_comms_list_clients))


# --- helm / weapons controls ---------------------------------------------------
# These two consoles are the ones LM never lays out (layout_widgets.mast //gui/normal_helm
# and //gui/normal_weap place no engine widgets at all), so the engine positions them in
# C++ and the mock is handed nothing.  The `defaults` below were measured off engine
# console captures with the widget-bounds overlay on; the numbers are CAPTURE PIXELS at
# _CAPTURE_W x _CAPTURE_H, anchored to a screen corner ("tl"/"tr"/"bl"/"br").
#
# Pixels rather than percent because the two captures disagree on percentages while
# agreeing on pixels - ship_data measures ~306x492 px in both, at different resolutions.
# The engine sizes these in pixels and anchors them to edges; the browser rescales by its
# own viewport height so the proportions survive a differently shaped window.

_register(_EngineWidget("throttle", "throttle", rect="op", hide="op", defaults={
    "normal_helm": ("bl", 0, 22, 134, 542)}))
_register(_EngineWidget("helm_movement", "helm_move", rect="op", hide="op", defaults={
    "normal_helm": ("bl", 128, 3, 331, 295)}))
_register(_EngineWidget("shield_control", "shield_ctrl", rect="op", hide="op", defaults={
    "normal_helm": ("tr", 13, 342, 325, 85),
    "normal_weap": ("tr", 22, 645, 660, 65)}))
_register(_EngineWidget("request_dock", "dock_ctrl", rect="op", hide="op", defaults={
    "normal_helm": ("tr", 13, 434, 325, 76)}))
_register(_EngineWidget("main_screen_control", "mainscreen_ctrl", rect="op", hide="op",
                        defaults={
    "normal_helm": ("tr", 13, 61, 373, 252),
    "normal_weap": ("tr", 22, 78, 535, 247)}))
# Jump drives: drawn so the console is not a hole, but inert - ENGINE_WIDGETS.md open
# questions 2-3 leave their delivery unconfirmed, and guessing a data_set key would be
# worse than saying plainly that the mock does not emulate them.
_register(_EngineWidget("helm_jump", "helm_jump", rect="op", hide="op", defaults={
    "normal_helm": ("bl", 453, 28, 1435, 83)}))
_register(_EngineWidget("quick_jump", "quick_jump", rect="op", hide="op", defaults={
    "normal_helm": ("bl", 1400, 111, 418, 134)}))

_register(_EngineWidget("weapon_control", "weapon_ctrl", rect="op", hide="op", defaults={
    "normal_weap": ("br", 22, 0, 570, 295)}))
_register(_EngineWidget("weap_beam_freq", "beam_freq", rect="op", hide="op", defaults={
    "normal_weap": ("tr", 22, 715, 660, 75)}))
_register(_EngineWidget("weap_beam_speed", "beam_speed", rect="op", hide="op", defaults={
    "normal_weap": ("tr", 22, 795, 660, 75)}))
_register(_EngineWidget("weap_torp_conversion", "torp_conv", rect="op", hide="op", defaults={
    "normal_weap": ("tr", 22, 875, 660, 95)}))

# --- science -------------------------------------------------------------------
# No defaults: LM lays every science widget out with gui_layout_widget
# (layout_widgets.mast //gui/normal_sci), so real rects already reach the mock - the
# names were simply being dropped.
_register(_EngineWidget("science_data", "sci_data", rect="op", hide="op"))
_register(_EngineWidget("science_data_tabs", "sci_tabs", rect="op", hide="op"))
_register(_EngineWidget("science_data_freq", "sci_freq", rect="op", hide="op"))
_register(_EngineWidget("science_sorted_list", "sci_list", rect="op", hide="op"))


# Engine widget names seen in a widget list that the mock has no renderer for.
# Reported once each so an unimplemented widget is distinguishable from a broken
# one - previously both looked like an empty rectangle.
_unknown_widgets_seen: set = set()


def get_client_console_name(clientID: int) -> str:
    """The console name last activated for this client (e.g. 'gamemaster_overseer_comms',
    'normal_sci'), or '' if unknown. The runner reads it to route a radar-click select."""
    return _console_name.get(clientID, "")


def get_client_2d_widget(clientID: int) -> str:
    """The 2D-view widget name on this client's console (e.g. 'comms_2d_view',
    'science_2d_view'), or '' if none. The engine puts this in a selection event's
    value_tag; the runner reads it so a radar-click select matches the engine exactly."""
    return _view2d_widget_clients.get(clientID, "")


def send_client_widget_list(clientID: int, consoleType: str, widgetList: str) -> None:
    """Record the console type (base behaviour) and drive the browser's gameplay
    views from this client's widget list: activate the 3dview when a "3dview"
    widget is present, and register a 2D radar rect when a 2D-view widget is."""
    _base_mock.send_client_widget_list(clientID, consoleType, widgetList)
    # Remember the console NAME for this client — a radar-click selection event needs it as
    # event.sub_tag so consoledispatcher routes to comms/science by name. Keep the last
    # NON-EMPTY name: a repaint (or widget-only update) can call this with an empty
    # consoleType (the Admiral doesn't re-run gui_activate_console on its repaint), and wiping
    # the name would make a later 2D-view select route to normal_target_UID instead of
    # comms_target_UID — breaking comms selection after e.g. a comms button. The engine tracks
    # the console name independently and never loses it; this mirrors that.
    if consoleType:
        _console_name[clientID] = consoleType
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

    # Every remaining engine widget is table-driven: declare it and the browser starts
    # drawing it, drop it and the browser is told to hide it.  Widgets the mission never
    # lays out (helm and weapons - LM leaves both to the engine's C++ layout) also get
    # their capture-measured default placement here; a later script rect overrides it.
    for w in _ENGINE_WIDGETS.values():
        shown = w.name in widgets
        if not shown and clientID not in w.clients:
            continue
        _hud_cache.pop((clientID, w.cmd), None)   # force a FULL state re-send on return
        if w.on_change is not None:
            w.on_change(clientID)
        if shown:
            w.clients.add(clientID)
            _send_default_rect(clientID, w, consoleType)
        else:
            w.clients.discard(clientID)
            _hide_widget(clientID, w)

    # target_data HUD — mock-only, and keyed on the console NAME rather than a widget
    # name, so it stays outside the table.
    if consoleType == "normal_main":
        _view_target_clients.add(clientID)
    elif clientID in _view_target_clients:
        _view_target_clients.discard(clientID)
        _send(clientID, "target_data", active=False)
        _hud_cache.pop((clientID, "target_data"), None)

    # An engine widget with no descriptor draws nothing.  Say so once per name, so an
    # unimplemented widget is distinguishable from a broken one - both used to look
    # like an empty rectangle with no explanation anywhere.
    for name in widgets:
        if (not name or name in _ENGINE_WIDGETS or name in _2D_VIEW_WIDGETS
                or name == "3dview" or name in _unknown_widgets_seen):
            continue
        _unknown_widgets_seen.add(name)
        print(f"[mock] engine widget {name!r} is not emulated - its rectangle "
              f"will be blank in the browser")


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


def _systems_health(ds) -> list:
    """The 4 engine ship systems (sbs.SHPSYS) as [{name, pct, heat}], where pct is
    health from system_damage / system_max_damage (100% if no max set) and heat is
    the engine's system_cur_heat (engineering overpower/coolant, 0..1 -> %)."""
    out = []
    for name, idx in _base_mock.SHIP_SYSTEMS:
        dmg = ds.get("system_damage", idx)
        mx = ds.get("system_max_damage", idx)
        heat = ds.get("system_cur_heat", idx)
        dmg = 0.0 if dmg is None else float(dmg)
        mx = 0.0 if mx is None else float(mx)
        heat = 0.0 if heat is None else float(heat)
        pct = round((1.0 - dmg / mx) * 100) if mx > 0 else 100
        out.append({"name": name, "pct": max(0, min(100, pct)),
                    "heat": max(0, min(100, round(heat * 100)))})
    return out


def _shield_frac(obj) -> float:
    """Total current / total max shields across all facings, 0..1, for the radar's
    shield ring color. Returns -1.0 for objects with no shields (stations, terrain,
    pickups) so the browser can skip the ring."""
    ds = obj.data_set
    n = int(ds.get("shield_count", 0) or 0)
    if n <= 0:
        return -1.0
    cur = sum((ds.get("shield_val", i) or 0.0) for i in range(n))
    mx = sum((ds.get("shield_max_val", i) or 0.0) for i in range(n))
    if mx <= 0:
        return -1.0
    return round(max(0.0, min(1.0, cur / mx)), 3)


def _shield_fracs(obj):
    """(front, aft) shield fractions 0..1 for the split shield ring (facing 0 = fore,
    1 = aft). Falls back to the fore value on a single-facing ship; (-1, -1) with no shields."""
    ds = obj.data_set
    n = int(ds.get("shield_count", 0) or 0)
    if n <= 0:
        return (-1.0, -1.0)

    def frac(i):
        mx = ds.get("shield_max_val", i) or 0.0
        if mx <= 0:
            return 0.0
        return round(max(0.0, min(1.0, (ds.get("shield_val", i) or 0.0) / mx)), 3)

    f = frac(0)
    return (f, frac(1) if n >= 2 else f)


def _ship_stat_payload(o, space) -> dict:
    """Common vitals (vitals + systems + torpedoes) for a ship object - shared by
    the ship_data and target_data HUDs."""
    ds = o.data_set

    def g(k, d=0.0):
        # data_set.get(name, index=0) - 2nd arg is the INDEX, not a default; read
        # facet 0 and coalesce None to our display default.
        v = ds.get(k, 0)
        return d if v is None else v

    tid = ds.get("weapon_target_UID", 0) or ds.get("target_id", 0) or 0
    t = space.get(tid)
    tname = (getattr(t, "name", None) or getattr(t, "_data_tag", "")) if t is not None else ""
    loaded = {x.strip() for x in str(ds.get("tube_contents", 0) or "").split(",") if x.strip()}
    torps = []
    for tt in [x.strip() for x in str(ds.get("torpedo_types_available", 0) or "").split(",") if x.strip()]:
        torps.append({"name": tt, "num": int(g(f"{tt}_NUM")),
                      "max": int(g(f"{tt}_MAX")), "tube": tt in loaded})
    # Per-facing shields (engine shield_count facings). Facing 0 = fore, 1 = aft on a
    # 2-shield ship; the browser shows each separately. shield/shield_max stay as the
    # facing-0 (fore) value for any older consumer.
    n_sh = int(ds.get("shield_count", 0) or 0)
    shields = [round(float(ds.get("shield_val", i) or 0.0), 1) for i in range(n_sh)]
    shields_max = [round(float(ds.get("shield_max_val", i) or 0.0), 1) for i in range(n_sh)]
    return dict(
        name=getattr(o, "name", None) or getattr(o, "_data_tag", "") or "ship",
        shield=round(float(g("shield_val")), 1),
        shield_max=round(float(g("shield_max_val")), 1),
        shields=shields,
        shields_max=shields_max,
        energy=round(float(g("energy")), 1),
        hull=round(float(g("armor")), 1),
        hull_max=round(float(g("armorMax")), 1),
        throttle=round(float(g("playerThrottle")), 2),
        speed=round(float(getattr(o, "_cur_speed", 0.0)), 1),
        dock_state=str(ds.get("dock_state", 0) or ""),
        red_alert=int(g("red_alert", 0)),
        target=tname,
        systems=_systems_health(ds),
        torps=torps,
    )


def _push_stat_panel(cid: int, panel: str, obj, obj_id: int, space) -> None:
    """Stream a ship/target stat panel for one client, sending only what CHANGED.

    Skips entirely when the object's data_set is unchanged since our last push (its
    `gen` counter) AND its speed is unchanged - no recompute, no send. Otherwise it
    computes the payload, diffs it against the last one sent to this client, and sends
    only the differing fields (the browser merges partials). A change of which object
    the panel tracks (obj_id) forces a full re-send. `obj is None` -> a single
    active=False (deactivate), sent once."""
    key = (cid, panel)
    if obj is None:
        if _hud_cache.get(key) is not None:        # was active -> deactivate once
            _send(cid, panel, active=False)
            _hud_cache[key] = None
        return
    # Cheap early-out: same object, data_set unchanged (gen), speed steady.
    gen = obj.data_set.gen
    speed = round(float(getattr(obj, "_cur_speed", 0.0)), 1)
    prev = _hud_cache.get(key)
    same_obj = prev is not None and prev.get("oid") == obj_id
    if same_obj and prev["gen"] == gen and prev["speed"] == speed:
        return
    payload = _ship_stat_payload(obj, space)
    last = prev["payload"] if same_obj else None    # object changed -> full re-send
    if last is None:
        _send(cid, panel, active=True, **payload)   # first send (or new object): full
    else:
        delta = {k: v for k, v in payload.items() if last.get(k) != v}
        if delta:
            _send(cid, panel, active=True, **delta)  # subsequent: only changed fields
    _hud_cache[key] = {"oid": obj_id, "gen": gen, "speed": speed, "payload": payload}


def _push_ship_data() -> None:
    """Stream each ship_data client's player-ship vitals so the browser can render
    a live HUD (shields, energy, dock_state, throttle, speed, hull, heat, target,
    systems, torpedoes). Only changed fields are sent (see _push_stat_panel)."""
    if _base_mock.sim is None or gui_queue is None:
        return
    space = _base_mock.sim.space_objects
    for cid in list(_view_shipdata_clients):
        sid = _base_mock.get_ship_of_client(cid)
        _push_stat_panel(cid, "ship_data", space.get(sid), sid, space)


def _push_target_data() -> None:
    """Stream the current weapon/selected target's stats so the browser can render
    a target HUD (mock-only - the engine has no such panel). Shown only on the
    main-screen console ("normal_main"). active=False when there's no target."""
    if _base_mock.sim is None or gui_queue is None:
        return
    space = _base_mock.sim.space_objects
    for cid in list(_view_target_clients):
        ship = space.get(_base_mock.get_ship_of_client(cid))
        t, tid = None, 0
        if ship is not None:
            tid = ship.data_set.get("weapon_target_UID", 0) or ship.data_set.get("target_id", 0) or 0
            t = space.get(tid)
        _push_stat_panel(cid, "target_data", t, tid, space)


def _push_text_active() -> None:
    """Re-assert the text waterfall each tick for clients whose console declares
    it, so the per-tick root send_gui_clear (server rebuild) doesn't leave the
    event-driven waterfall hidden."""
    if gui_queue is None:
        return
    for cid in list(_view_text_clients):
        _send(cid, "text_active", active=True)


def _ship_red_alert(cid, get_inventory_value, space) -> bool:
    """True if the ship assigned to client `cid` is in red alert. Red alert lives on the
    Agent INVENTORY in the mock (handlerhooks.py: set_inventory_value(ship, "red_alert",
    ...)) OR the engine data_set in real Cosmos; space.get() returns the ENGINE object
    (has data_set, NO get_inventory_value), so read inventory by id via the procedural API."""
    sid = _base_mock.get_ship_of_client(cid)
    if not sid:
        return False
    inv_v = get_inventory_value(sid, "red_alert", 0)
    obj = space.get(sid)
    ds_v = obj.data_set.get("red_alert", 0) if obj is not None else 0
    return bool(inv_v or ds_v or 0)


def _push_red_alert() -> None:
    """Two streams, both transition-only (browser retains state):
      1. the alert VIGNETTE to every connected console whose assigned ship is in red alert
         (ship-wide — helm/weapons/comms/engineering/science), and
      2. the toggle BUTTON's on-state to consoles that declare the red_alert widget."""
    if _base_mock.sim is None or gui_queue is None:
        return
    # Lazy import (procedural imports `sbs` — this module — so import at call time to
    # avoid a load-order cycle, matching the other lazy imports in this file).
    from sbs_utils.procedural.inventory import get_inventory_value
    space = _base_mock.sim.space_objects

    # (1) Vignette — every connected console client, keyed on its OWN ship's state.
    for cid in _base_mock.get_client_ID_list():
        alert = True if _FORCE_RED_ALERT else _ship_red_alert(cid, get_inventory_value, space)
        if _redalert_state.get(cid) != alert:
            _redalert_state[cid] = alert
            _send(cid, "red_alert", active=True, alert=alert)

    # (2) Button on-state — only consoles that declare the widget (position comes from
    # send_client_widget_rects; here we keep the button's label/glow in sync with state).
    for cid in list(_view_redalert_clients):
        on = _ship_red_alert(cid, get_inventory_value, space)
        if _redalert_btn_state.get(cid) != on:
            _redalert_btn_state[cid] = on
            _send(cid, "red_alert_btn", active=True, on=on)


# ---------------------------------------------------------------------------
# comms_control — the comms action menu (button tree)
# ---------------------------------------------------------------------------
def _comms_clients_for_origin(origin_id):
    """Console clients whose assigned ship IS the comms origin. The comms system addresses
    the header/buttons by origin (ship/cam) id; the mock renders on the console(s) viewing
    that origin. Callers filter by which comms widget the client declares. Runs on the MAST
    thread (comms event handling)."""
    if not origin_id:
        return []
    return [cid for cid in _base_mock.get_client_ID_list()
            if _base_mock.get_ship_of_client(cid) == origin_id]


def send_comms_selection_info(origin_id, face, color, title) -> None:
    """Comms header — face/colour/title. Drives BOTH the comms_control panel (OPEN: clear
    prior buttons + set header; send_comms_button_info then appends buttons in set_buttons
    order) and the comms_face portrait (the face string)."""
    if gui_queue is None:
        return
    for cid in _comms_clients_for_origin(origin_id):
        if cid in _view_comms_control_clients:
            _send(cid, "comms_control", op="open", face=face or "", color=color or "white",
                  title=title or "")
        if cid in _view_comms_face_clients:
            _send(cid, "comms_face", op="face", face=face or "",
                  title=title or "", color=color or "white")


def send_comms_button_info(origin_id, color, msg, tag) -> None:
    """One comms button: label `msg`, `tag` is the button INDEX the engine echoes back in
    press_comms_button.sub_tag. Appended to the panel opened by send_comms_selection_info."""
    if gui_queue is None:
        return
    for cid in _comms_clients_for_origin(origin_id):
        if cid in _view_comms_control_clients:
            _send(cid, "comms_control", op="button", tag=str(tag), color=color or "white",
                  msg=msg or "")


def send_comms_message_to_player_ship(playerID, otherID, faceDesc, titleText, titleColor,
                                      bodyText, bodyColor) -> None:
    """A comms transmission to a player ship (comms_message / comms_transmit / comms_broadcast
    all route here). Streamed to that ship's comms_waterfall consoles as an iMessage-style
    message: sender face + coloured title + body. otherID is the other party (not rendered)."""
    if gui_queue is None or _base_mock.sim is None:
        return
    for cid, sid in list(_base_mock.sim.client_ships.items()):
        if sid == playerID and cid in _view_comms_wf_clients:
            _send(cid, "comms_wf", op="msg", face=faceDesc or "",
                  title=titleText or "", title_color=titleColor or "white",
                  body=bodyText or "", body_color=bodyColor or "white")


def _push_comms_list() -> None:
    """Stream each comms_sorted_list console a list of nearby comms-target ships (sided
    active objects, nearest first). The engine builds this widget internally; the mock
    approximates it. A row click reuses the select_space_object path (routed to comms by
    console name)."""
    _push_contact_list(_ENGINE_WIDGETS["comms_sorted_list"].clients, "comms_list")

def _push_delta(cid: int, panel: str, payload, ident=None) -> None:
    """Stream a panel payload, sending only the fields that CHANGED since last time.

    Generalises the diff half of _push_stat_panel for the console-widget panels.
    `ident` is what the panel is tracking (a ship id, a selection id): when it changes
    the payload is re-sent in FULL, because the browser's merged state describes the
    previous subject.  payload None -> one active=False, sent once."""
    key = (cid, panel)
    prev = _hud_cache.get(key)
    if payload is None:
        if prev is not None:
            _send(cid, panel, active=False)
            _hud_cache[key] = None
        return
    same = prev is not None and prev.get("oid") == ident
    last = prev["payload"] if same else None
    if last is None:
        _send(cid, panel, active=True, **payload)
    else:
        delta = {k: v for k, v in payload.items() if last.get(k) != v}
        if not delta:
            return
        _send(cid, panel, active=True, **delta)
    _hud_cache[key] = {"oid": ident, "gen": None, "speed": None, "payload": payload}


def _client_ship(cid: int):
    """The space object this client is flying, or None."""
    s = _base_mock.sim
    if s is None:
        return None
    return s.space_objects.get(_base_mock.get_ship_of_client(cid))


def _heading_deg(o) -> float:
    """Compass heading of a space object in degrees (0 = +Z, 90 = +X), matching the
    bearings the 2D radar labels."""
    f = o.forward_vector()
    return round(math.degrees(math.atan2(f.x, f.z)) % 360.0, 1)


def _base_beam_cycle(o) -> float:
    """The hull's UNMODIFIED primary-beam cycle time, from shipData.

    Read back from the hull rather than cached, so the weapons fire-rate widget stays
    stateless: the live beamCycleTime is always base/rate, so the selected rate is
    recoverable by division and nothing has to survive a mission reload."""
    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        info = get_ship_data_for(getattr(o, "_data_tag", "") or "") or {}
        beams = info.get("hull_port_sets", {}).get("beam Primary Beams", [])
        if beams:
            return float(beams[0].get("cycle_time", 6.0)) or 6.0
    except Exception:
        pass
    return 6.0


def _deactivate(cid: int, panels) -> None:
    """Blank a set of console panels for a client with no ship (destroyed, unassigned)."""
    for panel in panels:
        _push_delta(cid, panel, None)


# ---------------------------------------------------------------------------
# Helm
# ---------------------------------------------------------------------------
def _push_helm() -> None:
    """Stream the helm control widgets' state: speed and throttle, heading and
    altitude, shield and dock state, and the main-screen selection.  Every value is
    read straight off the ship's data_set - the same keys the engine widgets write -
    so what the browser shows is what a mission script would poll."""
    if _base_mock.sim is None or gui_queue is None:
        return
    w_thr = _ENGINE_WIDGETS["throttle"].clients
    w_mov = _ENGINE_WIDGETS["helm_movement"].clients
    w_shd = _ENGINE_WIDGETS["shield_control"].clients
    w_dok = _ENGINE_WIDGETS["request_dock"].clients
    w_mss = _ENGINE_WIDGETS["main_screen_control"].clients
    every = set(w_thr) | set(w_mov) | set(w_shd) | set(w_dok) | set(w_mss)
    if not every:
        return
    for cid in every:
        o = _client_ship(cid)
        sid = _base_mock.get_ship_of_client(cid)
        if o is None:
            _deactivate(cid, ("throttle", "helm_move", "shield_ctrl",
                              "dock_ctrl", "mainscreen_ctrl"))
            continue
        ds = o.data_set
        if cid in w_thr:
            # `warp` gates the WARP band exactly as the engine widget does: a throttle
            # above 1.0 only means anything on a ship that has a warp drive.
            _push_delta(cid, "throttle", {
                "throttle": round(float(ds.get("playerThrottle", 0) or 0.0), 2),
                "speed": round(float(getattr(o, "_cur_speed", 0.0)), 2),
                "warp_ok": bool(float(ds.get("warp", 0) or 0.0) == 1.0),
            }, sid)
        if cid in w_mov:
            f = o.forward_vector()
            _push_delta(cid, "helm_move", {
                "ang": _heading_deg(o),
                "alt": round(float(o._pos.y), 0),
                "azi": round(math.degrees(math.asin(max(-1.0, min(1.0, f.y)))), 1),
                "steering": bool(ds.get("steeringToDirFlag", 0) or 0),
            }, sid)
        if cid in w_shd:
            _push_delta(cid, "shield_ctrl", {
                "up": bool(ds.get("shields_raised_flag", 0) or 0)}, sid)
        if cid in w_dok:
            _push_delta(cid, "dock_ctrl", {
                "state": str(ds.get("dock_state", 0) or "")}, sid)
        if cid in w_mss:
            from sbs_utils.procedural.inventory import get_inventory_value
            _push_delta(cid, "mainscreen_ctrl", {
                "view": str(get_inventory_value(sid, "MAIN_SCREEN_VIEW", "3d_view")),
                "facing": str(get_inventory_value(sid, "MAIN_SCREEN_FACING", "front")),
                "mode": str(get_inventory_value(sid, "MAIN_SCREEN_MODE", "chase")),
            }, sid)


# ---------------------------------------------------------------------------
# Weapons
# ---------------------------------------------------------------------------
def _push_weapons() -> None:
    """Stream the weapons console widgets: beam frequency, beam fire rate, torpedo
    tubes and stock, and the energy<->torpedo conversion offers."""
    if _base_mock.sim is None or gui_queue is None:
        return
    w_frq = _ENGINE_WIDGETS["weap_beam_freq"].clients
    w_spd = _ENGINE_WIDGETS["weap_beam_speed"].clients
    w_ctl = _ENGINE_WIDGETS["weapon_control"].clients
    w_cnv = _ENGINE_WIDGETS["weap_torp_conversion"].clients
    every = set(w_frq) | set(w_spd) | set(w_ctl) | set(w_cnv)
    if not every:
        return
    space = _base_mock.sim.space_objects
    for cid in every:
        o = _client_ship(cid)
        sid = _base_mock.get_ship_of_client(cid)
        if o is None:
            _deactivate(cid, ("beam_freq", "beam_speed", "weapon_ctrl", "torp_conv"))
            continue
        ds = o.data_set
        if cid in w_frq:
            # scan_type_for_shld_freq spans the five bands A-E over 0.0-1.0.
            f = float(ds.get("scan_type_for_shld_freq", 0) or 0.0)
            _push_delta(cid, "beam_freq", {
                "index": max(0, min(4, int(round(f * 4.0)))),
                "weak": _target_weak_freq(ds, space),
            }, sid)
        if cid in w_spd:
            cyc = float(ds.get("beamCycleTime", 0) or 0.0)
            base = _base_beam_cycle(o)
            rate = 1 if cyc <= 0 else max(1, min(4, int(round(base / cyc))))
            _push_delta(cid, "beam_speed", {"rate": rate, "cycle": round(cyc, 2)}, sid)
        if cid in w_ctl:
            loaded = [x.strip() for x in str(ds.get("tube_contents", 0) or "").split(",")]
            tubes = int(ds.get("torpedo_tube_count", 0) or 0)
            types = _torp_types(ds)
            _push_delta(cid, "weapon_ctrl", {
                "types": types,
                "stock": {t: int(ds.get(t + "_NUM", 0) or 0) for t in types},
                "tubes": [loaded[i] if i < len(loaded) else "" for i in range(tubes)],
            }, sid)
        if cid in w_cnv:
            _push_delta(cid, "torp_conv", {
                "energy": round(float(ds.get("energy", 0) or 0.0), 1),
                "offers": [_torp_conversion_offer(ds, t) for t in _torp_types(ds)],
            }, sid)


def _torp_types(ds) -> list:
    """The torpedo type names this ship can carry, in the ship's own order."""
    raw = str(ds.get("torpedo_types_available", 0) or "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def _torp_conversion_offer(ds, kind: str) -> dict:
    """One row of the weap_torp_conversion widget: what this torpedo type is worth as
    energy, and what it costs to build one.  Values come from the torpedo's own style
    string (energy_conversion_value / energy_to_torp_cost), as the engine widget does."""
    val = _torp_prop(kind, "energy_conversion_value", 100.0)
    cost = val + _torp_prop(kind, "energy_to_torp_cost", 50.0)
    have = int(ds.get(kind + "_NUM", 0) or 0)
    mx = int(ds.get(kind + "_MAX", 0) or 0)
    energy = float(ds.get("energy", 0) or 0.0)
    return {"kind": kind, "value": val, "cost": cost,
            "can_scrap": have > 0, "can_build": energy >= cost and have < mx}


def _torp_prop(kind: str, prop: str, default: float) -> float:
    """Read a numeric property out of a torpedo type's shared style string."""
    try:
        s = _base_mock.get_shared_string(kind) or ""
    except Exception:
        return default
    for part in s.split(";"):
        k, _, v = part.partition(":")
        if k.strip() == prop:
            try:
                return float(v.strip())
            except ValueError:
                return default
    return default


def _target_weak_freq(ds, space) -> int:
    """Which beam band (0-4 = A-E) the current weapons target is weakest to, or -1 with
    no target.  Derived from the target id because the mock has no per-hull frequency
    profile to read - stable per contact rather than flickering each tick."""
    tid = ds.get("weapon_target_UID", 0) or ds.get("target_id", 0) or 0
    if not tid or space.get(tid) is None:
        return -1
    return int(tid) % 5


# ---------------------------------------------------------------------------
# Science
# ---------------------------------------------------------------------------
def _push_science() -> None:
    """Stream the science console widgets: the contact list, the selected contact's
    data panel, its scan tabs, and the frequency readout."""
    if _base_mock.sim is None or gui_queue is None:
        return
    w_lst = _ENGINE_WIDGETS["science_sorted_list"].clients
    w_dat = _ENGINE_WIDGETS["science_data"].clients
    w_tab = _ENGINE_WIDGETS["science_data_tabs"].clients
    w_frq = _ENGINE_WIDGETS["science_data_freq"].clients
    if not (w_lst or w_dat or w_tab or w_frq):
        return
    space = _base_mock.sim.space_objects
    if w_lst:
        _push_contact_list(w_lst, "sci_list")
    for cid in set(w_dat) | set(w_tab) | set(w_frq):
        o = _client_ship(cid)
        tid = int(o.data_set.get("science_target_UID", 0) or 0) if o is not None else 0
        t = space.get(tid) if tid else None
        if cid in w_dat:
            _push_delta(cid, "sci_data", _science_payload(o, t, tid), tid)
        if cid in w_tab:
            # Which tabs exist AND which are already scanned, so the strip can mark them.
            _push_delta(cid, "sci_tabs", None if t is None else {
                "tabs": _science_tabs(t),
                "done": [tab for tab in _science_tabs(t) if _tab_scanned(o, t, tab)],
            }, tid)
        if cid in w_frq:
            # Band strengths are a stable function of the contact, so the readout holds
            # steady while a contact is selected instead of dancing every tick.
            _push_delta(cid, "sci_freq", None if t is None else {
                "weak": int(tid) % 5,
                "bands": [round(0.35 + 0.16 * ((int(tid) // (5 ** i)) % 4), 2)
                          for i in range(5)],
            }, tid)


def _science_tabs(t) -> list:
    """The scan tabs this contact exposes (scan_type_list), always including 'scan'."""
    raw = str(t.data_set.get("scan_type_list", 0) or "")
    tabs = [x.strip() for x in raw.split(",") if x.strip()]
    return ["scan"] + [x for x in tabs if x != "scan"]


def _science_payload(o, t, tid: int):
    """The science_data panel for the selected contact.

    Scan state is per (target, TAB, side) - science_get_scan_data reads the tab off the
    target's blob keyed by the scanning ship's side - so this reports every tab, not a
    single "scanned" flag, plus where each queued tab sits in the ship's scan queue."""
    if o is None or t is None:
        return None
    dx = t._pos.x - o._pos.x
    dy = t._pos.y - o._pos.y
    dz = t._pos.z - o._pos.z
    ds = t.data_set
    n_sh = int(ds.get("shield_count", 0) or 0)
    queue = _base_mock.science_scan_queue(o.unique_ID)
    # Per tab: scanned yet, and its queue position (1 = the one actually scanning).
    tabs = _science_tabs(t)
    state = {}
    for tab in tabs:
        pos = next((i + 1 for i, e in enumerate(queue)
                    if e["target"] == tid and e["tab"] == tab), 0)
        state[tab] = {"scanned": _tab_scanned(o, t, tab), "queued": pos}
    return {
        "name": (ds.get("name_tag") or ds.get("display_text")
                 or getattr(t, "_data_tag", "") or "?"),
        "side": getattr(t, "_side", "") or "",
        "range": int(math.sqrt(dx * dx + dy * dy + dz * dz)),
        "bearing": int(math.degrees(math.atan2(dx, dz)) % 360.0),
        "altitude": int(dy),
        "shields": [round(float(ds.get("shield_val", i) or 0.0), 0) for i in range(n_sh)],
        "systems": _systems_health(ds),
        "tab_state": state,
        "queue_len": len(queue),
        # Progress belongs to the head of the queue, whatever the console is looking at.
        "percent": int(o.data_set.get("cur_scan_percent", 0) or 0),
    }


def _tab_scanned(o, t, tab: str) -> bool:
    """Whether the scanning ship's SIDE already holds scan data for this tab of this
    contact.  Asks the real science store (data lives on the TARGET, keyed by tab and
    side) rather than keeping a parallel one that could disagree with the mission."""
    if o is None or t is None:
        return False
    try:
        from sbs_utils.procedural.science import science_get_scan_data
        # unique_ID, not .id: the mock's space_object has no `id`, and reaching for one
        # inside a broad try/except is how this silently answered "unscanned" forever.
        v = science_get_scan_data(o.unique_ID, t.unique_ID, tab)
    except Exception:
        return False
    if v is None:
        return False
    v = str(v).strip()
    # science_is_unknown treats these placeholders as "not scanned"; match it per tab.
    return v not in ("", "no data", "Default Scan")


# The 2D view marks the console's selection with a reticle, in that console's own colour
# from preferences.json.  Each console type reads a different selection UID and a different
# colour key - the same split consoledispatcher makes when it routes a 2D-view click.
#   console name contains -> (selection UID, preferences colour key)
_RETICLE_BY_CONSOLE = (
    ("weap",    ("weapon_target_UID",  "gui-color-weapon-reticle")),
    ("sci",     ("science_target_UID", "gui-color-science-reticle")),
    ("admiral", ("science_target_UID", "gui-color-science-reticle")),
    ("comm",    ("comms_target_UID",   "gui-color-comms-reticle")),
)
# Helm/normal has no reticle colour in preferences.json, so it takes the main GUI colour.
_RETICLE_DEFAULT = ("normal_target_UID", "gui-color-main")

# Which cell of reticle-set.png (a 5x4 grid) each console draws.  One knob per console so
# they can be set independently once the engine's choices are known.
_RETICLE_CELL = {"weapon": 1, "science": 19, "comms": 6, "normal": 10}

# Same knob as the runner's select trace (MOCK_LOG_SELECT=1).
_LOG_SELECT = os.environ.get("MOCK_LOG_SELECT", "") not in ("", "0", "false", "False")
_reticle_sent: dict = {}


def _reticle_for(console: str):
    """(selection UID key, colour, cell) for a console name."""
    cn = (console or "").lower()
    uid, colour_key = _RETICLE_DEFAULT
    kind = "normal"
    for token, pair in _RETICLE_BY_CONSOLE:
        if token in cn:
            uid, colour_key = pair
            kind = {"weap": "weapon", "sci": "science",
                    "admiral": "science", "comm": "comms"}[token]
            break
    colour = _base_mock.get_preference_string(colour_key) or "#ccf"
    return uid, colour, _RETICLE_CELL.get(kind, 0)


def _push_reticle() -> None:
    """Stream each 2D-view console its current selection, so the browser can draw the
    reticle over it.  Sent on change only - the browser retains it."""
    if _base_mock.sim is None or gui_queue is None or not _view2d_widget_clients:
        return
    size = _base_mock.get_preference_int("lock-reticle-size-2D") or 60
    for cid in list(_view2d_widget_clients.keys()):
        o = _client_ship(cid)
        uid_key, colour, cell = _reticle_for(_console_name.get(cid, ""))
        sel = int(o.data_set.get(uid_key, 0) or 0) if o is not None else 0
        snap = (sel, colour, cell, size)
        if _reticle_sent.get(cid) == snap:
            continue
        _reticle_sent[cid] = snap
        if _LOG_SELECT:
            # Pairs with the runner's [select] line: that one says what the CLICK derived,
            # this one says what the ship's blob actually holds a moment later. A click
            # that traces fine but shows sel=0 here means the selection never stored.
            print(f"[reticle] client={cid} console={_console_name.get(cid, '')!r} "
                  f"uid={uid_key} sel={sel} colour={colour} cell={cell}")
        _send(cid, "reticle", id=str(sel) if sel else "",
              color=colour, cell=cell, size=size)


def _push_contact_list(clients, cmd: str) -> None:
    """Stream a nearest-first list of sided contacts to each client in `clients`.

    Shared by comms_sorted_list and science_sorted_list: the engine builds both
    internally and they differ only in which console a row click routes through, which
    the select event already carries."""
    s = _base_mock.sim
    if s is None or gui_queue is None or not clients:
        return
    with s._lock:   # snapshot under the lock (MAST thread spawns/deletes) - see _push_radar
        objs = dict(s.space_objects)
        active = list(set(s._active_ids) & objs.keys())
        client_ships = dict(s.client_ships)
    for cid in list(clients):
        oid = client_ships.get(cid, 0)
        oo = objs.get(oid)
        ox = oo._pos.x if oo is not None else 0.0
        oz = oo._pos.z if oo is not None else 0.0
        items = []
        for i in active:
            if i == oid:
                continue
            o = objs[i]
            if not getattr(o, "side", None) or _drop_from_radar(o) or _not_selectable(o):
                continue
            dx = o._pos.x - ox
            dz = o._pos.z - oz
            name = (o.data_set.get("name_tag") or o.data_set.get("display_text")
                    or getattr(o, "_data_tag", "") or "?")
            items.append((dx * dx + dz * dz, {"id": str(i), "name": name, "side": o._side}))
        items.sort(key=lambda t: t[0])
        _send(cid, cmd, op="list", items=[it for _, it in items[:60]])


_last_colors_sent = None


def _push_colors() -> None:
    """Broadcast the side icon colors, diplomacy colors, and side relations so the radar can
    colour by SIDE or by DIPLOMACY (viewer-relative). Set via side_set_icon_color /
    sim.set_diplomacy_color / side_set_relations at mission setup; sent on change only (and
    re-sent to late joiners via _force_terrain_push resetting the snapshot)."""
    global _last_colors_sent
    s = _base_mock.sim
    if s is None or gui_queue is None:
        return
    sides = dict(getattr(s, "side_icon_colors", {}) or {})
    diplo = {str(int(k)): v for k, v in (getattr(s, "diplomacy_colors", {}) or {}).items()}
    rels = []
    # Keys are ordered (from, to) pairs -- the engine's table is directional, so send each
    # entry as authored rather than collapsing it to an unordered pair.
    for (a, b), dip in (getattr(s, "side_relations", {}) or {}).items():
        rels.append([a, b, int(dip)])
    snap = (tuple(sorted(sides.items())), tuple(sorted(diplo.items())),
            tuple(sorted((tuple(sorted((str(r[0]), str(r[1])))), r[2]) for r in rels)))
    if snap == _last_colors_sent:
        return
    _last_colors_sent = snap
    _send(0, "colors", sides=sides, diplo=diplo, relations=rels)


def physics_tick(dt: float = 1.0 / 60.0) -> None:
    """Delegate to base physics then broadcast a radar delta to the browser."""
    global sim, _radar_tick, _cinematic_tick, _comms_list_tick
    _base_mock.physics_tick(dt)
    sim = _base_mock.sim   # keep local alias in sync (create_new_sim may have changed it)
    _radar_tick += 1
    if _radar_tick >= _RADAR_INTERVAL:
        _radar_tick = 0
        _push_radar()
        _push_fx()
        _cinematic_tick += 1
        if _cinematic_tick >= _CINEMATIC_INTERVAL:
            _cinematic_tick = 0
            _push_cinematic()      # ~15 Hz; browser lerps the camera between updates
        _push_2dview_rects()
        _push_ship_data()
        _push_target_data()
        _push_text_active()
        _push_red_alert()
        # Console control widgets (helm / weapons / science).  Each is a no-op unless a
        # connected console actually declares one of its widgets, so a mission that
        # never opens those consoles pays nothing for them.
        _push_helm()
        _push_weapons()
        _push_reticle()
        _comms_list_tick += 1
        if _comms_list_tick >= _COMMS_LIST_INTERVAL:
            _comms_list_tick = 0
            _push_comms_list()
            _push_science()
            _push_colors()
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


def _is_body_kind(obj, behavior: str, tag: str) -> bool:
    """True if the object is an engine-drawn body of this kind.

    The BEHAVIOR decides: ``behav_maelstrom`` IS the black hole and ``behav_planet`` IS the
    gas giant, each with its own engine renderer. The art/data tag is only a convention a
    mission is free to change (and for these bodies it isn't even a shipData key), so it is
    kept as a fallback, not the test.
    """
    return (getattr(obj, "_tick_type", "") == behavior
            or getattr(obj, "_data_tag", "") == tag)


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
    if not _is_body_kind(obj, "behav_nebula", "nebula"):
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


def _planet_info(obj):
    """If the object is a planet, return its gas-giant surface params for the 3dview,
    else None.

    A planet runs ``behav_planet`` and there is NO "planet" key in shipData at all — the
    engine draws it with shader-gasgiant.ps, not an OBJ. So _art_root_for falls back to the
    raw tag, the browser fetches /ships/planet.obj, 404s, and the body is silently ABSENT
    from the 3D view (the "worldlets don't show in 3D" symptom). Stream the shader levers
    instead, exactly as nebulae are streamed as volume params.

    Field names are the engine planet-editor labels with a ``planet_`` prefix (see
    nebula_shader_optimization/GASGIANT_OPTIMIZATION.md). One name mismatch the engine
    handles internally: ``planet_fresnel`` is the shader's ``fresnelPow``.
    """
    if not _is_body_kind(obj, "behav_planet", "planet"):
        return None
    ds = obj.data_set

    def _f(key, default):
        v = ds.get(key)
        return float(v) if v is not None else default

    def _rgb(prefix, default):
        return [round(_f(prefix + "R", default[0]), 3),
                round(_f(prefix + "G", default[1]), 3),
                round(_f(prefix + "B", default[2]), 3)]

    # planet_radius IS the drawn size. Fall back to the exclusion radius (what a caller
    # that only set the collision size would expect) and finally to a visible default.
    radius = _f("planet_radius", 0.0)
    if radius <= 0.0:
        radius = float(getattr(obj, "exclusion_radius", 0) or 0) or 500.0
    return {
        "pradius": round(radius, 1),
        "pbase":   _rgb("planet_baseColor",       (0.55, 0.16, 0.28)),
        "pemis":   _rgb("planet_emissiveColor",   (0.06, 0.04, 0.03)),
        "pcloud":  _rgb("planet_upperCloudColor", (1.0, 1.0, 1.0)),
        "pband":   round(_f("planet_bandScale", 3.72), 3),
        "pcstr":   round(_f("planet_upperCloudStrength", 3.12), 3),
        "pcexp":   round(_f("planet_upperCloudExponent", 3.96), 3),
        "pfpow":   round(_f("planet_fresnel", 11.96), 3),      # -> shader fresnelPow
        "pfbias":  round(_f("planet_fresnelBias", 0.42), 3),
        # windSpeed1/2 drive no ANIMATION (the engine hardcodes iTime=timeScale=1), but they
        # are still added to the noise seed, so they shift the pattern. Stream them or the
        # mock's surface would not match the engine's for a planet that sets them.
        "pws1":    round(_f("planet_windSpeed1", 0.0), 3),
        "pws2":    round(_f("planet_windSpeed2", 0.0), 3),
    }


def _blackhole_info(obj):
    """If the object is a black hole (maelstrom), return its 3dview params, else None.

    Same shape of problem as the planet: a black hole is its own behavior
    (``behav_maelstrom``, spawned by terrain.py terrain_spawn_black_hole) with no shipData
    entry and no OBJ, so it 404s and vanishes from the 3D view. The browser draws the event
    horizon as a black sphere with a hot rim plus accretion rings out at the gravity radius.
    """
    if not _is_body_kind(obj, "behav_maelstrom", "maelstrom"):
        return None
    horizon = float(getattr(obj, "exclusion_radius", 0) or 0) or 100.0
    grav = obj.data_set.get("gravity_radius")
    return {
        "bhr":    round(horizon, 1),
        "bhgrav": round(float(grav) if grav is not None else horizon * 12.0, 1),
    }


def _render_payload(obj):
    """Render params for an object the 3dview draws PROCEDURALLY instead of from an OBJ
    (nebula / planet / black hole), as ``(flag_key, params)`` — or None for ordinary art.

    Kept as one helper because the terrain change-detection signature has to include these
    params, not just the position: a mission sets the knobs on the tick AFTER the spawn
    (see LM prefab_planetoid / OU worldlet_spawn), and the physics thread can push the
    terrain snapshot in between. Without the params in the signature the body would be
    streamed once with defaults and never corrected.
    """
    neb = _nebula_info(obj)
    if neb is not None:
        return ("nebula", neb)
    pl = _planet_info(obj)
    if pl is not None:
        return ("planet", pl)
    bh = _blackhole_info(obj)
    if bh is not None:
        return ("blackhole", bh)
    return None


def _quat_of(obj) -> list:
    """Object orientation as [w, x, y, z] for the 3dview (full yaw/pitch/roll).
    The mock uses the standard quaternion->basis convention (forward = +Z),
    which matches Three.js, so it can be applied directly browser-side."""
    q = obj._rot_quat
    return [round(q._w, 4), round(q._x, 4), round(q._y, 4), round(q._z, 4)]


def _mesh_scale_for(obj) -> float:
    """Resolve the engine meshscale (OBJ→world size factor) for a space object,
    so the 3dview sizes hull meshes correctly. Mirrors send_gui_3dship.

    Terrain (asteroids) also carry a per-OBJECT ``local_scale_{x,y,z}_coeff`` (set
    in terrain.py, range ~2.5-15) that the engine multiplies into the mesh size.
    shipData meshscale alone is 0.5, so without this asteroids draw 5-30x too
    small and read as invisible while ships (no local_scale) look right. Fold the
    average of the per-axis coeffs into the scalar meshscale (uniform approximation;
    per-axis stretch would need a vec3 in the instance stream)."""
    tag = getattr(obj, "_data_tag", "") or ""
    base = 1.0
    if tag:
        try:
            from sbs_utils.procedural.ship_data import get_ship_data_for
            info = get_ship_data_for(tag) or {}
            base = float(info.get("meshscale", 1.0))
        except Exception:
            base = 1.0
    try:
        ds = obj.data_set
        sx = ds.get("local_scale_x_coeff", 0) or 0.0
        sy = ds.get("local_scale_y_coeff", 0) or 0.0
        sz = ds.get("local_scale_z_coeff", 0) or 0.0
        avg = (sx + sy + sz) / 3.0
        if avg > 0.0:
            base *= avg
    except Exception:
        pass
    return base


def _mesh_scale_axes_for(obj) -> list:
    """The engine's PER-AXIS mesh scale, as `[sx, sy, sz]`.

    The scalar `_mesh_scale_for` averages the three coefficients, which was fine while
    the only thing using them was an asteroid roughened by +/-20%. It is not fine for a
    wall: a plate is a 100 x 100 x 1.25 slab stretched wide and left thin, and averaged
    into one number it draws as a small cube. The whole point of looking at a relic in
    the browser is judging whether the walls read as walls, so the stretch has to travel.
    """
    tag = getattr(obj, "_data_tag", "") or ""
    base = 1.0
    if tag:
        try:
            from sbs_utils.procedural.ship_data import get_ship_data_for
            info = get_ship_data_for(tag) or {}
            base = float(info.get("meshscale", 1.0))
        except Exception:
            base = 1.0
    try:
        ds = obj.data_set
        axes = [ds.get("local_scale_x_coeff", 0) or 0.0,
                ds.get("local_scale_y_coeff", 0) or 0.0,
                ds.get("local_scale_z_coeff", 0) or 0.0]
    except Exception:
        axes = [0.0, 0.0, 0.0]
    if not any(a > 0.0 for a in axes):
        return [base, base, base]
    # A missing axis means "same as the others", not "flat": an object with only x set
    # would otherwise collapse to a plane.
    fill = sum(a for a in axes if a > 0.0) / max(1, len([a for a in axes if a > 0.0]))
    return [base * (a if a > 0.0 else fill) for a in axes]


def _exhaust_ports_for(obj) -> list:
    """Engine-port (exhaust) local positions from shipData's ``hull_port_sets.exhaust``,
    so the 3dview vents engine smoke from the REAL ports rather than the hull center.
    Positions are in mesh-local coords (same frame as the OBJ verts); the browser
    subtracts the mesh centroid and scales by meshscale. Empty when the art defines none."""
    tag = getattr(obj, "_data_tag", "") or ""
    if not tag:
        return []
    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        info = get_ship_data_for(tag) or {}
        ex = (info.get("hull_port_sets") or {}).get("exhaust") or []
        out = []
        for e in ex:
            p = e.get("position")
            if p and len(p) == 3:
                out.append([round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2)])
        return out
    except Exception:
        return []


_COLOR_NAMES = {
    "green": (0.2, 1.0, 0.3), "red": (1.0, 0.25, 0.2), "blue": (0.35, 0.6, 1.0),
    "cyan": (0.4, 0.9, 1.0), "yellow": (1.0, 0.9, 0.3), "orange": (1.0, 0.6, 0.2),
    "white": (1.0, 1.0, 1.0), "purple": (0.7, 0.4, 1.0), "magenta": (1.0, 0.3, 0.9),
    "pink": (1.0, 0.5, 0.8),
}


def _parse_color(s, default=(0.549, 0.863, 1.0)):
    """Parse a shipData color (name like 'green' or hex like '#090'/'#00ff33') to (r,g,b) 0..1."""
    if not s:
        return default
    s = str(s).strip().lower()
    if s in _COLOR_NAMES:
        return _COLOR_NAMES[s]
    if s.startswith("#"):
        h = s[1:]
        try:
            if len(h) == 3:
                return (int(h[0], 16) / 15.0, int(h[1], 16) / 15.0, int(h[2], 16) / 15.0)
            if len(h) >= 6:
                return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)
        except Exception:
            pass
    return default


def _beam_ports_for(obj) -> list:
    """Beam-emitter local positions + color from shipData ``hull_port_sets`` (any ``beam*`` set),
    so the 3dview fires beams from the REAL emitters in the ship's beam color. Each entry is
    ``[x, y, z, r, g, b]``; mesh-local coords (browser subtracts the centroid + scales by meshscale).
    Empty when the art defines none."""
    tag = getattr(obj, "_data_tag", "") or ""
    if not tag:
        return []
    try:
        from sbs_utils.procedural.ship_data import get_ship_data_for
        info = get_ship_data_for(tag) or {}
        hps = info.get("hull_port_sets") or {}
        out = []
        for name, ports in hps.items():
            if not str(name).lower().startswith("beam"):
                continue
            for e in ports or []:
                p = e.get("position")
                if p and len(p) == 3:
                    r, g, b = _parse_color(e.get("color"))
                    ba = float(e.get("barrel_angle", 0.0) or 0.0)   # emitter facing (deg, 0=fore, +=starboard)
                    aw = float(e.get("arcwidth", 360.0) or 360.0)   # emitter arc width (deg)
                    out.append([round(float(p[0]), 2), round(float(p[1]), 2), round(float(p[2]), 2),
                                round(r, 3), round(g, 3), round(b, 3), round(ba, 1), round(aw, 1)])
        return out
    except Exception:
        return []


# Last skybox name broadcast to browsers; reset on connect so late joiners get it.
_last_skybox_sent = "\0"   # sentinel != any real name (incl. None)


def _force_terrain_push() -> None:
    """Reset delta snapshots so the next physics tick sends a full terrain + dynamic state.

    Call this when a new browser client connects so they receive complete radar state
    immediately rather than waiting for the next incremental change.
    """
    global _last_terrain_snapshot, _last_per_ship, _last_skybox_sent, _last_colors_sent
    _last_terrain_snapshot = frozenset()
    _last_per_ship = {}
    _last_skybox_sent = "\0"   # force the skybox to re-broadcast to the new client
    _last_colors_sent = None   # force the colour config to re-broadcast to the new client
    _reticle_sent.clear()      # ditto the selection reticle (also sent on change only)


def radar_resync_ids(ids) -> int:
    """Drop `ids` from every per-ship delta baseline so the next push re-sends a
    FULL record for them.

    The browser refuses to build an object out of a delta record (a delta carries
    pose only - no art/side/tick_type - so a slot built from one stays invisible
    for the object's whole life), and instead counts it as a "delta orphan" and
    asks us for a resync. That request lands here. Any lost full record - a push
    racing a mission reload, a dropped queue put - becomes self-healing rather
    than a permanently missing ship.
    """
    n = 0
    for snap in _last_per_ship.values():
        for id_ in ids:
            try:
                id_i = int(id_)
            except (TypeError, ValueError):
                continue
            if snap.pop(id_i, None) is not None:
                n += 1
    _stream_stats["resync"] += n
    return n


_last_fx_nonempty = False


def _push_fx() -> None:
    """Broadcast transient combat visuals for the 2D radar: beam-fire lines
    (this tick's firer->target pairs) and projectile dots (current in-flight
    missiles/drones). World coords are (x, z). One trailing empty push clears
    stale beams when firing stops."""
    global _last_fx_nonempty
    s = _base_mock.sim
    if s is None or gui_queue is None:
        return
    space = s.space_objects
    # Cull to what SOME client could actually render. _push_radar culls objects to
    # CULL_RADIUS per ship, but this channel is a single broadcast (clientID 0) and had no
    # distance test at all - so a browser was streamed beams and torpedoes from 47km away,
    # fired by ships that were never in its object stream. A beam like that is undrawable by
    # construction (the renderer needs the firer's meta, which the cull already withheld -
    # that was the `nometa` count), and a 120u warhead at that range is a fraction of a pixel.
    # Tested against EVERY client ship rather than per-client, so nothing one console can see
    # is dropped because another console is elsewhere.
    eyes = []
    for cid, ship_id in s.client_ships.items():
        o = space.get(s.client_alt_ships.get(cid, ship_id)) or space.get(ship_id)
        if o is not None:
            eyes.append((o._pos.x, o._pos.z))

    def _near_any_client(px: float, pz: float) -> bool:
        if not eyes:
            return True            # no assigned ships (GM / lobby) -> no basis to cull
        r2 = CULL_RADIUS * CULL_RADIUS
        for ex, ez in eyes:
            dx, dz = px - ex, pz - ez
            if dx * dx + dz * dz <= r2:
                return True
        return False

    beams = []
    for entry in getattr(_base_mock, "_beam_fires", ()):
        fid, tid = entry[0], entry[1]
        inten = entry[2] if len(entry) > 2 else 1.0   # beam "lit" intensity (fades as it expires)
        f = space.get(fid)
        t = space.get(tid)
        if f is not None and t is not None:
            # EITHER end near a client keeps it: a beam fired at you from just past the cull
            # is still drawn (its target is you), and the far end is only a line endpoint.
            if not (_near_any_client(f._pos.x, f._pos.z) or _near_any_client(t._pos.x, t._pos.z)):
                continue
            beams.append([round(f._pos.x, 1), round(f._pos.z, 1),
                          round(t._pos.x, 1), round(t._pos.z, 1), round(inten, 2), str(fid), str(tid)])
    projectiles = []
    for p in getattr(_base_mock, "_projectiles", ()):
        if p.get("kind") == "mine":
            continue   # a deployed mine is a real space object now (renders as the mine mesh), not an fx dot
        pos = p["pos"]
        if not _near_any_client(pos.x, pos.z):
            continue
        d = p.get("dir") or (0.0, 0.0, 0.0)   # travel heading -> 3dview draws an oriented missile + exhaust
        # y/dy are APPENDED (indices 5,6) so the existing [x, z, kind, dx, dz] prefix stays
        # valid for the 2D radar, which is top-down and ignores altitude. The 3D view needs
        # them: without a streamed y it drew every torpedo, mine and drone on the y=0 plane,
        # so anything launched at altitude flew visibly below or above the ships that fired it.
        projectiles.append([round(pos.x, 1), round(pos.z, 1), p.get("kind", "missile"),
                            round(d[0], 3), round(d[2], 3),
                            round(pos.y, 1), round(d[1], 3)])
    if not beams and not projectiles and not _last_fx_nonempty:
        return
    _last_fx_nonempty = bool(beams or projectiles)
    try:
        gui_queue.put_nowait({"clientID": 0, "cmd": "fx",
                              "beams": beams, "projectiles": projectiles})
    except Exception:
        pass


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
    gen = _reset_gen         # world generation this push is built against

    # This runs on the 30 Hz physics thread while the MAST/main thread spawns and
    # deletes objects under s._lock. Take ONE locked snapshot of the registries up
    # front and read only from it for the rest of the build - otherwise a delete
    # racing a `s.space_objects[id]` lookup raises KeyError and kills the radar push
    # (observed overnight: "physics worker error: <id>" / KeyError in _push_radar).
    with s._lock:
        objs = dict(s.space_objects)
        terrain_ids = set(s._terrain_ids) & objs.keys()
        active_all = set(s._active_ids) & objs.keys()
        client_ships = dict(s.client_ships)
        client_alt_ships = dict(s.client_alt_ships)
        nav_points = dict(s.nav_points)
        nav_by_id = list(s.nav_points_by_id.values())

    # --- Channel 1: terrain — rebroadcast when the terrain SET changes OR any terrain MOVES.
    # A set-only trigger missed reconcile-in-place moves: the galaxy-board unit/fleet icons
    # move to a new cell offset WITHOUT changing id, so a moved marker stayed pinned to its
    # first-drawn spot (only the marker at the overseer's own system ever showed). Key the
    # snapshot on (id, rounded x, rounded z) so a move re-streams; positions are rounded so a
    # static object reassigning the same value each tick never thrashes.
    # Selection/marker helpers (grid icon 0 = blank) are omitted so they never draw.
    visible_terrain_ids = [tid for tid in terrain_ids
                           if not _is_hidden_marker(objs[tid])
                           and not _drop_from_radar(objs[tid])]
    # Position identifies an ordinary rock; a procedurally-drawn body (nebula / planet /
    # black hole) also carries its shader params, which arrive a tick or more AFTER the
    # spawn — see _render_payload.
    current_terrain_sig = frozenset(
        (tid, round(objs[tid]._pos.x, 1), round(objs[tid]._pos.z, 1),
         repr(_render_payload(objs[tid])))
        for tid in visible_terrain_ids)
    if current_terrain_sig != _last_terrain_snapshot and gen == _reset_gen:
        _last_terrain_snapshot = current_terrain_sig
        terrain_objects = []
        for tid in visible_terrain_ids:
            obj = objs[tid]
            rec = {
                "id":   str(obj._id),
                "x":    round(obj._pos.x, 1),
                "z":    round(obj._pos.z, 1),
                "side": obj._side,
                "y":    round(obj._pos.y, 1),
                "q":    _quat_of(obj),
                # Behavior tag; the 3dview skips behav_selection (2D-only markers) so they
                # don't render as stray 3D spheres alongside real terrain meshes.
                "tick_type": obj._tick_type,
                # name_tag is the on-radar label (galaxy-board markers/icons carry one).
                "name": obj.data_set.get("name_tag") or obj.data_set.get("display_text") or "",
                # Per-object radar colour (map markers set radar_color_override instead of a
                # side); the client prefers it over the side colour. Distinct key from the
                # nebula "color" (emission) so `rec.update(neb)` below never clobbers it.
                "tint": obj.data_set.get("radar_color_override") or None,
                # Flat radar-atlas glyph (behav_selection markers: galaxy board etc.). The
                # engine draws icon_index from the game atlas, sized by icon_scale, tinted by
                # radar_color_override — NOT the ship mesh. None when unset (drawn as a dot).
                "icon_index": obj.data_set.get("icon_index"),
                "icon_scale": obj.data_set.get("icon_scale"),
                # Not hit-testable (selectable==0 asteroids/nebula, or invisible cambots).
                "nosel": _not_hittable(obj),
            }
            payload = _render_payload(obj)
            if payload is not None:
                # Procedurally drawn (nebula volume / gas-giant surface / black hole) —
                # these have no OBJ at all, so send an empty art and the shader params.
                kind, params = payload
                rec[kind]        = True
                rec["art"]       = ""
                rec["meshscale"] = 1.0
                rec.update(params)
            else:
                rec["art"]       = _art_root_for(obj)
                rec["meshscale"] = _mesh_scale_for(obj)
                rec["scale"]     = _mesh_scale_axes_for(obj)
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
    # Drop selection/marker helpers (grid icon 0 = blank) and invisible non-player objects
    # so they never draw. The behav_player cambot (invisible) is KEPT — it draws its faint
    # dot — but is streamed `nosel` (below) so the pick skips it. selectable==0 terrain also
    # stays and is `nosel`.
    active_ids = {id_ for id_ in active_all
                  if not _is_hidden_marker(objs[id_]) and not _drop_from_radar(objs[id_])}
    r2 = CULL_RADIUS * CULL_RADIUS
    # Player ships are NEVER culled — the 3dview cycles/tracks all of them, so a varying player
    # count (6 ships showing as 1 when some fall outside CULL_RADIUS) would break the 'v' key.
    player_ids = {id_ for id_ in active_ids
                  if "player" in str(getattr(objs[id_], "_tick_type", "")).lower()}

    # Build navpoints + navareas + client_focus (sent in every per-ship message).
    navpts: list = []
    for name, nav in nav_points.items():
        navpts.append({"name": name, "x": round(nav._pos.x, 1), "z": round(nav._pos.z, 1)})

    # Navareas are navpoints (a subclass) kept in the ID registry, not the name
    # dict above — pull them out by type.
    navareas: list = []
    for nav in nav_by_id:
        if not isinstance(nav, _base_mock.navarea):
            continue
        navareas.append({
            "name":   nav._text,
            "color":  nav._color,
            "points": [[round(px, 1), round(pz, 1)] for (px, pz) in nav._points],
        })

    client_focus: dict = {}
    for cid, ship_id in client_ships.items():
        # assign_client_to_alt_ship: the 2D radar focuses on the ALT ship (e.g. the
        # galaxy-theater cam) instead of the assigned one. Mirror the engine's
        # documented behavior - the mock previously stored the alt ship but never used
        # it, so the view never moved. Fall back to the assigned ship if the alt is gone.
        focus_id = client_alt_ships.get(cid, ship_id)
        obj = objs.get(focus_id)
        if obj is None:
            focus_id = ship_id
            obj = objs.get(ship_id)
        if obj is not None:
            client_focus[str(cid)] = {
                "x":       round(obj._pos.x, 1),
                "z":       round(obj._pos.z, 1),
                "ship_id": str(focus_id),
                # The viewer's own side — the radar DIPLOMACY colour mode needs it and can't
                # always find the own ship in _dynamicMeta (it isn't always a drawn dot).
                "side":    getattr(obj, "_side", None),
            }

    # Unique ships with at least one connected client, plus the GM view (ship_id=0).
    ships: dict = {}          # ship_id (int) → space_object or None
    for sid in client_ships.values():
        if sid not in ships:
            ships[sid] = objs.get(sid)
    ships[0] = None           # GM / spectator / unassigned — no distance culling

    for ship_id, ship_obj in ships.items():
        sid_str = str(ship_id)
        last    = _last_per_ship.setdefault(sid_str, {})

        # Determine the visible set for this ship.
        if ship_obj is not None:
            sx, sz  = ship_obj._pos.x, ship_obj._pos.z
            in_view: set = set()
            for id_ in active_ids:
                obj = objs[id_]
                dx  = obj._pos.x - sx
                dz  = obj._pos.z - sz
                if dx * dx + dz * dz <= r2:
                    in_view.add(id_)
            in_view |= player_ids            # players are always visible (never culled)
        else:
            in_view = set(active_ids)   # GM sees everything

        removed = [str(id_) for id_ in last if id_ not in in_view]
        changed: list = []
        new_snap: dict = {}

        for id_ in in_view:
            obj = objs[id_]
            fwd = obj.forward_vector()
            x   = round(obj._pos.x, 1)
            z   = round(obj._pos.z, 1)
            y   = round(obj._pos.y, 1)           # altitude - must be streamed too, or
            fx  = round(fwd.x, 3)                 # the 3D view renders ships at spawn Y
            fz  = round(fwd.z, 3)
            shp = _shield_frac(obj)              # total shield fraction (change detection + ring color)
            shpf, shpa = _shield_fracs(obj)      # front / aft fractions for the split shield ring
            cur = (x, z, fx, fz, shp, y)

            prev = last.get(id_)
            if prev is None:
                new_snap[id_] = cur
                _stream_stats["full"] += 1
                changed.append({
                    "id":        str(id_),
                    "x": x, "z": z, "fx": fx, "fz": fz,
                    "side":      obj._side,
                    "tick_type": obj._tick_type,
                    "name":      obj.data_set.get("name_tag") or obj.data_set.get("display_text") or "",
                    "art":       _art_root_for(obj),
                    "y":         y,
                    "meshscale": _mesh_scale_for(obj),
                    "scale":     _mesh_scale_axes_for(obj),
                    "q":         _quat_of(obj),
                    "exhaust":   _exhaust_ports_for(obj),   # engine-port local positions (static per art)
                    "beamports": _beam_ports_for(obj),      # beam-emitter local positions (static per art)
                    "shp":       shp,
                    "shpf":      shpf, "shpa": shpa,        # front/aft shield fractions (split ring)
                    "nosel":     _not_hittable(obj),
                    "new":       True,
                })
            else:
                lx, lz, lfx, lfz, lshp, ly = prev
                ddx, ddz = x - lx, z - lz
                dhdg = abs(fx - lfx) + abs(fz - lfz)
                # Re-send on enough movement/turn (incl. ALTITUDE), or a meaningful
                # shield change (so a parked ship under fire still updates its ring).
                if (ddx * ddx + ddz * ddz >= _DYNAMIC_POS_THRESHOLD_SQ
                        or (y - ly) * (y - ly) >= _DYNAMIC_POS_THRESHOLD_SQ
                        or dhdg >= _DYNAMIC_HDG_THRESHOLD
                        or abs(shp - lshp) >= 0.05):
                    changed.append({"id": str(id_), "x": x, "z": z, "y": y, "fx": fx, "fz": fz,
                                    "q": _quat_of(obj), "shp": shp, "shpf": shpf, "shpa": shpa})
                    new_snap[id_] = cur
                    _stream_stats["delta"] += 1
                else:
                    # NOT sent -- the baseline must stay at the last value the browser
                    # actually RECEIVED, not this tick's true position.  Advancing it
                    # here would compare only ONE tick of motion against the threshold,
                    # so anything slower than 5 units/tick (150 u/s -- i.e. every NPC,
                    # whose top speed is 36 u/s) never crosses it and stays frozen at
                    # its spawn point in the browser forever.  Carrying `prev` lets the
                    # drift accumulate until it is worth a packet.
                    new_snap[id_] = prev

        # A mission reload landed while this push was being built: everything above
        # describes the PREVIOUS world. Committing new_snap would re-poison the
        # freshly-cleared baseline with recycled ids (see _reset_gen), and the
        # message would arrive after world_reset as phantom objects. Drop both.
        if gen != _reset_gen:
            _stream_stats["dropped_gen"] += 1
            return
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
