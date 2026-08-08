"""The mock knows a ship's interior SHAPE, so a bad layout can fail a test.

Before this, `cosmos_dev/mock/sbs.py`'s hullmap was a stub: `is_grid_point_open` hardcoded
`return 1`, `w`/`h` stayed 0, `get_objects_at_point` returned `[]`, and both grid-point
finders returned `[0, 0]`. Headless, every ship was a solid rectangle with no interior -
so nothing in the test path could report a room placed outside the hull, and the
room-detection half of the damcon AI was untestable.

The shape comes from the engine, CAPTURED (`hull_capture.py` / `hull_maps.json`) rather
than derived. It was once derived - alpha bounding box, split into
internalmapw x internalmaph, grid row 0 at the bottom - and that rule scored 0.987 against
the authored interiors and was still wrong: measured against the engine it agrees only
0.790. See `GRID_REFERENCE.md` s2. The art-derived path survives as a FALLBACK for hulls
with no capture (a new mod ship), and is known to be wrong in detail.

In the engine none of this runs: `is_grid_point_open` is answered by the engine directly.

No PIL. `sbs_utils` takes no pip packages and `cosmos_dev` does not either, so the PNG
decoder is `zlib` plus the five unfilter predictors - and `test_decoder_reads_a_png_we_
built_ourselves` checks it against a PNG this file constructs, so decoder correctness
does not depend on the game's art being present.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import struct
import unittest
import zlib

import cosmos_dev.mock.sbs as mock
from cosmos_dev.mock import hull_capture, hull_mask


def _make_png(width, height, alpha_rows):
    """Build a minimal RGBA PNG. `alpha_rows` is a list of rows of 0/255."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)                       # filter type 0 (None)
        for x in range(width):
            raw += bytes((255, 255, 255, alpha_rows[y][x]))

    def chunk(tag, body):
        return (struct.pack(">I", len(body)) + tag + body
                + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw)))
            + chunk(b"IEND", b""))


class TestPngDecoder(unittest.TestCase):
    def setUp(self):
        hull_mask.clear_cache()

    def test_decoder_reads_a_png_we_built_ourselves(self):
        """Decoder correctness, independent of the game's art files."""
        rows = [[0, 0, 0, 0],
                [0, 255, 255, 0],
                [0, 255, 255, 0],
                [0, 0, 0, 0]]
        path = os.path.join(os.path.dirname(__file__), "_tmp_hull_mask.png")
        with open(path, "wb") as f:
            f.write(_make_png(4, 4, rows))
        try:
            w, h, alpha = hull_mask.read_alpha(path)
            self.assertEqual((w, h), (4, 4))
            self.assertEqual(alpha, bytes(v for row in rows for v in row))
            self.assertEqual(hull_mask.alpha_bbox(w, h, alpha), (1, 1, 3, 3))
        finally:
            os.remove(path)

    def test_every_png_filter_type_round_trips(self):
        """Sub/Up/Average/Paeth, not just None - real art uses all of them."""
        width = height = 8
        rows = [[255 if (x + y) % 3 else 0 for x in range(width)] for y in range(height)]
        expected = bytes(v for row in rows for v in row)

        for ftype in (0, 1, 2, 3, 4):
            raw = bytearray()
            prev = [0] * (width * 4)
            for y in range(height):
                line = []
                for x in range(width):
                    line += [255, 255, 255, rows[y][x]]
                enc = []
                for i, val in enumerate(line):
                    a = line[i - 4] if i >= 4 else 0
                    b = prev[i]
                    c = prev[i - 4] if i >= 4 else 0
                    if ftype == 0:   pred = 0
                    elif ftype == 1: pred = a
                    elif ftype == 2: pred = b
                    elif ftype == 3: pred = (a + b) >> 1
                    else:
                        p = a + b - c
                        pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                        pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                    enc.append((val - pred) & 0xFF)
                raw.append(ftype)
                raw += bytes(enc)
                prev = line

            def chunk(tag, body):
                return (struct.pack(">I", len(body)) + tag + body
                        + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

            blob = (b"\x89PNG\r\n\x1a\n"
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(bytes(raw)))
                    + chunk(b"IEND", b""))
            path = os.path.join(os.path.dirname(__file__), f"_tmp_filter{ftype}.png")
            with open(path, "wb") as f:
                f.write(blob)
            try:
                _w, _h, alpha = hull_mask.read_alpha(path)
                self.assertEqual(alpha, expected, f"filter type {ftype} decoded wrong")
            finally:
                os.remove(path)

    def test_unreadable_art_reports_unknown_not_solid(self):
        """A missing file must not read as 'this ship has no hull'."""
        self.assertIsNone(hull_mask.open_cells("no_such_art_at_all", 10, 10))


