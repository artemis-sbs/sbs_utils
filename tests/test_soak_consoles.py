"""`--consoles` / `--clients`: how the engine leg spaces and names its clients.

A console cannot be a client command-line argument -- launch arguments reach only the
SERVER, and a client process never runs `script.py`. The engine's one per-client channel
is `request_client_string`, seeded from a SHARED file before the client starts, so
clients have to be launched one at a time far enough apart that each reads its own value.
These tests pin the spacing rule, because getting it wrong is silent: the consoles simply
come up swapped.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import contextlib
import io
import unittest

from cosmos_dev.tools.mission_soak import (
    parse_consoles, plain_clients, CLIENT_SETTLE, DEFAULT_FIRST_CLIENT)


class TestParseConsoles(unittest.TestCase):
    def test_names_are_spaced_by_the_settle(self):
        """The default spacing is what keeps the shared seed file safe."""
        got = parse_consoles("helm,science,engineering")
        self.assertEqual(["helm", "science", "engineering"], [n for n, _ in got])
        times = [t for _, t in got]
        self.assertEqual(DEFAULT_FIRST_CLIENT, times[0])
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual(b - a, CLIENT_SETTLE)

    def test_explicit_times_are_honored_and_sorted(self):
        got = parse_consoles("engineering@40,helm@1,science@20")
        self.assertEqual([("helm", 1.0), ("science", 20.0), ("engineering", 40.0)], got)

    def test_too_close_still_parses_but_warns(self):
        """Honored, not silently corrected -- but the caller is told."""
        with _capture() as out:
            got = parse_consoles("helm@1,science@2")
        self.assertEqual([("helm", 1.0), ("science", 2.0)], got)
        self.assertIn("may swap consoles", out.getvalue())

    def test_whitespace_and_empties_are_ignored(self):
        self.assertEqual(["helm", "science"],
                         [n for n, _ in parse_consoles(" helm , , science ")])

    def test_nothing_means_no_clients(self):
        self.assertEqual([], parse_consoles(""))
        self.assertEqual([], parse_consoles(None))

    def test_a_bad_time_is_refused_not_guessed(self):
        with self.assertRaises(SystemExit):
            parse_consoles("helm@soon")


class TestPlainClients(unittest.TestCase):
    def test_count_gives_unnamed_clients_on_the_same_spacing(self):
        """No name means nothing is seeded, so the shared file is never touched."""
        got = plain_clients(3)
        self.assertEqual([None, None, None], [n for n, _ in got])
        times = [t for _, t in got]
        self.assertEqual(DEFAULT_FIRST_CLIENT, times[0])
        for a, b in zip(times, times[1:]):
            self.assertGreaterEqual(b - a, CLIENT_SETTLE)

    def test_zero_and_negative_are_no_clients(self):
        self.assertEqual([], plain_clients(0))
        self.assertEqual([], plain_clients(-2))


@contextlib.contextmanager
def _capture():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


if __name__ == "__main__":
    unittest.main()
