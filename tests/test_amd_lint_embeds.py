"""Lint checks the pictures a BODY names - faces, images, ships, icons.

A description, a scene's line or a briefing can draw `![](face://...) Name`,
`![](image://key)`, `[](ship://hull)`, `![](icon://check.on) Done` and
`[](bullet://...)`. Every way one goes wrong is silent in the game: an unreadable face,
an image nobody has, a hull the ship data lacks and an unknown icon name all draw
NOTHING, and a picture with its brackets off is drawn as text, marks and all.

The fixture is a small install on disk - `data/shipData.yaml`, `data/graphics/`, and a
mission with `story.json`, a `media/` folder and a MAST file that registers names - so
every check runs against the same kind of evidence it reads in a real mission.
"""
import os
import struct
import tempfile
import unittest
import zlib

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.procedural import amd_lint as L
from sbs_utils.procedural.amd_lint import amd_lint

GOOD_FACE = "ter #e4cb8e 1 0;ter #fff 12 6;ter #e4cb8e 3 1"


def _png(path):
    """A real 1x1 PNG - the image check opens what it finds to read its size."""
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))
    raw = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
    raw += chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw)


class _Mission(unittest.TestCase):
    ship_data = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        data = os.path.join(self.tmp.name, "data")
        self.mission = os.path.join(data, "missions", "Demo")
        os.makedirs(self.mission)
        with open(os.path.join(self.mission, "story.json"), "w") as f:
            f.write('{"sbslib": [], "mastlib": []}')
        if self.ship_data:
            with open(os.path.join(data, "shipData.yaml"), "w") as f:
                f.write('{ "#ship-list": [\n  { "key": "tsn_light_cruiser", "name": "LC" },\n'
                        '  { "key": "starbase_command", "name": "SB" }\n] }\n')
        _png(os.path.join(data, "graphics", "stock_pic.png"))
        _png(os.path.join(self.mission, "media", "my_pic.png"))
        with open(os.path.join(self.mission, "story.mast"), "w") as f:
            f.write('gui_image_add_atlas("logo", "media/logo_sheet")\n'
                    'face_register_sheet("tng", 8, 8)\n'
                    'gui_icon_add_atlas("lm.star", "media/stars")\n')
        L._EMBED_VOCAB.clear()
        L._MISSION_CODE.clear()

    def lint(self, body):
        path = os.path.join(self.mission, "mission.amd")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# [Notes](notes)\n---\nObjective: Look around.\n---\n" + body + "\n")
        return [(f.line, f.code) for f in amd_lint(path, cross_file=False)
                if f.code.startswith(("embed", "transclude"))]


class TestFaces(_Mission):
    def test_a_good_face_says_nothing(self):
        self.assertEqual([], self.lint(f"![](face://{GOOD_FACE}) Harbormaster Quill"))

    def test_a_face_cut_short(self):
        self.assertEqual([(5, "embed-face-unreadable")],
                         self.lint("![](face://ter #e4cb8e 1 0;ter) Cut short"))

    def test_a_layer_that_is_not_a_color(self):
        self.assertEqual([(5, "embed-face-unreadable")],
                         self.lint("![](face://ter e4cbzz 1 0) Bad color"))

    def test_a_sheet_nobody_registers(self):
        self.assertEqual([(5, "embed-face-unreadable")],
                         self.lint("![](face://trr #fff 1 0) Typo"))

    def test_a_sheet_the_mission_registers(self):
        self.assertEqual([], self.lint("![](face://tng #fff 1 0) A mod face"))

    def test_a_face_keyword_is_not_a_face_string(self):
        # `face://terran` is not drawn - the text area hands the engine the string.
        self.assertEqual([(5, "embed-face-unreadable")],
                         self.lint("![](face://terran) Somebody"))


