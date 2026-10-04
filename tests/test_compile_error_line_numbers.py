"""A compile error names the line it is on - also the SECOND error in a file.

Found by the lesson "Just enough MAST". After a line the compiler did not recognize, every
later error in the file was reported one line too high up the page: the writer fixed the
first, looked at the line named for the second, and found nothing wrong with it.

    python -m unittest tests.test_compile_error_line_numbers
"""
import re
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (always import explicitly)
from sbs_utils.mast.mast import Mast

BAD = "// a note written the wrong way"


def error_lines(source):
    mast = Mast()
    errors = mast.compile(source, "story.mast", mast)
    return [int(m.group(1)) for e in errors
            for m in [re.search(r"story\.mast Line (\d+)", str(e))] if m]


class CompileErrorLineNumberTests(unittest.TestCase):
    def test_one_unrecognized_line(self):
        self.assertEqual(error_lines("x = 1\n" + BAD + "\ny = 2\n"), [2])

    def test_a_second_one_two_lines_later(self):
        source = "x = 1\n" + BAD + "\ny = 2\n" + BAD + "\nz = 3\n"
        self.assertEqual(error_lines(source), [2, 4])

    def test_three_in_a_row(self):
        source = "x = 1\n" + BAD + "\n" + BAD + "\n" + BAD + "\nz = 3\n"
        self.assertEqual(error_lines(source), [2, 3, 4])

    def test_with_blank_lines_between(self):
        source = "x = 1\n\n" + BAD + "\n\n\n" + BAD + "\n"
        self.assertEqual(error_lines(source), [3, 6])

    def test_the_last_line_with_no_newline_after_it(self):
        self.assertEqual(error_lines("x = 1\n" + BAD), [2])

    def test_a_different_error_after_it(self):
        # `==` for `=`: a line the compiler reads and Python refuses.
        source = "x = 1\n" + BAD + "\ny = 2\nz = (1,\n"
        lines = error_lines(source)
        self.assertEqual(lines[0], 2)
        self.assertTrue(all(n >= 4 for n in lines[1:]), lines)


if __name__ == "__main__":
    unittest.main()
