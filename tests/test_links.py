from cosmos_dev.mock import sbs as sbs
import unittest

from sbs_utils.spaceobject import SpaceObject
from sbs_utils.objects import Npc
from sbs_utils.procedural.links import (
    link, unlink, has_link, linked_to,
    get_dedicated_link, set_dedicated_link, clear_dedicated_link,
)
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.helpers import FrameContext, Context, FakeEvent

test_set_exe_dir()


class TestDedicatedLinks(unittest.TestCase):
    """LM issue 686 - a dedicated link must be clearable, not just replaceable."""

    def setUp(self) -> None:
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.craft = Npc().spawn(0, 0, 0, "Fighter", "tsn", "Battle Cruiser", "behav_npcship")
        self.carrier = Npc().spawn(100, 0, 0, "Carrier", "tsn", "Battle Cruiser", "behav_npcship")
        self.other = Npc().spawn(200, 0, 0, "Other", "tsn", "Battle Cruiser", "behav_npcship")
        return super().setUp()

    def test_set_and_get(self):
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        self.assertEqual(get_dedicated_link(self.craft.id, "my_carrier"), self.carrier.id)

    def test_set_replaces_previous_target(self):
        """A dedicated link holds exactly one target."""
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        set_dedicated_link(self.craft.id, "my_carrier", self.other.id)
        self.assertEqual(get_dedicated_link(self.craft.id, "my_carrier"), self.other.id)
        self.assertEqual(linked_to(self.craft.id, "my_carrier"), {self.other.id})

    def test_set_none_clears_the_link(self):
        """The issue: passing None used to quit early, leaving the link in place."""
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        set_dedicated_link(self.craft.id, "my_carrier", None)
        self.assertIsNone(get_dedicated_link(self.craft.id, "my_carrier"))

    def test_clear_dedicated_link_helper(self):
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        clear_dedicated_link(self.craft.id, "my_carrier")
        self.assertIsNone(get_dedicated_link(self.craft.id, "my_carrier"))

    def test_clear_purges_the_has_link_registry(self):
        """Clearing must not leave the source listed in has_link()."""
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        self.assertIn(self.craft.id, has_link("my_carrier"))
        clear_dedicated_link(self.craft.id, "my_carrier")
        self.assertNotIn(self.craft.id, has_link("my_carrier"))
        self.assertEqual(linked_to(self.craft.id, "my_carrier"), set())

    def test_clear_then_set_again(self):
        """A cleared link is reusable, and re-registers in has_link()."""
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        clear_dedicated_link(self.craft.id, "my_carrier")
        set_dedicated_link(self.craft.id, "my_carrier", self.other.id)
        self.assertEqual(get_dedicated_link(self.craft.id, "my_carrier"), self.other.id)
        self.assertIn(self.craft.id, has_link("my_carrier"))

    def test_clear_when_never_set_is_a_noop(self):
        clear_dedicated_link(self.craft.id, "my_carrier")
        self.assertIsNone(get_dedicated_link(self.craft.id, "my_carrier"))

    def test_clear_leaves_other_links_alone(self):
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        set_dedicated_link(self.craft.id, "home_dock", self.other.id)
        clear_dedicated_link(self.craft.id, "my_carrier")
        self.assertIsNone(get_dedicated_link(self.craft.id, "my_carrier"))
        self.assertEqual(get_dedicated_link(self.craft.id, "home_dock"), self.other.id)

    def test_clear_does_not_affect_other_agents(self):
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        set_dedicated_link(self.other.id, "my_carrier", self.carrier.id)
        clear_dedicated_link(self.craft.id, "my_carrier")
        self.assertEqual(get_dedicated_link(self.other.id, "my_carrier"), self.carrier.id)
        self.assertIn(self.other.id, has_link("my_carrier"))

    def test_unlink_also_clears_a_dedicated_link(self):
        """The issue reports unlink not working on dedicated links."""
        set_dedicated_link(self.craft.id, "my_carrier", self.carrier.id)
        unlink(self.craft.id, "my_carrier", self.carrier.id)
        self.assertIsNone(get_dedicated_link(self.craft.id, "my_carrier"))

    def test_set_none_on_a_missing_source_is_a_noop(self):
        """A bad source id must not raise."""
        set_dedicated_link(999999, "my_carrier", None)


if __name__ == '__main__':
    unittest.main()
