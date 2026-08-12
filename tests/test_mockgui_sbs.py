from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import multiprocessing
import queue as _queue
import sys
import unittest

import cosmos_dev.mock.sbs as _base_mock
import cosmos_dev.mockgui.sbs as mockgui


class TestMockguiQueue(unittest.TestCase):
    """Outgoing queue: verify send_gui_* calls serialise correctly."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        # create_new_sim() emits a world_reset on every (re)start; discard it so each
        # test reads from a clean queue.
        mockgui.gui_queue = _queue.Queue()

    def _get(self):
        return mockgui.gui_queue.get_nowait()

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items

    # ------------------------------------------------------------------
    # send_gui_clear
    # ------------------------------------------------------------------

    def test_send_gui_clear_enqueues_cmd(self):
        mockgui.send_gui_clear(0, "root")
        msg = self._get()
        self.assertEqual(msg["cmd"], "clear")
        self.assertEqual(msg["clientID"], 0)
        self.assertEqual(msg["tag"], "root")

    # ------------------------------------------------------------------
    # send_gui_complete
    # ------------------------------------------------------------------

    def test_send_gui_complete_enqueues_cmd(self):
        mockgui.send_gui_complete(0, "")
        msg = self._get()
        self.assertEqual(msg["cmd"], "complete")
        self.assertEqual(msg["clientID"], 0)

    # ------------------------------------------------------------------
    # send_gui_button
    # ------------------------------------------------------------------

    def test_send_gui_button_preserves_all_fields(self):
        mockgui.send_gui_button(2, "parent", "mybtn", "color:red;", 10, 20, 90, 80)
        msg = self._get()
        self.assertEqual(msg["cmd"], "button")
        self.assertEqual(msg["clientID"], 2)
        self.assertEqual(msg["parent"], "parent")
        self.assertEqual(msg["tag"], "mybtn")
        self.assertEqual(msg["style"], "color:red;")
        self.assertEqual(msg["left"], 10)
        self.assertEqual(msg["top"], 20)
        self.assertEqual(msg["right"], 90)
        self.assertEqual(msg["bottom"], 80)

    # ------------------------------------------------------------------
    # send_gui_text
    # ------------------------------------------------------------------

    def test_send_gui_text_preserves_fields(self):
        mockgui.send_gui_text(1, "", "lbl", "text:Hello;", 0, 5, 50, 15)
        msg = self._get()
        self.assertEqual(msg["cmd"], "text")
        self.assertEqual(msg["clientID"], 1)
        self.assertEqual(msg["tag"], "lbl")
        self.assertEqual(msg["top"], 5)
        self.assertEqual(msg["bottom"], 15)

    # ------------------------------------------------------------------
    # send_gui_face (extra face_string parameter)
    # ------------------------------------------------------------------

    def test_send_gui_face_has_face_string(self):
        mockgui.send_gui_face(0, "", "face1", "terran 3 4", 0, 0, 20, 20)
        msg = self._get()
        self.assertEqual(msg["cmd"], "face")
        self.assertEqual(msg["face_string"], "terran 3 4")

    # ------------------------------------------------------------------
    # send_gui_slider (extra current parameter)
    # ------------------------------------------------------------------

    def test_send_gui_slider_has_current_value(self):
        mockgui.send_gui_slider(0, "", "sl1", 0.75, "low:0;high:1;", 0, 0, 100, 10)
        msg = self._get()
        self.assertEqual(msg["cmd"], "slider")
        self.assertEqual(msg["current"], 0.75)
        self.assertEqual(msg["style"], "low:0;high:1;")

    # ------------------------------------------------------------------
    # FIFO ordering
    # ------------------------------------------------------------------

    def test_multiple_sends_arrive_in_fifo_order(self):
        mockgui.send_gui_clear(0, "")
        mockgui.send_gui_button(0, "", "btn", "", 0, 0, 10, 10)
        mockgui.send_gui_complete(0, "")
        items = self._drain()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0]["cmd"], "clear")
        self.assertEqual(items[1]["cmd"], "button")
        self.assertEqual(items[2]["cmd"], "complete")

    # ------------------------------------------------------------------
    # client_id scoping
    # ------------------------------------------------------------------

    def test_client_id_preserved_for_different_clients(self):
        mockgui.send_gui_button(7, "", "x", "", 0, 0, 10, 10)
        msg = self._get()
        self.assertEqual(msg["clientID"], 7)

    # ------------------------------------------------------------------
    # Widget variants — spot-check cmd name for each override
    # ------------------------------------------------------------------

    def _widget_cmd(self, fn_name, cmd):
        fn = getattr(mockgui, fn_name)
        fn(0, "", "t", "s", 0, 0, 10, 10)
        return self._get()["cmd"]

    def test_send_gui_checkbox_cmd(self):
        self.assertEqual(self._widget_cmd("send_gui_checkbox", "checkbox"), "checkbox")

    def test_send_gui_dropdown_cmd(self):
        self.assertEqual(self._widget_cmd("send_gui_dropdown", "dropdown"), "dropdown")

    def test_send_gui_icon_cmd(self):
        self.assertEqual(self._widget_cmd("send_gui_icon", "icon"), "icon")

    def test_send_gui_image_cmd(self):
        self.assertEqual(self._widget_cmd("send_gui_image", "image"), "image")

    def test_send_gui_typein_cmd(self):
        self.assertEqual(self._widget_cmd("send_gui_typein", "typein"), "typein")

    def test_send_gui_sub_region_cmd(self):
        self.assertEqual(self._widget_cmd("send_gui_sub_region", "sub_region"), "sub_region")


class TestMockguiSimSharing(unittest.TestCase):
    """Simulation state is shared between the base mock and the GUI layer."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        # create_new_sim() emits a world_reset on every (re)start; discard it so each
        # test reads from a clean queue.
        mockgui.gui_queue = _queue.Queue()

    def test_create_new_sim_sets_mockgui_sim(self):
        self.assertIsNotNone(mockgui.sim)

    def test_mockgui_sim_is_same_object_as_base_mock_sim(self):
        self.assertIs(mockgui.sim, _base_mock.sim)

    def test_space_object_created_via_mockgui_visible_in_base_mock(self):
        obj_id = mockgui.sim.create_space_object("ACTIVE", "test", 0)
        self.assertIn(obj_id, _base_mock.sim.space_objects)

    def test_space_object_created_via_base_mock_visible_in_mockgui(self):
        _base_mock.create_new_sim()
        mockgui.sim = _base_mock.sim   # re-sync manually (simulates create_new_sim call path)
        obj_id = _base_mock.sim.create_space_object("PASSIVE", "rock", 0)
        self.assertIn(obj_id, mockgui.sim.space_objects)

    def test_sbs_module_alias_routes_send_gui_to_queue(self):
        # After importing mockgui, sys.modules["sbs"] should use the
        # GUI-capable overrides — i.e. send_gui_clear puts something on the queue.
        sbs_alias = sys.modules["sbs"]
        sbs_alias.send_gui_clear(0, "")
        msg = mockgui.gui_queue.get_nowait()
        self.assertEqual(msg["cmd"], "clear")


