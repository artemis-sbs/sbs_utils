"""A face sheet registered at RUNTIME reaches the browser, with its cell size.

The page used to learn face aliases only from data/graphics/allFaceFiles.txt, read when
it loaded, so a sheet given to `add_face_bitmap_sheet` - a mod's faces, a ship portrait
set - composited as a blank square in the mock while drawing in the engine.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import queue as _queue
import unittest

import cosmos_dev.mock.sbs as _base_mock
import cosmos_dev.mockgui.sbs as mockgui
from cosmos_dev.mockgui import server


class TestRuntimeFaceSheet(unittest.TestCase):
    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        self.addCleanup(server._runtime_face_sheets.clear)

    def test_REGISTERING_SENDS_THE_SHEET_AND_ITS_CELL(self):
        mockgui.add_face_bitmap_sheet("shp_base0",
                                      "data/missions/__lib__/media/p/ship_portraits/base_0",
                                      256, 256)
        msg = mockgui.gui_queue.get_nowait()
        self.assertEqual(msg["cmd"], "face_sheet")
        self.assertEqual(msg["alias"], "shp_base0")
        self.assertEqual(msg["cell"], [256, 256])
        self.assertEqual(_base_mock.face_sheet_cells["shp_base0"], (256, 256))

    def test_a_late_tab_gets_it_in_the_page_table(self):
        server._runtime_face_sheets["shp_base0"] = {
            "url": server._face_sheet_url("data/missions/__lib__/media/p/x/base_0"),
            "cell": [256, 256]}
        table = server._face_alias_table()
        self.assertEqual(table["shp_base0"], {"url": "/missions/__lib__/media/p/x/base_0",
                                              "cell": [256, 256]})

    def test_url_shapes(self):
        self.assertEqual(server._face_sheet_url("data/missions/M/media/a.png"),
                         "/missions/M/media/a")
        self.assertEqual(server._face_sheet_url("../missions/M/media/a"), "/missions/M/media/a")


if __name__ == "__main__":
    unittest.main()
