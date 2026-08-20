"""data_set linter: the shape that raises on a real bridge, and what must stay quiet."""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.blob_lint import blob_lint


def codes(findings):
    return [f.code for f in findings]


# The lines as they shipped in LM maps/florbin_case.mast, which crashed a real session
# with "argument of type 'NoneType' is not iterable" (fixed in LM c1be07f).
FLORBIN = """===== fb_scanning_cargo_containers ======
    for p in role("__player__"):
        n = get_science_selection(p)
        sel_so = to_object(n)
        if sel_so is not None:
            if n and has_roles(n, "suspect"):
                scan_tabs = sel_so.data_set.get("scan_type_list",  0)
                dist = scan_tabs and sbs.distance_id(p, n)
                if "Hold 1" not in scan_tabs and dist <= 600:
                    follow_route_select_science(p,n)
"""


class TestBlobLint(unittest.TestCase):
    def test_the_bug_that_shipped(self):
        f = blob_lint(content=FLORBIN)
        self.assertEqual(codes(f), ["blob-unguarded-none"])
        self.assertEqual(f[0].line, 7)                 # the READ, where the fix goes
        self.assertIn("scan_type_list", f[0].message)
        self.assertIn("line 9", f[0].message)          # names the line that raises

    def test_the_fix_is_quiet(self):
        fixed = FLORBIN.replace('get("scan_type_list",  0)', 'get("scan_type_list",  0) or ""')
        self.assertEqual(codes(blob_lint(content=fixed)), [])

    def test_ordering_comparison(self):
        src = ('== m ==\n'
               '    fuel_value = p_obj.data_set.get("fuel_value", 0)\n'
               '    if fuel_value < 1000:\n'
               '        refuel()\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_procedural_wrapper_is_read_too(self):
        src = ('== m ==\n'
               '    cur = get_data_set_value(tid, "system_damage", sysidx)\n'
               '    if cur < 1:\n'
               '        cur = 1\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_guard_at_the_use_is_not_a_finding(self):
        """ai/grid_brains.mast already writes this - flagging it would be the first false
        positive, and one is enough to get a rule ignored."""
        src = ('== m ==\n'
               '    length = obj.data_set.get("path_len", 0)\n'
               '    if length is not None and length < 0.01:\n'
               '        stop()\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_equality_is_not_a_finding(self):
        """`None == "docked"` is False, which is the right answer - and this shape is
        everywhere (every dock_state read in LM)."""
        src = ('== m ==\n'
               '    dock_status = p_obj.data_set.get("dock_state", 0)\n'
               '    if dock_status == "docked":\n'
               '        arrive()\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_a_new_label_ends_the_watch(self):
        """Task variables do not cross a label, so neither does the rule - the `count`
        below is a different variable from the one read above it."""
        src = ('== a ==\n'
               '    count = obj.data_set.get("shield_count", 0)\n'
               '== b ==\n'
               '    if count < 3:\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_reassignment_with_a_coalesce_clears_it(self):
        src = ('== m ==\n'
               '    v = obj.data_set.get("energy", 0)\n'
               '    v = obj.data_set.get("energy", 0) or 0\n'
               '    if v < 30:\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_lint_allow_suppresses(self):
        src = ('== m ==\n'
               '    # lint: allow blob-unguarded-none\n'
               '    v = obj.data_set.get("energy", 0)\n'
               '    if v < 30:\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_one_finding_per_read(self):
        """The Florbin block tests the same variable four times over; the author has one
        fix to make, so they get one finding."""
        src = ('== m ==\n'
               '    tabs = obj.data_set.get("scan_type_list", 0)\n'
               '    if "Hold 1" not in tabs:\n'
               '        pass\n'
               '    if "Hold 2" not in tabs:\n'
               '        pass\n'
               '    if "Hold 3" not in tabs:\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_arithmetic_on_the_read_line(self):
        """LM's gamemaster torpedo control: the read raises on its OWN line, so there is
        no later use to walk to. It was only caught by luck (a `< 0` further down)."""
        src = ('== m ==\n'
               '    newCount = get_data_set_value(sel, "Homing_NUM", 0) + count\n')
        f = blob_lint(content=src)
        self.assertEqual(codes(f), ["blob-unguarded-none"])
        self.assertEqual(f[0].line, 2)
        self.assertIn("arithmetically", f[0].message)

    def test_int_of_the_read(self):
        """int(None) raises the same way - the other shape in that same route."""
        src = ('== m ==\n'
               '    curCount = int(get_data_set_value(sel, "Homing_NUM", 0))\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_read_through_an_alias(self):
        """LM's docking refit binds `player_blob = DOCKING_PLAYER.data_set` and reads
        through it - which hid an unguarded `torp_now < torp_max` from the first cut."""
        src = ('== m ==\n'
               '    player_blob = DOCKING_PLAYER.data_set\n'
               '    torp_now = player_blob.get("Homing_NUM", 0)\n'
               '    if torp_now < torp_max:\n'
               '        pass\n')
        f = blob_lint(content=src)
        self.assertEqual(codes(f), ["blob-unguarded-none"])
        self.assertEqual(f[0].line, 3)

    def test_alias_does_not_leak_into_the_next_label(self):
        src = ('== a ==\n'
               '    blob = obj.data_set\n'
               '== b ==\n'
               '    v = blob.get("energy", 0)\n'
               '    if v < 30:\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_augmented_assignment_a_line_later(self):
        """LM docking: `shield_rate = blob.get(...)` then `shield_rate *= coeff`."""
        src = ('== m ==\n'
               '    shield_rate = player_blob.data_set.get("repair_rate_shields", 0)\n'
               '    shield_rate *= shields_coeff\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_handed_to_range(self):
        """`for shield in range(sCount)` - range(None) raises the same way."""
        src = ('== m ==\n'
               '    sCount = obj.data_set.get("shield_count", 0)\n'
               '    for shield in range(sCount):\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_iterating_the_read(self):
        """`for t in _torp_types` where the read never split - iterating None raises."""
        src = ('== m ==\n'
               '    _torp_types = npc_blob.data_set.get("torpedo_types_available", 0)\n'
               '    for torps in _torp_types:\n'
               '        pass\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_to_blob_alias(self):
        """LM grid_comms binds `cur_blob = to_blob(id)` - strict-blob mode found the
        crash there before the rule could see it."""
        src = ('== m ==\n'
               '    cur_blob = to_blob(GRID_SELECTED_ID)\n'
               '    cur_scale = cur_blob.get("icon_scale", 0)\n'
               '    cur_blob.set("icon_scale", cur_scale*2, 0)\n')
        self.assertEqual(codes(blob_lint(content=src)), ["blob-unguarded-none"])

    def test_truthiness_guard_is_not_a_finding(self):
        """collisions/collision.mast: `if not shield_strength: ->END` IS the guard."""
        src = ('== m ==\n'
               '    shield_strength = get_data_set_value(player, "shield_val", idx)\n'
               '    if not shield_strength:\n'
               '        ->END\n'
               '    shield_power = shield_strength * 2\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_isinstance_guard_is_not_a_finding(self):
        """hangar/hangar_loadout.mast checks the TYPE, which covers None too."""
        src = ('== m ==\n'
               '    avail = blob.data_set.get("torpedo_types_available", 0)\n'
               '    if not isinstance(avail, str):\n'
               '        avail = ""\n'
               '    types = [a.strip() for a in avail.split(",")]\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_default_keyword_is_a_coalesce(self):
        """The message recommends `default=`; flagging it would be indefensible."""
        src = ('== m ==\n'
               '    thr = get_data_set_value(sid, "playerThrottle", 0, default=0)\n'
               '    test_expect("caps", thr <= 1.0)\n')
        self.assertEqual(codes(blob_lint(content=src)), [])

    def test_coalesced_arithmetic_is_quiet(self):
        src = ('== m ==\n'
               '    newCount = (get_data_set_value(sel, "Homing_NUM", 0) or 0) + count\n')
        self.assertEqual(codes(blob_lint(content=src)), [])


if __name__ == "__main__":
    unittest.main()