class TestMockguiViews(unittest.TestCase):
    """View activation driven by the console widget list: 2D radar rect, 3D view
    activation, default rects, and explicit script-set sizes."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        # create_new_sim() emits a world_reset on every (re)start; discard it so each
        # test reads from a clean queue.
        mockgui.gui_queue = _queue.Queue()
        # Module-global view state persists between calls — reset for isolation.
        mockgui._view2d_widget_clients.clear()
        mockgui._view3d_widget_clients.clear()
        mockgui._explicit_2d_rects.clear()
        mockgui._view3d_rects.clear()
        _base_mock._view_modes.clear()
        _base_mock._cinematic.clear()

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items

    def _cmds(self, cmd):
        return [m for m in self._drain() if m["cmd"] == cmd]

    def _assign_player(self, cid=5):
        sid = mockgui.sim.create_space_object("behav_playership", "test", 0x20)
        mockgui.sim.space_objects[sid]._pos = mockgui.vec3(0, 0, 0)
        mockgui.sim.client_ships[cid] = sid
        return sid

    # -- 2D radar rect ------------------------------------------------------

    def test_2dview_widget_streams_default_rect(self):
        mockgui.send_client_widget_list(5, "helm", "2dview^throttle")
        self._drain()
        mockgui.physics_tick(dt=0.5)
        rects = [m for m in self._cmds("widget_rect") if m["widget"] == "2dview"]
        self.assertTrue(rects)
        r = rects[-1]
        # degenerate rect → browser applies its own full-panel default
        self.assertEqual((r["left"], r["top"], r["right"], r["bottom"]), (0, 0, 0, 0))

    def test_no_2d_view_widget_streams_no_rect(self):
        mockgui.send_client_widget_list(5, "eng", "ship_internal_view^grid_control")
        self._drain()
        mockgui.physics_tick(dt=0.5)
        self.assertEqual(self._cmds("widget_rect"), [])

    def test_explicit_2dview_rect_suppresses_default(self):
        mockgui.send_client_widget_list(5, "custom", "2dview^ship_data")
        mockgui.send_client_widget_rects(5, "2dview", 10, 20, 90, 80, 10, 20, 90, 80)
        self._drain()
        mockgui.physics_tick(dt=0.5)
        # the script sized the view, so the per-tick default backs off
        rects = [m for m in self._cmds("widget_rect") if m["widget"] == "2dview"]
        self.assertEqual(rects, [])

    # -- 3D view activation -------------------------------------------------

    def test_3dview_widget_activates_with_topbar_inset(self):
        self._assign_player(5)
        mockgui.send_client_widget_list(5, "main", "3dview^ship_data")
        self._drain()
        mockgui.physics_tick(dt=0.5)
        cins = self._cmds("cinematic")
        self.assertTrue(cins)
        self.assertTrue(cins[-1]["active"])
        self.assertEqual(cins[-1]["rect"], [0.0, 3.0, 100.0, 100.0])

    def test_switching_off_3dview_deactivates(self):
        self._assign_player(5)
        mockgui.send_client_widget_list(5, "main", "3dview")
        self._drain()
        mockgui.send_client_widget_list(5, "helm", "2dview^throttle")
        cins = self._cmds("cinematic")
        self.assertTrue(any(c.get("active") is False for c in cins))

    def test_cinematic_view_is_full_bleed(self):
        self._assign_player(5)
        mockgui.set_main_view_modes(5, "3dview", "front", "cinematic")
        mockgui.cinematic_control(5, 0, 0, None, 0, None)   # auto chase-cam
        self._drain()
        mockgui.physics_tick(dt=0.5)
        cins = self._cmds("cinematic")
        self.assertTrue(cins)
        self.assertTrue(cins[-1]["active"])
        self.assertEqual(cins[-1]["rect"], [0.0, 0.0, 100.0, 100.0])

    def test_explicit_3dview_rect_is_honored(self):
        self._assign_player(5)
        mockgui.send_client_widget_list(5, "custom", "3dview^ship_data")
        mockgui.send_client_widget_rects(5, "3dview", 5, 10, 70, 90, 5, 10, 70, 90)
        self._drain()
        mockgui.physics_tick(dt=0.5)
        cins = self._cmds("cinematic")
        self.assertTrue(cins)
        self.assertEqual(cins[-1]["rect"], [5, 10, 70, 90])

    # -- navareas in the radar push ----------------------------------------

    def test_navareas_streamed_in_radar_push(self):
        mockgui.sim.add_navarea(0, 0, 100, 0, 0, 100, 100, 100, "Zone", "#f80")
        mockgui.physics_tick(dt=0.5)
        radars = self._cmds("radar")
        self.assertTrue(radars)
        areas = next((r["navareas"] for r in radars if r.get("navareas")), [])
        self.assertTrue(areas)
        self.assertEqual(areas[0]["name"], "Zone")


class TestCinematicDirectorPacing(unittest.TestCase):
    """The auto cinematic camera holds a shot (min dwell) instead of flickering to
    whichever object is hottest each tick; a much hotter event (a kill) cuts early."""

    def setUp(self):
        _base_mock.create_new_sim()
        _base_mock._cam_focus.clear()
        self.a = _base_mock.sim.create_space_object("behav_npcship", "", 0x10)
        self.b = _base_mock.sim.create_space_object("behav_npcship", "", 0x10)
        self.cid = 5

    def _excite(self, oid, v):
        _base_mock.sim.space_objects[oid].data_set.set("exciting", float(v))

    def test_holds_through_minor_flicker(self):
        self._excite(self.a, 200); self._excite(self.b, 200)
        first = _base_mock._director_focus(self.cid)
        self.assertIn(first, (self.a, self.b))
        # the other ship edges slightly higher within the dwell window
        other = self.b if first == self.a else self.a
        self._excite(other, 210)
        self.assertEqual(_base_mock._director_focus(self.cid), first)

    def test_hotter_event_steals_early(self):
        self._excite(self.a, 200); self._excite(self.b, 200)
        first = _base_mock._director_focus(self.cid)
        other = self.b if first == self.a else self.a
        self._excite(other, _base_mock._EXCITE_KILL)   # a kill outranks a firefight
        self.assertEqual(_base_mock._director_focus(self.cid), other)

    def test_cold_returns_zero(self):
        self._excite(self.a, 200)
        _base_mock._director_focus(self.cid)
        self._excite(self.a, 0)
        self.assertEqual(_base_mock._director_focus(self.cid), 0)

    def test_lateral_cut_after_dwell(self):
        self._excite(self.a, 200); self._excite(self.b, 200)
        first = _base_mock._director_focus(self.cid)
        other = self.b if first == self.a else self.a
        _base_mock._cam_focus[self.cid]["since"] -= _base_mock._CAM_MIN_DWELL + 1
        self._excite(other, 220)
        self.assertEqual(_base_mock._director_focus(self.cid), other)


class TestMockguiRadarHiddenBehaviors(unittest.TestCase):
    """behav_selection markers are grid icon 0 (blank) - the radar stream must omit
    them so they never draw on the 2D view (or place a mesh in the 3D view)."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        # Radar delta state persists between pushes - reset for isolation.
        mockgui._last_terrain_snapshot = frozenset()
        mockgui._last_per_ship.clear()

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items

    def _ids_in(self, cmd_name):
        ids = set()
        for m in self._drain():
            if m.get("cmd") == cmd_name:
                for o in m.get("objects", []):
                    ids.add(o["id"])
                for o in m.get("changed", []):
                    ids.add(o["id"])
        return ids

    def test_selection_marker_excluded_from_terrain_radar(self):
        rock = mockgui.sim.create_space_object("behav_asteroid", "", 0x00)
        mockgui.sim.space_objects[rock]._pos = mockgui.vec3(100, 0, 100)
        marker = mockgui.sim.create_space_object("behav_selection", "", 0x00)
        mockgui.sim.space_objects[marker]._pos = mockgui.vec3(200, 0, 200)

        mockgui._push_radar()
        terrain_ids = self._ids_in("radar_terrain")
        self.assertIn(str(rock), terrain_ids)        # normal terrain still shown
        self.assertNotIn(str(marker), terrain_ids)   # selection marker omitted

    def test_active_selection_marker_excluded_from_radar_delta(self):
        # GM view (ship_id 0) sees all active objects with no culling.
        ship = mockgui.sim.create_space_object("behav_npcship", "", 0x10)
        mockgui.sim.space_objects[ship]._pos = mockgui.vec3(0, 0, 0)
        marker = mockgui.sim.create_space_object("behav_selection", "", 0x10)
        mockgui.sim.space_objects[marker]._pos = mockgui.vec3(50, 0, 50)

        mockgui._push_radar()
        radar_ids = self._ids_in("radar")
        self.assertIn(str(ship), radar_ids)
        self.assertNotIn(str(marker), radar_ids)

    def test_selection_marker_WITH_art_is_shown(self):
        # behav_selection is ALSO the production behaviour for VISIBLE map markers (nebula
        # markers, the galaxy-theater board). One WITH an art (data tag) is a real marker,
        # not a blank helper - it must draw. name_tag + radar_color_override ride along.
        marker = mockgui.sim.create_space_object("behav_selection", "generic-sphere", 0x00)
        mo = mockgui.sim.space_objects[marker]
        mo._pos = mockgui.vec3(400, 0, 400)
        mo.data_set.set("name_tag", "System 2,1", 0)
        mo.data_set.set("radar_color_override", "#ff4444", 0)

        mockgui._push_radar()
        rec = None
        for m in self._drain():
            if m.get("cmd") == "radar_terrain":
                for o in m.get("objects", []):
                    if o["id"] == str(marker):
                        rec = o
        self.assertIsNotNone(rec, "art-bearing behav_selection marker must be streamed")
        self.assertEqual(rec.get("name"), "System 2,1")   # name_tag rides the terrain rec
        self.assertEqual(rec.get("tint"), "#ff4444")       # radar_color_override rides too

    def test_terrain_restreams_when_a_marker_moves(self):
        # Reconcile-in-place moves a marker without changing its id; the terrain channel
        # must re-stream on the position change (not only on an id-set change), or a moved
        # galaxy-board icon stays pinned to its first-drawn spot.
        marker = mockgui.sim.create_space_object("behav_selection", "generic-sphere", 0x00)
        mo = mockgui.sim.space_objects[marker]
        mo._pos = mockgui.vec3(400, 0, 400)
        mockgui._push_radar()
        self.assertIn(str(marker), self._ids_in("radar_terrain"))   # initial stream
        # No move -> no re-stream (id-set + positions unchanged).
        mockgui._push_radar()
        self.assertNotIn(str(marker), self._ids_in("radar_terrain"))
        # Move it -> must re-stream at the new position.
        mo._pos = mockgui.vec3(9000, 0, 9000)
        mockgui._push_radar()
        moved = None
        for m in self._drain():
            if m.get("cmd") == "radar_terrain":
                for o in m.get("objects", []):
                    if o["id"] == str(marker):
                        moved = o
        self.assertIsNotNone(moved, "a moved marker must be re-streamed")
        self.assertEqual(moved["x"], 9000)


