"""The wear routes must not name library CONSTANTS.

Firing a torpedo threw a runtime error on the bridge:

    NameError: name 'WEAR_PER_TUBE_SHOT' is not defined
    line: 53 in file: wear.mast   label: __route__launch/missile__155__

The constant exists - `internal_damage.py` defines it - but only FUNCTIONS become MAST
globals. A module-level constant named in a `.mast` expression is a NameError every time,
at the moment the route fires, and it reads perfectly until then. Both wear routes did it,
so firing a BEAM crashed the same way.

`grid_wear_shield_hit` and `grid_wear_travel` already looked their own amounts up on the
library side. `grid_wear_beam_hit` and `grid_wear_tube_shot` now do too.
"""
import os
import re
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as mock  # noqa: F401
from sbs_utils.procedural import internal_damage as ID

#: Every wear amount that lives as a module constant. None of these may appear in a
#: `.mast` file, because none of them is reachable from one.
WEAR_CONSTANTS = [n for n in dir(ID) if n.startswith("WEAR_")]

_LM = os.path.join(os.path.dirname(__file__), "..", "..", "LegendaryMissions")


class TestTheHelpersExist(unittest.TestCase):
    def test_a_beam_hit_has_one(self):
        self.assertTrue(callable(ID.grid_wear_beam_hit))

    def test_a_tube_shot_has_one(self):
        self.assertTrue(callable(ID.grid_wear_tube_shot))

    def test_they_take_only_a_ship_and_a_count(self):
        """The amount must NOT be a parameter, or a caller has to name the constant
        again and we are back where we started."""
        import inspect
        for fn in (ID.grid_wear_beam_hit, ID.grid_wear_tube_shot):
            params = list(inspect.signature(fn).parameters)
            self.assertEqual(params, ["ship_id", "count"], fn.__name__)


class TestNoMastFileNamesAConstant(unittest.TestCase):
    """The guard. This is the shape of the bug, not the instance of it."""

    def mast_files(self):
        for root, _dirs, files in os.walk(_LM):
            if ".git" in root:
                continue
            for f in files:
                if f.endswith(".mast"):
                    yield os.path.join(root, f)

    def test_no_wear_constant_is_named_in_a_route(self):
        if not os.path.isdir(_LM):
            self.skipTest("LegendaryMissions is not checked out beside sbs_utils")
        offenders = []
        for path in self.mast_files():
            with open(path, encoding="utf-8", errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    code = line.split("#", 1)[0]
                    for name in WEAR_CONSTANTS:
                        if re.search(r"\b%s\b" % name, code):
                            offenders.append("%s:%d %s" % (os.path.basename(path),
                                                           i, name))
        self.assertEqual(offenders, [], "MAST cannot see these: %s" % offenders)


if __name__ == "__main__":
    unittest.main()
