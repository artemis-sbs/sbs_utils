"""The 2026-09 face-sheet redraw: layer tables, migration, expressions, animation.

The six stock atlases were REPLACED in place - same aliases, same filenames, different
grids and different meanings per cell. Three things follow, and each is covered here:

  * the layer tables have to agree with the art. A wrong entry does not fail, it draws
    somebody's hat across their chin, so what can be checked mechanically is checked
    mechanically: every declared cell in range, no two features claiming one cell.
  * a face string authored before the redraw has to be translatable, and the result has
    to be a VALID face of the right race - not necessarily the same-looking person,
    because the art is different and no mapping can make it otherwise.
  * expression, viseme and blink swaps must touch ONLY the layer they name. Changing
    somebody's clothes when they frown is the kind of bug nobody reports precisely.

    python -m unittest tests.test_face_redraw
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils import faces


RACES = ("terran", "skaraan", "kralien", "torgoth", "ximni", "arvonian")


class TestLayerTables(unittest.TestCase):
    def test_every_race_names_a_known_sheet(self):
        for race in RACES:
            alias = faces.FACE_LAYERS[race]["alias"]
            with self.subTest(race=race):
                self.assertIn(alias, faces.FACE_SHEETS)

    def test_every_declared_cell_is_on_its_sheet(self):
        """The one table error that is silently invisible: a column or row past the edge
        of the atlas. The compositor skips it, so the layer just never draws."""
        for race in RACES:
            spec = faces.FACE_LAYERS[race]
            cols, rows = faces.FACE_SHEETS[spec["alias"]]
            for layer, (row, columns) in spec["cells"].items():
                with self.subTest(race=race, layer=layer):
                    self.assertTrue(0 <= row < rows, f"row {row} off a {rows}-row sheet")
                    for c in columns:
                        self.assertTrue(0 <= c < cols, f"col {c} off a {cols}-col sheet")

    def test_no_cell_belongs_to_two_features(self):
        """Several rows host two or three features - Terran headwear is hats, eyewear and
        headsets; Ximni row 3 is masks then mouths. They must not overlap, or parse_face
        attributes a layer to whichever feature the dict happened to yield first."""
        for race in RACES:
            seen = {}
            for layer, (row, columns) in faces.FACE_LAYERS[race]["cells"].items():
                for c in columns:
                    with self.subTest(race=race, cell=(c, row)):
                        self.assertNotIn((c, row), seen,
                                         f"{layer} and {seen.get((c, row))} share a cell")
                        seen[(c, row)] = layer

    def test_draw_order_covers_every_layer(self):
        """A layer missing from `order` is never emitted, however carefully it is set."""
        for race in RACES:
            spec = faces.FACE_LAYERS[race]
            with self.subTest(race=race):
                self.assertEqual(set(spec["order"]), set(spec["cells"]),
                                 "order and cells disagree about what this race has")

    def test_a_tinted_layer_has_a_palette(self):
        for race in RACES:
            for layer, kind in faces.FACE_LAYERS[race].get("tint", {}).items():
                with self.subTest(race=race, layer=layer):
                    self.assertTrue(faces.face_tone_names(race, kind),
                                    f"{layer} asks for the {kind} palette, which is empty")

    def test_names_match_their_cell_count(self):
        for race in RACES:
            for layer, names in faces.FACE_LAYERS[race].get("names", {}).items():
                with self.subTest(race=race, layer=layer):
                    self.assertEqual(len(names), faces.face_layer_count(race, layer))

    def test_races_without_a_layer_say_so_rather_than_guessing(self):
        # Torgoth lost its mouth row and Arvonian is eight whole busts. Callers branch on
        # this, so it is a contract, not an accident.
        self.assertEqual(faces.face_layer_count("torgoth", "mouth"), 0)
        self.assertEqual(faces.face_layer_count("arvonian", "eyes"), 0)
        self.assertEqual(faces.face_layer_count("arvonian", "mouth"), 0)
        self.assertIsNone(faces.face_cell("torgoth", "mouth", 0))

    def test_an_out_of_range_index_wraps(self):
        """Every pre-redraw caller passes indices sized for the old sheets. Wrapping is
        what keeps them producing a face instead of raising."""
        n = faces.face_layer_count("skaraan", "eyes")
        self.assertEqual(faces.face_cell("skaraan", "eyes", n + 2),
                         faces.face_cell("skaraan", "eyes", 2))


class TestBuiltFaces(unittest.TestCase):
    def test_every_random_face_is_in_range(self):
        for race in RACES:
            for _i in range(40):
                face = faces.random_face(race)
                with self.subTest(race=race, face=face):
                    self.assertTrue(faces.face_is_valid(face))

    def test_a_built_face_always_has_a_body(self):
        # A face with no body layer is an invisible face - the parts float in the dark.
        for race in RACES:
            face = faces.face_build(race, eyes=0)
            with self.subTest(race=race):
                self.assertTrue(face, "built nothing at all")
                first = faces._parse_face_layers(face)[0]
                self.assertEqual(first["row"], 0, "the body is not the bottom layer")

    def test_an_unknown_race_builds_nothing(self):
        self.assertEqual(faces.face_build("nosuchrace", eyes=1), "")

    def test_the_explicit_builder_is_deterministic(self):
        """terran() must not roll dice. If it does, face_migrate is non-deterministic and
        the source sweep rewrites the same file differently on every run."""
        args = (0, 3, 4, 2, None, 1, None, None, 5, 2)
        self.assertEqual(len({faces.terran(*args) for _ in range(20)}), 1)

    def test_no_tint_is_spelled_the_short_way(self):
        # Every hand-written face string in the tree uses "#fff"; emitting "#ffffff"
        # would make build_face(parse_face(s)) differ from s by characters that mean
        # nothing, and break the round trip the avatar editor depends on.
        self.assertIn("#fff ", faces.face_build("terran", body=0, skin=0))


class TestMigration(unittest.TestCase):
    """A face authored before the redraw."""

    OLD = {
        "terran": "ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;"
                  "ter #fff 3 5;ter #964b00 8 4;",
        "terran_offsets": "ter #492816 0 0;ter #492816 0 2;ter #492816 1 2;"
                          "ter #1E1a33 7 3 6 -2;ter #fff 14 0 14 -2;ter #fff 2 4;"
                          "ter #fff 13 1 20 4;",
        "skaraan": "ska #fff 0 0;ska #fff 0 3;ska #fff 1 5;ska #fff 2 0;ska #fff 1 2;",
        "arvonian": "arv #fff 0 0;arv #fff 0 4;arv #fff 1 6;arv #fff 3 0;arv #fff 1 3;",
        "torgoth": "tor #fff 0 0;tor #fff 0 2;tor #fff 3 1;tor #fff 2 0;tor #fff 1 2;",
        "kralien": "kra #fff 0 0;kra #fff 0 3;kra #fff 1 4;kra #fff 2 0;kra #fff 5 0;",
        "ximni": "zim #fff 0 0;zim #fff 0 2;zim #fff 2 1;zim #fff 3 0;zim #fff 1 1;",
    }

    def test_every_old_face_migrates_to_a_valid_one(self):
        for label, old in self.OLD.items():
            new = faces.face_migrate(old)
            with self.subTest(label=label, new=new):
                self.assertTrue(faces.face_is_valid(new), f"{label} -> {new}")
                self.assertIsNotNone(faces.parse_face(new))

    def test_the_race_survives(self):
        for label, old in self.OLD.items():
            want = old.split()[0]
            with self.subTest(label=label):
                self.assertTrue(faces.face_migrate(old).startswith(want + " "))

    def test_migration_is_deterministic(self):
        """The source sweep rewrites files in place. If this wobbles, running it twice
        produces a different diff and nobody can review it."""
        for label, old in self.OLD.items():
            with self.subTest(label=label):
                self.assertEqual(len({faces.face_migrate(old) for _ in range(10)}), 1)

    def test_a_hand_written_old_face_keeps_its_hair(self):
        """Hand-written strings left the layer offsets off.

        The old builder always emitted hair as "6 -2" and facial hair as "12 4", so the
        parser keys on that - but a face typed into a .mast by hand is just
        "ter #964b00 8 1". Without the coordinate fallback every such character migrated
        bald, which is exactly the kind of loss that reads as "the new art is worse".
        """
        migrated = faces.face_migrate(self.OLD["terran"])
        rows = {lay["row"] for lay in faces._parse_face_layers(migrated)}
        hair_row = faces.FACE_LAYERS["terran"]["cells"]["hair"][0]
        self.assertIn(hair_row, rows, f"hair was dropped: {migrated}")

    def test_distinct_old_faces_stay_distinct(self):
        """Where the new art dropped a feature its index is folded into one that
        survives, so two different-looking old faces do not collapse onto one person."""
        a = faces.face_migrate("arv #fff 0 0;arv #fff 0 1;")
        b = faces.face_migrate("arv #fff 0 0;arv #fff 0 4;")
        self.assertNotEqual(a, b)

    def test_a_mod_face_is_left_alone(self):
        # A mod atlas did not change, so migrating one would be pure damage.
        self.assertEqual(faces.face_migrate("tng2 #fff 3 1;"), "tng2 #fff 3 1;")

    def test_junk_is_returned_unchanged(self):
        for junk in ("", None, "garbage", "terran"):
            self.assertEqual(faces.face_migrate(junk), junk)

    def test_face_is_valid_catches_stale_alien_faces(self):
        # Honest about its limits: the alien sheets lost rows 5-7 so most stale strings
        # are detectable, while Terran's 24x7 still contains nearly every old
        # coordinate. This pins the half that does work.
        self.assertFalse(faces.face_is_valid(self.OLD["skaraan"]))
        self.assertFalse(faces.face_is_valid(self.OLD["arvonian"]))


class TestExpressions(unittest.TestCase):
    def test_every_expression_names_cells_the_race_has(self):
        for race, table in faces.FACE_EXPRESSIONS.items():
            for name, (eye, mouth) in table.items():
                with self.subTest(race=race, expression=name):
                    self.assertIsNotNone(faces.face_cell(race, "eyes", eye))
                    if mouth is None:
                        self.assertEqual(faces.face_layer_count(race, "mouth"), 0,
                                         "a race with mouth art should use it")
                    else:
                        self.assertIsNotNone(faces.face_cell(race, "mouth", mouth))

    def test_an_expression_changes_only_the_eyes_and_mouth(self):
        for race in RACES:
            if not faces.face_expressions(race):
                continue
            base = faces.random_face(race)
            moved = {faces.FACE_LAYERS[race]["cells"][k][0]
                     for k in ("eyes", "mouth") if k in faces.FACE_LAYERS[race]["cells"]}
            for name in faces.face_expressions(race):
                out = faces.face_expression(base, name)
                with self.subTest(race=race, expression=name):
                    self.assertEqual(len(faces._parse_face_layers(out)),
                                     len(faces._parse_face_layers(base)),
                                     "an expression added or dropped a layer")
                    for was, now in zip(faces._parse_face_layers(base),
                                        faces._parse_face_layers(out)):
                        self.assertEqual(was["color"], now["color"], "a tint changed")
                        if was["row"] not in moved:
                            self.assertEqual(was["col"], now["col"],
                                             f"row {was['row']} moved and should not have")

    def test_an_expression_result_is_still_a_valid_face(self):
        for race in RACES:
            for name in faces.face_expressions(race):
                out = faces.face_expression(faces.random_face(race), name)
                with self.subTest(race=race, expression=name):
                    self.assertTrue(faces.face_is_valid(out))

    def test_an_unknown_expression_is_a_no_op(self):
        base = faces.random_terran_male()
        self.assertEqual(faces.face_expression(base, "smouldering"), base)

    def test_arvonian_has_no_expression_and_says_so(self):
        # Its busts are drawn whole - there is no eye or mouth layer to move.
        base = faces.random_arvonian()
        self.assertEqual(faces.face_expressions("arvonian"), [])
        self.assertEqual(faces.face_expression(base, "angry"), base)


class TestAnimation(unittest.TestCase):
    def test_visemes_are_real_mouth_cells(self):
        for race, pool in faces.FACE_VISEMES.items():
            for index in pool:
                with self.subTest(race=race, index=index):
                    self.assertIsNotNone(faces.face_cell(race, "mouth", index))

    def test_talking_cycles_the_mouth_and_nothing_else(self):
        base = faces.random_terran_male()
        mouth_row = faces.FACE_LAYERS["terran"]["cells"]["mouth"][0]
        seen = set()
        for step in range(len(faces.face_visemes("terran"))):
            frame = faces.face_talk_frame(base, step / 7.0)
            for was, now in zip(faces._parse_face_layers(base),
                                faces._parse_face_layers(frame)):
                if was["row"] == mouth_row:
                    seen.add(now["col"])
                else:
                    self.assertEqual(was["col"], now["col"])
        self.assertEqual(len(seen), len(faces.face_visemes("terran")),
                         "the talk cycle repeated instead of using every viseme")

    def test_a_race_with_no_mouth_does_not_flap(self):
        base = faces.random_torgoth()
        self.assertEqual(faces.face_talk_frame(base, 0.3), base)

    def test_blink_shuts_the_eyes_briefly_and_only_the_eyes(self):
        # Built, not rolled. A rolled face could already carry the closed-eye cell, and
        # then "the blink never closed" is true and means nothing - which is exactly how
        # this test failed once, intermittently, for the wrong reason.
        base = faces.face_build("terran", body=0, eyes=1, mouth=0, clothes=0)
        shut = faces.face_blink_frame(base, 0.0)
        open_again = faces.face_blink_frame(base, 1.0)
        self.assertNotEqual(shut, base, "the blink never closed")
        self.assertEqual(open_again, base, "the eyes stayed shut")
        mouth_row = faces.FACE_LAYERS["terran"]["cells"]["mouth"][0]
        for was, now in zip(faces._parse_face_layers(base),
                            faces._parse_face_layers(shut)):
            if was["row"] == mouth_row:
                self.assertEqual(was["col"], now["col"], "a blink moved the mouth")

    def test_only_terran_blinks(self):
        # The alien sheets draw eye COLOURS, not eye expressions - nobody else has a
        # closed-eye cell, and inventing one would shut the wrong feature.
        for race in RACES:
            if race == "terran":
                continue
            base = faces.random_face(race)
            with self.subTest(race=race):
                self.assertEqual(faces.face_blink_frame(base, 0.0), base)


class TestUniform(unittest.TestCase):
    def test_a_crewed_face_is_in_uniform_and_a_civilian_is_not(self):
        self.assertTrue(all(faces.face_in_uniform(faces.random_terran(0, False))
                            for _ in range(30)))
        self.assertFalse(any(faces.face_in_uniform(faces.random_terran(0, True))
                             for _ in range(30)))

    def test_an_undressed_face_is_not_in_uniform(self):
        self.assertFalse(faces.face_in_uniform(faces.face_build("terran", body=0)))

    def test_a_mod_face_is_not_claimed_either_way(self):
        self.assertFalse(faces.face_in_uniform("tng1 #fff 0 0;"))


class TestTints(unittest.TestCase):
    def test_index_zero_is_always_no_tint(self):
        """"No tint" has to keep meaning the face exactly as drawn, or the art as the
        artist made it becomes unreachable from the editor."""
        for race in RACES:
            for kind in ("skin", "hair"):
                if not faces.face_tone_names(race, kind):
                    continue
                with self.subTest(race=race, kind=kind):
                    self.assertEqual(faces.face_tint(race, kind, 0), "fff")

    def test_names_and_tints_line_up(self):
        for race in RACES:
            for kind in ("skin", "hair"):
                with self.subTest(race=race, kind=kind):
                    self.assertEqual(len(faces.face_tone_names(race, kind)),
                                     len(faces.face_tone_tints(race, kind)))

    def test_a_raw_hex_passes_through(self):
        # A caller with its own colour is never second-guessed.
        self.assertEqual(faces.face_tint("terran", "skin", "#a1b2c3"), "a1b2c3")

    def test_every_tinted_race_randomises_its_skin(self):
        """All six, and across the whole palette.

        The five alien randomisers used to leave skin untouched entirely, and Arvonian
        had no palette at all on the reasoning that tinting a painted bust is tinting
        somebody's tattoos - which turned out to be wrong when rendered: the pattern
        takes the tint with the skin and reads as a different coloration of the same
        person. So pressing Randomize now changes somebody's colour whoever they are.
        """
        for race in RACES:
            if faces.FACE_LAYERS[race].get("tint", {}).get("body") != "skin":
                continue
            seen = set()
            for _i in range(200):
                parsed = faces.parse_face(faces.random_face(race))
                for i, f in enumerate(faces.FACE_FEATURES[race]):
                    if f["key"] == "tone:skin":
                        seen.add(parsed["values"][i])
            with self.subTest(race=race):
                self.assertGreater(len(seen), 15,
                                   f"{race} barely varies its skin: {sorted(seen)}")

    def test_the_full_range_includes_the_exotic_tones(self):
        """RANDOM_FULL_TONE_RANGE is the owner's call: the greens and blues are real art
        and a randomiser that never reaches them means nobody ever sees them."""
        self.assertTrue(faces.RANDOM_FULL_TONE_RANGE)
        names = faces.face_tone_names("terran", "skin")
        tints = faces.face_tone_tints("terran", "skin")
        exotic = {tints[i] for i, n in enumerate(names) if n not in faces._NATURAL_SKIN}
        hits = 0
        for _i in range(300):
            body = faces._parse_face_layers(faces.random_terran_male())[0]
            if body["color"] in exotic:
                hits += 1
        self.assertGreater(hits, 0, "a random Terran never reaches the exotic palette")

    def test_turning_the_full_range_off_restores_flesh_tones_only(self):
        """One switch, so a mission that wants a strictly human-looking crew has one
        thing to set - and everything else still reaches every tone."""
        was = faces.RANDOM_FULL_TONE_RANGE
        faces.RANDOM_FULL_TONE_RANGE = False
        try:
            natural = set(faces.face_tone_tints("terran", "skin")[i]
                          for i in faces.face_tone_indices("terran", "skin",
                                                           natural_only=True))
            for _i in range(200):
                body = faces._parse_face_layers(faces.random_terran_male())[0]
                self.assertIn(body["color"], natural | {"fff"})
        finally:
            faces.RANDOM_FULL_TONE_RANGE = was
        # The editor and face_build are unaffected either way.
        self.assertEqual(len(faces.face_tone_names("terran", "skin")), 39)


if __name__ == "__main__":
    unittest.main()
