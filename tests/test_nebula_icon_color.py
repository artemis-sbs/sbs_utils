"""A nebula's radar icon is derived from the nebula, not maintained beside it.

An entry in `_neb_colors` used to carry two unrelated descriptions of the same cloud: a
hand-written "radar_color_override" hex for the 2D icon, and the emission/scattering/
absorption levers the engine draws with. Nothing tied them together, so retuning either
side desynced them silently -- `red` ended up with a MAGENTA icon over a red cloud, and
every icon drifted ~3x too dark to tell apart on radar.

The icon is now computed from emission, so the two cannot disagree. These tests pin that,
and pin the thing that let the old bug hide: nothing ever checked that the icon and the
cloud still agreed.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import itertools
import math
import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.query import to_data_set
from sbs_utils.procedural import terrain as terrain_mod
from sbs_utils.procedural.terrain import (
    _neb_colors, terrain_nebula_icon_color, terrain_spawn_nebula_sphere,
    NEB_ICON_PEAK, NEB_ICON_FALLBACK_COLOR, NEB_ICON_VAL_MIN, NEB_ICON_VAL_MAX)


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


def _rgb(hex_str):
    return (int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16))


def _emission(entry):
    return [entry["emission_red"], entry["emission_green"], entry["emission_blue"]]


def _hue(hex_str):
    """Hue alone -- what the jitter must never move."""
    import colorsys
    r, g, b = (c / 255.0 for c in _rgb(hex_str))
    return colorsys.rgb_to_hsv(r, g, b)[0]


def _value(hex_str):
    import colorsys
    r, g, b = (c / 255.0 for c in _rgb(hex_str))
    return colorsys.rgb_to_hsv(r, g, b)[2]


def _normalized(chans):
    top = max(chans)
    return [c / top for c in chans] if top else [0.0, 0.0, 0.0]


class TestDerivation(unittest.TestCase):
    """The icon says what the cloud is."""

    def test_icon_channels_match_emission_ratios(self):
        """The whole point: icon hue IS the cloud's emission hue. That is what the old
        hand-written table could not promise -- red's icon was [0.97, 0.20, 1.00] over a
        [1.0, 0.3, 0.1] cloud."""
        for name, entry in _neb_colors.items():
            with self.subTest(color=name):
                icon = _normalized(list(_rgb(entry["radar_color_override"])))
                cloud = _normalized(_emission(entry))
                for chan, i, c in zip("rgb", icon, cloud):
                    self.assertAlmostEqual(
                        i, c, delta=0.02,
                        msg=f"{name}: icon {chan} channel {i:.3f} != cloud {c:.3f}")

    def test_every_icon_is_bright_enough_to_read(self):
        """The old icons peaked at 0x44-0x63 -- near-black on a dark radar, which is how
        an orange cluster and a purple one became the same smudge."""
        for name, entry in _neb_colors.items():
            with self.subTest(color=name):
                self.assertEqual(max(_rgb(entry["radar_color_override"])), NEB_ICON_PEAK,
                                 f"{name} does not peak at {NEB_ICON_PEAK:#04x}")

    def test_red_is_red_not_magenta(self):
        """The specific regression: 0ae545ea rewrote red's cloud to [1.0, 0.3, 0.1] and
        carried its icon line across byte-identical, leaving the magenta inherited from
        LegendaryMissions' 2025 '#e0e'."""
        r, g, b = _rgb(_neb_colors["red"]["radar_color_override"])
        self.assertGreater(r, b, "red's icon still has more blue than red -- magenta")
        self.assertGreater(r, g)

    def test_derivation_is_pure(self):
        """Same input, same answer -- no RNG left in the icon. The old table drew every
        icon from color_noise() at import time."""
        entry = _neb_colors["orange"]
        self.assertEqual(terrain_nebula_icon_color(entry),
                         terrain_nebula_icon_color(entry))
        self.assertEqual(terrain_nebula_icon_color("orange"),
                         entry["radar_color_override"])

    def test_no_emission_says_so_instead_of_inventing_a_hue(self):
        self.assertEqual(terrain_nebula_icon_color({}), NEB_ICON_FALLBACK_COLOR)
        self.assertEqual(terrain_nebula_icon_color(
            {"emission_red": 0, "emission_green": 0, "emission_blue": 0}),
            NEB_ICON_FALLBACK_COLOR)
        self.assertEqual(terrain_nebula_icon_color(None), NEB_ICON_FALLBACK_COLOR)


