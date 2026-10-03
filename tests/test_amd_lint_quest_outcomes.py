"""`; completes x` in a hail is a real outcome, and lint knows it in ANY mission.

`accepts`, `completes` and `fails` are registered by `quest_driver` as it imports. The
outcome check loads the boarding verbs itself, which made its registry non-trivial and
turned off its own "cannot judge" guard - but it never loaded the quest verbs. So a plain
mission with no vocabulary file of its own was told:

    `completes` is not an outcome verb, so nothing applies it

about a line that completes the quest. Found by the first dialogue lesson.

IN A FRESH INTERPRETER, and that is the point: any other test that imports `quest_driver`
first registers the verbs for the whole process, and this would then pass with the fix
taken out.

    python -m unittest tests.test_amd_lint_quest_outcomes
"""
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CHILD = r'''
import sys
sys.path.insert(0, sys.argv[1])
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.procedural.amd_lint import amd_lint
DOC = """# [M](m)

## [Dialogue](dialogue)

### [Hello](hello)
---
Speaker: quill
When: hail
---
% Hello.

- [Done]() ; completes ds1_calls
- [Take it]() ; accepts ds1_calls
- [No]() ; fails ds1_calls
- [Typo]() ; compleets ds1_calls
"""
for f in amd_lint(content=DOC, cross_file=False):
    if f.code == "unknown-outcome-verb":
        print("FOUND", f.line, str(f).split("`")[1])
'''


class QuestVerbsAreKnownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run([sys.executable, "-c", CHILD, ROOT],
                             capture_output=True, text=True)
        cls.err = run.stderr
        cls.found = [line.split()[2] for line in run.stdout.splitlines()
                     if line.startswith("FOUND")]

    def test_the_child_ran(self):
        self.assertNotIn("Traceback", self.err)

    def test_the_three_quest_verbs_are_not_reported(self):
        for verb in ("completes", "accepts", "fails"):
            self.assertNotIn(verb, self.found)

    def test_a_misspelled_one_still_is(self):
        self.assertEqual(self.found, ["compleets"])


if __name__ == "__main__":
    unittest.main()