class TestMockHullMap(unittest.TestCase):
    def setUp(self):
        mock.create_new_sim()
        hull_mask.clear_cache()

    def _ship(self, key):
        oid = mock.sim.create_space_object("behav_playership", key, 0x10)
        return oid

    def test_dimensions_come_from_ship_data(self):
        hm = mock.get_hull_map(self._ship("tsn_light_cruiser"))
        self.assertEqual((hm.w, hm.h), (10, 17))
        self.assertEqual(hm.symmetrical_flag, 1)
        self.assertEqual(hm.art_file_root, "tsn_light_cruiser")

    def test_a_hull_has_a_shape_not_a_rectangle(self):
        """The whole point: some cells are outside the ship."""
        hm = mock.get_hull_map(self._ship("tsn_light_cruiser"))
        closed = sum(1 for y in range(hm.h) for x in range(hm.w)
                     if not hm.is_grid_point_open(x, y))
        self.assertGreater(closed, 0, "every cell was open - the mock is still blind")
        open_ = hm.w * hm.h - closed
        self.assertGreater(open_, 0, "no cell was open - the mask is inverted or empty")

    def test_out_of_bounds_is_closed(self):
        hm = mock.get_hull_map(self._ship("tsn_light_cruiser"))
        for x, y in ((-1, 0), (0, -1), (hm.w, 0), (0, hm.h)):
            self.assertEqual(hm.is_grid_point_open(x, y), 0, f"({x},{y}) should be closed")

    def test_a_ship_with_no_interior_stays_permissive(self):
        """Asteroids and pickups have no internalmapw. Absent != solid rock."""
        hm = mock.get_hull_map(self._ship("plain_asteroid_6"))
        self.assertEqual((hm.w, hm.h), (0, 0))
        self.assertEqual(hm.is_grid_point_open(3, 3), 1)

    def test_grid_point_search_returns_an_open_cell(self):
        """It used to return [0,0] always - which is now usually OUTSIDE the hull."""
        sid = self._ship("tsn_light_cruiser")
        hm = mock.get_hull_map(sid)
        loc = mock.find_valid_grid_point_for_vector3(sid, mock.vec3(0.5, 0, 0.5), 5)
        self.assertEqual(len(loc), 2)
        self.assertTrue(hm.is_grid_point_open(loc[0], loc[1]),
                        f"{loc} is not an open cell")

    def test_unoccupied_search_avoids_occupied_cells(self):
        sid = self._ship("tsn_light_cruiser")
        hm = mock.get_hull_map(sid)
        taken = mock.find_valid_grid_point_for_vector3(sid, mock.vec3(0.5, 0, 0.5), 5)

        go = hm.create_grid_object("room", "room", "")
        go.data_set.set("curx", taken[0], 0)
        go.data_set.set("cury", taken[1], 0)

        loc = mock.find_valid_unoccupied_grid_point_for_vector3(
            sid, mock.vec3(0.5, 0, 0.5), 5)
        self.assertNotEqual(loc, taken, "the unoccupied search returned an occupied cell")
        self.assertTrue(hm.is_grid_point_open(loc[0], loc[1]))

    def test_objects_at_point_finds_them(self):
        """Was hardcoded []; damcon room detection depends on this."""
        sid = self._ship("tsn_light_cruiser")
        hm = mock.get_hull_map(sid)
        go = hm.create_grid_object("sick-bay:3,5", "sick-bay:3,5", "")
        go.data_set.set("curx", 3, 0)
        go.data_set.set("cury", 5, 0)

        self.assertEqual(hm.get_objects_at_point(3, 5), [go.unique_ID])
        self.assertEqual(hm.get_objects_at_point(4, 5), [])

    def test_module_delete_grid_object_clears_the_hull_map(self):
        """A grid object must leave the hull map, not just the sim registry.

        `sbs.delete_grid_object` (the module function, which is the one
        `DeleteQueue` calls for every deferred grid delete) used to pop only
        `sim.grid_objects`, leaving the entry on the host's `grid_items`. The
        hull map then kept handing that dead id to `get_objects_at_point`, and
        `grid_take_internal_damage_at` crashed on its `None` blob the next time
        internal damage landed on that cell.
        """
        sid = self._ship("tsn_light_cruiser")
        hm = mock.get_hull_map(sid)
        go = hm.create_grid_object("sick-bay:3,5", "sick-bay:3,5", "")
        go.data_set.set("curx", 3, 0)
        go.data_set.set("cury", 5, 0)
        gid = go.unique_ID

        mock.delete_grid_object(sid, gid)

        self.assertNotIn(gid, mock.sim.grid_objects, "left in the sim registry")
        self.assertEqual(hm.get_objects_at_point(3, 5), [],
                         "deleted grid object is still on the hull map")
        self.assertEqual(hm.get_grid_object_count(), 0)