class TestCallerSuppliedColors(unittest.TestCase):
    """cluster_color accepts a caller's own dict; it gets the same rule."""

    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())

    def tearDown(self):
        DeleteQueue.clear()
        FrameContext.context = None

    def _icon_of_spawned(self, color):
        nebula = terrain_spawn_nebula_sphere(0, 0, 0, 2000, 1.0,
                                             cluster_color=color, marker=False)[0]
        return to_data_set(nebula).get("radar_color_override")

    def test_a_hand_built_dict_gets_a_derived_icon(self):
        """A mission writing its own color dict describes the CLOUD; it should not also
        have to hand-pick an icon that agrees with it. The spawned icon carries this
        object's jitter, so it matches the canonical one in HUE, not byte for byte."""
        teal = {"display_text": "teal", "emission_red": 0.0,
                "emission_green": 0.8, "emission_blue": 1.0}
        self.assertAlmostEqual(_hue(self._icon_of_spawned(teal)),
                               _hue(terrain_nebula_icon_color(teal)), delta=0.01)

    def test_an_explicit_icon_is_left_alone(self):
        """Naming one is a deliberate override, not an omission -- backward compatible
        with any mission already passing a full dict. It is NOT jittered either: asking
        for a color should get that color."""
        custom = {"display_text": "signal", "emission_red": 1.0,
                  "emission_green": 0.0, "emission_blue": 0.0,
                  "radar_color_override": "#00ff00"}
        self.assertEqual(self._icon_of_spawned(custom), "#00ff00")

    def test_a_named_color_reaches_the_blob(self):
        self.assertAlmostEqual(_hue(self._icon_of_spawned("purple")),
                               _hue(_neb_colors["purple"]["radar_color_override"]),
                               delta=0.01)

    def test_two_nebulae_in_one_cluster_are_not_identical(self):
        """The point of the jitter: a cluster should read as cloud, not as a stencil."""
        nebulae = terrain_spawn_nebula_sphere(0, 0, 0, 8000, 2.0,
                                              cluster_color="purple", marker=False)
        icons = {to_data_set(n).get("radar_color_override") for n in nebulae}
        self.assertGreater(len(nebulae), 2, "need a real cluster to test variety")
        self.assertGreater(len(icons), 1, "every nebula in the cluster got one icon")
        for icon in icons:
            self.assertAlmostEqual(
                _hue(icon), _hue(_neb_colors["purple"]["radar_color_override"]),
                delta=0.01, msg=f"{icon} drifted off purple's hue")


# Two entries render as a color their NAME does not claim, so honest icons make them
# look alike on radar. This is a defect in the CLOUD (the shader values), not in the
# derivation -- confirmed by running the engine's own raymarch
# (data/graphics/shader-emissivenebula.ps:152-180) over each entry:
#
#     red    emission [1.00, 0.30, 0.10] -> renders [1.00, 0.29, 0.10]
#     orange emission [1.00, 0.28, 0.06] -> renders [1.00, 0.27, 0.05]   same as red
#     yellow emission [0.40, 1.00, 0.30] -> renders [0.41, 1.00, 0.30]   chartreuse
#
# Fixing it means retuning those clouds, which changes what nebulae LOOK like in game --
# a separate, visible call. Listed here so the pair test still guards every OTHER pair,
# and so retuning one surfaces as a failing test that says "update this list".
KNOWN_CLOUD_COLLISIONS = {frozenset(("red", "orange")), frozenset(("yellow", "green"))}
MIN_ICON_SEPARATION = 60.0


