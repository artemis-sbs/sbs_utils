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


if __name__ == "__main__":
    unittest.main()