class TestCapturePrecedence(unittest.TestCase):
    """The capture is the engine's answer and must win over the approximation."""

    def setUp(self):
        hull_mask.clear_cache()
        hull_capture.clear_capture_cache()

    def test_capture_is_used_when_present(self):
        cap = hull_capture.load_capture()
        if not cap:
            self.skipTest("no capture file - run the engine probe")
        key = "tsn_light_cruiser"
        e = cap[key]
        cells = hull_mask.open_cells(e["art"], e["w"], e["h"], ship_key=key)
        expected = [[c == "#" for c in row] for row in e["open"]]
        self.assertEqual(cells, expected, "the capture was not used verbatim")

    def test_capture_differs_from_the_approximation(self):
        """If these ever matched, the capture would be mock output, not engine output.

        Measured: 0.84 agreement, 0 of 63 hulls identical.
        """
        cap = hull_capture.load_capture()
        if not cap:
            self.skipTest("no capture file - run the engine probe")
        key = "tsn_light_cruiser"
        e = cap[key]
        approx = hull_mask.open_cells(e["art"], e["w"], e["h"])          # no ship_key
        captured = hull_mask.open_cells(e["art"], e["w"], e["h"], ship_key=key)
        self.assertNotEqual(approx, captured,
                            "capture equals the approximation - is hull_maps.json a "
                            "MOCK run rather than an engine run?")

    def test_dimension_mismatch_falls_back(self):
        """shipData changed since the capture: the recorded shape is for another grid."""
        cap = hull_capture.load_capture()
        if not cap:
            self.skipTest("no capture file - run the engine probe")
        self.assertIsNone(hull_capture.captured_cells("tsn_light_cruiser", 99, 99))

    def test_uncaptured_hull_falls_back_to_the_art(self):
        cells = hull_mask.open_cells("tsn_light_cruiser", 10, 17,
                                     ship_key="no_such_ship_key")
        self.assertIsNotNone(cells, "fallback did not run for an uncaptured hull")


