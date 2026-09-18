"""await-block linter: a plain statement directly inside an `await ...:` block.

The block exists for inline choices - `+`/`*` buttons, `=` inline labels and `on`
handlers, which attach to the await - and the runtime resumes at the block's END, so
any other line there compiles and never runs:

    await delay_sim(5):
        log("done waiting")        # never executed, no error

The MAST compiler already WARNS about this (a warning, not an error, because a story
that compiled before must still compile). This rule surfaces the same warning in
`sbs lint` and the editor. It does not re-implement the check: it compiles the file and
reads the compiler's own records, so the two can never disagree about what counts.

One rule: ``await-block-stray-statement`` (WARNING). Reuses amd_lint's AmdFinding so
`sbs lint` prints these uniformly.
"""
import contextlib
import re
import io
import os

from .amd_lint import AmdFinding, WARNING, _source_lines

CODE = "await-block-stray-statement"

#: A top-level `import x.mast` / `import x.py` line (column 0, like the compiler's).
_IMPORT = re.compile(r"^import\s+\S")


def await_lint(file_path=None, content=None):
    """Return [AmdFinding] for statements that sit directly in an `await ...:` block.

    Compiles the one file with a scratch compiler. Anything else the compile reports
    (an unknown import, an undefined label) is ignored - this rule speaks only to what
    the compiler WARNED about, and only for lines in this file.
    """
    if not any("await" in line for line in _source_lines(file_path, content)):
        return []                                    # cheap: most files have no await
    text = content
    if text is None:
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
    # A lone file's `import x.mast` resolves against nothing, and a failed import ends
    # the compile before the lines this rule is about. Blank them - blank, not removed,
    # so every line number still matches the file.
    text = "\n".join("" if _IMPORT.match(line) else line for line in text.split("\n"))
    from ..mast.mast import Mast
    from ..mast_sbs import story_nodes  # noqa: F401  registers the button/`on` nodes
    name = os.path.basename(file_path) if file_path else "<lint>"
    mast = Mast()
    was = Mast.print_compile_warnings
    Mast.print_compile_warnings = False
    try:
        # A lone file's `import x.mast` lines resolve against nothing and print load
        # errors - noise in a lint report, and not this rule's business.
        with contextlib.redirect_stdout(io.StringIO()):
            mast.compile(text, name, mast)
    except Exception:                                # noqa: BLE001  a lint never crashes
        return []
    finally:
        Mast.print_compile_warnings = was
    findings = []
    for file_name, line_no, message in getattr(mast, "compile_warning_records", []):
        if file_name == name:
            findings.append(AmdFinding(line_no, WARNING, CODE, message))
    return findings
