"""One place AMD failures are reported, so they stop being silent.

Until this module, a broken .amd could not fail anything. `document_get_amd_file`
wrapped the parser in a bare `try/except` and turned ANY exception into an empty
document whose title was the exception object; a missing file printed "no file"
to stdout; and every fence error the parser collected was thrown away, because
the runtime never passed a collector. Meanwhile the warnings that DID get logged
went to loggers named `quest` / `action` / `cutscene` / `media`, and `Mast` only
attaches a FileHandler to `mast.compile` and `mast.runtime` -- so nothing landed
anywhere the harness looks. The net result was a mission that rendered a blank
panel and reported PASS.

Three things fix that, and they are deliberately different severities:

* an ERROR (the document did not parse) goes to the `mast.runtime` logger, which
  is the one logger with a FileHandler on mast.runtime.log -- that is what lets
  MastVerdict.sweep_runtime_log see AMD at all -- and through `on_amd_error`.
* a WARNING (one field, one fence line) goes to the `amd` logger and NOT to
  mast.runtime.log, because sweep_runtime_log treats any content in that file as
  a failed run and the shipped corpus has legitimate warnings in it.
* `strict` re-raises instead of returning a stub document. Dev and --test only.

`on_amd_error` is a seam in the same shape as `Mast.on_compile_error` and
`MastScheduler.on_runtime_error`: None in the shipped engine, so the cost in the
game is one `is not None` check, and cosmos_dev hangs its verdict off it.
"""
import logging

# Set by cosmos_dev (see cosmos_dev/verdict.py). Signature:
#     on_amd_error(message, file_path, line, severity)
on_amd_error = None

# When True, the readers RAISE instead of degrading to a stub document. The game
# must never set this -- a raise inside a GUI present takes the frame down -- but
# a headless --test wants the traceback.
strict = False


def amd_error(message, file_path=None, line=None, severity="error"):
    """Report one AMD problem. Never raises; honoring `strict` is the caller's job,
    because only the caller knows whether it has a sane value to return instead."""
    # A line number is useful even when the text was handed in as `content=` and
    # there is no path to name -- that is the in-game case, and 'line 4' is still
    # the difference between a findable problem and an unfindable one.
    if file_path and line:
        where = f"{file_path}:{line}"
    elif file_path:
        where = str(file_path)
    elif line:
        where = f"line {line}"
    else:
        where = ""
    text = f"AMD {severity}: {where}: {message}" if where else f"AMD {severity}: {message}"
    try:
        if severity == "error":
            logging.getLogger("mast.runtime").error(text)
        else:
            logging.getLogger("amd").warning(text)
    except Exception:
        pass
    cb = on_amd_error
    if cb is not None:
        try:
            cb(message, file_path, line, severity)
        except Exception:
            # A broken listener must not turn a reportable problem into a crash.
            pass
    return text


def amd_warn(message, file_path=None, line=None):
    """Shorthand for the field/fence-level severity."""
    return amd_error(message, file_path, line, severity="warning")