class TestMockguiRadarThreadSafety(unittest.TestCase):
    """_push_radar runs on the 30 Hz physics thread while the MAST/main thread spawns
    and deletes objects. It must never raise KeyError when an object is deleted mid-
    build (the overnight soak crashed here: "physics worker error: <id>" / KeyError in
    _push_radar). Regression: hammer the radar push against concurrent churn."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        mockgui._last_terrain_snapshot = frozenset()
        mockgui._last_per_ship.clear()

    def test_push_radar_survives_concurrent_delete(self):
        import threading
        sim = mockgui.sim
        # Seed a viewer ship so Channel 2 actually walks the active set.
        viewer = sim.create_space_object("behav_playership", "test", 0x20)
        sim.space_objects[viewer]._pos = mockgui.vec3(0, 0, 0)
        sim.client_ships[5] = viewer

        errors = []
        stop = threading.Event()

        def churn():
            while not stop.is_set():
                ids = []
                for _ in range(40):
                    a = sim.create_space_object("behav_npcship", "", 0x10)
                    sim.space_objects[a]._pos = mockgui.vec3(10, 0, 10)
                    t = sim.create_space_object("behav_asteroid", "", 0x00)
                    sim.space_objects[t]._pos = mockgui.vec3(20, 0, 20)
                    ids += [a, t]
                for i in ids:
                    mockgui.delete_object(i)

        def push():
            while not stop.is_set():
                try:
                    mockgui._push_radar()
                except Exception as e:        # the bug surfaced as KeyError here
                    errors.append(e)
                    return

        churner = threading.Thread(target=churn)
        pusher = threading.Thread(target=push)
        churner.start(); pusher.start()
        import time as _t
        _t.sleep(0.6)
        stop.set()
        churner.join(timeout=5); pusher.join(timeout=5)

        self.assertEqual(errors, [], f"_push_radar raised under concurrent churn: {errors}")


class TestMockguiRadarDeltaBaseline(unittest.TestCase):
    """The delta radar suppresses a re-send until an object has moved
    _DYNAMIC_POS_THRESHOLD_SQ. The baseline it compares against must be the last
    value the browser RECEIVED, not the current one - otherwise only a single
    tick of motion is ever tested, and anything slower than 5 units/tick (150
    u/s: every NPC, whose top speed is 36 u/s) is never re-sent and stays frozen
    at its spawn point in the browser."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        mockgui._last_terrain_snapshot = frozenset()
        mockgui._last_per_ship.clear()

    def _updates_for(self, obj_id):
        """Position updates (excluding the initial 'new' record) drained so far."""
        n = 0
        while not mockgui.gui_queue.empty():
            m = mockgui.gui_queue.get_nowait()
            if m.get("cmd") != "radar":
                continue
            for o in m.get("changed", []):
                if o["id"] == str(obj_id) and not o.get("new"):
                    n += 1
        return n

    def test_slow_drift_accumulates_into_a_resend(self):
        sim = mockgui.sim
        npc = sim.create_space_object("behav_npcship", "", 0x10)
        o = sim.space_objects[npc]
        o._pos = mockgui.vec3(0, 0, 0)

        mockgui._push_radar()          # initial 'new' record
        self._updates_for(npc)

        # Creep 1 unit per tick - under the 5-unit threshold every single tick.
        for i in range(1, 21):
            o._pos = mockgui.vec3(float(i), 0, 0)
            mockgui._push_radar()

        sent = self._updates_for(npc)
        self.assertGreater(sent, 0,
                           "a slowly cruising NPC must eventually re-send its position")
        # ~20 units of travel at a 5-unit threshold - a handful of packets, not one per tick.
        self.assertLessEqual(sent, 8, "delta suppression must still throttle the stream")

    def test_stationary_object_sends_nothing(self):
        sim = mockgui.sim
        rock = sim.create_space_object("behav_npcship", "", 0x10)
        sim.space_objects[rock]._pos = mockgui.vec3(500, 0, 500)

        mockgui._push_radar()
        self._updates_for(rock)
        for _ in range(20):
            mockgui._push_radar()
        self.assertEqual(self._updates_for(rock), 0,
                         "a parked object must not re-send every tick")


