"""AMD content creates are keyed by the record's own key.

An AMD record already carries an identity - the `# [Display](key)` heading - so declaring
the same record twice should CONVERGE rather than place a second copy. That matters
because these loaders run from places that can legitimately run more than once: a map
body, a setup signal (`//shared/signal` is server-once per EMIT, not one emit), a
re-entered console start.

Keyed against the live world rather than a did-I-run flag, so a landmark that was
destroyed or a cast that was cleared IS re-created - the deliberate reset still works.
`sides_declare` has behaved this way all along; this brings landmarks and lifeforms in
line.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock
from sbs_utils.procedural.amd_landmarks import (
    landmark_spawn, landmarks_spawn, landmark_object, landmark_key_role,
)
from sbs_utils.procedural.amd_lifeforms import (
    lifeform_from_record, lifeform_of_key, lifeform_key_role,
)
from sbs_utils.procedural.query import to_id, to_id_list
from sbs_utils.procedural.roles import role, has_role
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.mast.mast_node import MastDataObject


def _landmark(key="relay", name="Relay Station"):
    return MastDataObject({
        "key": key, "name": name, "kind": "station", "art": "starbase_1",
        "side": "tsn", "roles": "relay", "loc": (1000, 0, 2000),
    })


def _person(key="doc", name="Doc Harrow"):
    return MastDataObject({"key": key, "name": name, "face": None, "roles": "crew",
                           "color": "green"})


class LandmarkKeyedTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_second_spawn_returns_the_same_object(self):
        first = landmark_spawn(_landmark())
        self.assertIsNotNone(first)
        second = landmark_spawn(_landmark())
        self.assertEqual(to_id(second), to_id(first))
        self.assertTrue(has_role(to_id(first), landmark_key_role("relay")))

    def test_section_rerun_does_not_duplicate(self):
        section = [_landmark("a", "A"), _landmark("b", "B")]
        # landmarks_spawn takes a raw section, so drive landmark_spawn directly here -
        # the identity behaviour is what is under test, not the section parser.
        first = [landmark_spawn(r) for r in section]
        again = [landmark_spawn(r) for r in section]
        self.assertEqual([to_id(o) for o in again], [to_id(o) for o in first])

    def test_distinct_keys_are_distinct_objects(self):
        a = landmark_spawn(_landmark("a", "A"))
        b = landmark_spawn(_landmark("b", "B"))
        self.assertNotEqual(to_id(a), to_id(b))

    def test_destroyed_landmark_is_replaced(self):
        first = landmark_spawn(_landmark())
        delete_object(to_id(first))
        self.assertIsNone(landmark_object("relay"))
        second = landmark_spawn(_landmark())
        self.assertNotEqual(to_id(second), to_id(first))

    def test_artless_record_is_still_skipped(self):
        rec = _landmark()
        rec.art = None
        self.assertIsNone(landmark_spawn(rec))

    def test_keyless_record_still_spawns_every_time(self):
        # No key means no identity to converge on; behaviour is unchanged.
        rec = _landmark(key=None)
        a = landmark_spawn(rec)
        b = landmark_spawn(rec)
        self.assertNotEqual(to_id(a), to_id(b))


class LifeformKeyedTests(unittest.TestCase):
    def setUp(self):
        self.sim = reset_mock(sbs)

    def test_second_cast_returns_the_same_character(self):
        first = lifeform_from_record(_person())
        second = lifeform_from_record(_person())
        self.assertEqual(second.id, first.id)

    def test_same_record_on_two_hosts_makes_two_characters(self):
        # The reason the key includes the host: one crew roster, many stations.
        a = lifeform_from_record(_person(), host_id=101)
        b = lifeform_from_record(_person(), host_id=202)
        self.assertNotEqual(a.id, b.id)
        self.assertEqual(lifeform_of_key("doc", 101).id, a.id)
        self.assertEqual(lifeform_of_key("doc", 202).id, b.id)

    def test_hosted_and_unhosted_are_distinct(self):
        loose = lifeform_from_record(_person())
        hosted = lifeform_from_record(_person(), host_id=101)
        self.assertNotEqual(loose.id, hosted.id)

    def test_distinct_keys_are_distinct_people(self):
        a = lifeform_from_record(_person("doc", "Doc"))
        b = lifeform_from_record(_person("eng", "Eng"))
        self.assertNotEqual(a.id, b.id)

    def test_key_role_includes_the_host(self):
        self.assertNotEqual(lifeform_key_role("doc"), lifeform_key_role("doc", 101))


if __name__ == "__main__":
    unittest.main()
