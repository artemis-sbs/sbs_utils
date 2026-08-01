"""Lower third carrying ONE face, on the left or the right.

A conversation is this strip shown repeatedly with ``align`` alternating - the
face moves side to side and only the speaker is on screen. Two portraits at once
would spend the strip's width on someone who is not talking, and would not read
for a monologue or a three-hander.

The layout assertions drive the BUILDER directly (its gui_* imports are inside
the function, so patching the source modules records exactly what it asks for),
which keeps the tests about column order and justification rather than about
pixel output.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural.gui import overlay as OV
from sbs_utils.procedural.gui import text as TEXT
from sbs_utils.procedural.gui import face as FACE
from sbs_utils.procedural.gui import blank as BLANK
from sbs_utils.procedural.gui import row as ROW
from sbs_utils.procedural.gui import section as SECTION
from sbs_utils.procedural.gui.overlay import (
    overlay_lower_third_portrait, _lower_third_portrait_builder, PORTRAIT_COL,
    OVERLAY_KINDS, _KIND_DEFAULT_SLOT, _KIND_PRIMARY_FIELD, _CYCLE_KINDS,
    _KIND_TEXT_WIDTH)


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


class _RecordingSubSection:
    """Stand-in for gui_sub_section's context manager."""
    def __init__(self, trace, style):
        self.trace = trace
        self.style = style

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.trace.append(("sub_section_end", self.style))
        return False


class PortraitBuilderBase(unittest.TestCase):
    """Records the builder's layout calls in order."""

    def setUp(self):
        self.trace = []
        self._saved = {}

        def patch(mod, name, fn):
            self._saved[(mod, name)] = getattr(mod, name)
            setattr(mod, name, fn)

        t = self.trace
        patch(ROW, "gui_row", lambda style=None: t.append(("row", style)))
        patch(TEXT, "gui_text", lambda s, *a, **k: t.append(("text", s)))
        patch(FACE, "gui_face", lambda f, *a, **k: t.append(("face", f)))
        patch(BLANK, "gui_blank", lambda *a, **k: t.append(("blank", None)))

        def _sub(style=None):
            t.append(("sub_section", style))
            return _RecordingSubSection(t, style)
        patch(SECTION, "gui_sub_section", _sub)

    def tearDown(self):
        for (mod, name), fn in self._saved.items():
            setattr(mod, name, fn)

    # helpers -----------------------------------------------------------------
    def build(self, **content):
        content.setdefault("name", "Harkin")
        content.setdefault("line", "Hold position.")
        _lower_third_portrait_builder(0, content)
        return self.trace

    def kinds(self):
        return [k for (k, _v) in self.trace]

    def index_of(self, kind):
        return self.kinds().index(kind)

    def texts(self):
        return [v for (k, v) in self.trace if k == "text"]


class TestPortraitSide(PortraitBuilderBase):
    def test_align_left_puts_the_face_before_the_text(self):
        self.build(face="F1", align="left")
        self.assertLess(self.index_of("face"), self.index_of("text"),
                        "face column is emitted first when aligned left")

    def test_align_right_puts_the_face_after_the_text(self):
        self.build(face="F1", align="right")
        self.assertGreater(self.index_of("face"), self.index_of("text"),
                           "text column is emitted first when the face is right")

    def test_default_align_is_left(self):
        self.build(face="F1")
        self.assertLess(self.index_of("face"), self.index_of("text"))

    def test_align_synonyms_and_case(self):
        for value in ("RIGHT", "Right", "r", "end"):
            self.trace.clear()
            self.build(face="F1", align=value)
            self.assertGreater(self.index_of("face"), self.index_of("text"),
                               f"{value!r} should read as the right side")

    def test_text_justifies_toward_the_face(self):
        # The line hangs off the portrait; justified the other way it would float
        # away from the speaker it belongs to.
        self.build(face="F1", align="left")
        self.assertTrue(all("justify:left" in s for s in self.texts()))
        self.trace.clear()
        self.build(face="F1", align="right")
        self.assertTrue(all("justify:right" in s for s in self.texts()))

    def test_only_one_face_is_ever_drawn(self):
        self.build(face="F1", align="right")
        self.assertEqual(self.kinds().count("face"), 1,
                         "a conversation alternates ONE face, never shows two")


