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
from sbs_utils.procedural.terrain import (
    _neb_colors, terrain_nebula_icon_color, terrain_spawn_nebula_sphere,
    NEB_ICON_PEAK, NEB_ICON_FALLBACK_COLOR)


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
        have to hand-pick an icon that agrees with it."""
        teal = {"display_text": "teal", "emission_red": 0.0,
                "emission_green": 0.8, "emission_blue": 1.0}
        self.assertEqual(self._icon_of_spawned(teal), terrain_nebula_icon_color(teal))

    def test_an_explicit_icon_is_left_alone(self):
        """Naming one is a deliberate override, not an omission -- backward compatible
        with any mission already passing a full dict."""
        custom = {"display_text": "signal", "emission_red": 1.0,
                  "emission_green": 0.0, "emission_blue": 0.0,
                  "radar_color_override": "#00ff00"}
        self.assertEqual(self._icon_of_spawned(custom), "#00ff00")

    def test_a_named_color_reaches_the_blob(self):
        self.assertEqual(self._icon_of_spawned("purple"),
                         _neb_colors["purple"]["radar_color_override"])


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
