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
from sbs_utils.procedural.gui import ship as SHIP
from sbs_utils.procedural.gui import icon as ICON
from sbs_utils.procedural.gui import image as IMAGE
from sbs_utils.procedural.gui import blank as BLANK
from sbs_utils.procedural.gui import row as ROW
from sbs_utils.procedural.gui import section as SECTION
from sbs_utils.procedural.gui.overlay import (
    overlay_lower_third_portrait, _lower_third_portrait_builder, PORTRAIT_EM,
    PORTRAIT_GUTTER_EM, SQUARE_STYLE, _portrait_text_frac, OVERLAY_KINDS,
    _KIND_DEFAULT_SLOT, _KIND_PRIMARY_FIELD, _CYCLE_KINDS, _KIND_TEXT_WIDTH)


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
        patch(FACE, "gui_face",
              lambda f, style=None: t.append(("face", style)))
        patch(SHIP, "gui_ship",
              lambda f, style=None: t.append(("ship", style)))
        patch(ICON, "gui_icon",
              lambda f, style=None: t.append(("icon", style)))
        patch(IMAGE, "gui_image_keep_aspect_ratio_center",
              lambda f, style=None: t.append(("image", style)))
        patch(BLANK, "gui_blank",
              lambda count=1, style=None: t.append(("blank", style)))

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
    """A face is a SQUARE column - it sizes itself from the row height. Giving it
    a col-width is not a tuning choice but a bug: a bare number is an ABSOLUTE
    percent of the region, so two of them oversubscribe a strip that is not full
    width, and the engine does not clip - the text draws outside its box and over
    whatever is beside it. That is exactly what an explicit 22/78 split did."""

    def test_the_visual_asks_to_be_square(self):
        self.build(face="F1")
        faces = [v for (k, v) in self.trace if k == "face"]
        self.assertEqual(faces, [SQUARE_STYLE])

    def test_the_text_column_is_flex(self):
        self.build(face="F1")
        subs = [v for (k, v) in self.trace if k == "sub_section"]
        self.assertEqual(len(subs), 1, "only the text is a sub-section now")
        self.assertIsNone(subs[0], "no col-width: flex takes what is left")

    def test_a_thin_gutter_separates_face_from_text(self):
        self.build(face="F1")
        blanks = [v for (k, v) in self.trace if k == "blank"]
        self.assertEqual(len(blanks), 1, "one separator column")
        self.assertIn(f"col-width: {PORTRAIT_GUTTER_EM}em", blanks[0])

    def test_the_gutter_sits_between_them_on_both_sides(self):
        # The text column emits a name row AND a line row, so assert the gutter
        # separates the two COLUMNS rather than counting emissions.
        for align in ("left", "right"):
            self.trace.clear()
            self.build(face="F1", align=align)
            kinds = self.kinds()
            gutter = kinds.index("blank")
            faces = [i for i, k in enumerate(kinds) if k == "face"]
            texts = [i for i, k in enumerate(kinds) if k == "text"]
            if align == "left":
                self.assertTrue(all(i < gutter for i in faces), align)
                self.assertTrue(all(i > gutter for i in texts), align)
            else:
                self.assertTrue(all(i > gutter for i in faces), align)
                self.assertTrue(all(i < gutter for i in texts), align)

    def test_missing_face_still_reserves_the_column(self):
        # Otherwise a run of beats jumps sideways whenever a speaker has no face.
        self.build(face=None)
        blanks = [v for (k, v) in self.trace if k == "blank"]
        self.assertEqual(len(blanks), 2, "placeholder + gutter")
        self.assertIn(f"col-width: {PORTRAIT_EM}em", blanks[0])
        self.assertNotIn("face", self.kinds())

    def test_no_name_drops_the_plate_row_only(self):
        self.build(name="", face="F1")
        self.assertEqual(len(self.texts()), 1, "just the line")
        self.assertIn("Hold position.", self.texts()[0])

    def test_no_style_carries_a_percent(self):
        # A '%' anywhere in a row/col style is an exception at render time, and
        # only an integration run catches it - so pin it here.
        self.build(face="F1")
        styles = [v for (k, v) in self.trace
                  if k in ("row", "sub_section", "blank") and v]
        self.assertFalse([st for st in styles if "%" in st], styles)

    def test_no_bare_number_widths(self):
        # A bare col-width number is an ABSOLUTE percent of the region, not a
        # weight - which is how the first cut drew outside its box.
        self.build(face="F1")
        widths = [v for (k, v) in self.trace
                  if k in ("sub_section", "blank") and v and "col-width" in v]
        for w in widths:
            self.assertTrue("em" in w or "px" in w or "content" in w,
                            f"{w} is an absolute region percent")

    def test_background_fills_the_strip_and_can_be_turned_off(self):
        self.build(face="F1")
        outer = [v for (k, v) in self.trace if k == "row"][0]
        self.assertIn("background:", outer)
        self.trace.clear()
        self.build(face="F1", background=None)
        outer = [v for (k, v) in self.trace if k == "row"][0]
        self.assertNotIn("background:", outer)


VISUALS = ("face", "ship", "icon", "image")