class TestPortraitColumns(PortraitBuilderBase):
    def test_columns_split_the_strip(self):
        self.build(face="F1")
        widths = [v for (k, v) in self.trace if k == "sub_section"]
        self.assertEqual(len(widths), 2, "a face column and a text column")
        # WEIGHTS, not percents - the layout lexer has no '%' token, so a style
        # carrying one raises instead of laying out.
        self.assertIn(f"col-width: {PORTRAIT_COL};", widths[0])
        self.assertIn(f"col-width: {100.0 - PORTRAIT_COL};", widths[1])
        self.assertNotIn("%", " ".join(widths))

    def test_missing_face_still_reserves_the_column(self):
        # Otherwise a run of beats jumps sideways whenever a speaker has no face.
        self.build(face=None)
        widths = [v for (k, v) in self.trace if k == "sub_section"]
        self.assertEqual(len(widths), 2)
        self.assertIn("blank", self.kinds())
        self.assertNotIn("face", self.kinds())

    def test_no_name_drops_the_plate_row_only(self):
        self.build(name="", face="F1")
        self.assertEqual(len(self.texts()), 1, "just the line")
        self.assertIn("Hold position.", self.texts()[0])

    def test_no_style_carries_a_percent(self):
        # A '%' anywhere in a row/col style is an exception at render time, and
        # only an integration run catches it - so pin it here.
        self.build(face="F1")
        styles = [v for (k, v) in self.trace if k in ("row", "sub_section") and v]
        self.assertFalse([s for s in styles if "%" in s], styles)

    def test_background_fills_the_strip_and_can_be_turned_off(self):
        self.build(face="F1")
        outer = [v for (k, v) in self.trace if k == "row"][0]
        self.assertIn("background:", outer)
        self.trace.clear()
        self.build(face="F1", background=None)
        outer = [v for (k, v) in self.trace if k == "row"][0]
        self.assertNotIn("background:", outer)


class TestPortraitRegistration(unittest.TestCase):
    def test_registered_as_its_own_kind(self):
        self.assertIn("lower_third_portrait", OVERLAY_KINDS)

    def test_shares_the_lower_third_slot(self):
        self.assertEqual(_KIND_DEFAULT_SLOT["lower_third_portrait"], "lower_third")

    def test_line_is_the_primary_field_and_cycles(self):
        self.assertEqual(_KIND_PRIMARY_FIELD["lower_third_portrait"], "line")
        self.assertEqual(_CYCLE_KINDS["lower_third_portrait"], ("line", "gui-3"))

    def test_text_width_excludes_the_portrait(self):
        self.assertAlmostEqual(_KIND_TEXT_WIDTH["lower_third_portrait"],
                               (100.0 - PORTRAIT_COL) / 100.0)


class TestPortraitCycling(unittest.TestCase):
    """The line is split against the strip MINUS the portrait, or the segments
    it produces still do not fit."""

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 0
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(0)
        client.page_stack.append(self.page)
        FrameContext.page = self.page

        self.fracs = []
        self._real_split = OV._split_to_fit

        def _spy(cid, slot, text, font, width_frac=1.0):
            self.fracs.append(width_frac)
            return [text]
        OV._split_to_fit = _spy

    def tearDown(self):
        OV._split_to_fit = self._real_split
        TickDispatcher.clear()
        FrameContext.page = None
        FrameContext.context = None

    def test_line_is_measured_against_the_remaining_width(self):
        overlay_lower_third_portrait("Harkin", "Hold position.", face="F1")
        self.assertTrue(self.fracs)
        self.assertAlmostEqual(self.fracs[0], (100.0 - PORTRAIT_COL) / 100.0)

    def test_plain_lower_third_still_measures_the_whole_strip(self):
        from sbs_utils.procedural.gui.overlay import overlay_lower_third
        overlay_lower_third("Harkin", "Hold position.")
        self.assertAlmostEqual(self.fracs[0], 1.0)

    def test_subtitle_plays_through_once_by_default(self):
        # A repeating subtitle reads as a stutter.
        from sbs_utils.procedural.gui.overlay import _KIND_LOOP_DEFAULT
        self.assertIs(_KIND_LOOP_DEFAULT["lower_third_portrait"], False)


if __name__ == "__main__":
    unittest.main()
