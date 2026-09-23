"""Icons and cell links in gui_text_area: `![](icon://name) text` lines (and icon
bullets), icons and `[Text](ref://key)` links in table cells, and what the AMD
exporters print for them."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.pages.layout.text_area import TextArea, TableLine, IconLine, TextLine
from sbs_utils.pages.layout.layout import Bounds
from sbs_utils.procedural.amd_blocks import amd_blocks_text


class _Rec:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("send_gui_"):
            return lambda *a: self.calls.append((name, a))
        raise AttributeError(name)


class _Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _calc(self, text):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 40, 80)
        ta.calc_rich(0)
        return ta


class TestIconLine(_Base):
    def test_icon_then_text(self):
        ta = self._calc("# Crew\n![](icon://137?color=#8cf) Helm is manned")
        icons = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertEqual(len(icons), 1)
        self.assertEqual(icons[0].text, "Helm is manned")
        rec = _Rec()
        icons[0].send_gui(rec, 0, "r", "x", 0, 0, 40, 5)
        names = [n for n, _ in rec.calls]
        self.assertEqual(names, ["send_gui_icon", "send_gui_text"])
        self.assertIn("icon_index:137", rec.calls[0][1][3])
        self.assertIn("color:#8cf", rec.calls[0][1][3])
        # The text starts to the RIGHT of the icon.
        self.assertGreater(rec.calls[1][1][4], rec.calls[0][1][6] - 1e-9)

    def test_icon_is_the_bullet(self):
        ta = self._calc("- ![](icon://137) Shields up\n- ![](icon://137) Tractor off")
        icons = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertEqual([i.text for i in icons], ["Shields up", "Tractor off"])
        self.assertTrue(all(i.indent == 2 for i in icons))        # the ul indent
        self.assertFalse(any(isinstance(ln, TextLine) and "-" in ln.text for ln in ta.lines))

    def test_named_icon_resolves(self):
        from sbs_utils.procedural.gui.icon_sheet import icon_resolve
        index, _ = icon_resolve("wanted")
        ta = self._calc("![](icon://wanted) Bounty posted\nnext")
        rec = _Rec()
        [ln for ln in ta.lines if isinstance(ln, IconLine)][0].send_gui(rec, 0, "r", "x", 0, 0, 40, 5)
        self.assertIn(f"icon_index:{index}", rec.calls[0][1][3])

    def test_unknown_name_draws_text_only(self):
        ta = self._calc("![](icon://no_such_glyph) Still readable\nnext")
        rec = _Rec()
        [ln for ln in ta.lines if isinstance(ln, IconLine)][0].send_gui(rec, 0, "r", "x", 0, 0, 40, 5)
        self.assertEqual([n for n, _ in rec.calls], ["send_gui_text"])

    def test_single_line_takes_the_rich_path(self):
        ta = TextArea("t", "![](icon://137) Alone")
        self.assertFalse(ta.simple_text)


class TestLeadPictures(_Base):
    """Faces, images and ships lead a line the same way an icon does."""
    FACE = "ter #ffffff 1 2"

    def _draw(self, line):
        rec = _Rec()
        line.send_gui(rec, 0, "r", "x", 0, 0, 40, 10)
        return rec.calls

    def test_face_with_text_is_a_lead_line(self):
        ta = self._calc(f"![](face://{self.FACE}) Admiral Harkin\nnext")
        lead = [ln for ln in ta.lines if isinstance(ln, IconLine)][0]
        self.assertEqual((lead.ns, lead.text), ("face", "Admiral Harkin"))
        calls = self._draw(lead)
        self.assertEqual([n for n, _ in calls], ["send_gui_face", "send_gui_text"])
        self.assertEqual(calls[0][1][3], self.FACE)

    def test_face_is_two_lines_and_ship_four(self):
        ta = self._calc(f"![](face://{self.FACE}) A\n![](icon://137) B\n[](ship://tsn_battle_cruiser) C")
        face, icon, ship = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertAlmostEqual(face.icon_px, 2 * icon.icon_px)
        self.assertAlmostEqual(ship.icon_px, 4 * icon.icon_px)
        self.assertEqual([n for n, _ in self._draw(ship)][0], "send_gui_3dship")

    def test_size_option(self):
        ta = self._calc("![](icon://137?size=3) Big\n![](icon://137) Small")
        big, small = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertAlmostEqual(big.icon_px, 3 * small.icon_px)

    def test_a_picture_alone_keeps_its_block_form(self):
        from sbs_utils.pages.layout.text_area import FaceLine
        ta = self._calc(f"![](face://{self.FACE})\nnext")
        self.assertTrue(any(isinstance(ln, FaceLine) for ln in ta.lines))
        self.assertFalse(any(isinstance(ln, IconLine) for ln in ta.lines))

    def test_list_bullet_of_another_kind(self):
        ta = self._calc(f"[](bullet://face://{self.FACE})\n- Harkin\n- Vex")
        leads = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertEqual([(l.ns, l.urn, l.text) for l in leads],
                         [("face", self.FACE, "Harkin"), ("face", self.FACE, "Vex")])

    def test_face_in_a_cell(self):
        md = f"| Who | Post |\n|:--|:--|\n| ![](face://{self.FACE}) Harkin | Admiral |"
        t = [ln for ln in self._calc(md).lines if isinstance(ln, TableLine)][0]
        self.assertEqual(t.icons[(1, 0)][0], "face")
        rec = _Rec()
        t.send_gui(rec, 0, "r", "tb", 0, 0, 40, 20)
        self.assertTrue(any(n == "send_gui_face" for n, _ in rec.calls))


class TestTableCells(_Base):
    def test_icon_cells(self):
        md = ("| Station | Crew |\n|:--|:--:|\n"
              "| ![](icon://137) Helm | ![](icon://137) |")
        t = [ln for ln in self._calc(md).lines if isinstance(ln, TableLine)][0]
        self.assertEqual(set(t.icons), {(1, 0), (1, 1)})
        rec = _Rec()
        t.send_gui(rec, 0, "r", "tb", 0, 0, 40, 20)
        icons = [a for n, a in rec.calls if n == "send_gui_icon"]
        self.assertEqual(len(icons), 2)
        texts = [a[3] for n, a in rec.calls if n == "send_gui_text"]
        self.assertTrue(any("Helm" in s for s in texts))
        self.assertFalse(any("icon://" in s for s in texts))

    def test_link_cell_routes_through_the_area(self):
        md = ("| Race | Notes |\n|:--|:--|\n"
              "| [Kralien](ref://kralien) | hostile |")
        ta = self._calc(md)
        t = [ln for ln in ta.lines if isinstance(ln, TableLine)][0]
        self.assertEqual(len(t.links), 1)
        ctag = t.links[(1, 0)]
        self.assertEqual(ta._link_map[ctag], "kralien")
        rec = _Rec()
        t.send_gui(rec, 0, "r", "tb", 0, 0, 40, 20)
        self.assertTrue(any(n == "send_gui_clickregion" and a[2] == ctag for n, a in rec.calls))
        texts = [a[3] for n, a in rec.calls if n == "send_gui_text"]
        self.assertTrue(any("Kralien" in s and TableLine.LINK_COLOR in s for s in texts))

        # A click resolves it like a whole-line link.
        got = []
        ta.on_link_cb = lambda key, w: got.append(key)
        ev = FakeEvent(0, "gui_message")
        ev.sub_tag = ctag
        ta.on_message(ev)
        self.assertEqual(got, ["kralien"])


class TestExporters(unittest.TestCase):
    def test_icon_line_is_a_paragraph_keeping_its_text(self):
        blocks = amd_blocks_text("![](icon://wanted) Bounty posted")
        self.assertEqual([b["type"] for b in blocks], ["paragraph"])
        self.assertIn("Bounty posted", blocks[0]["text"])

    def test_markdown_and_html_tokens(self):
        from sbs_utils.procedural.amd_markdown import _inline_marks
        from sbs_utils.procedural.amd_render import esc_marks
        s = "- ![](icon://check.on) Shields and [WEAP](gauge://0.4?max=1)"
        md = _inline_marks(s)
        self.assertIn("[check.on]", md)
        self.assertIn("WEAP 0.4/1", md)
        self.assertNotIn("icon://", md)
        html = esc_marks(s)
        self.assertIn('class="icon"', html)
        self.assertIn("<meter", html)
        self.assertNotIn("icon://", html)


if __name__ == "__main__":
    unittest.main()
