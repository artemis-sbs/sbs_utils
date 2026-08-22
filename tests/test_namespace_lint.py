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

    def test_generic_name_warns(self):
        py = [("consoles/r.py", "def is_creditable(x):\n    return True\n")]
        f = namespace_lint_project(py)
        self.assertEqual(codes(f), ["ns-generic-name"])
        self.assertEqual(f[0][1].severity, "warning")

    def test_an_underscore_helper_is_private_and_not_linted(self):
        """This test used to assert the OPPOSITE, and it was right to: an underscore def
        was exported exactly like a public one. Both registration paths skip them now
        (2026-08-16), so `_is_creditable` is genuinely unreachable from MAST - warning
        about its name would tell the author to prefix something nothing can call."""
        py = [("consoles/r.py", "def _is_creditable(x):\n    return True\n")]
        self.assertEqual(codes(namespace_lint_project(py)), [])

    def test_an_underscore_helper_cannot_collide_with_a_mast_variable(self):
        """The collision that actually emptied stories: A28's `_mine` against autoplay's
        `_mine = to_object(closest(...))`."""
        py = [("a28_skyboxes/a28.py", "def _mine():\n    return []\n")]
        mast = [("autoplay/auto.mast", "== m ==\n    _mine = 1\n")]
        self.assertEqual(codes(namespace_lint_project(py, mast)), [])

    def test_a_public_name_still_collides(self):
        """The filter narrows what is exported - it does not stop linting what is."""
        py = [("a/x.py", "def mine():\n    return []\n")]
        mast = [("b/y.mast", "== m ==\n    mine = 1\n")]
        self.assertEqual(codes(namespace_lint_project(py, mast)), ["ns-mast-var-collision"])

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

    # --- metadata keys that shadow a builtin (LM #657) ----------------------

    CLOAK = ("=== elite_cloak_start\nmetadata: ```\n"
             "type: elite/cloak\nrange: close or far\n```\n"
             "    for i in range(6):\n        await delay_sim(5)\n")

    def test_metadata_key_shadowing_a_builtin(self):
        """The cloak ability's `range:` is why range() stopped working inside it."""
        f = namespace_lint_project([], [("fleets/elite.mast", self.CLOAK)])
        self.assertEqual(codes(f), ["ns-metadata-shadows-builtin"])
        self.assertEqual(f[0][1].line, 4)                     # the KEY, not the call
        self.assertIn("injected as task variables", f[0][1].message)

    def test_metadata_type_key_is_not_flagged(self):
        """`type:` is on ~96 LM labels and must stay silent. MAST replaces __builtins__
        with its own table, and `type` is not in it - so the key hides nothing, and the
        convention labels_get_type() reads is safe by construction, not by exemption."""
        self.assertEqual(codes(namespace_lint_project(
            [], [("fleets/elite.mast", self.CLOAK.replace("range: close or far", ""))])), [])

    def test_metadata_key_shadowing_the_sim_handle(self):
        """The worst case is not a builtin at all: `sim` is in MAST's globals, so a key
        by that name takes sim.AddTractorConnection away from the whole label."""
        src = "=== m\nmetadata: ``` yaml\nsim: 3\n```\n    sim.AddTractorConnection(a, b)\n"
        self.assertEqual(codes(namespace_lint_project([], [("a/m.mast", src)])),
                         ["ns-metadata-shadows-builtin"])

    def test_metadata_key_that_shadows_nothing_is_quiet(self):
        """`id`, `sum`, `float` and friends are NOT reachable from MAST, so a key by one
        of those names hides nothing and must not be reported."""
        src = "=== m\nmetadata: ``` yaml\nid: 0\nsum: 2\nfloat: 1.0\n```\n    pass\n"
        self.assertEqual(codes(namespace_lint_project([], [("a/m.mast", src)])), [])

    def test_metadata_yaml_fence_is_read(self):
        """LM writes `metadata: ``` yaml`; the bare fence is not the only form."""
        src = ("=== prefab_turret\nmetadata: ``` yaml\ndisplay_text: Turret\nrange: 2500\n```\n"
               "    yield result deploy(range)\n")
        self.assertEqual(codes(namespace_lint_project([], [("turrets/t.mast", src)])),
                         ["ns-metadata-shadows-builtin"])

    def test_metadata_nested_yaml_key_is_not_flagged(self):
        """Only COLUMN-0 keys are injected as variables; nested ones are data."""
        src = ("=== m\nmetadata: ``` yaml\nProperties:\n    list: gui_int_slider()\n```\n    pass\n")
        self.assertEqual(codes(namespace_lint_project([], [("maps/m.mast", src)])), [])

    def test_metadata_shadow_lint_allow_suppresses(self):
        src = self.CLOAK.replace("range: close or far",
                                 "range: close or far  # lint: allow ns-metadata-shadows-builtin")
        self.assertEqual(codes(namespace_lint_project([], [("fleets/elite.mast", src)])), [])

    # --- var= control bindings that shadow a builtin --------------------------
    #
    # The same bug through a different door. A gui control's var= name is written into
    # the TASK scope, and a `Properties:` block (a map's, or a fabrication recipe's) seeds
    # every one of them through set_variable before rendering. Unlike a metadata key,
    # nothing checked it: the nested-YAML rule above deliberately ignores keys below
    # column 0, which is exactly where a Properties grid lives.

    MAP_RANGE = (
        '@map/m "M"\n'
        'metadata: ``` yaml\n'
        'Properties:\n'
        '    Range: \'gui_drop_down("list: near, far", var="range")\'\n'
        '```\n'
        '    for i in range(6):\n'
        '        pass\n')

    def test_var_binding_shadowing_a_builtin(self):
        f = namespace_lint_project([], [("maps/m.mast", self.MAP_RANGE)])
        self.assertEqual(codes(f), ["ns-var-shadows-builtin"])
        self.assertEqual(f[0][1].line, 4)                     # the BINDING, not the loop
        self.assertIn("written into the task scope", f[0][1].message)

    def test_var_binding_in_ordinary_gui_code_is_flagged_too(self):
        """Not just Properties grids - gui_drop_down binds var= to the task the same way."""
        src = '== panel\n    d = gui_drop_down("list: a, b", var="list")\n'
        self.assertEqual(codes(namespace_lint_project([], [("a/p.mast", src)])),
                         ["ns-var-shadows-builtin"])

    def test_var_binding_that_shadows_nothing_is_quiet(self):
        """The overwhelmingly common case: a domain name binds nothing away."""
        src = ('== panel\n    d = gui_drop_down("list: a, b", var="menu")\n'
               '    e = gui_drop_down("list: c, d", var="beacon_range")\n')
        self.assertEqual(codes(namespace_lint_project([], [("a/p.mast", src)])), [])

    def test_var_binding_lint_allow_suppresses(self):
        src = ('== panel\n    d = gui_drop_down("list: a, b", var="list")'
               '  # lint: allow ns-var-shadows-builtin\n')
        self.assertEqual(codes(namespace_lint_project([], [("a/p.mast", src)])), [])

    def test_var_binding_found_in_an_amd_fence(self):
        """The reason this is its own rule: a recipe's Properties block is .amd, which the
        metadata rule never reads. amd_lint calls the same checker once per file."""
        from sbs_utils.procedural.namespace_lint import namespace_lint_var_bindings
        amd = ('# [Sensor Beacon](recipe_beacon_sensor)\n---\nOutput: Beacon\n'
               'Properties:\n'
               '  Range: \'gui_drop_down("list: medium, long", var="range")\'\n---\n')
        found = namespace_lint_var_bindings(amd)
        self.assertEqual([f.code for f in found], ["ns-var-shadows-builtin"])
        self.assertEqual(found[0].line, 5)


if __name__ == "__main__":
    unittest.main()
