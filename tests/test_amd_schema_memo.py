"""The schema lookup memo: fast, and identical to the scan it replaces.

_declared is called three times per authored field line (amd_is_declared, then
amd_canonical_label -> _declared_under, then _declared again inside
amd_read_field), and each call walks every declared label in every applicable
table, re-normalizing as it goes. On a 6.5k-line document _norm_label was the
largest single cost in the parser.

A memo over tables that mutate is only safe if EVERY mutation invalidates it, so
most of this file is about invalidation rather than speed. The parity test is the
one that matters: for a memo, "faster" is worthless without "same answer".
"""
import random
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_schema as S


class SchemaMemoBase(unittest.TestCase):
    def setUp(self):
        # Snapshot the registries so a test that registers cannot leak into the
        # next one -- these are module-level and shared across the whole suite.
        self._arch = {k: dict(v) for k, v in S.ARCHETYPES.items()}
        self._traits = {k: dict(v) for k, v in S.TRAITS.items()}
        self._at = dict(S.ARCHETYPE_TRAITS)
        self._sections = dict(S._SECTION_ALIASES)
        S._schema_changed()

    def tearDown(self):
        S.ARCHETYPES.clear(); S.ARCHETYPES.update(self._arch)
        S.TRAITS.clear(); S.TRAITS.update(self._traits)
        S.ARCHETYPE_TRAITS.clear(); S.ARCHETYPE_TRAITS.update(self._at)
        S._SECTION_ALIASES.clear(); S._SECTION_ALIASES.update(self._sections)
        S._schema_changed()


class TestItIsActuallyMemoized(SchemaMemoBase):
    def test_repeated_lookups_do_not_rescan(self):
        calls = []
        real = S._norm_label

        def counting(label):
            calls.append(label)
            return real(label)

        S._norm_label = counting
        try:
            S._declared("Reward", "quest")     # cold: walks the tables
            cold = len(calls)
            calls.clear()
            for _ in range(50):
                S._declared("Reward", "quest")  # warm: one normalize, then a dict hit
            warm = len(calls)
        finally:
            S._norm_label = real
        self.assertGreater(cold, 10, "cold lookup should have scanned")
        self.assertLessEqual(warm, 50, "warm lookups should not rescan the tables")

    def test_a_miss_is_cached_too(self):
        # The undeclared case is the EXPENSIVE one -- it walks every table to the
        # end -- so it is the one most worth caching.
        self.assertIsNone(S._declared("no_such_field_at_all", "quest"))
        self.assertIn(("no_such_field_at_all", "quest", ()), S._DECLARED_MEMO)

    def test_norm_label_cache_is_capped(self):
        for i in range(9000):
            S._norm_label("Label %d" % i)
        self.assertLessEqual(len(S._NORM_CACHE), 8192)

    def test_norm_label_still_correct_for_non_strings(self):
        self.assertEqual(S._norm_label(None), "none")
        self.assertEqual(S._norm_label(12), "12")
        self.assertEqual(S._norm_label(" Fail On Signal "), "fail_on_signal")


class TestEveryRegistrarInvalidates(SchemaMemoBase):
    def test_register_fields(self):
        self.assertIsNone(S._declared("memo_probe_a", "quest"))   # seed a negative
        S.amd_register_fields("quest", {"memo_probe_a": S.text()}, domain="test")
        self.assertIsNotNone(S._declared("memo_probe_a", "quest"))

    def test_register_trait(self):
        self.assertIsNone(S._declared("memo_probe_b", "quest", traits=("memo_trait",)))
        S.amd_register_trait("memo_trait", {"memo_probe_b": S.text()}, domain="test")
        self.assertIsNotNone(S._declared("memo_probe_b", "quest", traits=("memo_trait",)))

    def test_register_archetype_traits(self):
        S.amd_register_trait("memo_trait2", {"memo_probe_c": S.text()}, domain="test")
        self.assertIsNone(S._declared("memo_probe_c", "quest"))   # not implicit yet
        S.amd_register_archetype_traits("quest", ("memo_trait2",))
        self.assertIsNotNone(S._declared("memo_probe_c", "quest"),
                             "an implicit trait added after a lookup stayed invisible")

    def test_declared_under_invalidates_too(self):
        self.assertFalse(S._declared_under("memo_probe_d", "quest"))
        S.amd_register_fields("quest", {"memo_probe_d": S.text()}, domain="test")
        self.assertTrue(S._declared_under("memo_probe_d", "quest"))


class TestParityWithTheColdScan(SchemaMemoBase):
    def test_memo_agrees_with_a_cold_lookup_everywhere(self):
        # The assertion that makes the memo trustworthy: over a wide spread of
        # (label, archetype, traits), the cached answer is the scanned answer.
        rng = random.Random(20260809)
        archetypes = sorted(S.ARCHETYPES) + [None, "not_an_archetype"]
        labels = []
        for table in list(S.ARCHETYPES.values()) + [S.GLOBAL] + list(S.TRAITS.values()):
            labels.extend(list(table)[:8])
        labels += ["Reward", "reward", "Fail On Signal", "fail-on-signal", "",
                   "nope", "Also", "At", "Kind"]
        trait_sets = [(), ("economy",), ("reputation",), ("economy", "reputation"),
                      ["economy"], ("no_such_trait",)]

        checked = 0
        for _ in range(500):
            label = rng.choice(labels)
            arch = rng.choice(archetypes)
            traits = rng.choice(trait_sets)
            warm = S._declared(label, arch, traits)
            S._schema_changed()
            cold = S._declared(label, arch, traits)
            self.assertIs(warm, cold,
                          "memo disagreed for %r / %r / %r" % (label, arch, traits))
            checked += 1
        self.assertEqual(checked, 500)

    def test_list_and_tuple_traits_are_the_same_key(self):
        # lru_cache would have raised TypeError on the list form, at parse time,
        # on an author's file. _traits_key normalizes instead.
        a = S._declared("Reward", "quest", ["economy"])
        b = S._declared("Reward", "quest", ("economy",))
        self.assertIs(a, b)

    def test_trait_case_and_spacing_do_not_split_the_key(self):
        a = S._declared("Reward", "quest", (" Economy ",))
        b = S._declared("Reward", "quest", ("economy",))
        self.assertIs(a, b)


if __name__ == "__main__":
    unittest.main()
