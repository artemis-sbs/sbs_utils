"""The `taught` urge condition: stop explaining once the crew have done it.

An affordance nobody was told about (open comms with NO target selected and there is an
Ultra-Beam list; hail a friendly and you can give it orders) is invisible until a
character mentions it. A character who keeps mentioning it after the crew have used it
is a character the crew learn to tune out - which costs the mission every other line
they have.

So: `Whenever: not taught <lesson>` keeps a nudge alive until the affordance is used,
and `Until: taught <lesson>` retires the urge permanently once it is.

    python -m unittest tests.test_urge_teach
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural import urge as U
from sbs_utils.procedural.urge import (
    urge_teach_note, urge_taught, urge_taught_all, urge_teach_reset,
    urge_condition_eval, urge_conditions, urge_record, urge_add, urge_pick)


class TaughtConditionTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        urge_teach_reset()
        self.actor = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="A"))

    def tearDown(self):
        urge_teach_reset()

    def test_it_is_a_registered_condition(self):
        self.assertIn("taught", urge_conditions())

    def test_unlearned_is_false(self):
        self.assertFalse(urge_taught("ultra_beam"))
        self.assertFalse(urge_condition_eval(self.actor, "taught ultra_beam"))

    def test_noting_makes_it_true(self):
        urge_teach_note("ultra_beam")
        self.assertTrue(urge_taught("ultra_beam"))
        self.assertTrue(urge_condition_eval(self.actor, "taught ultra_beam"))

    def test_the_negated_form_is_what_authors_write(self):
        self.assertTrue(urge_condition_eval(self.actor, "not taught ultra_beam"))
        urge_teach_note("ultra_beam")
        self.assertFalse(urge_condition_eval(self.actor, "not taught ultra_beam"))

    def test_an_unknown_lesson_is_false_not_an_error(self):
        """A lesson nobody has stamped yet is simply not learned. It must NOT log the
        'no urge condition in ...' complaint - the phrase is known, the lesson is not."""
        self.assertFalse(urge_condition_eval(self.actor, "taught nothing_like_this"))

    def test_lessons_are_normalized(self):
        urge_teach_note("  Ultra_Beam  ")
        self.assertTrue(urge_taught("ultra_beam"))

    def test_an_empty_lesson_is_not_recorded(self):
        urge_teach_note("   ")
        self.assertEqual(urge_taught_all(), [])

    def test_it_is_per_mission(self):
        urge_teach_note("ultra_beam")
        urge_teach_reset()
        self.assertFalse(urge_taught("ultra_beam"))

    def test_urge_reset_clears_the_ledger(self):
        """A lesson the LAST crew learned is not one this crew has - carrying it over
        silences the character who exists to teach it, permanently and invisibly."""
        urge_teach_note("ultra_beam")
        U.urge_reset()
        self.assertEqual(urge_taught_all(), [])


class TaughtDrivesAnUrgeTests(unittest.TestCase):
    """The two slots an author actually writes, driven through urge_pick."""

    def setUp(self):
        reset_mock(sbs)
        urge_teach_reset()
        self.actor = to_id(create_enemy(0, 0, 0, "kralien_cruiser", name="A"))

    def tearDown(self):
        urge_teach_reset()

    def _add(self, **kw):
        urge_add(self.actor, urge_record(key="nudge", pool=["say it"], **kw))

    def test_whenever_gates_the_urge(self):
        self._add(whenever="not taught ultra_beam")
        self.assertIsNotNone(urge_pick(self.actor, now=0))
        urge_teach_note("ultra_beam")
        self.assertIsNone(urge_pick(self.actor, now=0))

    def test_whenever_lets_it_speak_again_if_never_learned(self):
        self._add(whenever="not taught ultra_beam")
        self.assertIsNotNone(urge_pick(self.actor, now=0))
        self.assertIsNotNone(urge_pick(self.actor, now=0))

    def test_until_retires_it_permanently(self):
        """`Until:` is a one-way door - retiring is not a cooldown, so a lesson that is
        somehow un-noted later must not bring the character back."""
        self._add(until="taught hail_storm")
        self.assertIsNotNone(urge_pick(self.actor, now=0))
        urge_teach_note("hail_storm")
        self.assertIsNone(urge_pick(self.actor, now=0))
        urge_teach_reset()
        self.assertIsNone(urge_pick(self.actor, now=0))



class EveryCadenceTests(unittest.TestCase):
    """`Every:` as the author wrote it.

    Both of these were silently wrong before, and neither could be seen from a mission:
    an urge that never fires looks exactly like an urge whose condition is false.

    * `Every: 3-5m` - the form the schema hint itself advertises - reached the urge as
      None, because the schema collapsed it with amd_duration_seconds, which cannot read
      a range. Every jittered urge fell back to the 60 second default, so the one thing
      ranges exist for (not sounding like a metronome) was the thing that did not work.
    * `Every: 5m` was converted to 300 by the schema and then read AGAIN as minutes by
      _every, giving 18000 seconds. Five minutes became five hours.
    """

    def _urge(self, spec):
        from sbs_utils.procedural.quest import document_get_amd_file
        from sbs_utils.procedural.amd_urge import urges_from_section
        doc = document_get_amd_file(
            None, "T", content=f"# [C](c)\n\n## [U](u)\n---\nUrge\nEvery: {spec}\n---\n% line\n")
        return urges_from_section(doc.get("children")[0])[0].get("every")

    def test_a_range_in_minutes_survives(self):
        self.assertEqual(self._urge("3-5m"), (180.0, 300.0))

    def test_a_range_reads_its_unit_off_the_whole_string(self):
        """`4-7m` is four-to-seven MINUTES, not four seconds to seven minutes."""
        self.assertEqual(self._urge("4-7m"), (240.0, 420.0))

    def test_minutes_are_not_converted_twice(self):
        self.assertEqual(self._urge("5m"), 300.0)

    def test_seconds_stay_seconds(self):
        self.assertEqual(self._urge("90s"), 90.0)

    def test_a_bare_number_is_minutes(self):
        """The documented convention (amd_duration_seconds): a bare number is minutes."""
        self.assertEqual(self._urge("5"), 300.0)

    def test_a_number_handed_straight_to_every_is_seconds(self):
        """Nothing may multiply an already-converted value by 60 a second time."""
        from sbs_utils.procedural.amd_urge import _every
        self.assertEqual(_every(300), 300.0)
        self.assertEqual(_every(300.0), 300.0)


if __name__ == "__main__":
    unittest.main()
