# Building the docs

```
pip install -r requirements.txt
mkdocs serve      # local preview at http://127.0.0.1:8000
mkdocs build      # static site into ./site
mkdocs gh-deploy  # build + publish to GitHub Pages (sbs_utils repo)
```

This is the **canonical Cosmos docs site**. The LegendaryMissions docs are authored
in the [LegendaryMissions repo](https://github.com/artemis-sbs/LegendaryMissions)
(`mkdocs/docs`) and stitched into the **LegendaryMissions** section at build time
&mdash; sbs_utils stays dependency-free of LM.

## The LegendaryMissions stitch (already wired)

`mkdocs.yml` pulls LM's docs via `mkdocs-multirepo-plugin`:

- the plugin is enabled with a bare `- multirepo` under `plugins`, and
- the nav imports LM's own mkdocs project:

  ```yaml
  - LegendaryMissions: '!import https://github.com/artemis-sbs/LegendaryMissions?branch=v1.4.0_dev&config=mkdocs/mkdocs.yml&docs_dir=mkdocs/docs'
  ```

Notes / gotchas (learned the hard way):

- **`config=mkdocs/mkdocs.yml` + `docs_dir=mkdocs/docs`** are required because LM's
  mkdocs project lives under `mkdocs/`, not the repo root.
- **`branch=v1.4.0_dev`** &mdash; LM is branch-only (never merges to `main`), so point
  at the branch that holds the current LM docs. Update this when that changes.
- **UTF-8**: the plugin prints an emoji during its git import; on Windows the
  default cp1252 stdout crashes. `mkdocs_hooks.py` reconfigures stdout/stderr to
  UTF-8 so a plain `mkdocs build` works (no `PYTHONUTF8=1` needed).
- The build needs **network access** to clone LM at build time.
- **Don't manually delete the plugin's `temp_dir`** during a build &mdash; the
  plugin manages it; removing it mid-build can race the clone and fail with
  `File not found: legendarymissions/index.md`. Just re-run.
- The stitch pulls LM **from GitHub** (the `branch=` above), not your local LM
  working tree &mdash; push LM doc changes before they'll appear in the build.

A plain `mkdocs build` produces the full unified site (sbs_utils + the stitched
`/legendarymissions/` section).
