"""No widget builds a $text: value by hand-quoting an interpolation.

A dynamic value has to reach the engine through ``gui_text_escape``. Writing the
backticks inline instead -- ``f"$text:`{name}`;"`` -- is correct only while the
value is non-empty and carries no backtick of its own:

* an EMPTY value collapses to ``$text:``;`` and the engine draws the lone
  delimiter as a visible ` (issue #641), which is then the first character the
  player's typing has to work around;
* a value CONTAINING a backtick closes the quote early, so the rest of it is
  parsed as style properties (issue #569).

``gui_text_escape`` handles both -- "" for empty, delimiter stripped -- so this
scans the library for the hand-quoted form rather than trusting each new call
site to remember. A literal is fine (``$text:`prev`;``); only an interpolation
is flagged.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import unittest

LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sbs_utils")


def _hand_quoted_sites():
    """(path, line number, text) for every ``$text:`...{`` in the library."""
    hits = []
    for root, dirs, files in os.walk(LIB):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", errors="replace") as f:
                for n, line in enumerate(f, 1):
                    i = 0
                    while True:
                        i = line.find("$text:`", i)
                        if i == -1:
                            break
                        start = i + len("$text:`")
                        close = line.find("`", start)
                        inner = line[start:close] if close != -1 else line[start:]
                        if "{" in inner:
                            hits.append((os.path.relpath(path, LIB), n, line.strip()))
                        i = start
    return hits


class TestGuiTextQuoting(unittest.TestCase):
    def test_no_hand_quoted_interpolation(self):
        hits = _hand_quoted_sites()
        self.assertEqual(
            hits, [],
            "hand-quoted $text: interpolation -- use gui_text_escape(value):\n" +
            "\n".join(f"  {p}:{n}: {t}" for p, n, t in hits))


if __name__ == "__main__":
    unittest.main()
