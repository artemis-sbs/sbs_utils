"""Determinism enabler: settings_seed_apply seeds the one global RNG that every
sbs_utils random draw funnels through (module-level random.* AND the
`from random import ...` bindings in vec/scatter).  See AUTOPLAY_PLAN.md."""
import random
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.settings import settings_seed_apply
from sbs_utils.vec import Vec3
from sbs_utils import scatter


def _draws():
    """A sequence touching every binding style the library uses."""
    return [
        random.random(),                       # module-level global instance
        random.randint(0, 1_000_000),
        Vec3.rand_in_sphere(5000).x,           # vec.py: `from random import uniform`
        [v.x for v in scatter.box(5, 0, 0, 0, 1000, 1000, 1000)],  # scatter.py binding
    ]


class TestSettingsSeed(unittest.TestCase):
    def test_returns_the_seed_applied(self):
        self.assertEqual(settings_seed_apply(42), 42)

    def test_same_seed_reproduces_all_sources(self):
        settings_seed_apply(12345)
        first = _draws()
        settings_seed_apply(12345)
        second = _draws()
        self.assertEqual(first, second)

    def test_different_seeds_diverge(self):
        settings_seed_apply(1)
        a = _draws()
        settings_seed_apply(2)
        b = _draws()
        self.assertNotEqual(a, b)

    def test_zero_picks_a_concrete_nonzero_seed(self):
        # 0 / falsy means "don't care" -> a fresh seed is generated and returned
        # so the run is reproducible after the fact.
        s = settings_seed_apply(0)
        self.assertIsInstance(s, int)
        self.assertNotEqual(s, 0)

    def test_returned_random_seed_reproduces(self):
        s = settings_seed_apply(0)     # picks a random seed s
        after = _draws()
        settings_seed_apply(s)         # replay it
        self.assertEqual(after, _draws())

    def test_none_uses_seed_value_setting(self):
        # With the default settings (seed_value == 0) None resolves to a fresh
        # concrete seed rather than crashing or returning None.
        s = settings_seed_apply(None)
        self.assertIsInstance(s, int)
        self.assertNotEqual(s, 0)


if __name__ == "__main__":
    unittest.main()
