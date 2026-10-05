"""reach linter: a line that can never run because the label already ended.

    await task_schedule(spawn_players)
    ->END
    relics_spawn(get_mission_dir_filename("mission.amd"))     # never runs, no error

`->END` ends the task. A line after it, in the same block, compiles and is skipped - and
the author's only evidence is that the thing they added is not in the game. It is the
commonest way a pasted line goes wrong: the end of a map label LOOKS like the place to
add one more line, and `->END` is the last thing there.

One rule: ``mast-unreachable`` (WARNING). Line-based on purpose - it needs no compile, so
it still speaks when the file has other problems, and it reports the first dead line of
each run of them, not every one.

Only an UNCONDITIONAL `->END` counts (`->END if x` falls through), and only lines at the
same indent or deeper: a dedent is a different block (`if x:` / `->END` / back out), and
anything at column 0 is a new label.
"""
import re

from .amd_lint import AmdFinding, WARNING, _source_lines

CODE = "mast-unreachable"

_END = re.compile(r"^(\s+)->\s*END\s*(#.*)?$")
# A line that STARTS a label: a route (`//signal/x`, `///inline`), a `== label ==`, a
# `--- inline` label, or a decorator label (`@map/...`).
_LABEL = re.compile(r"^(//|={2,}|-{3,}\s*\w|@\w+/)")


def _indent(line):
    return len(line) - len(line.lstrip(" \t"))


def reach_lint(file_path=None, content=None):
    """Return [AmdFinding] for the first line after each unconditional `->END` that sits
    in the same block, and so can never run."""
    findings = []
    dead_at = None          # indent of the `->END` that ended this block
    dead_line = 0
    reported = False
    in_text = False         # inside a triple-quoted block: its lines are text, not code
    for number, line in enumerate(_source_lines(file_path, content), 1):
        stripped = line.strip()
        if stripped.count('"""') % 2 == 1:
            in_text = not in_text
            continue
        if in_text or not stripped or stripped.startswith("#"):
            continue
        indent = _indent(line)
        if dead_at is not None:
            if indent < dead_at or _LABEL.match(stripped):
                # Left the block that ended - or a NEW label starts here. A route or a
                # label line begins one wherever it is indented: a recipe card pasted
                # with four spaces in front of it runs (measured), and this said its
                # first line never would.
                dead_at = None
            elif not reported:
                findings.append(AmdFinding(
                    number, WARNING, CODE,
                    f"this line never runs: the label ended at `->END` on line "
                    f"{dead_line}. If this line belongs to that label, move it above "
                    f"line {dead_line}. If line {dead_line} is the end of something you "
                    f"pasted INTO a label, move what you pasted to the end of the file: "
                    f"it cut the label in two"))
                reported = True
                continue
            else:
                continue
        m = _END.match(line)
        if m:
            dead_at, dead_line, reported = len(m.group(1)), number, False
    return findings