class TestAgainstTheAuthoredCorpus(unittest.TestCase):
    """Does the hull shape agree with where 3171 hand-placed rooms actually sit?

    Against the ENGINE capture this is 0.9912 - 28 cells across 4 ships
    (`tsn_missile_cruiser` 17, `science_ship` 5, `starbase_industry` 4,
    `transport_ship` 2). That residue is real authoring slop, and much smaller than the
    art-derived approximation made it look: it blamed `science_ship` for 13 cells that
    are in fact inside the engine's hull.
    """

    def test_authored_rooms_land_on_open_cells(self):
        from sbs_utils.procedural.grid import grid_get_grid_data
        from sbs_utils.procedural.ship_data import get_ship_data_for

        hull_mask.clear_cache()
        hull_capture.clear_capture_cache()
        captured = bool(hull_capture.load_capture())
        total = hits = 0
        checked = 0
        for key, entry in grid_get_grid_data().items():
            objs = entry.get("grid_objects") or []
            data = get_ship_data_for(key)
            if not objs or not data or not data.get("internalmapw"):
                continue
            w, h = int(data["internalmapw"]), int(data["internalmaph"])
            cells = hull_mask.open_cells(data.get("artfileroot"), w, h, ship_key=key)
            if cells is None:
                continue
            checked += 1
            for x, y in {(int(o["x"]), int(o["y"])) for o in objs}:
                total += 1
                if 0 <= y < h and 0 <= x < w and cells[y][x]:
                    hits += 1

        self.assertGreater(checked, 30, "the authored corpus did not load")
        ratio = hits / total
        # 0.99 against the engine capture; 0.97 is all the approximation can manage.
        bar = 0.99 if captured else 0.97
        self.assertGreater(ratio, bar,
                           f"only {ratio:.4f} of authored rooms land on open cells "
                           f"(bar {bar}, capture={'yes' if captured else 'no'})")


if __name__ == "__main__":
    unittest.main()


class TestArtFilePath(unittest.TestCase):
    """`hullmap.art_file_path` - engine 1.3.5.

    A FOLDER, working together with `art_file_root` rather than replacing it, resolved
    against the exe directory. Confirmed from the engine team's own example:

        "artfileroot": "tsn_light_cr",
        "artfilepath": "data/missions/BeamArcTest/extraShipGraphicData"

    Worth a test because the mock must actually LOOK there, not just store the string - a
    property that remembers a path and then reads the stock folder anyway would pass a
    smoke test and silently give every modded hull the wrong interior.
    """

    def setUp(self):
        from cosmos_dev.mock import sbs as mock
        self.hull = mock.hullmap()

    def test_defaults_to_empty(self):
        self.assertEqual(self.hull.art_file_path, "")
        self.assertIsNone(self.hull._art_dir(),
                          "empty must mean the stock folder, chosen by open_cells")

    def test_round_trips(self):
        self.hull.art_file_path = "data/missions/Mod/graphics/ships"
        self.assertEqual(self.hull.art_file_path, "data/missions/Mod/graphics/ships")

    def test_none_becomes_empty(self):
        self.hull.art_file_path = None
        self.assertEqual(self.hull.art_file_path, "")
        self.assertIsNone(self.hull._art_dir())

    def test_a_relative_path_resolves_against_the_exe(self):
        from sbs_utils import fs
        self.hull.art_file_path = "data/missions/Mod/graphics/ships"
        resolved = self.hull._art_dir()
        self.assertTrue(resolved.startswith(fs.get_artemis_dir()), resolved)
        self.assertTrue(resolved.endswith(os.path.join("Mod", "graphics", "ships")), resolved)

    def test_an_absolute_path_is_left_alone(self):
        # abspath(), not a bare leading separator. A rooted path with no DRIVE letter
        # (one backslash, then the folders) stopped counting as absolute in Python 3.13:
        # os.path.isabs() returns False for it on Windows now. So the old form quietly
        # became a RELATIVE path on a 3.13+ dev interpreter and got joined onto the exe
        # dir, failing here. abspath gives a genuinely absolute path on either platform,
        # which is what this test was always about.
        #
        # NOTE the engine runs Python 3.11, where the driveless form IS absolute - so the
        # mock and the engine disagree about that one shape. Out of scope here; this test
        # is about 'absolute is passed through', not about which spellings are absolute.
        abs_path = os.path.abspath(os.path.join(os.path.sep, "somewhere", "art"))
        self.hull.art_file_path = abs_path
        self.assertEqual(self.hull._art_dir(), abs_path)

    def test_backslashes_are_accepted(self):
        """It is a path typed by a person on Windows as often as not."""
        self.hull.art_file_path = "data\missions\Mod\ships"
        self.assertTrue(self.hull._art_dir().endswith(os.path.join("Mod", "ships")))


