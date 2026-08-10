"""`Action: <actor> hails <scene>` - a beat that opens with an incoming call.

Before this, nothing could START a hail from AMD: every path into the queue went
through `hail_offer`, which is Python/MAST only. A quest step that opens with a call
therefore needed a hand-built `hail_offer` in MAST plus a `//shared/signal/hail` route
to bridge the answer back - boilerplate every mission would rewrite.

The two questions this verb has to answer are WHICH scene and WHO gets called, and both
are covered here. Everything else (title, audio, presentation, the words, the choices)
already came from the scene's fence before this existed.

    python -m unittest tests.test_hail_start
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent, get_story_id, clear_shared
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import amd_action as A
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import hail as H
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.spawn import player_spawn


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


NL = "\n"

SCENES = {
    "ds1_brief": {
        "key": "ds1_brief",
        "data": {"speaker": "ds1", "when": "hail", "title": "Ambassador Kidnapped",
                 "presentation": "portrait", "audio": "audio/ds1"},
        "description": "The ambassador was taken off this station." + NL
                       + "- [Take the case]()" + NL,
    },
    "ds1_market": {
        "key": "ds1_market",
        "data": {"speaker": "ds1", "when": "comms"},
        "description": "What can we sell you?" + NL,
    },
    "quiet": {
        "key": "quiet",
        "data": {"speaker": "nobody_calls", "when": "comms"},
        "description": "Nothing." + NL,
    },
}


class HailsVerbBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        Agent.clear()
        clear_shared()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        H.hail_reset()
        D.dialogue_scenes_registry_clear()
        D.dialogue_register_scenes(SCENES)
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.ship2 = to_id(player_spawn(0, 0, 500, "Hera", "tsn", "battle"))

    def tearDown(self):
        FrameContext.context = None
        H.hail_reset()
        D.dialogue_scenes_registry_clear()

    def pending(self, ship):
        return [r.get("scene") for r in (get_inventory_value(ship, H.KEY_QUEUE, []) or [])]

    def run_action(self, line, actor_id=None):
        return A.amd_action_run(line, actor_id=actor_id)


class WhichScene(HailsVerbBase):
    def test_a_named_scene_is_offered(self):
        self.run_action("DS1 hails ds1_brief")
        self.assertEqual(self.pending(self.ship), ["ds1_brief"])

    def test_the_bare_form_finds_the_speakers_hail_entry(self):
        # `DS1 hails` with no operand - the scene whose Speaker: is ds1 AND whose
        # When: is hail. `ds1_market` is the same speaker on the OTHER door and must
        # not be picked.
        self.run_action("DS1 hails")
        self.assertEqual(self.pending(self.ship), ["ds1_brief"])

    def test_a_speaker_with_no_hail_entry_hails_nobody(self):
        self.assertEqual(self.run_action("nobody_calls hails"), 0)
        self.assertEqual(self.pending(self.ship), [])

    def test_an_unknown_scene_hails_nobody_and_does_not_raise(self):
        # The lint finding's runtime twin. A typo must be a logged no-op, never an
        # exception - one bad direction cannot take the rest of the beat with it.
        self.assertEqual(self.run_action("DS1 hails ds1_breif"), 0)
        self.assertEqual(self.pending(self.ship), [])

    def test_the_SCENE_names_the_speaker_not_the_actor(self):
        # The actor is how the bare form finds a scene; it is not an override. Writing
        # `DS-1` would otherwise file the hail under `ds_1` while the document says
        # `ds1`, and the speaker card would resolve to a stranger.
        self.run_action("DS-1 hails ds1_brief")
        rec = (get_inventory_value(self.ship, H.KEY_QUEUE, []) or [])[0]
        self.assertEqual(rec.get("speaker"), "ds1")


class WhoGetsCalled(HailsVerbBase):
    """The audience is the block's own actor - which is what `Scope:` decides."""

    def test_a_shared_beat_hails_every_player(self):
        # `Scope: shared` runs the block ONCE, on the story agent, so it has to reach
        # everyone or only one bridge hears the call.
        shared = Agent()
        shared.id = get_story_id()
        shared.add()
        self.run_action("DS1 hails ds1_brief", actor_id=shared.id)
        self.assertEqual(self.pending(self.ship), ["ds1_brief"])
        self.assertEqual(self.pending(self.ship2), ["ds1_brief"])

    def test_a_ship_beat_hails_only_that_ship(self):
        # `Scope: ship` already runs the block once per holder, so hailing everyone
        # from each would be one call per ship SQUARED.
        self.run_action("DS1 hails ds1_brief", actor_id=self.ship)
        self.assertEqual(self.pending(self.ship), ["ds1_brief"])
        self.assertEqual(self.pending(self.ship2), [])

    def test_a_non_ship_actor_hails_everyone(self):
        # An urge's actor is the character speaking, not a ship.
        speaker = Agent()
        speaker.id = get_story_id()
        speaker.add()
        self.run_action("DS1 hails ds1_brief", actor_id=speaker.id)
        self.assertEqual(self.pending(self.ship), ["ds1_brief"])
        self.assertEqual(self.pending(self.ship2), ["ds1_brief"])


class WhatArrives(HailsVerbBase):
    def test_the_scenes_fence_comes_with_it(self):
        # Nothing about the hail is written at the call site - this is the whole point
        # of declaring it in the document.
        self.run_action("DS1 hails ds1_brief")
        rec = (get_inventory_value(self.ship, H.KEY_QUEUE, []) or [])[0]
        self.assertEqual(rec.get("title"), "Ambassador Kidnapped")
        self.assertEqual(rec.get("presentation"), "portrait")
        self.assertEqual(rec.get("audio"), "audio/ds1")
        self.assertEqual(rec.get("speaker"), "ds1")

    def test_it_resolves_its_words_from_the_REGISTRY(self):
        # The verb passes no `scenes` dict - there is none to pass. Without the
        # registry fallback the hail would open with no lines and no choices.
        self.run_action("DS1 hails ds1_brief")
        H.hail_accept(self.ship)
        beat = H.hail_beat(self.ship)
        self.assertIn("ambassador", (beat.get("text") or "").lower())
        self.assertEqual([c.label for c in H.hail_choices(self.ship)], ["Take the case"])

    def test_offering_twice_in_one_beat_does_not_stack(self):
        self.run_action("DS1 hails ds1_brief")
        self.run_action("DS1 hails ds1_brief")
        self.assertEqual(self.pending(self.ship), ["ds1_brief"])


if __name__ == "__main__":
    unittest.main()