class TestPortraitVariants(PortraitBuilderBase):
    """Four sources, one square slot. Requiring square is what makes them
    interchangeable: the strip, the gutter and the room left for the line do not
    move when a face is swapped for a ship."""

    def test_every_source_renders_its_own_widget(self):
        for v in VISUALS:
            self.trace.clear()
            self.build(**{v: "X"})
            self.assertIn(v, self.kinds(), v)

    def test_every_source_is_asked_to_be_square(self):
        # Face and Icon are square already; Ship and Image are NOT, and unsquared
        # they are flex columns that take half the strip.
        for v in VISUALS:
            self.trace.clear()
            self.build(**{v: "X"})
            style = [s for (k, s) in self.trace if k == v][0]
            self.assertEqual(style, SQUARE_STYLE, v)

    def test_no_source_is_given_an_explicit_width(self):
        # square and a width are mutually exclusive - a width would un-square it.
        for v in VISUALS:
            self.trace.clear()
            self.build(**{v: "X"})
            style = [s for (k, s) in self.trace if k == v][0]
            self.assertNotIn("em", style, v)
            self.assertNotIn("%", style, v)

    def test_the_layout_is_identical_whichever_source(self):
        shapes = set()
        for v in VISUALS:
            self.trace.clear()
            self.build(**{v: "X"})
            shapes.add(tuple("visual" if k in VISUALS else k
                             for k in self.kinds()))
        self.assertEqual(len(shapes), 1, f"variants diverged: {shapes}")

    def test_each_source_works_on_both_sides(self):
        for v in VISUALS:
            for align in ("left", "right"):
                self.trace.clear()
                self.build(align=align, **{v: "X"})
                kinds = self.kinds()
                gutter = kinds.index("blank")
                vis = kinds.index(v)
                texts = [i for i, k in enumerate(kinds) if k == "text"]
                if align == "left":
                    self.assertLess(vis, gutter, f"{v}/{align}")
                    self.assertTrue(all(i > gutter for i in texts))
                else:
                    self.assertGreater(vis, gutter, f"{v}/{align}")
                    self.assertTrue(all(i < gutter for i in texts))

    def test_first_set_wins_in_hero_order(self):
        # face, ship, icon, image - the same precedence overlay_hero uses, so the
        # two cards do not disagree about which visual a record means.
        self.build(face="F", ship="S", icon="I", image="M")
        self.assertIn("face", self.kinds())
        for other in ("ship", "icon", "image"):
            self.assertNotIn(other, self.kinds())
        self.trace.clear()
        self.build(ship="S", icon="I", image="M")
        self.assertIn("ship", self.kinds())
        self.assertNotIn("icon", self.kinds())
        self.trace.clear()
        self.build(icon="I", image="M")
        self.assertIn("icon", self.kinds())
        self.assertNotIn("image", self.kinds())

    def test_an_image_keeps_its_aspect_ratio_inside_the_square(self):
        # The BOX is square; a non-square source letterboxes rather than
        # distorting, which is why it goes through the keep-aspect front door.
        import sbs_utils.procedural.gui.overlay as O
        import inspect
        src = inspect.getsource(O._lower_third_portrait_builder)
        self.assertIn("gui_image_keep_aspect_ratio_center", src)


class TestPortraitRegistration(unittest.TestCase):
    def test_registered_as_its_own_kind(self):
        self.assertIn("lower_third_portrait", OVERLAY_KINDS)

    def test_shares_the_lower_third_slot(self):
        self.assertEqual(_KIND_DEFAULT_SLOT["lower_third_portrait"], "lower_third")

    def test_line_is_the_primary_field_and_cycles(self):
        self.assertEqual(_KIND_PRIMARY_FIELD["lower_third_portrait"], "line")
        self.assertEqual(_CYCLE_KINDS["lower_third_portrait"], ("line", "gui-3"))

    def test_text_width_is_measured_per_client_not_fixed(self):
        # The face is square, so its bite depends on the screen's aspect ratio.
        self.assertTrue(callable(_KIND_TEXT_WIDTH["lower_third_portrait"]))


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
        self.assertLess(self.fracs[0], 1.0, "the portrait takes a bite")
        self.assertGreater(self.fracs[0], 0.3)

    def test_the_bite_tracks_the_slot_geometry(self):
        # A taller slot holds a bigger square, so less is left for the line.
        import sbs_utils.procedural.gui.overlay as O
        w, h = [1920.0], [200.0]
        rw, rh = O._slot_px_width, O._slot_px_height
        O._slot_px_width = lambda cid, slot, pad=0.96: w[0]
        O._slot_px_height = lambda cid, slot: h[0]
        try:
            narrow = _portrait_text_frac(0, "lower_third")
            h[0] = 600.0
            wide = _portrait_text_frac(0, "lower_third")
        finally:
            O._slot_px_width, O._slot_px_height = rw, rh
        self.assertGreater(narrow, wide)

    def test_unmeasurable_screen_still_leaves_room_for_the_face(self):
        import sbs_utils.procedural.gui.overlay as O
        rw = O._slot_px_width
        O._slot_px_width = lambda cid, slot, pad=0.96: None
        try:
            self.assertLess(_portrait_text_frac(0, "lower_third"), 1.0)
        finally:
            O._slot_px_width = rw

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