class TestMockguiFullRecordAfterReset(unittest.TestCase):
    """A browser that has been told to wipe must be re-sent FULL records, never deltas.

    art / beamports / meshscale / side / tick_type ride the `new` record ONLY. If a
    browser first hears about an object through a delta it has no identity for it, and
    (before the client-side guard) invented art:'' + beamports:null -- an object invisible
    in the 3D view and beamless for the rest of its life. The same hazard exists on the
    browser-CONNECT path, where a late client receives broadcast deltas until the runner
    processes its connect event and calls _force_terrain_push().
    """

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        mockgui._last_terrain_snapshot = frozenset()
        mockgui._last_per_ship.clear()

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items

    def test_every_object_gets_a_full_record_after_a_reset(self):
        sim = mockgui.sim
        ship = sim.create_space_object("behav_npcship", "", 0x10)
        sim.space_objects[ship]._pos = mockgui.vec3(100, 0, 100)
        mockgui._push_radar()          # object is now in the server's snapshot
        self._drain()

        mockgui.create_new_sim()       # restart: browser is told to wipe
        sim = mockgui.sim
        again = sim.create_space_object("behav_npcship", "", 0x10)
        sim.space_objects[again]._pos = mockgui.vec3(200, 0, 200)
        mockgui._push_radar()

        saw_reset = False
        full, delta = set(), set()
        for m in self._drain():
            if m.get("cmd") == "world_reset":
                saw_reset = True
                continue
            if m.get("cmd") != "radar":
                continue
            for o in m.get("changed", []):
                (full if o.get("new") else delta).add(o["id"])
        self.assertTrue(saw_reset, "a reset must tell browsers to wipe")
        self.assertIn(str(again), full,
                      "after a reset every object must re-send a FULL record, not a delta")
        self.assertNotIn(str(again), delta - full,
                         "an object the browser just wiped must never arrive as a delta only")


class TestMockguiFxCulling(unittest.TestCase):
    """_push_fx is a single broadcast and had no distance test, while _push_radar culls
    objects to CULL_RADIUS per ship. So a browser was streamed beams and torpedoes from
    tens of km away, fired by ships it had never been sent - the beams were undrawable by
    construction (no meta for the firer) and the projectiles were sub-pixel."""

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        mockgui._last_per_ship.clear()
        self.sim = mockgui.sim
        self.me = self.sim.create_space_object("behav_playership", "tsn_battle_cruiser", 0x20)
        self.sim.space_objects[self.me]._pos = mockgui.vec3(0, 0, 0)
        self.sim.client_ships[1] = self.me

    def _fx(self):
        mockgui._push_fx()
        out = {"beams": [], "projectiles": []}
        while not mockgui.gui_queue.empty():
            m = mockgui.gui_queue.get_nowait()
            if m.get("cmd") == "fx":
                out = m
        return out

    def _npc(self, z):
        oid = self.sim.create_space_object("behav_npcship", "torgoth_destroyer", 0x10)
        self.sim.space_objects[oid]._pos = mockgui.vec3(0, 0, float(z))
        return oid

    def test_distant_projectiles_are_not_streamed(self):
        near, far = self._npc(5000), self._npc(47000)
        _base_mock._projectiles.clear()
        _base_mock.launch_missile(near, self.me, "Homing")
        _base_mock.launch_missile(far, far, "Homing")
        self.assertEqual(len(_base_mock._projectiles), 2)
        self.assertEqual(len(self._fx().get("projectiles") or []), 1,
                         "only the projectile near a client ship should be streamed")

    def test_beam_fired_at_you_from_beyond_the_cull_is_kept(self):
        """Either endpoint near a client keeps the record - a beam shot AT you from just
        past the cull is still drawn, since its target end is right on top of you."""
        shooter = self._npc(int(mockgui.CULL_RADIUS) + 5000)
        _base_mock._beam_fires.clear()
        _base_mock._beam_fires.append((shooter, self.me, 1.0))
        self.assertEqual(len(self._fx().get("beams") or []), 1)

    def test_beam_between_two_distant_ships_is_dropped(self):
        a = self._npc(int(mockgui.CULL_RADIUS) + 5000)
        b = self._npc(int(mockgui.CULL_RADIUS) + 6000)
        _base_mock._beam_fires.clear()
        _base_mock._beam_fires.append((a, b, 1.0))
        self.assertEqual(len(self._fx().get("beams") or []), 0,
                         "a beam neither end of which is near a client cannot be drawn")

