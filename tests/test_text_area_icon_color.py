"""An `icon://` drawn by a text area always carries a color.

The engine tints an icon whose props have no `color:` MAGENTA (its debug fallback). An
author writing `![](icon://hourglass) Ten minutes` - no `?color=`, which is how every
example writes it - got a magenta glyph beside blue text, on every quest page: author
course 2's Morrigan page (hourglass, skull) and course 3's Account for the Crew (person,
tablet) and Stand By the Sleepers (hourglass). An uncolored icon now takes the color of
the text it leads, white when there is none.

    python -m unittest tests.test_text_area_icon_color
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.pages.layout.text_area import TextArea, TableLine, IconLine, _icon_send
from sbs_utils.pages.layout.layout import Bounds


class _Rec:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        if name.startswith("send_gui_"):
            return lambda *a: self.calls.append((name, a))
        raise AttributeError(name)


# The course 3 lesson 5 quest body, as written.
BODY = """Somebody crewed that ship. Command wants names.

## Where names are kept

- ![](icon://person) Suits. Every suit in an airlock is tagged with its owner's name.
- ![](icon://tablet) The log. A captain's log says who is aboard.

![](icon://hourglass) Thirty seconds, while the last of the lids come up.
"""


def _icon_props(calls):
    return [a[3] for n, a in calls if n == "send_gui_icon"]


class IconColorTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def tearDown(self):
        FrameContext.context = None

    def draw(self, text):
        ta = TextArea("t", text)
        ta.bounds = Bounds(0, 0, 60, 80)
        ta.calc_rich(0)
        rec = _Rec()
        for ln in ta.lines:
            if isinstance(ln, (IconLine, TableLine)):
                ln.send_gui(rec, 0, "r", "x", 0, 0, 60, 10)
        return rec.calls

    def test_every_icon_in_a_quest_body_has_a_color(self):
        props = _icon_props(self.draw(BODY))
        self.assertEqual(len(props), 3, props)
        for p in props:
            self.assertIn("color:", p)

    def test_a_bullet_icon_takes_the_color_of_its_text(self):
        ta = TextArea("t", BODY)
        ta.bounds = Bounds(0, 0, 60, 80)
        ta.calc_rich(0)
        bullet = next(ln for ln in ta.lines if isinstance(ln, IconLine)
                      and ln.text.startswith("Suits"))
        text_color = bullet.style["style"].split("color:")[1].split(";")[0]
        rec = _Rec()
        bullet.send_gui(rec, 0, "r", "x", 0, 0, 60, 10)
        self.assertIn(f"color:{text_color};", _icon_props(rec.calls)[0])

    def test_an_authored_color_still_wins(self):
        props = _icon_props(self.draw("![](icon://hourglass?color=#f80) Hurry\nnext"))
        self.assertIn("color:#f80;", props[0])

    def test_a_table_cell_icon_has_a_color(self):
        props = _icon_props(self.draw("| What | Where |\n|---|---|\n"
                                      "| ![](icon://person) Suits | airlock |\n"))
        self.assertEqual(len(props), 1)
        self.assertIn("color:", props[0])

    def test_with_nothing_to_follow_it_is_white(self):
        rec = _Rec()
        _icon_send(rec, 0, "r", "x", "hourglass", 0, 0, 5, 5)
        self.assertIn("color:white;", _icon_props(rec.calls)[0])


if __name__ == "__main__":
    unittest.main()
