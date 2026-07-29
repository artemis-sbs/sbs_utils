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
    global sim, _last_fx_nonempty, _cinematic_tick
    result = _base_mock.create_new_sim()
    sim = _base_mock.sim
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
        _view_shipdata_clients.clear()
        _view_target_clients.clear()
        _view_text_clients.clear()
        _hud_cache.clear()          # drop stale HUD diff baselines from the old mission
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

    # red_alert toggle button — position it where the layout placed the widget (screen %).
    if widgetName == "red_alert":
        if gui_queue is not None:
            _send(clientID, "red_alert_btn", active=True,
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
        return

    # comms_control action-menu panel — position it where the layout placed the widget.
    if widgetName == "comms_control":
        if gui_queue is not None:
            _send(clientID, "comms_control", op="rect",
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
        return

    # comms_face portrait — position it where the layout placed the widget.
    if widgetName == "comms_face":
        if gui_queue is not None:
            _send(clientID, "comms_face", op="rect",
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
        return

    # comms_waterfall message list — position it where the layout placed the widget.
    if widgetName == "comms_waterfall":
        if gui_queue is not None:
            _send(clientID, "comms_wf", op="rect",
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
        return

    # radar_zoom_ctrl slider — position it where the layout placed the widget.
    if widgetName == "radar_zoom_ctrl":
        if gui_queue is not None:
            _send(clientID, "radar_zoom", op="rect",
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
        return

    # comms_sorted_list — position it where the layout placed the widget.
    if widgetName == "comms_sorted_list":
        if gui_queue is not None:
            _send(clientID, "comms_list", op="rect",
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
        return

    # Mock HUD overlays (ship_data, text_waterfall) default to a screen corner;
    # when a script positions them via a rect, move them to it.
    if widgetName in _HUD_WIDGETS:
        if explicit and gui_queue is not None:
            _send(clientID, "hud_rect", widget=widgetName,
                  left=round(l1, 2), top=round(t1, 2),
                  right=round(r1, 2), bottom=round(b1, 2))
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

# HUD overlays the browser draws for mock-only widgets; given an explicit rect via
# send_client_widget_rects they reposition (else they sit in a default corner).
_HUD_WIDGETS = frozenset({"ship_data", "text_waterfall"})

# Per-client console NAME (from send_client_widget_list's consoleType == page.console).
# Used to fill event.sub_tag on a radar-click selection so consoledispatcher routes it
# to the right console selection (a name with "comm" -> comms, "sci"/"admiral" -> science).
_console_name: dict = {}


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

    # ship_data HUD — _push_ship_data streams the player ship's vitals each tick.
    if "ship_data" in widgets:
        _view_shipdata_clients.add(clientID)
    elif clientID in _view_shipdata_clients:
        _view_shipdata_clients.discard(clientID)
        _send(clientID, "ship_data", active=False)
        _hud_cache.pop((clientID, "ship_data"), None)   # re-show later sends a full payload

    # target_data HUD — only on the main-screen console ("normal_main").
    if consoleType == "normal_main":
        _view_target_clients.add(clientID)
    elif clientID in _view_target_clients:
        _view_target_clients.discard(clientID)
        _send(clientID, "target_data", active=False)
        _hud_cache.pop((clientID, "target_data"), None)

    # text_waterfall — visible while the console declares it; hidden otherwise.
    if "text_waterfall" in widgets:
        _view_text_clients.add(clientID)
    elif clientID in _view_text_clients:
        _view_text_clients.discard(clientID)
        _send(clientID, "text_active", active=False)

    # red_alert TOGGLE BUTTON — shown on consoles whose widget list declares it (comms).
    # Its screen position arrives via send_client_widget_rects (ConsoleWidget layout); its
    # on-state is streamed by _push_red_alert. (The vignette is driven separately, per ship.)
    if "red_alert" in widgets:
        _view_redalert_clients.add(clientID)
        _redalert_btn_state.pop(clientID, None)   # force a fresh state push next tick
    elif clientID in _view_redalert_clients:
        _view_redalert_clients.discard(clientID)
        _redalert_btn_state.pop(clientID, None)
        _send(clientID, "red_alert_btn", active=False)

    # comms_control — the comms action menu. Position arrives via widget rects; content
    # via the send_comms_* overrides below, keyed on the comms origin.
    if "comms_control" in widgets:
        _view_comms_control_clients.add(clientID)
    elif clientID in _view_comms_control_clients:
        _view_comms_control_clients.discard(clientID)
        _send(clientID, "comms_control", op="hide")

    # comms_face — the selected target's portrait (fed by send_comms_selection_info).
    if "comms_face" in widgets:
        _view_comms_face_clients.add(clientID)
    elif clientID in _view_comms_face_clients:
        _view_comms_face_clients.discard(clientID)
        _send(clientID, "comms_face", op="hide")

    # comms_waterfall — the comms dialogue stream (iMessage-style message list).
    if "comms_waterfall" in widgets:
        _view_comms_wf_clients.add(clientID)
    elif clientID in _view_comms_wf_clients:
        _view_comms_wf_clients.discard(clientID)
        _send(clientID, "comms_wf", op="hide")

    # radar_zoom_ctrl — the 2D-view zoom slider (browser-local).
    if "radar_zoom_ctrl" in widgets:
        _view_radar_zoom_clients.add(clientID)
    elif clientID in _view_radar_zoom_clients:
        _view_radar_zoom_clients.discard(clientID)
        _send(clientID, "radar_zoom", op="hide")

    # comms_sorted_list — the comms-target list (mock builds + streams it each second).
    if "comms_sorted_list" in widgets:
        _view_comms_list_clients.add(clientID)
    elif clientID in _view_comms_list_clients:
        _view_comms_list_clients.discard(clientID)
        _send(clientID, "comms_list", op="hide")


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
    """Stream each comms_sorted_list console a list of nearby comms-target ships (sided active
    objects, nearest first). The engine builds this widget internally; the mock approximates
    it. A row click reuses the select_space_object path (routed to comms by console name)."""
    s = _base_mock.sim
    if s is None or gui_queue is None or not _view_comms_list_clients:
        return
    with s._lock:   # snapshot under the lock (MAST thread spawns/deletes) — see _push_radar
        objs = dict(s.space_objects)
        active = list(set(s._active_ids) & objs.keys())
        client_ships = dict(s.client_ships)
    for cid in list(_view_comms_list_clients):
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
        _send(cid, "comms_list", op="list", items=[it for _, it in items[:60]])


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
        _comms_list_tick += 1
        if _comms_list_tick >= _COMMS_LIST_INTERVAL:
            _comms_list_tick = 0
            _push_comms_list()
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
    global _last_terrain_snapshot, _last_per_ship, _last_skybox_sent, _last_colors_sent
    _last_terrain_snapshot = frozenset()
    _last_per_ship = {}
    _last_skybox_sent = "\0"   # force the skybox to re-broadcast to the new client
    _last_colors_sent = None   # force the colour config to re-broadcast to the new client


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
    beams = []
    for fid, tid in getattr(_base_mock, "_beam_fires", ()):
        f = space.get(fid)
        t = space.get(tid)
        if f is not None and t is not None:
            beams.append([round(f._pos.x, 1), round(f._pos.z, 1),
                          round(t._pos.x, 1), round(t._pos.z, 1)])
    projectiles = []
    for p in getattr(_base_mock, "_projectiles", ()):
        pos = p["pos"]
        projectiles.append([round(pos.x, 1), round(pos.z, 1), p.get("kind", "missile")])
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
    current_terrain_sig = frozenset(
        (tid, round(objs[tid]._pos.x, 1), round(objs[tid]._pos.z, 1))
        for tid in visible_terrain_ids)
    if current_terrain_sig != _last_terrain_snapshot:
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
    # Drop selection/marker helpers (grid icon 0 = blank) and invisible non-player objects
    # so they never draw. The behav_player cambot (invisible) is KEPT — it draws its faint
    # dot — but is streamed `nosel` (below) so the pick skips it. selectable==0 terrain also
    # stays and is `nosel`.
    active_ids = {id_ for id_ in active_all
                  if not _is_hidden_marker(objs[id_]) and not _drop_from_radar(objs[id_])}
    r2 = CULL_RADIUS * CULL_RADIUS

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
            shp = _shield_frac(obj)              # shield fraction for the ring color
            new_snap[id_] = (x, z, fx, fz, shp, y)

            prev = last.get(id_)
            if prev is None:
                changed.append({
                    "id":        str(id_),
                    "x": x, "z": z, "fx": fx, "fz": fz,
                    "side":      obj._side,
                    "tick_type": obj._tick_type,
                    "name":      obj.data_set.get("name_tag") or obj.data_set.get("display_text") or "",
                    "art":       _art_root_for(obj),
                    "y":         y,
                    "meshscale": _mesh_scale_for(obj),
                    "q":         _quat_of(obj),
                    "shp":       shp,
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
                                    "q": _quat_of(obj), "shp": shp})

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