class TestColorsAreTellableApart(unittest.TestCase):
    def test_no_new_collisions(self):
        for a, b in itertools.combinations(_neb_colors, 2):
            pair = frozenset((a, b))
            dist = math.dist(_rgb(_neb_colors[a]["radar_color_override"]),
                             _rgb(_neb_colors[b]["radar_color_override"]))
            close = dist < MIN_ICON_SEPARATION
            if pair in KNOWN_CLOUD_COLLISIONS:
                self.assertTrue(
                    close,
                    f"{a}/{b} are {dist:.0f} apart now -- if their clouds were retuned, "
                    f"drop this pair from KNOWN_CLOUD_COLLISIONS")
                continue
            self.assertFalse(
                close,
                f"{a} {_neb_colors[a]['radar_color_override']} and "
                f"{b} {_neb_colors[b]['radar_color_override']} are only {dist:.0f} apart "
                f"-- their clouds render the same color, so one is misnamed")


if __name__ == "__main__":
    unittest.main()


class TestPerObjectJitter(unittest.TestCase):
    """Variety inside a cluster, without moving the color off its name.

    This is what color_noise() was reaching for and never delivered: it ran once, inside
    the dict literal, so every purple nebula in a session shared one value and only the
    NEXT session looked different. The jitter is keyed on the nebula's own random_seed
    instead, which means it draws nothing -- the sower's promise that a queued chunk
    carries no randomness of its own still holds.
    """

    SEEDS = (2, 7, 99, 1234, 40001, 65535, 99999)

    def test_hue_never_moves(self):
        for name, entry in _neb_colors.items():
            canonical = _hue(entry["radar_color_override"])
            for seed in self.SEEDS:
                with self.subTest(color=name, seed=seed):
                    self.assertAlmostEqual(
                        _hue(terrain_nebula_icon_color(entry, seed=seed)), canonical,
                        delta=0.01, msg=f"{name} drifted off its hue at seed {seed}")

    def test_same_seed_same_color(self):
        """Keyed on the object's seed, so a reload paints the same field."""
        entry = _neb_colors["blue"]
        for seed in self.SEEDS:
            self.assertEqual(terrain_nebula_icon_color(entry, seed=seed),
                             terrain_nebula_icon_color(entry, seed=seed))

    def test_different_seeds_actually_differ(self):
        """The failure mode of the thing this replaces -- variance that is not there."""
        entry = _neb_colors["purple"]
        seen = {terrain_nebula_icon_color(entry, seed=s) for s in range(200)}
        self.assertGreater(len(seen), 20, f"only {len(seen)} distinct icons in 200 seeds")

    def test_value_stays_inside_its_band(self):
        """Floored so nothing fades into the radar background, capped so nothing
        outshines the ships and map furniture the peak was chosen to sit under."""
        for name, entry in _neb_colors.items():
            for seed in range(0, 5000, 137):
                with self.subTest(color=name, seed=seed):
                    v = _value(terrain_nebula_icon_color(entry, seed=seed))
                    self.assertGreaterEqual(v, NEB_ICON_VAL_MIN - 0.01)
                    self.assertLessEqual(v, NEB_ICON_VAL_MAX + 0.01)

    def test_seedless_call_is_still_the_canonical_color(self):
        """The table keeps one true color per name; jitter is a per-object view of it."""
        for name, entry in _neb_colors.items():
            self.assertEqual(terrain_nebula_icon_color(entry),
                             entry["radar_color_override"])

    def test_jitter_can_be_turned_off(self):
        """Both knobs to 0 gives back flat, identical icons."""
        sat, val = terrain_mod.NEB_ICON_SAT_JITTER, terrain_mod.NEB_ICON_VAL_JITTER
        terrain_mod.NEB_ICON_SAT_JITTER = 0.0
        terrain_mod.NEB_ICON_VAL_JITTER = 0.0
        try:
            entry = _neb_colors["orange"]
            for seed in self.SEEDS:
                self.assertEqual(terrain_nebula_icon_color(entry, seed=seed),
                                 entry["radar_color_override"])
        finally:
            terrain_mod.NEB_ICON_SAT_JITTER = sat
            terrain_mod.NEB_ICON_VAL_JITTER = val
