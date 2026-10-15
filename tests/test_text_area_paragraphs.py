"""A text area follows MARKDOWN paragraph rules (2026-10-14).

* Consecutive plain lines are ONE paragraph: a single newline joins them with a
  space, and the paragraph wraps as a whole.
* A blank line ends the paragraph and leaves a visible gap - half a line - before
  the next block.
* `^` and `<br>` are hard breaks, exactly as before. `^` still breaks inside a
  paragraph, without a gap.
* Every block kind (heading, list item, table, `<hr>`, gauge, choice, link, picture,
  `$`/`$$` style line) starts its own line.
* A plain line straight under a list item continues that item (markdown's "lazy
  continuation").
* `paragraphs=False` opts out; `markdown=False` and `line_styles` force it off.

These work on `calc_rich`'s line list and on what `_present` sends, because that is
where a join or a gap either happens or does not.
"""
import inspect
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.layout.text_area import TextArea, TextLine
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout import measure
from sbs_utils.pages.layout.measure import measure_line_height


class FakeEvent:
    client_id = 0


WIDE = Bounds(0, 0, 90, 90)          # wide and tall: nothing here wraps or scrolls


class Base(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        self.sbs = mock_sbs
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        measure.measure_cache_clear()

    def tearDown(self):
        measure.measure_cache_clear()
        FrameContext.context = None

    def area(self, text, bounds=WIDE, **kw):
        ta = TextArea("t", text, **kw)
        ta.tag = "t"
        ta.bounds = Bounds(bounds.left, bounds.top, bounds.right, bounds.bottom)
        ta.client_id = 0
        ta.calc_rich(0)
        return ta

    @staticmethod
    def texts(ta):
        return [ln.text for ln in ta.lines if isinstance(ln, TextLine)]

    @staticmethod
    def half_line_pct():
        return ((measure_line_height("gui-2", "M") or 24) / 2.0 / 768) * 100


class TestJoin(Base):
    def test_a_single_newline_joins_two_lines_into_one_paragraph(self):
        ta = self.area("The hull is cold.\nNobody answers.")
        self.assertEqual(["The hull is cold. Nobody answers."], self.texts(ta))

    def test_a_paragraph_wraps_as_a_whole(self):
        word = "derelict "
        ta = self.area((word * 12).strip() + "\n" + (word * 12).strip(),
                       Bounds(0, 0, 30, 90))
        lines = self.texts(ta)
        # Two source lines, wrapped together: no line is a short leftover of line one.
        self.assertEqual(" ".join(lines).split(), (word * 24).split())
        self.assertGreater(len(lines), 2)
        for ln in lines[:-1]:
            self.assertGreater(len(ln.split()), 2, f"a wrap boundary at a newline: {lines}")

    def test_indentation_does_not_reach_the_join(self):
        ta = self.area("    one\n    two")
        self.assertEqual(["one two"], self.texts(ta))

    def test_more_lines_keep_joining(self):
        ta = self.area("a\nb\nc\nd")
        self.assertEqual(["a b c d"], self.texts(ta))


class TestGap(Base):
    def test_a_blank_line_ends_the_paragraph_and_leaves_half_a_line(self):
        ta = self.area("First paragraph.\n\nSecond paragraph.")
        self.assertEqual(["First paragraph.", "Second paragraph."], self.texts(ta))
        first, second = ta.lines
        self.assertTrue(first.is_sec_end)
        self.assertAlmostEqual(first.sec_gap, self.half_line_pct(), places=4)
        self.assertFalse(second.is_sec_end, "no gap after the last block")

    def test_the_gap_is_in_the_forward_height_total(self):
        with_gap = self.area("First paragraph.\n\nSecond paragraph.")
        lines_only = sum(ln.height for ln in with_gap.lines)
        self.assertAlmostEqual(with_gap.content_height, lines_only + self.half_line_pct(),
                               places=4)

    def test_several_blank_lines_are_one_gap(self):
        ta = self.area("One.\n\n\n\nTwo.")
        self.assertAlmostEqual(ta.content_height,
                               sum(ln.height for ln in ta.lines) + self.half_line_pct(),
                               places=4)

    def test_leading_and_trailing_blank_lines_add_nothing(self):
        ta = self.area("One.^\n\n")
        self.assertAlmostEqual(ta.content_height, sum(ln.height for ln in ta.lines), places=4)

    def test_the_gap_is_half_a_body_line_after_any_block(self):
        # After a heading, a table or a picture the gap is still half a TEXT line - not
        # half of whatever the block measured.
        ta = self.area("# Orders\n\nGo.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\nAfter.")
        gaps = [ln.sec_gap for ln in ta.lines if ln.is_sec_end]
        self.assertEqual(3, len(gaps))
        for g in gaps:
            self.assertAlmostEqual(g, self.half_line_pct(), places=4)
        # A blank line after a heading is a gap too, and so is one after a table.
        self.assertTrue(ta.lines[0].is_sec_end, "the gap after the heading")

    def test_draw_places_the_next_block_below_the_gap(self):
        ta = self.area("First paragraph.\n\nSecond paragraph.")
        sent = []
        orig = self.sbs.send_gui_text
        self.sbs.send_gui_text = lambda cid, region, tag, msg, l, t, r, b: sent.append((msg, t, b))
        try:
            ta.recalc = False
            ta._present(FakeEvent())
        finally:
            self.sbs.send_gui_text = orig
        self.assertEqual(2, len(sent))
        (_, t0, b0), (_, t1, _) = sent
        self.assertAlmostEqual(t1, b0 + self.half_line_pct(), places=4)

    def test_the_scroll_back_track_counts_the_gap(self):
        # Enough paragraphs to scroll: the last page must fit INCLUDING the gaps, or the
        # bottom of the last paragraph is drawn past the widget.
        doc = "\n\n".join(["Paragraph %d of the briefing." % k for k in range(40)])
        ta = self.area(doc, Bounds(0, 0, 50, 20))
        self.assertTrue(ta.need_v_scroll)
        total = 0.0
        for ln in ta.lines[ta.last_line:]:
            total += ln.height + (ln.sec_gap if ln.is_sec_end else 0)
        self.assertLessEqual(total, ta.bounds.height + 1e-6)


class TestHardBreaks(Base):
    def test_caret_breaks_inside_a_paragraph_without_a_gap(self):
        ta = self.area("Deck one.^Deck two\ncontinues.")
        self.assertEqual(["Deck one.", "Deck two continues."], self.texts(ta))
        self.assertFalse(any(ln.is_sec_end for ln in ta.lines))

    def test_caret_survives_append_and_choose(self):
        # `append` and `choose` re-set the value from `content`: the break must ride.
        ta = self.area("Deck one.^Deck two")
        ta.append("Deck three", sep="\n")
        ta.calc_rich(0)
        self.assertEqual(["Deck one.", "Deck two Deck three"], self.texts(ta))

    def test_caret_then_newline_is_one_break(self):
        ta = self.area("One.^\nTwo.")
        self.assertEqual(["One.", "Two."], self.texts(ta))
        self.assertFalse(any(ln.is_sec_end for ln in ta.lines))

    def test_br_is_its_own_one_line_high_line(self):
        ta = self.area("Above.\n<br>\nBelow.")
        self.assertEqual(["Above.", "^", "Below."], self.texts(ta))
        self.assertFalse(any(ln.is_sec_end for ln in ta.lines))

    def test_gm_style_caret_list_stays_one_line_each(self):
        ta = self.area("Selected Object^Name: Artemis^Side: tsn")
        self.assertEqual(["Selected Object", "Name: Artemis", "Side: tsn"], self.texts(ta))


class TestBlocksFlush(Base):
    BLOCKS = {
        "heading": "# Heading",
        "numbered heading": "$nh2 Numbered",
        "table": "| a | b |\n|---|---|\n| 1 | 2 |",
        "rule": "<hr>",
        "break": "<br>",
        "gauge": "[Energy](gauge://5?max=10)",
        "choice": "[Go](signal://go_now)",
        "chosen": "[Went](chosen://go_now)",
        "link": "[Torgoth](ref://torgoth)",
        "icon line": "![](icon://check.on) Checked",
        "face": "![](face://ter #964b00 8 1;ter #968b00 3 0)",
        "ship": "[](ship://tsn_light_cruiser)",
        "fold": "##- Weapons",
        "list item": "- an item",
        "numbered item": "1. an item",
        "styled line": "$$font:gui-3; styled words",
        "style key line": "$p1 styled words",
    }
    # Blocks a following plain line may CONTINUE - a list item and a style line are the
    # start of a paragraph, as in markdown. Everything else ends at its own line.
    CONTINUABLE = {"list item", "numbered item", "styled line", "style key line"}

    def test_every_block_starts_its_own_line(self):
        for name, block in self.BLOCKS.items():
            with self.subTest(block=name):
                ta = self.area("Before the block.\n" + block + "\nAfter the block.")
                texts = self.texts(ta)
                self.assertIn("Before the block.", texts, f"{name}: {texts}")
                if name not in self.CONTINUABLE:
                    self.assertIn("After the block.", texts, f"{name}: {texts}")

    def test_a_list_item_takes_a_lazy_continuation(self):
        ta = self.area("- Find the beacon\nbefore the raiders do.\n- Come home")
        self.assertEqual(["- Find the beacon before the raiders do.", "- Come home"],
                         self.texts(ta))

    def test_list_items_do_not_join_each_other(self):
        ta = self.area("- one\n- two\n1. three\n2. four")
        self.assertEqual(["- one", "- two", "1. three", "2. four"], self.texts(ta))

    def test_a_plain_line_under_a_heading_does_not_join_it(self):
        ta = self.area("## Orders\nHold the line.\nDo not pursue.")
        self.assertEqual(["Orders", "Hold the line. Do not pursue."], self.texts(ta))

    def test_style_definitions_do_not_join(self):
        ta = self.area("One.\n=$warn color:red;\nTwo.")
        self.assertEqual(["One.", "Two."], self.texts(ta))


class TestOptOut(Base):
    def test_paragraphs_false_keeps_one_line_per_line(self):
        ta = self.area("The hull is cold.\nNobody answers.\n\nLater.", paragraphs=False)
        self.assertEqual(["The hull is cold.", "Nobody answers.", "Later."], self.texts(ta))
        self.assertFalse(any(ln.is_sec_end for ln in ta.lines))
        self.assertAlmostEqual(ta.content_height, sum(ln.height for ln in ta.lines), places=4)

    def test_markdown_false_forces_it_off(self):
        ta = self.area("line one\nline two\n\nline three", markdown=False)
        self.assertFalse(ta.paragraphs_on)
        self.assertEqual(["line one", "line two", "line three"], self.texts(ta))
        self.assertFalse(any(ln.is_sec_end for ln in ta.lines))

    def test_line_styles_force_it_off(self):
        ta = self.area("line one\nline two", line_styles=["_", "_"])
        self.assertFalse(ta.paragraphs_on)
        self.assertEqual(["line one", "line two"], self.texts(ta))

    def test_opted_out_caret_is_today_s_newline(self):
        ta = self.area("a^b", paragraphs=False)
        self.assertEqual(["a", "b"], ta.content)

    def test_gui_text_area_has_the_flag_default_on(self):
        from sbs_utils.procedural.gui.text import gui_text_area
        self.assertIs(True, inspect.signature(gui_text_area).parameters["paragraphs"].default)
        self.assertIs(True, inspect.signature(TextArea.__init__).parameters["paragraphs"].default)


class TestAppendTextNode(Base):
    def test_caret_block_appends_to_the_text_above_it(self):
        # `^^^ more ^^^` under a `"""text"""` block. It wrote `layout_text.message`, which
        # a TextArea never had - an AttributeError on the first append.
        from sbs_utils.mast_sbs.story_nodes.text import (TextRuntimeNode,
                                                         AppendTextRuntimeNode)

        class Node:
            code = None
            message = "and two beers"

        class Task:
            def format_string(self, m):
                return m

        holder = TextRuntimeNode()
        holder.layout_text = TextArea("t", "Thirsty?\nI have")
        TextRuntimeNode.current = holder
        try:
            AppendTextRuntimeNode().enter(None, Task(), Node())
        finally:
            TextRuntimeNode.current = None
        area = holder.layout_text
        area.tag = "t"
        area.bounds = Bounds(0, 0, 90, 90)
        area.calc_rich(0)
        self.assertEqual(["Thirsty? I have and two beers"], self.texts(area))


if __name__ == "__main__":
    unittest.main()
