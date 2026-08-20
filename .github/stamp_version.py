"""Write `sbs_utils/version__.py` from a release tag.

`__lib__.json` is the one place the version is authored, but it does NOT travel
inside the `.sbslib` -- the zip holds the `sbs_utils` package directory alone -- so
the number has to be baked into a module at build time.

The release job (`main.yml`) zips the package folder directly rather than going
through `sbs lib`, so without this step it publishes whatever `version__.py` happens
to be committed. That is how the v1.4.0 release shipped with `__version = (1,3,0)`
inside it, reported to every mission that calls the `version_get()` MAST global.

`sbs lib` stamps the same file from `__lib__.json` for local builds; this script is
the same stamp for the CI path, driven by the tag being released.

    python .github/stamp_version.py <tag> [target]

A tag that is not a version is left alone rather than failing the build: the
workflow fires on every tag and this repo also carries markers such as
`before-task-lifecycle`, which were never going to be released from anyway.
"""
import json
import os
import re
import sys

TEMPLATE = """
__version = ({major},{minor},{build})
def version_get():
    return __version

def version_get_major():
    return __version[0]

def version_get_minor():
    return __version[1]

def version_get_build():
    return __version[2]

"""


def parse(tag):
    """(major, minor, build) from a `v1.4.0` style tag, or None if it isn't one."""
    m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", tag)
    return m.groups() if m else None


def declared_version(path="__lib__.json"):
    """The version authored in __lib__.json, for a consistency warning."""
    try:
        with open(path) as f:
            return json.load(f).get("version")
    except Exception:
        return None


def main(argv):
    tag = (argv[1] if len(argv) > 1 else os.environ.get("GITHUB_REF_NAME", "")).strip()
    target = argv[2] if len(argv) > 2 else "sbs_utils/version__.py"

    parts = parse(tag)
    if parts is None:
        print(f"SKIP: tag {tag!r} is not vMAJOR.MINOR.BUILD - leaving {target} alone")
        return 0

    declared = declared_version()
    if declared is not None and parse(declared) != parts:
        # Not fatal: the tag is what is actually being published, so it wins. But a
        # disagreement means __lib__.json was not bumped, and every mission pinning
        # this line by filename will be asking for a version nothing declares.
        print(f"WARNING: __lib__.json says {declared!r} but the tag is {tag!r}")

    major, minor, build = parts
    with open(target, "w") as f:
        f.write(TEMPLATE.format(major=major, minor=minor, build=build))
    print(f"stamped {target} = ({major},{minor},{build}) from tag {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
