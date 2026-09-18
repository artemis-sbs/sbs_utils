---
name: packaging-and-release
description: How sbs_utils, missions and mods get from a working tree into the engine and onto GitHub - `sbs.pyz lib` local builds into `data/missions/__lib__/`, `__lib__.json` and `story.json`, the .sbslib / .mastlib / media-pack formats, committing in a shared tree, per-repo branches, and `sbs.pyz release -u` rereleases driven by a GitHub Action. Use when building local libraries, committing / pushing / rereleasing sbs_utils or a mission, editing `__lib__.json` or `story.json`, packaging an addon or media pack, when an edit "has no effect in the engine", when a released lib behaves differently from a local one, or when deciding which branch a repo uses.
---

Artemis Cosmos missions do not run source folders. They load **packaged libraries** from
`data/missions/__lib__/`, and the tool that builds and releases them is
`data/missions/sbs.pyz` (source: `data/missions/sbs_cli/src/`, `lib_cmd.py` and
`release_cmd.py`). This file is the build -> commit -> push -> release loop and the traps
in each step.

| artifact | what it is | built from | named |
|---|---|---|---|
| `.sbslib` | a Python package zip (zipimport) | an `sbslib` entry in the repo's `__lib__.json` | `{owner}.{package}.{tag}.sbslib` |
| `.mastlib` | a MAST addon zip | a `mastlib` entry | `{owner}.{repo}.{addon}.{tag}.mastlib` |
| media pack | a resource zip of engine-read files (art, shipData-shaped json) | a `zip` entry | `{owner}.{repo}.media.{tag}.zip`, unpacked to `__lib__/media/{owner}.{repo}.media.{tag}/` |

`__lib__.json` (repo root) says **what to build** and the version. A mission's
`story.json` says **what to load** (`sbslib`, `mastlib`, `shared_media` / `resources`).
A zip sitting in `__lib__` that `story.json` does not name is never loaded.

---

## The one rule: the engine never runs the working tree

It loads the `__lib__` zips (and the unpacked media). Every green local check can pass
over a stale build - and a stale sbslib typically shows up as "it hangs", because the map
task dies on its first line calling a function the old zip does not have.

**Rebuild in the same breath as the change - never as a future step.** "I will rebuild
before shipping" is the step that gets skipped. A new module, any `sbs_utils` edit, any
addon `.mast` / `.py` / `.amd` edit: build it now.

---

## Build local

```
cd E:/a/Cosmos-dev/data/missions         # the missions ROOT
python sbs.pyz lib sbs_utils              # sbs_utils + cosmos_dev .sbslib
python sbs.pyz lib LegendaryMissions      # every LM .mastlib + the LM media pack
python sbs.pyz lib OpenUniverse           # universe_core, admiral
```

No git side effects. Run each as a **separate statement** - `... | grep x && python sbs.pyz lib next`
skips the second build when grep filters every line.

What `lib` does (from `lib_cmd.lib_impl`):

1. Reads `<folder>/__lib__.json`; every key but `version` is the output extension.
2. Stamps `version__.py` in each sbslib package that already has one (so `version_get()`
   reports the `__lib__.json` version). This rewrites a tracked file - expect it in
   `git status` after a version bump.
