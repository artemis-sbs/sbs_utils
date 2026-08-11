"""Face compositing in a printed document, and the ordering that makes it work.

A face is not a file - it names cells of a race atlas, composited by
`cosmos_dev/mockgui/face.js`. On screen that can be lazy: the images arrive when
they arrive and the canvas fills in. A PRINTER cannot wait. A headless browser
asked for a PDF snapshots the page without any reason to expect work it has not
been told about, so "the atlases happened to load in time" is a race that passes
on a warm disk and fails on a cold one.

`FaceRender.warm()` plus parser-inserted preload images turn that race into a
guarantee: `getSheet` answers synchronously once a sheet is cached, so by the
time `paint()` runs there is nothing outstanding. These tests pin the pieces of
that argument that can be checked without a browser - above all the ORDER, which
is the entire mechanism and is invisible in the output if you are not looking.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.amd_core import parse
from sbs_utils.procedural.amd_render import amd_render_html


class _Atlas:
    """Stands in for MissionAssets without needing an engine install."""

    def media(self, block):
        return None

    def face_sheets(self, specs):
        return {"Arvonian": "data:image/png;base64,AA",
                "Zimni_Set": "data:image/png;base64,BB"}


def render(source, faces="canvas", assets=None):
    doc = parse(source, file_path="cast.amd")
    return amd_render_html([("cast.amd", doc)],
                           assets=_Atlas() if assets is None else assets,
                           faces=faces)


def body_of(html_text):
    """The page below the stylesheet. The CSS names `.facepreload` too, so a
    naive search finds the rule rather than the markup."""
    return html_text.split("</style>", 1)[1]


ONE_FACE = "# [C](c)\n![](face://arv #ffffff 0 0)\n"

# Three faces, two races - the case that separates "one preload per atlas" from
# "one per face".
THREE_FACES = ("# [Cast](cast)\n"
               "![](face://arv #ffffff 0 0)\n"
               "![](face://arv #ffffff 0 2)\n"
               "![](face://zim #ebb5b5 0 0)\n")


class TestCanvasMode(unittest.TestCase):
    def test_a_face_becomes_a_canvas(self):
        body = body_of(render(ONE_FACE))
        self.assertIn('<canvas class="face"', body)
        self.assertNotIn("art-missing", body)

    def test_the_compositor_is_reused_not_reimplemented(self):
        # face.js is inlined verbatim; a second copy of the layer stacking is
        # exactly what the shared-grammar discipline exists to prevent.
        out = render(ONE_FACE)
        self.assertIn("FaceRender", out)
        self.assertIn("setSheetResolver", out)

    def test_one_preload_per_atlas_not_per_face(self):
        # Six races is the ceiling however many characters a mission has. Getting
        # this wrong costs 3.8 MB per repeated Terran.
        body = body_of(render(THREE_FACES))
        self.assertEqual(body.count("FaceRender.warm("), 2)
        self.assertEqual(body.count('<canvas class="face"'), 3)

    def test_preload_images_are_parser_inserted(self):
        # An <img> the PARSER sees delays the load event; one built by script
        # does not. That difference is the whole reason this markup exists.
        body = body_of(render(ONE_FACE))
        self.assertIn('<div class="facepreload"', body)
        self.assertIn("<img src=", body)


class TestOrdering(unittest.TestCase):
    """The order is the mechanism, and nothing else in the output reveals it."""

    def test_compositor_then_preload_then_paint(self):
        body = body_of(render(ONE_FACE))
        resolver = body.index("FaceRender.setSheetResolver")
        preload = body.index('class="facepreload"')
        paint = body.index("querySelectorAll")
        self.assertLess(resolver, preload,
                        "preload <img> onload would fire against an undefined "
                        "FaceRender - a data: URI can decode before a later "
                        "script runs, and the warm would be lost")
        self.assertLess(preload, paint)


class TestPlaceholderMode(unittest.TestCase):
    """For a formatter that runs no JavaScript. WeasyPrint types better than any
    browser and would paint every canvas blank - the same silent failure the
    canvas guard already prevents, arrived at from the other side."""

    def test_no_canvas_and_no_script(self):
        out = render(ONE_FACE, faces="placeholder")
        body = body_of(out)
        self.assertNotIn("<canvas", body)
        self.assertNotIn("<script", out)
        self.assertNotIn("facepreload", body)

    def test_it_says_a_face_goes_here(self):
        body = body_of(render(ONE_FACE, faces="placeholder"))
        self.assertIn("art-missing", body)
        self.assertIn(">a face<", body)
        # the face string is still shown, so the gap is diagnosable on paper
        self.assertIn("arv #ffffff 0 0", body)

    def test_every_face_gets_one(self):
        body = body_of(render(THREE_FACES, faces="placeholder"))
        self.assertEqual(body.count("art-missing"), 3)


class TestDefaultsUnchanged(unittest.TestCase):
    def test_canvas_is_the_default(self):
        self.assertEqual(render(ONE_FACE), render(ONE_FACE, faces="canvas"))

    def test_no_resolver_means_no_canvas_and_no_preload(self):
        # NoAssets has no face_sheets, so `_face_capable` is False and the page
        # falls through to the placeholder - the shipped default for `sbs docs`.
        class NoFaces:
            def media(self, block):
                return None

        body = body_of(render(ONE_FACE, assets=NoFaces()))
        self.assertNotIn("<canvas", body)
        self.assertNotIn("facepreload", body)
        self.assertIn("art-missing", body)


if __name__ == "__main__":
    unittest.main()