class TestEngineConsoleWidgets(unittest.TestCase):
    """The Family-B console widgets (gui_console's engine widget list): registration,
    default placement, the state streams, and the browser controls that drive them.

    These cover the "the mock is unplayable" gap - helm/weapons/science declared widgets
    the browser silently dropped, and nothing in the browser could write playerThrottle.
    """

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        for w in mockgui._ENGINE_WIDGETS.values():
            w.clients.clear()
        mockgui._view2d_widget_clients.clear()
        mockgui._view3d_widget_clients.clear()
        mockgui._explicit_2d_rects.clear()
        mockgui._hud_cache.clear()
        mockgui._unknown_widgets_seen.clear()

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items

    def _cmds(self, cmd):
        return [m for m in self._drain() if m["cmd"] == cmd]

    def _assign_player(self, cid=5):
        sid = mockgui.sim.create_space_object("behav_playership", "test", 0x20)
        mockgui.sim.space_objects[sid]._pos = mockgui.vec3(0, 0, 0)
        mockgui.sim.client_ships[cid] = sid
        return sid

    # -- registration + placement ------------------------------------------

    def test_helm_widgets_are_registered(self):
        """Every widget gui_console("helm") declares has a descriptor - the whole point
        of the change is that none of them is silently dropped any more."""
        for name in ("throttle", "helm_movement", "shield_control", "request_dock",
                     "main_screen_control", "helm_jump", "quick_jump"):
            self.assertIn(name, mockgui._ENGINE_WIDGETS, name)

    def test_helm_console_streams_default_rects(self):
        """Helm is laid out by the engine in C++ and never calls gui_layout_widget, so
        the mock has to supply the placement or the console is blank."""
        mockgui.send_client_widget_list(5, "normal_helm", "2dview^throttle^helm_movement")
        thr = [m for m in self._drain()
               if m["cmd"] == "throttle" and m.get("op") == "defrect"]
        self.assertTrue(thr, "throttle got no default rect")
        self.assertEqual(thr[-1]["anchor"], "bl")
        self.assertGreater(thr[-1]["h"], 0)

    def test_science_console_gets_no_default_rect(self):
        """Science lays itself out in MAST (layout_widgets.mast //gui/normal_sci), so a
        built-in default would fight the mission's own rect."""
        mockgui.send_client_widget_list(5, "normal_sci", "science_2d_view^science_data")
        self.assertEqual([m for m in self._drain() if m.get("op") == "defrect"], [])

    def test_script_rect_is_forwarded(self):
        mockgui.send_client_widget_list(5, "normal_sci", "science_data")
        self._drain()
        mockgui.send_client_widget_rects(5, "science_data", 10, 20, 90, 80,
                                         10, 20, 90, 80)
        rect = [m for m in self._cmds("sci_data") if m.get("op") == "rect"]
        self.assertTrue(rect)
        self.assertEqual((rect[-1]["left"], rect[-1]["bottom"]), (10, 80))

    def test_dropping_a_widget_hides_it(self):
        mockgui.send_client_widget_list(5, "normal_helm", "throttle")
        self._drain()
        mockgui.send_client_widget_list(5, "normal_comm", "comms_control")
        self.assertTrue([m for m in self._cmds("throttle") if m.get("op") == "hide"])

    def test_empty_widget_list_clears_then_restores(self):
        """A console with no engine widgets (a GUI tab) sends an EMPTY list; that has to
        hide them, and coming back has to bring them back with their state.

        The restore is the subtle half: _push_delta sends only CHANGED fields, so without
        invalidating the cache on declare/drop the payload looks unchanged, nothing is
        sent, and the browser keeps whatever it had when it was hidden."""
        sid = self._assign_player()
        mockgui.sim.space_objects[sid].data_set.set("playerThrottle", 0.5, 0)
        helm = "2dview^throttle^shield_control"
        mockgui.send_client_widget_list(5, "normal_helm", helm)
        mockgui.physics_tick(dt=0.5)
        self._drain()

        mockgui.send_client_widget_list(5, "quest", "")
        hides = [m for m in self._cmds("throttle") if m.get("op") == "hide"]
        self.assertTrue(hides, "an empty widget list must hide the widgets")
        self.assertNotIn(5, mockgui._ENGINE_WIDGETS["throttle"].clients)

        mockgui.send_client_widget_list(5, "normal_helm", helm)
        mockgui.physics_tick(dt=0.5)
        back = self._cmds("throttle")
        self.assertTrue([m for m in back if m.get("op") == "defrect"], "no placement on return")
        state = [m for m in back if "throttle" in m]
        self.assertTrue(state, "returning console got no state re-sent")
        self.assertIn("warp_ok", state[-1], "state came back as a partial delta, not in full")

    def test_unemulated_widget_is_reported_once(self):
        """An unimplemented widget used to be indistinguishable from a broken one."""
        mockgui.send_client_widget_list(5, "normal_engi", "eng_power_controls")
        self.assertIn("eng_power_controls", mockgui._unknown_widgets_seen)

    # -- state streams ------------------------------------------------------

    def test_throttle_state_is_streamed(self):
        sid = self._assign_player()
        mockgui.sim.space_objects[sid].data_set.set("playerThrottle", 0.5, 0)
        mockgui.send_client_widget_list(5, "normal_helm", "throttle")
        self._drain()
        mockgui.physics_tick(dt=0.5)
        thr = [m for m in self._cmds("throttle") if "throttle" in m]
        self.assertTrue(thr)
        self.assertAlmostEqual(thr[-1]["throttle"], 0.5)

    def test_science_data_reports_per_tab_scan_state(self):
        """Scan state is per (target, TAB, side), not one flag per target: science stores
        each tab's text on the target keyed by the scanning ship's side."""
        sid = self._assign_player()
        tid = mockgui.sim.create_space_object("behav_npcship", "target", 0)
        mockgui.sim.space_objects[tid]._pos = mockgui.vec3(1000, 0, 0)
        mockgui.sim.space_objects[sid].data_set.set("science_target_UID", tid, 0)
        mockgui.send_client_widget_list(5, "normal_sci", "science_data")
        self._drain()
        for _ in range(mockgui._COMMS_LIST_INTERVAL + 1):
            mockgui.physics_tick(dt=0.1)
        data = [m for m in self._cmds("sci_data") if "tab_state" in m]
        self.assertTrue(data)
        self.assertEqual(data[-1]["range"], 1000)
        self.assertFalse(data[-1]["tab_state"]["scan"]["scanned"])
        self.assertEqual(data[-1]["tab_state"]["scan"]["queued"], 0)