3. Zips each listed folder into `__lib__/` (skipping `__pycache__` and engine-baked
   derived art). sbslibs keep the package dir at the zip root; mastlibs and media zips
   are **flat**. Each mastlib gets an `.amd` lint stamp; AMD lint errors are printed and
   do **not** stop the build (the mission's `--test` gate will then fail).
4. Skips (keeping the old zip) a listed folder that is missing or empty - so a
   `SKIP ...` line means `__lib__` still holds the previous build.
5. Unpacks media packs that some mission's `story.json` pins, and prunes unpacked packs
   nothing pins.

**Gotchas in the command itself** (verified in `lib_cmd.py` / `cli_cmd.py`):

- The folder argument is resolved against **the directory `sbs.pyz` lives in**, not the
  current directory. Pass the folder NAME.
- **`sbs lib` with no argument builds LegendaryMissions** (the click default). Running
  it from inside some other repo expecting "this folder" builds LM instead.
- A folder with no `__lib__.json` (including `.`) crashes with an `AttributeError`
  (`lib_get_json` returns None) rather than a clean error.
- `sbs.bat` runs `..\..\PyRuntime\python sbs.pyz`, relative to the current directory - it
  only works from the missions root.

**Exit 0 is not evidence - open the zip.**

```python
import zipfile
z = zipfile.ZipFile(r"__lib__/artemis-sbs.LegendaryMissions.consoles.v1.4.0.mastlib")
print(sorted(z.namelist())[:20])
print(b"my_new_function" in z.read("consoles.mast"))   # the change is really in there
```

For an sbslib, check the entry path too: `sbs_utils/procedural/foo.py`, not `procedural/foo.py`.

**Under a release hold**, rebuilding into the shared `__lib__` pushes unreleased content
into every mission on the machine. Verify the source file directly instead, and say the
end-to-end run is deferred.

---

## What each check actually sees

| check | reads | blind to |
|---|---|---|
| unit tests | working tree | everything packaged |
| `mission_runner --use-working-tree` | working-tree sbs_utils (prints "using working-tree sbs_utils") | the sbslib |
| `mission_runner` (no flag) | the packaged sbslib | nothing on the library side - but see addons below |
| a repo running its OWN addons | the addon source folders | its packed `.mastlib` and media pack |
| a consumer mission (SecretMeeting, WalkTheLine...) | the `.mastlib`s and media pack in `__lib__` | the addon source |
| the engine | `__lib__` zips + unpacked media | nothing - it is the truth |

**Addons: source wins in the repo that owns them.** Since 2026-07-30 `Mast.find_add_ons`
skips a declared mastlib when the mission folder holds that addon's source
(`<addon>/__init__.mast`) and prints `Using mission SOURCE for N declared addon(s) instead
of __lib__`. So an LM edit shows up running LM from its clone, and is **still missing** in
every other mission until `sbs lib LegendaryMissions` runs. A fix that "shipped" with no
visible effect in a consumer mission is almost always a stale mastlib.

**Data files follow the `.mast` that reads them.** `media_read_relative_file` reads from
the zip when the running `.mast` came from a mastlib, else from the folder. A consumer
therefore reads the zipped `.amd` / `.json`; a new record that was never rebuilt is simply
absent - no error. Diagnose by reading the zip, never the disk.

**`--use-working-tree` is right for iterating and wrong as the only check.** Re-verify
once without it before calling a library change done.

**The mock is not the engine.** A mock PASS at `labels 0/N` is a story that did not
compile; check the label count, not the verdict.

---

## Commit

- **Stage explicit files. Never `git add -A` or `git add <dir>`.** These working trees are
  shared - other sessions and the maintainer's own uncommitted debug edits live in them.
- Before committing: `git diff --cached --stat` and confirm every file is yours.
- **Pairing: commit -> `sbs.pyz lib <folder>`** for each changed repo, so local runs match
  the commit.
- Batch related changes into one logical commit rather than a commit per tweak.

**Shared-tree hygiene.** Another session can rewrite a file you edited, or switch the
branch under you, with no announcement. The tells: a sudden `ImportError` for a function
you wrote, `git diff --stat` showing far fewer lines than you changed, or a built zip that
is AHEAD of its source (the next `sbs lib` would silently regress it).

- Before editing, `git diff --stat <file>`; after a long sequence, `grep -c "def name"` to
  confirm your code is still there.
- Re-apply your hunks ON TOP of the current file. Never restore your whole copy - that
  destroys theirs the same way.
- For a file both sides edited: `git show <base>:<path> > <path>`, re-apply only your hunks,
  `git add`, then restore the full working copy from a scratch backup.
- An inexplicable failure: check `git branch --show-current` and `git reflog` early.
- Prefer `git cherry-pick` onto the checked-out branch; ask before checking anything out.

**Line endings** - see the CRLF trap under Packaging. After creating or rewriting a file in
a mission repo, run `git ls-files --eol <paths>`.

---

## Branches per repo

| repo | commit / push to | notes |
|---|---|---|
| sbs_utils | `v1.4.0_dev`, push `origin v1.4.0_dev` | never PR or merge into `master` - the maintainer controls that |
| LegendaryMissions, OpenUniverse | `v1.4.0_dev` | never PR/merge to `main`. LM's branch is shared - fetch and check ahead/behind before pushing |
| sbs_cli | `main` directly | PR only to fix a GitHub issue or when asked. Not a lib: no `__lib__.json`, never released with `sbs release` |
| mod repos (Cosmos-TNG-Mod and siblings) | `main` directly, no feature branch | a stray branch leaves the release tag dangling off `main` |
| StormsBeacon | `main` | **not tagged** - push and stop |

- **Every push needs explicit approval**, per repo. "push" / "rerelease" from the
  maintainer is that approval for the repos in play. Ask separately for anything unusual:
  force-push, a new branch, deleting a branch or tag.
- Do not apply a generic "branch first" habit to these repos.
- Rebuilding `__lib__` locally does not affect other people's playtests - they pull from
  GitHub.

---

## Push and rerelease

**Pairing: push -> rerelease** the pushed folders.

```
python sbs.pyz release sbs_utils "Short ASCII summary of the changes" -u
python sbs.pyz release LegendaryMissions "..." -u
```

What it does (`release_cmd.py`, verified):

- Reads `version` from `<folder>/__lib__.json` (the tag name, e.g. `v1.4.0`).
- `-u`: `git tag --delete <version>` then `git push --delete origin <version>`.
- With a message: `git tag -a <version> -m "<message>"` then **`git push --tags`**.
- Net effect: the version tag moves to the current HEAD, and the tag push fires the
  repo's release workflow, which builds and uploads the assets.

Gotchas:

- **It does not touch the local `__lib__`.** Only `sbs lib` does. Releasing without
  building locally leaves the engine on the old zip.
- **`-u` needs the tag to exist.** A first release is `release <folder> "<msg>"` with no
  `-u`; `-u` on a missing tag raises on the local delete and stops.
- **`-u` without a message deletes the tag and re-creates nothing.**
- **`-v/--version` is accepted and ignored** - the code overwrites it from `__lib__.json`.
- **`git push --tags` pushes EVERY local tag**, and every workflow here triggers on
  `tags: "*"`. Stray local marker tags get pushed (and fire a release run) too.
- The message is interpolated into the command line: ASCII, no double quotes.
- It tags the **checked-out** HEAD, so on a `v1.4.0_dev` tree it can only roll `v1.4.0`.
- A repo whose `__lib__.json` version does not match its tag line (StormsBeacon uses a
  separate `vEA*` line) would get a NEW tag created, not an existing one moved - which is
  why it is not a release target.

**The GitHub Action owns the release assets. Never `gh release upload`, never
`--clobber`, never touch them by hand.**

- Right after the command, `gh release view` still shows the PREVIOUS build - the Action
  has not run yet, and a run can take minutes even to appear in `gh run list`. That looks
  exactly like a failed upload and is not one.
- The published asset does not match your local `__lib__` zip byte for byte - CI builds its
  own. A size/hash difference is expected, not a symptom.
- The only observation needed is whether the run succeeded:
  `gh run list --repo artemis-sbs/<repo>` or `gh api repos/artemis-sbs/<repo>/actions/runs`.
- **If the release run FAILS:** read it with `gh run view <id> --log-failed`. A bare
  `Error 500` from the upload step is GitHub's API, not the code - repair with
  `gh run rerun <id> --failed` (ask first; it writes to the release). Never a manual upload.
- **Name the workflow before reporting a failure.** A push can fire more than one:
  sbs_utils has `Create Release` (tag) and `Tests (offline suites)` (every push/PR);
  LM has `Create Archive`; OpenUniverse has `Create Archive` plus `Docs are current`, which
  fails on stale generated docs (`sbs site OpenUniverse --emit`) independently of
  the release.

Report a rerelease in one line: which repos, which tag, done.

**Release targets:** sbs_utils, LegendaryMissions, OpenUniverse (and mods that carry a
tag line). Not StormsBeacon, not sbs_cli.

---

## Packaging contract

### .mastlib: flat, and named

- **FLAT.** MAST opens the zip and reads `__init__.mast` at the **zip root**
  (`find_add_ons` -> `import_content` -> `ZipFile(lib).open("__init__.mast")`). A nested
  `<addon>/__init__.mast` makes that open fail and the addon **silently never loads** -
  zero labels, still "PASS".
- **An sbslib is the opposite:** the package dir must be at the zip root
  (`sbs_utils/...`) because zipimport has no namespace packages.
- **Named** `{owner}.{repo}.{addon}.{tag}.mastlib` - exactly what `story.json` refers to.
- Any repo shipping a mastlib needs CI that zips flat. LM and OU commit
  `.github/zip_flat.py` (mirrors `file_help.zipdir`); LM's workflow reads the addon list
  straight from `__lib__.json`, so adding an addon there ships it.
- **Verify a mastlib by loading it, never by inspecting it** - check the label count.

### Local build and release build share no code

| path | built by | sees |
|---|---|---|
| local | `sbs lib` -> `lib_cmd.lib_impl` | the working tree, as `__lib__.json` lists it |
| release | the tag's `.github/workflows/main.yml` (sbs_utils zips with `thedoctor0/zip-release`; LM/OU with `zip_flat.py`) | only what is **committed** |

Anything `sbs lib` does at build time is absent from the release unless CI does it too.
Example: `version__.py` - `sbs lib` stamps it from `__lib__.json`, CI stamps it from the
tag with `.github/stamp_version.py`. Before both did, a release shipped reporting the
previous version.

**Only the package directory ships in an sbslib.** `__lib__.json`, `README`, `script.py`
and the rest of the repo root are not in it, so the library cannot read a root manifest at
runtime - bake it into a module. Check with `zipfile.ZipFile(lib).namelist()`.

### The CRLF trap

On Windows (`core.autocrlf=true`), and for files created by editors and tools on this
machine, the WORKING TREE can be CRLF while git stages LF - `git status` and the diff look
clean. `sbs lib` zips the working tree. Three readers disagree:

| reader | CRLF effect |
|---|---|
| MAST from a folder (`open(file_name)`, `mast.py` ~966) | text mode translates it away - works |
| MAST from a mastlib (`f.read().decode('UTF-8')`, `mast.py` ~948) | bytes; `== label ==` stops matching, labels vanish, still PASS |
| the engine reading media itself (shipData-shaped json) | rejects the file - fails far away (seen as `MemoryError` in `create_space_object`) |

`.grid` files and `.amd` headings are CRLF-safe; `.mast` in a mastlib and engine-read media
are not. So a dev tree running from source never sees it, and the same file breaks the
moment it is packaged.

```
git ls-files --eol <paths>            # i/lf w/crlf = mangled working tree
rm <path> && git checkout -- <path>   # restore it as LF
```

- `git status` is not the check - the index caches the checkout's stat, so a CRLF tree
  reports clean and flipping `core.autocrlf` afterwards changes nothing on disk.
  `git checkout-index -a -f` also does nothing, for the same reason; renormalizing an
  existing clone needs the delete-and-restore.
- A file that is CRLF **in the index** (`i/crlf`) needs `git add --renormalize`.
- Every packaging repo wants `* text=auto eol=lf` in `.gitattributes` (LM has it, with
  `*.png binary`). Before adding the rule, `git ls-files --eol | awk '$1=="i/-text"'` names
  the real binaries.
- Verify the zip too: `zipfile.ZipFile(lib).read("x.mast").count(b"\r\n")` must be 0.

### Media packs

A media pack holds files **the engine opens itself** (art, shipData-shaped json). A mastlib
is a zip the engine cannot read, so engine-read files belong in the media pack, never in a
mastlib. What the engine reads is the **unpacked** copy under
`__lib__/media/<owner>.<repo>.media.<tag>/` - after an edit, compare the source file with
the unpacked one, not with itself. `sbs lib` only unpacks packs some mission's `story.json`
pins (`shared_media` or `resources`), and prunes unpacked packs nothing pins.

---

## Testing a PR locally

sbs_utils CI on a PR runs only the offline suites (`Tests (offline suites)`: AMD, golden
parse, signal/namespace lint, ship-data wrapper). "Does PR #N pass?" still means running
the full suite by hand.

- **Test the MERGE, not the PR head.** A contributor branch is usually behind
  `v1.4.0_dev`, so its head runs fewer tests and can fail on things already fixed.
  `git fetch origin pull/<n>/head:pr<n>`, merge `v1.4.0_dev` into it, run
  `python -m unittest discover -s tests` on the result.
- **Cheapest correct setup: a temp branch in the real repo**, then check the original
  branch out again (in a shared tree, ask first).
- **Worktree traps** - both produce long, convincing, bogus failure lists:
  1. `is_dev_build()` is `os.path.isdir(mission + "\\.git")`; a worktree's `.git` is a
     FILE, so dev-build-only raises switch off (grep the failures for
     `EDGE CASE: Did you set END or Yield the last GUI Task?`).
  2. The worktree must be a **sibling under `data/missions/`** - path resolution walks up
     into the Cosmos data tree, and a scratchpad location fails ~60 tests.
- Before blaming the PR, run a failing test on the target branch in the same harness.
- `git worktree remove --force` can fail with "Permission denied" (a `__pycache__` lock);
  finish with `rm -rf <dir>` and `git worktree prune`.

---

## Release lines

sbs_utils ships two lines. The version comes from each branch's `__lib__.json`, so the
branch decides the tag.

| branch | version / tag | tag moved by |
|---|---|---|
| `master` | `v1.3.0` | by hand from a master ref: delete tag, `git tag -a` at master's tip, push |
| `v1.4.0_dev` | `v1.4.0` | `python sbs.pyz release sbs_utils "<msg>" -u` |

- **Keep `master` an ancestor of `v1.4.0_dev`.** After anything lands on master, merge it
  into `v1.4.0_dev` (conflicts resolve to ours - v1.4.0_dev is the superset) and check
  `git merge-base --is-ancestor master v1.4.0_dev`. That keeps a future merge a pure
  fast-forward.
- The release job runs no tests (mock tests need Cosmos data files; master's v1.3.0 code
  also imports `ctypes.WinDLL` at module scope and cannot import on Linux). The workflow
  needs `allowUpdates` / `replacesArtifacts`, or a rolling tag 422s and the published lib
  silently stays stale.
- **"Version X behaves differently":** read the mission's `story.json` first - it names the
  exact sbslib file. Then unzip that file and grep for the change.
- sbs_utils, LegendaryMissions and OpenUniverse ship **as a set** on one line.
- `sbs create` templates (artemis-sbs/mast_starter) have a branch per line (`main`,
  `v1.3.0`, `v1.4.0`); a template can only use what its line's sbslib has, so never re-pin
  one across lines.

**Production missions** - the set to verify a library change against: LegendaryMissions,
remote_mission_pick, SecretMeeting, WalkTheLine.
