"""map_path() — read a selected map's path whatever form the variable is in.

A mission's selected-map variable is a Label once the picker has resolved it,
but it starts as the plain path STRING settings.yaml supplies, and the window
between the two spans awaits. LM's start_server sets WORLD_SELECT to the string,
then resolves the Label some sixty lines and two awaits later.

Eight places in LM read `.path` off it, three of them from routes that can fire
at any moment (two //damage/destroy, plus the end-condition watchers). Every one
of them raised "'str' object has no attribute 'path'" if it ran in that window.

The guard has to be Python: getattr is not in MAST's eval globals.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.maps import map_path


class FakeMapLabel:
    """What the picker resolves WORLD_SELECT to."""
    def __init__(self, path):
        self.path = path


class TestMapPath(unittest.TestCase):
    def test_a_resolved_map_label(self):
        self.assertEqual("siege", map_path(FakeMapLabel("siege")))

    def test_the_settings_string_before_it_is_resolved(self):
        # The regression: this is WORLD_SELECT for the whole startup window.
        self.assertEqual("siege", map_path("siege"))

    def test_none_is_empty_not_an_error(self):
        # `default WORLD_SELECT = None` is a real state (game_results.mast).
        self.assertEqual("", map_path(None))

    def test_comparisons_behave_the_same_either_way(self):
        # What the call sites actually do -- and the point of the fix: the same
        # answer whether or not the picker has resolved the label yet.
        for world in (FakeMapLabel("peacetime"), "peacetime"):
            self.assertEqual("peacetime", map_path(world))
            self.assertNotEqual("deep_strike", map_path(world))

    def test_an_object_without_a_path_is_empty_not_an_error(self):
        self.assertEqual("", map_path(object()))

    def test_an_empty_path_is_empty(self):
        self.assertEqual("", map_path(""))
        self.assertEqual("", map_path(FakeMapLabel("")))


if __name__ == "__main__":
    unittest.main()
