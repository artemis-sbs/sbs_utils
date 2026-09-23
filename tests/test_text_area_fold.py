"""List-wide icon bullets (`[](bullet://..)`) and collapsible headings (`##+` / `##-`)
in gui_text_area, and what the AMD tooling does with them."""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.pages.layout.text_area import TextArea, IconLine, FoldLine, TextLine, TableLine
from sbs_utils.pages.layout.layout import Bounds
from sbs_utils.procedural.amd_blocks import amd_blocks_text


def _texts(ta):
    return [ln.text for ln in ta.lines if isinstance(ln, (TextLine, IconLine))]


class _Base(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _calc(self, text, height=80):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 40, height)
        ta.calc_rich(0)
        return ta


class TestListBullet(_Base):
    def test_one_declaration_serves_the_list(self):
        ta = self._calc("[](bullet://check.on?color=#8f8)\n- Shields up\n- Tractor off\n\n- plain again")
        icons = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertEqual([i.text for i in icons], ["Shields up", "Tractor off"])
        self.assertTrue(all(i.urn.startswith("check.on") for i in icons))
        # The blank line ended the list, and its bullet with it.
        self.assertTrue(any(isinstance(ln, TextLine) and "plain again" in ln.text for ln in ta.lines))

    def test_an_item_can_still_pick_its_own(self):
        ta = self._calc("[](bullet://check.on)\n- ![](icon://check.off) Not yet\n- Done")
        icons = [ln for ln in ta.lines if isinstance(ln, IconLine)]
        self.assertEqual([i.urn for i in icons], ["check.off", "check.on"])

    def test_numbered_lists_keep_their_numbers(self):
        ta = self._calc("[](bullet://check.on)\n1. First\n2. Second")
        self.assertFalse(any(isinstance(ln, IconLine) for ln in ta.lines))

    def test_none_stops_it(self):
        ta = self._calc("[](bullet://check.on)\n- a\n[](bullet://none)\n- b")
        self.assertEqual([ln.text for ln in ta.lines if isinstance(ln, IconLine)], ["a"])

    def test_directive_is_not_drawn(self):
        ta = self._calc("[](bullet://check.on)\n- a")
        self.assertFalse(any("bullet://" in t for t in _texts(ta)))


DOC = "\n".join([
    "# Ship",
    "##+ Weapons",
    "Beams ready.",
    "| Tube | Load |",
    "|:--|:--|",
    "| 1 | Homing |",
    "###- Tubes",
    "Two tubes.",
    "##- Engines",
    "Impulse nominal.",
    "# Crew",
    "Forty aboard.",
])


class TestFold(_Base):
    def test_closed_section_is_skipped_to_the_next_heading(self):
        ta = self._calc(DOC)
        folds = [ln for ln in ta.lines if isinstance(ln, FoldLine)]
        self.assertEqual([(f.text, f.is_open) for f in folds],
                         [("Weapons", False), ("Engines", True)])
        body = " ".join(_texts(ta))
        self.assertNotIn("Beams ready", body)
        self.assertNotIn("Two tubes", body)          # a nested heading goes with it
        self.assertFalse(any(isinstance(ln, TableLine) for ln in ta.lines))
        self.assertIn("Impulse nominal", body)        # same level ends the section
        self.assertIn("Forty aboard", body)

    def test_click_opens_and_state_survives_a_new_value(self):
        ta = self._calc(DOC)
        weapons = [ln for ln in ta.lines if isinstance(ln, FoldLine)][0]
        ev = FakeEvent(0, "gui_message")
        ev.sub_tag = weapons.click_tag
        ta.present = lambda e: None               # the repaint itself is the engine's
        ta.on_message(ev)
        body = " ".join(_texts(ta))
        self.assertIn("Beams ready", body)
        self.assertIn("Two tubes", body)
        self.assertTrue(any(isinstance(ln, TableLine) for ln in ta.lines))
        # Re-setting the text (a live document) keeps the reader's choice.
        ta.value = DOC
        ta.calc_rich(0)
        self.assertIn("Beams ready", " ".join(_texts(ta)))

    def test_toggle_by_key(self):
        ta = self._calc(DOC)
        self.assertEqual(ta.toggle_fold("##Engines"), False)
        ta.calc_rich(0)
        self.assertNotIn("Impulse nominal", " ".join(_texts(ta)))
        self.assertIsNone(ta.toggle_fold("##Nope"))

    def test_heading_scrolls_into_view_on_toggle(self):
        long = "\n".join(["# Top"] + [f"line {i}" for i in range(60)] + ["##+ Late", "hidden"])
        ta = self._calc(long, height=20)
        late = [ln for ln in ta.lines if isinstance(ln, FoldLine)][0]
        ev = FakeEvent(0, "gui_message")
        ev.sub_tag = late.click_tag
        ta.present = lambda e: None
        ta.on_message(ev)
        idx = next(i for i, ln in enumerate(ta.lines) if isinstance(ln, FoldLine))
        first = ta.last_line - ta.scroll_line
        self.assertLessEqual(first, idx)

    def test_marker_needs_to_touch_the_hashes(self):
        ta = self._calc("## - not a fold\ntext")
        self.assertFalse(any(isinstance(ln, FoldLine) for ln in ta.lines))


class TestHeadingEndsAtItsLine(_Base):
    def _fonts(self, text):
        from sbs_utils.helpers import split_props
        ta = self._calc(text)
        out = []
        for ln in ta.lines:
            st = ln.style.get("style", "") if isinstance(getattr(ln, "style", None), dict) else ""
            out.append((ln.text, split_props(st, "font").get("font")))
        return out

    def test_a_line_after_a_heading_is_body_text(self):
        f = dict(self._fonts("## Kralien\nSwarm tactics.\n### Orders\nHold."))
        self.assertEqual(f["Kralien"], "gui-4")
        self.assertEqual(f["Swarm tactics."], "gui-2")
        self.assertEqual(f["Orders"], "gui-3")
        self.assertEqual(f["Hold."], "gui-2")

    def test_an_icon_line_after_a_heading_is_body_text(self):
        ta = self._calc("## arrival\n![](icon://square) Nominal")
        self.assertEqual([ln for ln in ta.lines if isinstance(ln, IconLine)][0].font, "gui-2")

    def test_other_styles_still_carry(self):
        f = dict(self._fonts("$p1 First paragraph line\nsecond line"))
        self.assertEqual(f["second line"], f["First paragraph line"])


class TestTooling(unittest.TestCase):
    def test_fold_heading_is_its_title_and_bullet_is_silent(self):
        blocks = amd_blocks_text("##+ Weapons\n\n[](bullet://check.on)\n- a")
        self.assertEqual(blocks[0], {"type": "paragraph", "line": 1, "text": "Weapons", "links": []})
        self.assertEqual(blocks[1]["type"], "style_ref")
        self.assertFalse(any(b.get("type") == "media" for b in blocks))


if __name__ == "__main__":
    unittest.main()