class TestMockScienceScanQueue(unittest.TestCase):
    """The science scan QUEUE the mock gained so the science console can finish a scan.

    cur_scan_percent existed in the data_set schema but nothing ever advanced it and
    science_scan_complete was never fired, so "Start Scan" could not work at all. The
    queue is owned by the scanning SHIP; entries are (target, tab); only the head
    advances, and completing one starts the next.
    """

    def setUp(self):
        mockgui.create_new_sim()
        self.ship = mockgui.sim.create_space_object("behav_playership", "test", 0x20)
        self.a = mockgui.sim.create_space_object("behav_npcship", "a", 0)
        self.b = mockgui.sim.create_space_object("behav_npcship", "b", 0)
        mockgui.sim.space_objects[self.ship]._pos = mockgui.vec3(0, 0, 0)
        mockgui.sim.space_objects[self.a]._pos = mockgui.vec3(500, 0, 0)
        mockgui.sim.space_objects[self.b]._pos = mockgui.vec3(600, 0, 0)
        while not _base_mock._pending_physics_events.empty():
            _base_mock._pending_physics_events.get_nowait()

    def _events(self):
        out = []
        while not _base_mock._pending_physics_events.empty():
            out.append(_base_mock._pending_physics_events.get_nowait())
        return out

    def _run(self, seconds=12):
        for _ in range(seconds):
            _base_mock._physics_science_scans(mockgui.sim, 1.0)

    def test_queue_is_fifo_and_only_the_head_advances(self):
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        _base_mock.start_science_scan(self.ship, self.b, "scan")
        q = _base_mock.science_scan_queue(self.ship)
        self.assertEqual([e["target"] for e in q], [self.a, self.b])
        _base_mock._physics_science_scans(mockgui.sim, 1.0)
        q = _base_mock.science_scan_queue(self.ship)
        self.assertGreater(q[0]["pct"], 0, "the head should be scanning")
        self.assertEqual(q[1]["pct"], 0, "a waiting entry must not advance")

    def test_active_scan_is_published_to_the_ship(self):
        """The engine publishes the active scan in the SHIP's data_set; scripts poll it."""
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        ds = mockgui.sim.space_objects[self.ship].data_set
        self.assertEqual(ds.get("cur_scan_ID", 0), self.a)
        self.assertEqual(ds.get("cur_scan_type", 0), "scan")

    def test_completing_one_entry_starts_the_next(self):
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        _base_mock.start_science_scan(self.ship, self.b, "scan")
        self._run(6)          # long enough for the HEAD only (a scan takes ~5s in range)
        done = [e for e in self._events() if e[0] == "science_scan_complete"]
        self.assertTrue(done, "the head never completed")
        self.assertEqual(done[0][3], self.a)
        self.assertEqual(done[0][-1]["extra_tag"], "scan")
        q = _base_mock.science_scan_queue(self.ship)
        self.assertTrue(q and q[0]["target"] == self.b, "the next entry did not start")
        self.assertEqual(mockgui.sim.space_objects[self.ship].data_set.get("cur_scan_ID", 0),
                         self.b)

    def test_each_tab_is_its_own_entry(self):
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        _base_mock.start_science_scan(self.ship, self.a, "intel")
        self.assertEqual(len(_base_mock.science_scan_queue(self.ship)), 2)

    def test_queueing_the_same_tab_twice_is_a_no_op(self):
        self.assertTrue(_base_mock.start_science_scan(self.ship, self.a, "scan"))
        self.assertFalse(_base_mock.start_science_scan(self.ship, self.a, "scan"))
        self.assertEqual(len(_base_mock.science_scan_queue(self.ship)), 1)

    def test_stop_removes_an_entry_and_promotes_the_next(self):
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        _base_mock.start_science_scan(self.ship, self.b, "scan")
        self.assertTrue(_base_mock.stop_science_scan(self.ship, self.a, "scan"))
        q = _base_mock.science_scan_queue(self.ship)
        self.assertEqual([e["target"] for e in q], [self.b])
        self.assertEqual(mockgui.sim.space_objects[self.ship].data_set.get("cur_scan_ID", 0),
                         self.b)
        self.assertEqual(self._events(), [], "a cancelled scan must not complete")

    def test_stopping_the_last_entry_clears_the_active_scan(self):
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        _base_mock.stop_science_scan(self.ship, self.a, "scan")
        self.assertEqual(mockgui.sim.space_objects[self.ship].data_set.get("cur_scan_ID", 0), 0)

    def test_entries_for_a_dead_target_are_dropped(self):
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        _base_mock.start_science_scan(self.ship, self.b, "scan")
        del mockgui.sim.space_objects[self.a]
        _base_mock._physics_science_scans(mockgui.sim, 1.0)
        q = _base_mock.science_scan_queue(self.ship)
        self.assertEqual([e["target"] for e in q], [self.b])
        self.assertEqual(self._events(), [])

    def test_world_reset_clears_the_queue(self):
        """A queued scan belongs to the mission that started it - carrying one into the
        next run is exactly the reused-interpreter bug the reset ledger exists for."""
        _base_mock.start_science_scan(self.ship, self.a, "scan")
        self.assertTrue(_base_mock._science_scans)
        mockgui.create_new_sim()
        self.assertFalse(_base_mock._science_scans)


