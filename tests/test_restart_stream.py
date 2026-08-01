"""Radar-stream identity across a mission RESTART.

The bug class this locks down: the mock reuses one Python interpreter across a
``run_next_mission`` reload where the engine forks a fresh process, so a delta
baseline that survives the reload silently withholds the FULL record a browser
needs in order to draw an object. Space-object ids RECYCLE across
``sim.__init__()``, so a new NPC that inherits a stale baseline entry looks
"already known": it is streamed as pose-only deltas, the browser refuses to
invent identity from a delta, and the ship is invisible/frozen for the whole run.

That reads as "enemies stopped moving on the second run" and is invisible in a
single run - which is why it needs a test, not an eyeball.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import queue as _queue
import unittest

import cosmos_dev.mock.sbs as _base_mock
import cosmos_dev.mockgui.sbs as mockgui


def _spawn_npc(name="Raider"):
    """One active (physics-ticked) NPC the radar push will stream."""
    oid = _base_mock.sim.create_space_object("behav_npcship", "raider", 0x10)
    obj = _base_mock.sim.space_objects[oid]
    obj._side = "raider"
    obj._name = name
    obj._pos = _base_mock.vec3(1000.0, 0.0, 1000.0)
    return oid


class TestRestartStreamIdentity(unittest.TestCase):
    def setUp(self):
        mockgui.gui_queue = _queue.Queue()
        mockgui.create_new_sim()
        mockgui.gui_queue = _queue.Queue()
        mockgui.stream_stats_reset()

    def _radar_msgs(self):
        out = []
        while not mockgui.gui_queue.empty():
            m = mockgui.gui_queue.get_nowait()
            if m.get("cmd") == "radar":
                out.append(m)
        return out

    def _changed(self):
        recs = []
        for m in self._radar_msgs():
            recs.extend(m.get("changed") or [])
        return recs

    @staticmethod
    def _is_full(rec):
        """A record the browser can build an object from (see cmdRadar)."""
        return bool(rec.get("new")) and rec.get("art") is not None

    def test_first_push_sends_a_full_record(self):
        _spawn_npc()
        mockgui._push_radar()
        recs = self._changed()
        self.assertTrue(recs, "the NPC was never streamed at all")
        self.assertTrue(all(self._is_full(r) for r in recs))

    def test_recycled_id_after_restart_still_gets_a_full_record(self):
        first = _spawn_npc()
        mockgui._push_radar()
        self.assertTrue(self._changed())

        # Mission restart: the ids the next world hands out start over.
        mockgui.create_new_sim()
        while not mockgui.gui_queue.empty():
            mockgui.gui_queue.get_nowait()
        second = _spawn_npc()
        self.assertEqual(first, second,
                         "test assumes ids recycle - that is what makes the bug possible")

        mockgui._push_radar()
        recs = self._changed()
        self.assertTrue(recs, "the NPC of the SECOND run was never streamed")
        self.assertTrue(all(self._is_full(r) for r in recs),
                        "recycled id inherited a stale baseline and was streamed as a "
                        "delta the browser cannot draw")

    def test_push_racing_a_restart_is_discarded_not_committed(self):
        """The reset lands MID-PUSH (physics thread vs main thread).

        Forced deterministically: the reload happens while the push is building
        its records. The half-built push describes the previous world, so it must
        neither commit its baseline nor enqueue its message.
        """
        _spawn_npc()
        original = mockgui._quat_of
        state = {"fired": False}

        def _quat_of_reloading(obj):
            if not state["fired"]:
                state["fired"] = True
                mockgui.create_new_sim()      # the racing reload
            return original(obj)

        mockgui._quat_of = _quat_of_reloading
        try:
            mockgui._push_radar()
        finally:
            mockgui._quat_of = original

        self.assertTrue(state["fired"], "the race never fired - test is not exercising anything")
        self.assertEqual(mockgui._stream_stats["dropped_gen"], 1,
                         "a push built against the old world was committed anyway")
        self.assertEqual(sum(len(v) for v in mockgui._last_per_ship.values()), 0,
                         "the stale push re-poisoned the freshly cleared baseline")

        # And the next world streams cleanly.
        _spawn_npc()
        mockgui._push_radar()
        recs = self._changed()
        self.assertTrue(recs and all(self._is_full(r) for r in recs))

    def test_resync_reissues_a_full_record(self):
        """The browser's self-heal path: a lost full record is recoverable."""
        oid = _spawn_npc()
        mockgui._push_radar()
        while not mockgui.gui_queue.empty():
            mockgui.gui_queue.get_nowait()

        # Whatever lost it (a dropped send, a race we have not thought of), the
        # browser reports the orphan and we must re-issue a FULL record.
        n = mockgui.radar_resync_ids([str(oid)])
        self.assertGreaterEqual(n, 1)
        mockgui._push_radar()
        recs = [r for r in self._changed() if r["id"] == str(oid)]
        self.assertTrue(recs, "resync did not produce a new record")
        self.assertTrue(all(self._is_full(r) for r in recs))


if __name__ == "__main__":
    unittest.main()
