"""The completion proof for the away_* -> boarding_* rename.

A HARD rename has no safety net. There are no aliases, so a name left behind does not
fail to compile - it fails at RUNTIME, on whichever console first reaches the line, as
`NameError: away_choices is not defined`. Three things that normally catch mistakes all
miss it:

* `sbs lint` has no rule for an unknown MAST global (its `ns-*` rules are about
  DUPLICATE and SHADOWING names, not missing ones).
* The headless runner never opens a console page, so `--test` reports PASS.
* The unit suite imports the library directly, so it proves the library is consistent
  with ITSELF and says nothing about the 1000 textual references elsewhere.

So the guard is textual and it is deliberately dumb: no `away_` or `AWAY_` token may
exist anywhere in this repo. Cheap, total, and it fails the moment one comes back - which
is what makes "the rename is finished" a statement with evidence behind it rather than a
hope.

CHANGELOG.md is allowed to keep them: it is a historical record, and rewriting history to
match a rename is how a changelog stops being one.
"""
import io
import os
import re
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `away_foo` / `AWAY_FOO`, plus the player-facing shout `AWAY TEAM`. Plain English
# "away" is untouched - "far away" is not a symbol.
#
# `AWAY TEAM` is here because it is exactly what the first pass MISSED: both symbol
# patterns need an underscore, so the one string every player actually READ - the
# default party title - sailed straight through a clean run of this very test. A
# guard that only looks like a guard is worse than no guard.
GHOST = re.compile(r"\b(away_[a-zA-Z0-9]|AWAY_[A-Z0-9]|AWAY TEAM)")

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", "site", "__lib__"}
SKIP_FILES = {
    "CHANGELOG.md",              # a historical record; see the module docstring
    "test_no_away_namespace.py",  # this file names the ghost in order to hunt it
}
TEXT_SUFFIXES = (".py", ".md", ".mast", ".yml", ".yaml", ".json", ".amd", ".grid", ".html")


def _walk():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name in SKIP_FILES or not name.endswith(TEXT_SUFFIXES):
                continue
            yield os.path.join(root, name)


class NoAwayNamespaceTests(unittest.TestCase):
    def test_no_away_symbol_survives_anywhere_in_the_repo(self):
        found = []
        for path in _walk():
            try:
                text = io.open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if GHOST.search(line):
                    found.append("%s:%d: %s" % (os.path.relpath(path, REPO), n, line.strip()))
        self.assertEqual(
            [], found,
            "away_* survived the rename in %d place(s):\n  %s"
            % (len(found), "\n  ".join(found[:40])))

    def test_the_guard_can_actually_see_one(self):
        """Verified to FAIL on the thing it guards, not merely to pass.

        A pattern that matches nothing passes this suite forever while proving nothing.
        """
        self.assertTrue(GHOST.search("    x = away_choices(client_id)"))
        self.assertTrue(GHOST.search('    set_inventory_value(cid, "AWAY_RETURN", v)'))
        self.assertTrue(GHOST.search('    "title": title or "AWAY TEAM",'))
        self.assertIsNone(GHOST.search("a hunter that took a beat too long, 40km away."))
        self.assertIsNone(GHOST.search("    # scrolled away from the bottom"))


if __name__ == "__main__":
    unittest.main()