class TestConsoleControlRoundTrip(unittest.TestCase):
    """Browser console control -> data_set -> mock physics.

    The engine's helm/weapons widgets mostly fire NO event: they write a data_set key
    that scripts poll (ENGINE_WIDGETS.md).  So these assert the write, and - for the
    throttle - that the write actually MOVES the ship, which is the whole point of the
    change: before it, nothing in the browser could write playerThrottle at all.
    """

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        self.cid = 5
        self.sid = mockgui.sim.create_space_object("behav_playership", "tsn_light_cruiser", 0x20)
        self.o = mockgui.sim.space_objects[self.sid]
        self.o._pos = mockgui.vec3(0, 0, 0)
        mockgui.sim.client_ships[self.cid] = self.sid
        ds = self.o.data_set
        ds.set("torpedo_tube_count", 2, 0)
        ds.set("torpedo_types_available", "Homing,Nuke", 0)
        ds.set("Homing_NUM", 8, 0)
        ds.set("Homing_MAX", 8, 0)
        ds.set("energy", 950, 0)
        while not _base_mock._pending_physics_events.empty():
            _base_mock._pending_physics_events.get_nowait()

    def _ctl(self, etype, gev):
        from cosmos_dev.mission_runner import _console_control
        return _console_control(mockgui, self.cid, etype, gev)

    def test_throttle_write_moves_the_ship(self):
        self._ctl("helm_control", {"key": "playerThrottle", "value": 0.75})
        self.assertAlmostEqual(self.o.data_set.get("playerThrottle", 0), 0.75)
        _base_mock.resume_sim()
        for _ in range(90):                        # 3 sim-seconds at the physics rate
            _base_mock.physics_tick(1 / 30)
        self.assertGreater(self.o._cur_speed, 50, "throttle did not spin the drive up")
        self.assertGreater(abs(self.o._pos.z), 100, "ship did not actually move")

    def test_steering_writes_the_direction_channel(self):
        """The ring writes a DIRECTION + flag, the same channel the autoplay AI uses and
        the only one _playership_drive reads for players."""
        self._ctl("helm_steer", {"ang": 90})
        ds = self.o.data_set
        self.assertTrue(ds.get("steeringToDirFlag", 0))
        self.assertGreater(ds.get("steerToDirDX", 0), 0)     # 90 deg -> +X
        self.assertAlmostEqual(ds.get("steerToDirDZ", 0), 0, places=3)

    def test_shields_and_beam_frequency_write_their_keys(self):
        self._ctl("helm_control", {"key": "shields_raised_flag", "value": 1})
        self.assertTrue(self.o.data_set.get("shields_raised_flag", 0))
        self._ctl("weapon_control", {"op": "freq", "index": 4})
        self.assertAlmostEqual(self.o.data_set.get("scan_type_for_shld_freq", 0), 1.0)

    def test_beam_rate_divides_the_hull_cycle_time(self):
        self._ctl("weapon_control", {"op": "rate", "rate": 4})
        quarter = self.o.data_set.get("beamCycleTime", 0)
        self._ctl("weapon_control", {"op": "rate", "rate": 1})
        full = self.o.data_set.get("beamCycleTime", 0)
        self.assertAlmostEqual(quarter, full / 4.0, places=4)

    def test_load_then_fire_spends_the_round_and_emits_the_launch_event(self):
        """FIRE goes through the mock's own launch_torpedo, so //launch/missile fires
        exactly as it does in the engine rather than through a mock-only signal."""
        self._ctl("weapon_control", {"op": "load", "tube": 0, "kind": "Homing"})
        self.assertEqual(self.o.data_set.get("tube_contents", 0).split(",")[0], "Homing")
        self._ctl("weapon_control", {"op": "fire", "tube": 0})
        self.assertEqual(self.o.data_set.get("Homing_NUM", 0), 7)
        self.assertEqual(self.o.data_set.get("tube_contents", 0).split(",")[0], "")
        tags = []
        while not _base_mock._pending_physics_events.empty():
            tags.append(_base_mock._pending_physics_events.get_nowait()[0])
        self.assertIn("player_launches_missile", tags)

    def test_firing_an_empty_tube_does_nothing(self):
        self._ctl("weapon_control", {"op": "fire", "tube": 1})
        self.assertEqual(self.o.data_set.get("Homing_NUM", 0), 8)

    def test_torpedo_scrap_and_build_move_energy(self):
        self._ctl("weapon_control", {"op": "scrap", "kind": "Homing"})
        self.assertEqual(self.o.data_set.get("Homing_NUM", 0), 7)
        self.assertGreater(self.o.data_set.get("energy", 0), 950)
        before = self.o.data_set.get("energy", 0)
        self._ctl("weapon_control", {"op": "build", "kind": "Homing"})
        self.assertEqual(self.o.data_set.get("Homing_NUM", 0), 8)
        self.assertLess(self.o.data_set.get("energy", 0), before)

    def test_build_is_refused_when_the_racks_are_full(self):
        self.o.data_set.set("energy", 99999, 0)
        self._ctl("weapon_control", {"op": "build", "kind": "Homing"})
        self.assertEqual(self.o.data_set.get("Homing_NUM", 0), 8)   # already at _MAX

    def test_dock_request_needs_a_helm_selection(self):
        self._ctl("dock_request", {})
        self.assertFalse(self.o.data_set.get("dock_base_id", 0))
        base = mockgui.sim.create_space_object("behav_station", "base", 0)
        self.o.data_set.set("normal_target_UID", base, 0)
        self._ctl("dock_request", {})
        self.assertEqual(self.o.data_set.get("dock_base_id", 0), base)
        self.assertEqual(self.o.data_set.get("dock_state", 0), "docking")
        # Cancel is the documented dock_base_id = 0 / dock_state = unknown.
        self._ctl("dock_request", {"release": True})
        self.assertFalse(self.o.data_set.get("dock_base_id", 0))
        self.assertEqual(self.o.data_set.get("dock_state", 0), "unknown")

    def test_player_ship_starts_undocked(self):
        """The engine reports a non-docked player ship as "undocked" (ship_data shows it
        as State), and procedural/docking.py rests there. The mock left it "", so every
        mission gating on dock_state saw a state that was neither docked nor undocked -
        LM's //select/weapons route reads it to decide whether targeting is allowed and
        silently cleared every weapons selection."""
        self.assertEqual(self.o.data_set.get("dock_state", 0), "undocked")
        npc = mockgui.sim.create_space_object("behav_npcship", "tsn_light_cruiser", 0)
        self.assertEqual(mockgui.sim.space_objects[npc].data_set.get("dock_state", 0), "",
                         "dock_state is a player concept; NPCs should not gain one")

    def test_warp_availability_comes_from_the_hull(self):
        """The throttle's WARP band is gated on data_set `warp` == 1.0
        (ENGINE_WIDGETS.md). The mock never set that key, so the band was permanently
        unavailable; it is now derived from the hull's warp_energy_cost."""
        _base_mock.player_ship_setup_defaults(self.o)
        self.assertEqual(self.o.data_set.get("warp", 0), 1.0)

    def test_warp_throttle_values_are_written_through(self):
        """Warp 1-4 are playerThrottle 2-5; the mock's player drive reads >1 as warp."""
        for warp, pt in ((1, 2), (4, 5)):
            self._ctl("helm_control", {"key": "playerThrottle", "value": pt})
            self.assertAlmostEqual(self.o.data_set.get("playerThrottle", 0), pt,
                                   msg="warp %d" % warp)

    def test_reverse_throttle_is_accepted(self):
        """REV reads the impulse bar as 0..-1; -1 is full astern."""
        self._ctl("helm_control", {"key": "playerThrottle", "value": -1})
        self.assertAlmostEqual(self.o.data_set.get("playerThrottle", 0), -1.0)

    def test_a_console_with_no_ship_is_swallowed(self):
        del mockgui.sim.client_ships[self.cid]
        self.assertTrue(self._ctl("helm_control", {"key": "playerThrottle", "value": 1}))


