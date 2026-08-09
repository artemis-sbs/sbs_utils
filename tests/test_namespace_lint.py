"""Namespace-collision linter: the four classes it must catch, and what it must NOT."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.namespace_lint import namespace_lint_project


def codes(findings):
    return sorted(f.code for _, f in findings)


class TestNamespaceLint(unittest.TestCase):
    def test_duplicate_function_across_addons(self):
        """The LM market crash: two addons, same name, different signatures."""
        py = [("items/items.py", "def market_sell_price(station_id, key):\n    return 1\n"),
              ("casino/casino_market.py", "def market_sell_price(g):\n    return 2\n")]
        f = namespace_lint_project(py)
        self.assertEqual(codes(f), ["ns-duplicate-function", "ns-duplicate-function"])
        self.assertIn("last one loaded wins", f[0][1].message)
        # anchored at each defining site, so both authors see it
        self.assertEqual(sorted(p for p, _ in f), ["casino/casino_market.py", "items/items.py"])

    def test_same_name_twice_in_ONE_addon_is_not_a_collision(self):
        """Two files in the same addon are one author's problem, not a cross-addon trap."""
        py = [("items/a.py", "def item_price():\n    return 1\n"),
              ("items/b.py", "def item_price():\n    return 2\n")]
        self.assertEqual(codes(namespace_lint_project(py)), [])

    def test_duplicate_suppresses_the_generic_style_nag(self):
        """`load_map` in two addons is one finding, not a duplicate + a style nag."""
        py = [("admiral/move_to_lib.py", "def load_map(x):\n    return 1\n"),
              ("gamemaster/move_to_lib.py", "def load_map(x):\n    return 1\n")]
        self.assertEqual(codes(namespace_lint_project(py)),
                         ["ns-duplicate-function", "ns-duplicate-function"])

    def test_shadows_library_global(self):
        py = [("fleets/fleet.py", "def reputation_standing(ship_id, clan):\n    return 0\n")]
        f = namespace_lint_project(py, lib_globals={"reputation_standing"})
        self.assertEqual(codes(f), ["ns-shadows-library"])
        self.assertIn("works from Python, wrong from MAST", f[0][1].message)

    def test_shadow_suppresses_the_generic_style_nag(self):
        """One actionable finding per name, not two."""
        py = [("a/x.py", "def get_thing():\n    return 0\n")]
        f = namespace_lint_project(py, lib_globals={"get_thing"})
        self.assertEqual(codes(f), ["ns-shadows-library"])

    def test_mast_hard_assign_to_a_function_name(self):
        py = [("gallery/g.py", "def gallery_is_page(key):\n    return True\n")]
        mast = [("gallery/g.mast", "== main ==\n    gallery_is_page = 5\n")]
        f = namespace_lint_project(py, mast)
        self.assertEqual(codes(f), ["ns-mast-var-collision"])
        self.assertEqual(f[0][1].line, 2)

    def test_default_assign_is_exempt(self):
        """assign.py deliberately allows `default x = ...` onto an existing global."""
        py = [("fleets/e.py", "def elite_get_all_abilities():\n    return []\n")]
        mast = [("consoles/debug.mast", "== dbg ==\n    default elite_get_all_abilities = None\n")]
        self.assertEqual(codes(namespace_lint_project(py, mast)), [])

    def test_shared_assign_is_NOT_exempt(self):
        py = [("a/x.py", "def thing_go():\n    return 1\n")]
        mast = [("a/y.mast", "== m ==\n    shared thing_go = 1\n")]
        self.assertEqual(codes(namespace_lint_project(py, mast)), ["ns-mast-var-collision"])

    def test_generic_name_warns_including_underscore_helpers(self):
        py = [("consoles/r.py", "def _is_creditable(x):\n    return True\n")]
        f = namespace_lint_project(py)
        self.assertEqual(codes(f), ["ns-generic-name"])
        self.assertEqual(f[0][1].severity, "warning")

    def test_prefixed_names_are_clean(self):
        py = [("hangar/hangar.py",
               "def hangar_get_stats(cid, f):\n    return 0\n"
               "def _hangar_bump(a, k, n):\n    return 0\n")]
        self.assertEqual(codes(namespace_lint_project(py)), [])

    def test_lint_allow_comment_suppresses(self):
        py = [("consoles/r.py", "def _is_creditable(x):  # lint: allow ns-generic-name\n    return True\n")]
        self.assertEqual(codes(namespace_lint_project(py)), [])

    def test_nested_def_is_not_a_global(self):
        """Only column-0 defs become MAST globals."""
        py = [("a/x.py", "def a_outer():\n    def get_inner():\n        return 1\n    return get_inner\n")]
        self.assertEqual(codes(namespace_lint_project(py)), [])


if __name__ == "__main__":
    unittest.main()
