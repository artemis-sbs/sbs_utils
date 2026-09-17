"""The relic linter's WEB rules: what cannot be flown to, said at author time.

Every other relic rule reads the text. These three build the ruin's rail web the way the
game will and report what came out - so "part of this relic is unreachable" stops being
something a player discovers and becomes a line number.

Each fixture here is a relic that LOOKS fine. That is the point: a disconnected ruin
builds, dresses and runs, and the only symptom is a destination that quietly refuses.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

from sbs_utils.procedural.amd_lint import amd_lint


def _by_code(findings, code):
    return [f for f in findings if f.code == code]


HEAD = "# [Relics](relics)\n\n## [Relics](relics)\n\n"


def relic(parts, key="ruin", extra=""):
    """One relic and its parts, in the shape an author writes."""
    out = [HEAD, "### [The Ruin](%s)\n---\nAtmosphere: purple\n%s---\nprose\n\n"
           % (key, extra)]
    for name, body in parts:
        out.append("### [%s](%s)\n---\nRelic: %s\n%s---\nprose\n\n"
                   % (name.replace("_", " "), name, key, body))
    return "".join(out)


class ARuinInPieces(unittest.TestCase):
    def test_two_rooms_that_never_touch_are_reported(self):
        doc = relic([
            ("west", "Box: -3000, 0, 0, 400, 400, 400\n"),
            ("east", "Box: 3000, 0, 0, 400, 400, 400\n"),
            ("mouth", "Point: -3000, 0, 0\nRoles: entrance\n"),
            ("far", "Point: 3000, 0, 0\n"),
        ])
        got = _by_code(amd_lint(content=doc), "relic-disconnected")
        self.assertEqual(len(got), 1, "a ruin in two halves linted clean")
        self.assertIn("separate pieces", got[0].message)

    def test_rooms_that_ABUT_are_reported_too(self):
        """THE ONE THAT SHIPPED. `sink`'s inlet ended at x=-2400 and its basin BEGAN at
        x=-2400 - a containment test calls that one connected space, because a point on
        the plane is inside both, so the relic read as flyable while its only way in was
        sealed. Boxes must OVERLAP.
        """
        doc = relic([
            ("inlet", "Box: -1200, 0, 0, 1200, 300, 300\n"),
            ("basin", "Box: 1200, 0, 0, 1200, 300, 300\n"),
            ("mouth", "Point: -1200, 0, 0\nRoles: entrance\n"),
            ("deep", "Point: 1200, 0, 0\n"),
        ])
        got = _by_code(amd_lint(content=doc), "relic-disconnected")
        self.assertTrue(got, "a zero-thickness join linted clean")

    def test_an_overlapping_pair_is_clean(self):
        """The control. A rule that fires on everything is not a rule."""
        doc = relic([
            ("inlet", "Box: -1100, 0, 0, 1200, 300, 300\n"),
            ("basin", "Box: 1100, 0, 0, 1200, 300, 300\n"),
            ("mouth", "Point: -1100, 0, 0\nRoles: entrance\n"),
            ("deep", "Point: 1100, 0, 0\n"),
        ])
        findings = amd_lint(content=doc)
        self.assertEqual(_by_code(findings, "relic-disconnected"), [])
        self.assertEqual(_by_code(findings, "relic-unreachable-node"), [])


class APlaceNobodyCanGetTo(unittest.TestCase):
    def test_a_point_in_a_room_off_on_its_own(self):
        doc = relic([
            ("hall", "Box: 0, 0, 0, 1600, 300, 300\n"),
            ("vault", "Box: 0, 4000, 0, 300, 300, 300\n"),
            ("mouth", "Point: -1500, 0, 0\nRoles: entrance\n"),
            ("prize", "Point: 0, 4000, 0\n"),
        ])
        got = amd_lint(content=doc)
        codes = [f.code for f in got]
        self.assertTrue("relic-unreachable-node" in codes or
                        "relic-disconnected" in codes,
                        "a sealed vault with the prize in it linted clean")

    def test_a_reachable_point_is_not_reported(self):
        doc = relic([
            ("hall", "Box: 0, 0, 0, 1600, 300, 300\n"),
            ("mouth", "Point: -1500, 0, 0\nRoles: entrance\n"),
            ("prize", "Point: 1500, 0, 0\n"),
        ])
        self.assertEqual(_by_code(amd_lint(content=doc), "relic-unreachable-node"), [])


class ABarrierWithNoWayThrough(unittest.TestCase):
    #: A hall with a hatch across the middle. No loop, so shutting it cuts the ruin.
    SEALED = [
        ("hall", "Box: 0, 0, 0, 2400, 200, 200\n"),
        ("mouth", "Point: -2300, 0, 0\nRoles: entrance\n"),
        ("far side", "Point: 2300, 0, 0\n"),
    ]

    def test_a_hard_lock_with_nothing_to_open_it_is_reported(self):
        doc = relic(self.SEALED + [("hatch", "Barrier: 0, 0, 0, 300\n")])
        got = _by_code(amd_lint(content=doc), "relic-barrier-seals")
        self.assertEqual(len(got), 1, "a ruin locked shut forever linted clean")
        self.assertIn("hatch", got[0].message)

    def test_a_barrier_that_can_be_CUT_is_fine(self):
        """A shut way is a puzzle when something can open it, and a bug when nothing can.
        The rule is about the difference."""
        doc = relic(self.SEALED + [
            ("hatch", "Barrier: 0, 0, 0, 300\nClear with: beam\n")])
        self.assertEqual(_by_code(amd_lint(content=doc), "relic-barrier-seals"), [])

    def test_a_barrier_that_OPENS_on_a_signal_is_fine(self):
        doc = relic(self.SEALED + [
            ("hatch", "Barrier: 0, 0, 0, 300\nOpens when: signal power_restored\n")])
        self.assertEqual(_by_code(amd_lint(content=doc), "relic-barrier-seals"), [])

    def test_a_hard_lock_with_a_LONG_WAY_ROUND_is_fine(self):
        """This is the shape the whole feature is for: two ways there, one of them shut.
        Nothing is sealed off, so there is nothing to report."""
        doc = relic([
            ("hall", "Box: 0, 0, 0, 2400, 200, 200\n"),
            ("wleg", "Box: -2400, 0, 900, 200, 200, 900\n"),
            ("eleg", "Box: 2400, 0, 900, 200, 200, 900\n"),
            ("loop", "Box: 0, 0, 1700, 2400, 200, 200\n"),
            ("mouth", "Point: -2300, 0, 0\nRoles: entrance\n"),
            ("far side", "Point: 2300, 0, 0\n"),
            ("hatch", "Barrier: 0, 0, 0, 300\n"),
        ])
        self.assertEqual(_by_code(amd_lint(content=doc), "relic-barrier-seals"), [])


class ASecretNobodyCanFind(unittest.TestCase):
    """`Hidden:` is measured against the role MARKER a point gets, so a hidden point with
    no `Roles:` is never revealed - and it fails in complete silence: the relic builds, the
    place is on the web, a route passes through it, and it is simply never offered.

    Measured 2026-09-17: with `Roles:` the place appears the moment a suit comes within
    1200 units of it; without, it never appears at all.
    """

    HALL = ("hall", "Box: 0, 0, 0, 1600, 300, 300\n")
    MOUTH = ("mouth", "Point: -1500, 0, 0\nRoles: entrance\n")

    def test_hidden_with_no_roles_is_reported(self):
        doc = relic([self.HALL, self.MOUTH,
                     ("cache", "Point: 1200, 0, 0\nHidden: yes\n")])
        got = _by_code(amd_lint(content=doc), "relic-hidden-unreachable")
        self.assertEqual(len(got), 1, "a secret nobody can ever find linted clean")
        self.assertIn("cache", got[0].message)

    def test_hidden_WITH_roles_is_fine(self):
        doc = relic([self.HALL, self.MOUTH,
                     ("cache", "Point: 1200, 0, 0\nRoles: treasure\nHidden: yes\n")])
        self.assertEqual(_by_code(amd_lint(content=doc), "relic-hidden-unreachable"), [])

    def test_an_ordinary_point_with_no_roles_is_fine(self):
        """Only a HIDDEN point needs a marker. A visible place is on the list from the
        start and has nothing to be revealed."""
        doc = relic([self.HALL, self.MOUTH, ("corner", "Point: 1200, 0, 0\n")])
        self.assertEqual(_by_code(amd_lint(content=doc), "relic-hidden-unreachable"), [])


class TheRulesDoNotBreakTheRestOfTheLinter(unittest.TestCase):
    def test_a_relic_with_no_geometry_is_skipped_quietly(self):
        """The structural rules already report an unbuildable relic; a second complaint
        about the same line helps nobody."""
        doc = relic([("mouth", "Point: 0, 0, 0\nRoles: entrance\n")])
        findings = amd_lint(content=doc)
        self.assertEqual(_by_code(findings, "relic-disconnected"), [])
        self.assertEqual(_by_code(findings, "parse-skipped"), [])

    def test_the_new_fields_are_not_unknown_fields(self):
        """`Barrier:`, `Hidden:`, `Opens when:` and `Clear with:` have to be in the
        schema, or every relic that uses one collects a warning for it."""
        doc = relic([
            ("hall", "Box: 0, 0, 0, 1600, 300, 300\n"),
            ("mouth", "Point: -1500, 0, 0\nRoles: entrance\n"),
            ("cache", "Point: 1500, 0, 0\nHidden: yes\n"),
            ("hatch", "Barrier: 0, 0, 0, 200\nOpens when: signal x\nClear with: beam\n"),
        ], extra="Rail step: 300\n")
        unknown = [f for f in amd_lint(content=doc)
                   if f.code in ("unknown-field", "unknown-label")]
        self.assertEqual(unknown, [], "the new relic fields are not in the schema")


if __name__ == "__main__":
    unittest.main()
