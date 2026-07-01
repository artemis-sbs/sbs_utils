# Sharing reusable Python (`.sbslib`)

A `.sbslib` is a zip of a Python package that missions load at runtime from the
shared `__lib__/` folder. It's how sbs_utils itself ships &mdash; and how you can
share your own reusable Python (procedural helpers, classes) across missions.

## Lay out the package

Put your code in a normal Python package folder, e.g.:

```
my_lib_src/
├── __lib__.json        # declares what to build + a version
└── my_lib/             # the importable package
    ├── __init__.py
    └── helpers.py
```

`__lib__.json` lists the package folder(s) to package and a version:

```json
{
    "version": "v1.0.0",
    "sbslib": ["my_lib"]
}
```

## Build it

```
sbs lib my_lib_src -u your-github-user
```

This produces `your-github-user.my_lib.v1.0.0.sbslib` &mdash; a zip with the
package directory **at the zip root** (required: `zipimport` can't load namespace
packages, so the importable package must be top-level in the zip). The naming
scheme (`user.package.version`) avoids clashes and version mix-ups.

## Use it in a mission

1. Drop the `.sbslib` into `__lib__/` next to your missions.
2. List it in the mission's `story.json`:

```json
{ "sbslib": ["your-github-user.my_lib.v1.0.0.sbslib"] }
```

Now `import my_lib` works in the mission's Python. To make functions callable
directly from MAST, register the module into the MAST globals from your library:

```python
from sbs_utils.mast.mast_globals import MastGlobals
MastGlobals.import_python_module("my_lib.helpers")   # my_lib.helpers.foo -> foo in MAST
# add a prefix: MastGlobals.import_python_module("my_lib.helpers", "mylib")  -> mylib_foo
```

See also [Getting the library](../home/get_library.md) and
[Making add-ons](../build/addons.md) (the MAST/`.mastlib` equivalent).
