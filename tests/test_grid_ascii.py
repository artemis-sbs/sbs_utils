"""Ship interiors as ASCII floor plans: read, written, and checked.

The acceptance test is `test_every_shipped_interior_round_trips` - all 40 authored ships
render to ASCII and read back with identical semantics. That is the honest measure of
whether the format can express what the game already contains; a ship that will not
round-trip means the FORMAT is under-designed, not that the ship is special.

The format deliberately carries no mirroring and no scale. Both have measured reasons
recorded in `GRID_ASCII_FORMAT.md`: a half-map mirror corrupts 16.9% of the shipped cells
(it deletes `tsn_light_cruiser`'s saloon and turns a `beam-starboard` into a second
`beam-port`, changing what the ship survives), and icons are center-anchored on a node so
scale could never express room extent.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.procedural.grid_ascii import (GridAsciiError, grid_ascii_parse,
                                             grid_ascii_render, grid_ascii_validate)
from sbs_utils.procedural.grid_rooms import grid_room_roles


def _norm(objects):
    """Semantic identity: position, room, and the SET of roles.

    Case and role ORDER are excluded deliberately. Roles are lowercased by `add_role`, and
    the name is a tooltip - so `Impulse` and `impulse` are the same ship. Role order does
    matter for which icon is drawn, but that is the renderer's business and is checked by
    the registry preserving order, not here.
    """
    return {(int(o["x"]), int(o["y"]), o["name"].strip().lower(),
             frozenset(t.strip().lower() for t in o["roles"].split(",")))
            for o in objects}


class TestRoundTrip(unittest.TestCase):
    def test_every_shipped_interior_round_trips(self):
        from sbs_utils.procedural.grid import grid_get_grid_data
        from sbs_utils.procedural.ship_data import get_ship_data_for
        from cosmos_dev.mock import hull_capture

        checked = 0
        for key, entry in grid_get_grid_data().items():
            objs = entry.get("grid_objects") or []
            data = get_ship_data_for(key)
            if not objs or not data or not data.get("internalmapw"):
                continue
            w, h = int(data["internalmapw"]), int(data["internalmaph"])
            text = grid_ascii_render(key, objs, w, h,
                                     open_cells=hull_capture.captured_cells(key, w, h))
            back = grid_ascii_parse(text)
            checked += 1
            self.assertEqual((back["w"], back["h"]), (w, h), f"{key}: size changed")
            self.assertEqual(_norm(back["entry"]["grid_objects"]), _norm(objs),
                             f"{key}: semantics changed through the round trip")
        self.assertGreater(checked, 35, "the authored corpus did not load")

    def test_a_hull_whose_last_rows_are_empty_keeps_its_height(self):
        """The trailing-blank-row trap. Several hulls (xim_scout, pirate_brigantine) are
        entirely off-hull in their last rows, so those lines render blank. Trimming them
        as "end of file" silently shortens the grid - a ship one row shorter than shipData
        says, with nothing to show for it."""
        text = ("ship: t\nsize: 3x5\nlegend:\n  a: cargo\n---\n"
                "aaa\n...\n   \n\n\n")
        got = grid_ascii_parse(text)
        self.assertEqual((got["w"], got["h"]), (3, 5))
        self.assertEqual(len(got["entry"]["grid_objects"]), 3)


class TestParsing(unittest.TestCase):
    HEAD = "ship: test_ship\nsize: 4x2\nlegend:\n  c: cargo\n---\n"

    def test_roles_come_from_the_registry(self):
        got = grid_ascii_parse(self.HEAD + "cc..\n....")
        self.assertEqual(got["entry"]["grid_objects"][0]["roles"],
                         grid_room_roles("cargo"))

    def test_the_legend_can_override_roles(self):
        text = ("ship: t\nsize: 2x1\nlegend:\n  p: plunder-hold / room,bay,cargo\n---\npp")
        objs = grid_ascii_parse(text)["entry"]["grid_objects"]
        self.assertEqual(objs[0]["name"], "plunder-hold")
        self.assertEqual(objs[0]["roles"], "room,bay,cargo")

    def test_an_unknown_room_without_roles_is_an_error(self):
        """Better to refuse than to invent roles: a room with the wrong ones counts toward
        the wrong system pool, and nothing downstream would complain."""
        with self.assertRaises(GridAsciiError) as e:
            grid_ascii_parse("ship: t\nsize: 1x1\nlegend:\n  z: no-such-room\n---\nz")
        self.assertIn("no-such-room", str(e.exception))

    def test_an_unknown_map_character_is_an_error(self):
        """The tile map SKIPS unknown characters. Here that would silently delete a room,
        so it is an error - the one deliberate divergence from that convention."""
        with self.assertRaises(GridAsciiError) as e:
            grid_ascii_parse(self.HEAD + "cQ..\n....")
        self.assertIn("'Q'", str(e.exception))

    def test_a_duplicate_legend_key_is_an_error(self):
        with self.assertRaises(GridAsciiError):
            grid_ascii_parse("ship: t\nsize: 1x1\nlegend:\n  c: cargo\n  c: brig\n---\nc")

    def test_reserved_characters_cannot_be_legend_keys(self):
        for ch in (".", " "):
            with self.assertRaises(GridAsciiError):
                grid_ascii_parse(f"ship: t\nsize: 1x1\nlegend:\n  {ch!s}: cargo\n---\nc")

    def test_a_missing_separator_is_an_error(self):
        with self.assertRaises(GridAsciiError):
            grid_ascii_parse("ship: t\nsize: 1x1\nlegend:\n  c: cargo\n")

    def test_hallway_and_off_hull_produce_no_objects(self):
        got = grid_ascii_parse(self.HEAD + "....\n    ")
        self.assertEqual(got["entry"]["grid_objects"], [])

    def test_comments_and_blank_header_lines_are_ignored(self):
        got = grid_ascii_parse("# a comment\nship: t\n\nsize: 2x1\nlegend:\n"
                               "  c: cargo\n---\ncc")
        self.assertEqual(len(got["entry"]["grid_objects"]), 2)

    def test_theme_and_layout_carry_through(self):
        got = grid_ascii_parse("ship: t\nlayout: systems\ntheme: PirateTest\n"
                               "size: 1x1\nlegend:\n  c: cargo\n---\nc")
        self.assertEqual(got["layout"], "systems")
        self.assertEqual(got["entry"]["theme"], "PirateTest")


class TestRendering(unittest.TestCase):
    def test_legend_omits_roles_the_registry_already_knows(self):
        objs = [{"x": 0, "y": 0, "name": "cargo", "roles": grid_room_roles("cargo")}]
        text = grid_ascii_render("t", objs, 1, 1)
        self.assertIn("cargo", text)
        self.assertNotIn("/", text.split("---")[0])

    def test_legend_spells_out_roles_that_differ(self):
        objs = [{"x": 0, "y": 0, "name": "cargo", "roles": "room,cabin,brig"}]
        self.assertIn("/ room,cabin,brig", grid_ascii_render("t", objs, 1, 1))

    def test_confusable_characters_are_not_both_used(self):
        """This is a format people EDIT. A misread character does not look wrong - it puts
        a room in a different damage pool."""
        names = ["Impulse", "saloon", "officers-mess", "Workshop", "sensors", "shuttle"]
        objs = [{"x": i, "y": 0, "name": n, "roles": grid_room_roles(n) or "room"}
                for i, n in enumerate(names)]
        text = grid_ascii_render("t", objs, len(names), 1)
        used = {line.strip()[0] for line in text.split("---")[0].splitlines()
                if line.startswith("  ") and ":" in line}
        for group in ("Il1|", "O0o"):
            self.assertLessEqual(len(used & set(group)), 1,
                                 f"both {used & set(group)} used - confusable")

    def test_off_hull_cells_render_as_space(self):
        cells = [[False, True], [True, True]]
        text = grid_ascii_render("t", [], 2, 2, open_cells=cells)
        rows = text.split("---\n")[1].splitlines()
        self.assertTrue(rows[0].startswith(" "))
        self.assertEqual(rows[1], "..")

    def test_render_is_stable(self):
        objs = [{"x": 0, "y": 0, "name": "cargo", "roles": grid_room_roles("cargo")},
                {"x": 1, "y": 0, "name": "brig", "roles": grid_room_roles("brig")}]
        self.assertEqual(grid_ascii_render("t", objs, 2, 1),
                         grid_ascii_render("t", objs, 2, 1))


class TestValidator(unittest.TestCase):
    def test_a_room_outside_the_hull_is_an_error(self):
        cells = [[False, True]]
        objs = [{"x": 0, "y": 0, "name": "cargo", "roles": "room,bay,cargo"}]
        levels = [lvl for lvl, _ in grid_ascii_validate(objs, 2, 1, cells)]
        self.assertIn("error", levels)

    def test_a_room_off_the_grid_is_an_error(self):
        objs = [{"x": 9, "y": 0, "name": "cargo", "roles": "room,bay,cargo"}]
        self.assertIn("error", [lvl for lvl, _ in grid_ascii_validate(objs, 2, 1)])

    def test_asymmetry_is_a_hint_not_an_error(self):
        """17% of shipped rooms have no port/starboard counterpart, so treating this as an
        error would bury an author in false positives."""
        objs = [{"x": 0, "y": 0, "name": "saloon", "roles": "room,cabin,saloon"}]
        issues = grid_ascii_validate(objs, 3, 1)
        self.assertTrue(any(lvl == "hint" and "counterpart" in m for lvl, m in issues))
        self.assertNotIn("error", [lvl for lvl, _ in issues])

    def test_redefining_a_known_room_is_a_hint(self):
        objs = [{"x": 0, "y": 0, "name": "cargo", "roles": "room,cabin,brig"}]
        self.assertTrue(any(lvl == "hint" and "normally means" in m
                            for lvl, m in grid_ascii_validate(objs, 1, 1)))

    def test_missing_system_nodes_are_warned(self):
        ship = {"tubecount": 2, "hull_port_sets": {"beam Primary": [{}, {}]}}
        objs = [{"x": 0, "y": 0, "name": "cargo", "roles": "room,bay,cargo"}]
        msgs = [m for lvl, m in grid_ascii_validate(objs, 1, 1, None, ship) if lvl == "warn"]
        self.assertTrue(any("beam" in m for m in msgs))
        self.assertTrue(any("torpedo" in m for m in msgs))
        self.assertTrue(any("sensor" in m for m in msgs))

    def test_a_dense_ship_is_not_warned_about(self):
        """Measured against the ENGINE hull the shipped ships run 54-100%, median 74% -
        dense is the norm. An earlier 38-75% came from the refuted approximation's larger
        open-cell count, and warning on it flagged a quarter of the fleet."""
        cells = [[True] * 4]
        objs = [{"x": i, "y": 0, "name": "cargo", "roles": "room,bay,cargo"}
                for i in range(3)]
        levels = [lvl for lvl, _ in grid_ascii_validate(objs, 4, 1, cells)]
        self.assertNotIn("warn", levels)

    def test_the_shipped_corpus_has_no_surprises(self):
        """Every error over the shipped ships should be a KNOWN off-hull room. A new error
        class appearing here means the validator or the capture has drifted."""
        from sbs_utils.procedural.grid import grid_get_grid_data
        from sbs_utils.procedural.ship_data import get_ship_data_for
        from cosmos_dev.mock import hull_capture

        offenders = {}
        for key, entry in grid_get_grid_data().items():
            objs = entry.get("grid_objects") or []
            data = get_ship_data_for(key)
            if not objs or not data or not data.get("internalmapw"):
                continue
            w, h = int(data["internalmapw"]), int(data["internalmaph"])
            issues = grid_ascii_validate(objs, w, h,
                                         hull_capture.captured_cells(key, w, h), data)
            n = sum(1 for lvl, _ in issues if lvl == "error")
            if n:
                offenders[key] = n
        self.assertEqual(offenders,
                         {"tsn_missile_cruiser": 17, "science_ship": 5,
                          "starbase_industry": 4, "transport_ship": 2},
                         "the set of off-hull rooms in the shipped data changed")


if __name__ == "__main__":
    unittest.main()