class TestSciencePerTabState(unittest.TestCase):
    """Per-tab scan state, read through the REAL science store.

    Scan text lives on the TARGET keyed by (tab, scanning side), so "scanned" is a fact
    about a tab, not about a contact. This drives the science_data button, and it is where
    a silent bug hid: the reader reached for `o.id`, which the mock's space_object does
    not have, inside a broad try/except - so it answered "unscanned" forever.
    """

    def setUp(self):
        import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (breaks a circular import)
        from sbs_utils.helpers import FrameContext, Context
        from sbs_utils.spaceobject import SpaceObject
        from sbs_utils.procedural.spawn import npc_spawn
        from sbs_utils.procedural.query import to_id

        class _Ev:
            client_id = 0; tag = ""; sub_tag = ""; origin_id = 0; selected_id = 0
            parent_id = 0; value_tag = ""; extra_tag = ""; extra_extra_tag = ""
            sub_float = 0.0; source_point = None; event_time = 0

        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        FrameContext.context = Context(mockgui.sim, mockgui, _Ev())
        SpaceObject.clear()
        self.ship = to_id(npc_spawn(0, 0, 0, "Artemis", "tsn",
                                    "tsn_light_cruiser", "behav_playership"))
        self.tgt = to_id(npc_spawn(0, 0, 500, "Denmark", "civ",
                                   "tsn_light_cruiser", "behav_npcship"))
        self.o = mockgui.sim.space_objects[self.ship]
        self.t = mockgui.sim.space_objects[self.tgt]

    def test_unscanned_contact_reports_nothing_and_offers_only_the_scan_tab(self):
        self.assertFalse(mockgui._tab_scanned(self.o, self.t, "scan"))
        self.assertEqual(mockgui._science_tabs(self.t), ["scan"])

    def test_initial_scan_marks_only_the_scan_tab(self):
        from sbs_utils.procedural.science import science_set_scan_data
        science_set_scan_data(self.ship, self.tgt, "A civilian transport.")
        self.assertTrue(mockgui._tab_scanned(self.o, self.t, "scan"))
        self.assertFalse(mockgui._tab_scanned(self.o, self.t, "intel"))

    def test_other_tabs_appear_only_once_scanned(self):
        """scan_type_list is what the initial scan fills in, which is why the console
        cannot offer status/intel/bio before it."""
        from sbs_utils.procedural.science import science_set_scan_data
        self.assertEqual(mockgui._science_tabs(self.t), ["scan"])
        science_set_scan_data(self.ship, self.tgt,
                              {"scan": "A civilian transport.", "intel": "Wanted."})
        self.assertIn("intel", mockgui._science_tabs(self.t))
        self.assertTrue(mockgui._tab_scanned(self.o, self.t, "intel"))

    def test_placeholder_text_still_counts_as_unscanned(self):
        """science_is_unknown treats these as "no data"; the per-tab reader must agree,
        or a placeholder would render as a completed scan."""
        for placeholder in ("", "no data", "Default Scan"):
            self.t.data_set.set("scan", placeholder, "tsn")
            self.assertFalse(mockgui._tab_scanned(self.o, self.t, "scan"), placeholder)


class TestPreferencesAndReticle(unittest.TestCase):
    """preferences.json, and the selection reticle the 2D view draws from it.

    get_preference_float/int/string were STUBS returning 0/"" - every preference any
    mission asked for came back empty. The file is HJSON (it carries // comments), so it
    needs the comments stripped before json will take it.
    """

    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        mockgui._reticle_sent.clear()
        mockgui._view2d_widget_clients.clear()

    def test_preferences_actually_parse(self):
        prefs = _base_mock._load_preferences()
        self.assertGreater(len(prefs), 50, "preferences.json parsed as empty")
        self.assertEqual(_base_mock.get_preference_string("gui-color-weapon-reticle"), "#f30")
        self.assertEqual(_base_mock.get_preference_int("lock-reticle-size-2D"), 60)
        # A float preference must not come back as an int-ish 0.
        self.assertGreater(_base_mock.get_preference_float("player-fuel-use-coeff"), 0)

    def test_missing_preference_is_empty_not_an_error(self):
        self.assertEqual(_base_mock.get_preference_string("no-such-key"), "")
        self.assertEqual(_base_mock.get_preference_int("no-such-key"), 0)
        self.assertEqual(_base_mock.get_preference_float("no-such-key"), 0.0)

    def test_each_console_gets_its_own_selection_and_colour(self):
        """A console reads a different selection UID and a different colour - the same
        split consoledispatcher makes when routing a 2D-view click."""
        cases = {
            "normal_weap": ("weapon_target_UID", "#f30"),
            "normal_sci": ("science_target_UID", "#0f0"),
            "normal_comm": ("comms_target_UID", "#03f"),
            "gamemaster_overseer_comms": ("comms_target_UID", "#03f"),
        }
        for console, (uid, colour) in cases.items():
            got_uid, got_colour, _cell = mockgui._reticle_for(console)
            self.assertEqual(got_uid, uid, console)
            self.assertEqual(got_colour, colour, console)

    def test_helm_falls_back_to_the_main_gui_colour(self):
        """preferences.json defines no helm reticle colour, so it takes gui-color-main
        rather than an invented one."""
        uid, colour, _cell = mockgui._reticle_for("normal_helm")
        self.assertEqual(uid, "normal_target_UID")
        self.assertEqual(colour, _base_mock.get_preference_string("gui-color-main"))

    def test_reticle_streams_the_selection_and_only_on_change(self):
        sid = mockgui.sim.create_space_object("behav_playership", "test", 0x20)
        tid = mockgui.sim.create_space_object("behav_npcship", "target", 0)
        mockgui.sim.client_ships[5] = sid
        mockgui.send_client_widget_list(5, "normal_weap", "weapon_2d_view")
        mockgui.sim.space_objects[sid].data_set.set("weapon_target_UID", tid, 0)
        mockgui.gui_queue = _queue.Queue()
        mockgui._push_reticle()
        sent = [m for m in self._drain() if m["cmd"] == "reticle"]
        self.assertTrue(sent, "no reticle streamed")
        self.assertEqual(sent[-1]["id"], str(tid))
        self.assertEqual(sent[-1]["color"], "#f30")
        self.assertEqual(sent[-1]["size"], 60)
        mockgui._push_reticle()
        self.assertEqual([m for m in self._drain() if m["cmd"] == "reticle"], [],
                         "an unchanged selection must not re-stream every tick")

    def test_clearing_the_selection_streams_an_empty_id(self):
        sid = mockgui.sim.create_space_object("behav_playership", "test", 0x20)
        tid = mockgui.sim.create_space_object("behav_npcship", "target", 0)
        mockgui.sim.client_ships[5] = sid
        mockgui.send_client_widget_list(5, "normal_sci", "science_2d_view")
        ds = mockgui.sim.space_objects[sid].data_set
        ds.set("science_target_UID", tid, 0)
        mockgui._push_reticle()
        self._drain()
        ds.set("science_target_UID", 0, 0)
        mockgui._push_reticle()
        sent = [m for m in self._drain() if m["cmd"] == "reticle"]
        self.assertTrue(sent)
        self.assertEqual(sent[-1]["id"], "")

    def _drain(self):
        items = []
        while not mockgui.gui_queue.empty():
            items.append(mockgui.gui_queue.get_nowait())
        return items


if __name__ == "__main__":
    unittest.main()
