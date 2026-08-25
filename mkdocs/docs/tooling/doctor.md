# Checking your setup: `sbs doctor` and `sbs deps`

```
sbs doctor                 the environment, and every mission it can see
sbs doctor <folder>        the environment, and that one mission
sbs doctor --env           the environment only
sbs doctor --json          machine-readable
sbs doctor --strict        exit 1 if anything is flagged
```

## What doctor is for, and what it refuses to be

!!! info "Scope"
    Doctor answers **"is this machine and this mission set up correctly"**. It
    never answers **"is this content correct"**.

It reads `story.json`, `__lib__.json`, directory listings and file times. It does
not parse a `.amd` or compile a `.mast` - those belong to `sbs lint` and
`sbs compile`, and doctor points at them rather than growing a second opinion.

That is not fastidiousness. A report that also checks content becomes a slower
linter that disagrees with the linter, and then nobody trusts either. The rule is
enforced by a test that fails if doctor opens one of those files.

**Doctor exits 0.** A report that fails the build is a linter; `--strict` exists
for anyone who wants the other behavior.

## Reading the output

Three statuses, in a fixed column:

| | Meaning |
|---|---|
| `ok` | fine |
| `--` | absent, but optional - not a problem |
| `!!` | a problem, always followed by an indented remedy line |

```
Python
  ok  version     3.11.1 embedded (E:\Cosmos\PyRuntime\python.exe)
  ok  paths       PYTHONPATH is ignored and site-packages is not on sys.path
      use `sbs deps install X` for optional libraries
Tools
  ok  browser     chrome 151.0.7922.76 (C:\Program Files\Google\Chrome\...)
  --  weasyprint  not installed - PDFs will have no contents page numbers
      install the WeasyPrint package; pip alone cannot supply its GTK libraries
LegendaryMissions
  !!  freshness   source newer than the built lib: quests
      run: sbs lib LegendaryMissions
```

Sections: **sbs** (version, missions folder, running packaged or from source) -
**Python** - **Layout** (`__lib__`, which `sbs_utils` won, graphics, PyAddons,
face compositor) - **Tools** (git, curl, browser, weasyprint) - **Sidecar** -
**install** (derived art) - then one per mission.

The mission checks are: `story.json` parses; every declared library is actually
in `__lib__`; no addon source is **newer than its built `.mastlib`** (the classic
"my change did nothing" - the engine reads the lib while the runner reads the
source); the packaging lists are in step; and no generated `extraShipData.json`
is lying around, since the library reads it back *and* the addon merges the same
entries again, doubling hull counts from the second run onward.

## Half-baked art

Doctor also counts the art the ENGINE bakes for itself - a hull's `.paxmesh` and
its `<root>1024.png` / `<root>256.png`, generated on first draw and never
packaged.

```
install
  ok  art         193 baked, 20 not yet drawn, 0 half-baked in data/graphics
```

**Half-baked is the one that matters, and it is a crash.** If the engine dies
partway through a bake it leaves the mesh without its sprites; every later draw
retries, dies in the same place, and leaves the same wreckage - so one bad hull
crashes that client on every draw, forever. Three hulls were stuck like that in one
install and cost two separate crash investigations before anyone looked in the
folder. `sbs art clear` throws the partial files away so the engine can start over;
`sbs art bake` drives it. **Not yet drawn is normal** - art nobody has looked at -
and is deliberately not flagged.

Two things this check knows, both measured off a stock `data/graphics` rather than
assumed, because getting either wrong makes it cry wolf on a healthy install:

- **`.pointcube` is optional.** 120 of 184 baked ship roots have none.
- **Sprites are a `ships/` thing.** In `graphics/ships` every baked root has them
  and none lacks them; at the graphics root the nine effect meshes (typhon parts,
  drones, `AHBall`) have none and never get any, because nothing draws them
  face-on.

It also watches for `<root>256.png` turning up beside the executable instead of
beside the art - a known engine bug that quietly stops the art folder ever
completing.

---

# `sbs deps` - optional Python libraries

## Why plain `pip install` never worked

`sbs.bat` is `..\..\PyRuntime\python sbs.pyz`, so **`sbs` runs on the embedded
CPython 3.11**, not on your own Python. And `PyRuntime/python311._pth` has
`import site` commented out, which means:

- `site-packages` is never on `sys.path`
- `PYTHONPATH` is ignored
- `python -m pip` answers **"No module named pip"** - while pip is sitting right
  there in `PyRuntime/Lib/site-packages/pip`, present and invisible

So a `pip install` into any interpreter is invisible to `sbs`. That is not
friction to work around; it is the design of an embeddable distribution.

## What `sbs deps` does instead

It puts `site-packages` on the path of a **child process of the same
interpreter**, where pip then runs normally, and installs with `--target` into a
folder `sbs` adds to `sys.path` at startup.

Because it is the same interpreter, pip resolves wheels against the real 3.11
ABI - no `--python-version` guessing, no host/embedded mismatch, and C extensions
land correctly.

```
sbs deps install pypdf     PDF bookmarks and merged books for `sbs docs`
sbs deps list              what is installed, and where
sbs deps remove pypdf
sbs deps path              print the folder
```

## Two targets, because there are two sidecars

| Target | Folder | Loaded by | Reaches |
|---|---|---|---|
| default | `<missions>/__pylib__` | `sbs` | `sbs docs`, `sbs doctor` - host tooling |
| `--engine` | `<cosmos>/PyAddons` | the **engine**, at startup | a running mission |

`PyAddons` is not new - it is where `ryaml.pyd` lives, and the reason `ryaml` is
importable inside a running mission.

`sbs deps install X --engine` is **explicit and never the default**, and asks
before it acts, because:

- **A mission that imports it is no longer self-contained.** Missions ship as
  folders and mastlibs; PyAddons is part of the *install*. That mission then only
  runs where someone ran the same command.
- It writes into the Cosmos install directory, where it can collide with what
  Cosmos ships.
- `sbs_utils` itself stays stdlib-only regardless. An engine-side optional
  dependency may only take the shape `fs.ryaml_module()` uses: silent when
  absent, with a working fallback.

## What this cannot do

!!! warning "WeasyPrint is not pip-installable on Windows"
    `pip install weasyprint` succeeds and then fails at import with
    `cannot load library 'libgobject-2.0-0'`, because it needs GTK/Pango DLLs pip
    has no way to supply. `sbs deps install weasyprint` refuses up front rather
    than letting you find out later. Use the WeasyPrint Windows package instead.

Also worth knowing:

- **`pip --target` does no cross-install resolution.** Two separate installs can
  leave incompatible versions side by side without an error.
- **Nothing here is required.** Every feature that uses an optional library
  degrades to working without it.
