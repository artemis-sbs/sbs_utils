"""Widget tags must stay bounded across GUI rebuilds.

`self.tag = self.rebuild_tag + 100 % 100000` binds as `+ (100 % 100000)` ==
`+ 100`, so the intended wrap never happened and every rebuild pushed the tags
~2100 higher, forever. Measured against the real engine while investigating
LM #664: ten rebuilds of a five-widget screen already had it emitting tags near
20,000.

The +2000 gap between generations is the part that matters and is asserted here
too -- it is what keeps a new build's tags clear of the build still on screen.

    python -m unittest tests.test_story_page_tag_wrap
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs   # noqa: F401 -- puts the mock `sbs` on sys.modules
from sbs_utils.mast_sbs.maststorypage import StoryPage

WRAP = 100000
WIDGETS_PER_BUILD = 5


def _rebuild(page, widgets=WIDGETS_PER_BUILD):
    """One GUI build: hand out `widgets` tags, then swap generations."""
    page.is_processing_rebuild = True
    tags = [page.get_tag() for _ in range(widgets)]
    page.is_processing_rebuild = False
    page.advance_tag_generation()
    return tags


class TagGenerationTests(unittest.TestCase):

    def setUp(self):
        self.page = StoryPage()

    def test_tags_stay_bounded_over_many_rebuilds(self):
        page = self.page
        highest = 0
        for _ in range(2000):
            highest = max(highest, max(int(t) for t in _rebuild(page)))
        # Bounded by the wrap plus one generation's gap, not by the run length.
        self.assertLess(highest, WRAP + 2100)

    def test_a_new_build_does_not_reuse_the_live_builds_tags(self):
        page = self.page
        previous = set()
        for _ in range(2000):
            tags = set(_rebuild(page))
            self.assertFalse(previous & tags,
                             "a rebuild reused a tag the on-screen build is using")
            previous = tags

    def test_generations_are_separated_by_the_gap(self):
        page = self.page
        page.rebuild_tag = 200
        page.advance_tag_generation()
        self.assertEqual(300, page.tag)
        self.assertEqual(2300, page.rebuild_tag)

    def test_the_counter_wraps_instead_of_growing(self):
        page = self.page
        page.rebuild_tag = WRAP - 50
        page.advance_tag_generation()
        self.assertEqual(50, page.tag)


if __name__ == "__main__":
    unittest.main()
