import logging
import sys


# The multirepo plugin prints unicode (e.g. an emoji) during its git import; on
# Windows the default cp1252 stdout raises UnicodeEncodeError and aborts the
# build. Force UTF-8 on the streams so `mkdocs build` works without needing
# PYTHONUTF8=1 in the environment.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


# Suppress griffe "no type annotation" warnings until type hints are added.
# Revisit when Python 3.14 type system improvements land.
logging.getLogger("mkdocs.plugins.griffe").setLevel(logging.ERROR)