class TestArtFilePathIsActuallyUsed(unittest.TestCase):
    """The property must REDIRECT THE LOOKUP, not just remember a string.

    Written after a mutation check: deleting `ships_dir=self._art_dir()` from the
    `open_cells` call left all six `TestArtFilePath` tests passing. Those exercise the
    resolver in isolation, so a hullmap that stores the path and then reads the stock
    folder anyway looked perfectly healthy - every modded hull would silently get the wrong
    interior, or none.

    So this drives the real entry point, `is_grid_point_open`, with art that exists ONLY in
    a temp folder. Set the path and the mask is read; clear it and the art cannot be found,
    which `open_cells` reports as unknown and the hullmap answers permissively.
    """

    @staticmethod
    def _write_png(path, width, height, opaque):
        """Minimal 8-bit RGBA PNG: `opaque(x, y)` decides the alpha. stdlib only."""
        import struct, zlib
        raw = bytearray()
        for y in range(height):
            raw.append(0)                                   # filter 0
            for x in range(width):
                raw += bytes((255, 255, 255, 255 if opaque(x, y) else 0))

        def chunk(kind, body):
            return (struct.pack(">I", len(body)) + kind + body
                    + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))

        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n"
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                    + chunk(b"IEND", b""))

    def setUp(self):
        import tempfile
        from cosmos_dev.mock import sbs as mock
        from cosmos_dev.mock import hull_mask
        hull_mask.clear_cache()                 # or a previous test's mask answers for ours
        self.dir = tempfile.mkdtemp(prefix="artpath_")
        # Solid with a HOLE punched in the middle. Not "left half solid": the mask is fit
        # to the alpha BOUNDING BOX, so a half-empty image just yields a narrower bbox and
        # every cell still lands inside it - the first version of this test failed for
        # exactly that reason. A hole keeps the bbox full-size and makes the centre differ
        # from the edges.
        self._write_png(os.path.join(self.dir, "mod_only_hull1024.png"), 64, 64,
                        lambda x, y: not (20 <= x < 44 and 20 <= y < 44))
        self.hull = mock.hullmap()
        self.hull.art_file_root = "mod_only_hull"    # deliberately absent from the install
        self.hull._w, self.hull._h = 8, 8

    def tearDown(self):
        import shutil
        from cosmos_dev.mock import hull_mask
        hull_mask.clear_cache()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_the_mask_is_read_from_art_file_path(self):
        self.hull.art_file_path = self.dir
        edge = self.hull.is_grid_point_open(0, 0)
        middle = self.hull.is_grid_point_open(4, 4)
        self.assertEqual(edge, 1, "the corner is solid art and should read open")
        self.assertEqual(middle, 0,
                         "the centre is a transparent hole - if this reads open, the mask "
                         "was never loaded from art_file_path")

    def test_without_the_path_the_art_is_not_found(self):
        self.hull.art_file_path = ""
        # The root exists nowhere in the stock folder, so open_cells returns None and the
        # hullmap stays permissive rather than declaring a ship solid rock.
        self.assertEqual(self.hull.is_grid_point_open(6, 4), 1)
