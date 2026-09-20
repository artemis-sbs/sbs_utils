"""`parse_face` is the inverse of `build_face`, and the avatar editor depends on it.

The editor opened at the feature MINIMUMS every time - a stranger - because it had no way to
start from a face that already existed. `parse_face` is that way, so what it must guarantee
is a ROUND TRIP: parse a face, hand the values straight back to `build_face`, get the same
face. Anything less and pressing Edit Face silently changes how somebody looks before they
have touched a slider.

The None cases matter just as much. The editor falls back to its defaults for each, and each
falls back for a different and correct reason: nothing to resume, nothing parseable, or a mod
face whose atlas is whole drawn busts with no features to take apart.

    python -m unittest tests.test_face_parse_round_trip
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils import faces


class TestRoundTrip(unittest.TestCase):
    def assert_round_trips(self, face):
        parsed = faces.parse_face(face)
        self.assertIsNotNone(parsed, f"parse_face could not read {face!r}")
        rebuilt = faces.build_face(parsed["race"], parsed["values"], parsed["enables"])
        self.assertEqual(rebuilt, face)

    def test_every_stock_race_round_trips(self):
        # Sampled rather than exhaustive - each builder is random, so repeats cover the
        # feature space without pinning any one draw.
        builders = {
            # random_terran() also draws FLUID faces; those get their own test below.
            "terran": faces.random_terran_male,
            "torgoth": faces.random_torgoth,
            "skaraan": faces.random_skaraan,
            "ximni": faces.random_ximni,
            "arvonian": faces.random_arvonian,
            "kralien": faces.random_kralien,
        }
        for race, build in builders.items():
            for _i in range(25):
                face = build()
                with self.subTest(race=race, face=face):
                    self.assert_round_trips(face)

    def test_male_and_female_terran_round_trip(self):
        for build in (faces.random_terran_male, faces.random_terran_female):
            for _i in range(40):
                face = build()
                with self.subTest(face=face):
                    self.assert_round_trips(face)

    def test_a_feminine_terran_round_trips_exactly(self):
        """What the retired "+3 gender column" scheme used to get wrong.

        On the old sheets a feminine face, its eyes, its mouth and its shirt each lived
        three columns right of the masculine one, and eyes and mouth carried that offset
        INDEPENDENTLY of the body - which is what a fluid face was. Un-shifting them by
        the body's gender missed every mismatched pair, and a miss left the value at 0: a
        real index, not an error, so the face parsed "successfully" wearing somebody
        else's features.

        The redrawn sheets have no gender columns at all - body 0 is masculine, body 1
        feminine, and the eye, mouth and clothing art is shared - so the whole class of
        bug is gone rather than fixed. This pins that.
        """
        for _i in range(20):
            female = faces.random_terran_female()
            parsed = faces.parse_face(female)
            rebuilt = faces.build_face(parsed["race"], parsed["values"], parsed["enables"])
            with self.subTest(face=female):
                self.assertEqual(rebuilt, female)
                self.assertEqual(parsed["values"][0], 1, "body should read as feminine")

    def test_a_fluid_terran_face_now_round_trips_exactly(self):
        """The old KNOWN LIMIT, now closed by the redraw.

        Fluid used to have no exact representation: the builder encoded "feminine eyes on
        a masculine body" as `eye_id > eye_count`, and that comparison cannot express
        index 0, so one pair had nowhere to round-trip back to. Opening the avatar editor
        on such a face started it on the non-fluid twin.

        Nothing encodes gender in the eye index any more - it is a choice of POOL when
        rolling a random face and nothing at all once the face exists - so every fluid
        face is now exact. If this ever regresses, the editor is silently editing a
        different person again.
        """
        for _i in range(25):
            face = faces.random_terran_fluid()
            parsed = faces.parse_face(face)
            with self.subTest(face=face):
                self.assertIsNotNone(parsed)
                self.assertEqual(parsed["race"], "terran")
                rebuilt = faces.build_face(parsed["race"], parsed["values"],
                                           parsed["enables"])
                self.assertEqual(rebuilt, face)

    def test_the_parsed_race_names_itself(self):
        # The editor takes the race FROM the face rather than from its caller's guess.
        self.assertEqual(faces.parse_face(faces.random_kralien())["race"], "kralien")
        self.assertEqual(faces.parse_face(faces.random_terran_male())["race"], "terran")


class TestWhatCannotBeResumed(unittest.TestCase):
    """None means "start from the defaults", and the editor relies on that."""

    def test_an_empty_spec(self):
        self.assertIsNone(faces.parse_face(""))
        self.assertIsNone(faces.parse_face(None))

    def test_something_that_is_not_a_face(self):
        self.assertIsNone(faces.parse_face("garbage"))
        self.assertIsNone(faces.parse_face("terran"))

    def test_a_mod_face(self):
        # One whole drawn bust in a mod atlas - no features, nothing to take apart. The
        # editor's sliders cannot express it, so falling back is the honest answer.
        self.assertIsNone(faces.parse_face("tng2 #fff 0 0;"))


if __name__ == "__main__":
    unittest.main()
