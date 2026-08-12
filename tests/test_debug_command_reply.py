"""A debug command POSTed over HTTP can get the runner's real answer back.

The mock GUI server queues a POSTed command and replies `{"ok":true}` immediately, while
the runner's actual reply travels the /debug WEBSOCKET - which an HTTP caller is not on.
So `{"error": "no story is running yet"}` was unreachable by the tool that asked, and a
command that failed looked exactly like one that worked. The relic editor's Preview button
spent a session looking broken for precisely this reason.

`"wait": true` opts a caller into the answer: the command is tagged, the reply is matched
off the frame pump, and the HTTP body carries it. These tests drive the matching directly -
no sockets, no subprocess - which is why the two helpers exist as module functions rather
than inline code in the request handler.
"""
import asyncio
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mockgui import server


class DebugReplyMatchingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server._pending_replies.clear()

    async def asyncTearDown(self):
        server._pending_replies.clear()

    async def test_a_matching_reply_reaches_the_waiter(self):
        fut = server._debug_reply_future("abc")
        self.assertTrue(server._resolve_debug_reply(
            {"cmd": "debug_status", "_rid": "abc", "error": "no story is running yet"}))
        self.assertEqual((await fut)["error"], "no story is running yet")

    async def test_someone_elses_reply_is_left_alone(self):
        fut = server._debug_reply_future("abc")
        self.assertFalse(server._resolve_debug_reply({"cmd": "debug_status", "_rid": "xyz"}))
        self.assertFalse(fut.done())

    async def test_an_untagged_frame_resolves_nothing(self):
        """Every frame the runner emits passes through the pump - a /debug tab pressing
        pause, a status broadcast. None of those are anyone's answer."""
        fut = server._debug_reply_future("abc")
        for frame in ({"cmd": "debug_status", "ack": "sim paused"},
                      {"cmd": "gui_text", "clientID": 0}, None, "not a dict"):
            self.assertFalse(server._resolve_debug_reply(frame))
        self.assertFalse(fut.done())

    async def test_a_second_reply_does_not_explode_on_a_settled_future(self):
        # The runner may reply more than once for one command; the first wins and the
        # rest must be inert rather than raising InvalidStateError inside the pump.
        fut = server._debug_reply_future("abc")
        server._resolve_debug_reply({"_rid": "abc", "ack": "first"})
        self.assertFalse(server._resolve_debug_reply({"_rid": "abc", "ack": "second"}))
        self.assertEqual((await fut)["ack"], "first")

    async def test_a_waiter_that_times_out_leaves_nothing_behind(self):
        fut = server._debug_reply_future("abc")
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(fut, 0.01)
        server._pending_replies.pop("abc", None)      # what the request handler's finally does
        self.assertEqual(server._pending_replies, {})

    async def test_the_frame_still_goes_to_the_debug_page(self):
        """Resolving must not CONSUME the reply - the /debug tab shows every frame, and
        a command answered over HTTP should still appear there."""
        server._debug_reply_future("abc")
        payload = {"cmd": "debug_status", "_rid": "abc", "ack": "rebuilt"}
        server._resolve_debug_reply(payload)
        self.assertEqual(payload["ack"], "rebuilt")   # untouched, still forwardable


if __name__ == "__main__":
    unittest.main()