class TestBrokenShapes(_Mission):
    def test_a_space_between_the_brackets(self):
        self.assertEqual([(5, "embed-broken")],
                         self.lint(f"![] (face://{GOOD_FACE}) A space"))

    def test_a_missing_close(self):
        self.assertEqual([(5, "embed-broken")],
                         self.lint(f"![](face://{GOOD_FACE}; Missing bracket"))

    def test_the_older_no_slashes_form_still_draws(self):
        self.assertEqual([], self.lint("![](image:my_pic?scale=0.5)"))

    def test_prose_that_quotes_the_syntax_is_left_alone(self):
        self.assertEqual([], self.lint(
            "- `![](icon://NAME?color=..)` at the start of a line draws an icon.\n"
            "Inline objects: `![](image://key)`, `[](ship://hull)`."))

    def test_a_code_block_is_left_alone(self):
        self.assertEqual([], self.lint("```\n![](icon://nothing_here) x\n```"))


class TestImages(_Mission):
    def test_found_in_the_mission(self):
        self.assertEqual([], self.lint("![](image://my_pic)"))
        self.assertEqual([], self.lint("![](image://media/my_pic?scale=0.5)"))

    def test_found_in_the_games_graphics(self):
        self.assertEqual([], self.lint("![](image://stock_pic) Beside it"))

    def test_a_name_the_mission_registers(self):
        self.assertEqual([], self.lint("![](image://logo)"))

    def test_nowhere(self):
        self.assertEqual([(5, "embed-unknown-image")], self.lint("![](image://my_pik)"))
        self.assertEqual([(5, "embed-unknown-image")],
                         self.lint("[pic]: image://missing_pic"))


class TestShips(_Mission):
    def test_a_hull_in_the_ship_data(self):
        self.assertEqual([], self.lint("[](ship://tsn_light_cruiser?height=100)"))

    def test_a_hull_that_is_not(self):
        self.assertEqual([(5, "embed-unknown-ship")],
                         self.lint("[](ship://tsn_lite_cruiser)"))


class TestShipsWithNoShipData(_Mission):
    ship_data = False

    def test_says_nothing_rather_than_guess(self):
        self.assertEqual([], self.lint("[](ship://tsn_lite_cruiser)"))


class TestIcons(_Mission):
    def test_names_and_indices(self):
        self.assertEqual([], self.lint("![](icon://check.on) Shields up\n\n"
                                       "![](icon://137) By number\n\n"
                                       "- ![](icon://lm.star) A registered one"))

    def test_an_unknown_name(self):
        self.assertEqual([(5, "embed-unknown-icon")],
                         self.lint("![](icon://chek.on) Shields up"))

    def test_a_list_bullet(self):
        self.assertEqual([(5, "embed-unknown-icon")],
                         self.lint("[](bullet://chek.on?color=#8f8)\n- one\n- two"))
        self.assertEqual([], self.lint("[](bullet://none)"))
        self.assertEqual([], self.lint(f"[](bullet://face://{GOOD_FACE})\n- one"))

    def test_a_table_cell(self):
        self.assertEqual([(7, "embed-unknown-icon")],
                         self.lint("| | |\n|:--|:--|\n| ![](icon://chek.on) Hull | 100 |"))


class TestTransclusion(_Mission):
    def test_a_record_that_exists(self):
        self.assertEqual([], self.lint("![[notes]]\n\n# [Other](other)\n![[notes]]"))

    def test_a_record_in_another_file_of_the_mission(self):
        with open(os.path.join(self.mission, "help.amd"), "w", encoding="utf-8") as f:
            f.write("# [Docking](dock_help)\nHold at 2000 and hail.\n")
        self.assertEqual([], self.lint("![[dock_help]]"))

    def test_a_record_nothing_defines(self):
        # The crew would read `[missing: dock_halp]` in the middle of the text.
        self.assertEqual([(5, "transclude-missing")], self.lint("![[dock_halp]]"))


class TestALooseFile(unittest.TestCase):
    def test_no_mission_means_only_the_shape_checks(self):
        findings = [f.code for f in amd_lint(content=(
            "# [N](n)\n---\nObjective: x\n---\n![](image://who_knows)\n\n"
            "![](face://ter #fff 1 0;ter) Cut\n"), cross_file=False)
            if f.code.startswith("embed")]
        self.assertEqual(["embed-face-unreadable"], findings)


if __name__ == "__main__":
    unittest.main()
