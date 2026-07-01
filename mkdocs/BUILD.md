# Building the docs

```
pip install -r requirements.txt
mkdocs serve      # local preview at http://127.0.0.1:8000
mkdocs build      # static site into ./site
mkdocs gh-deploy  # build + publish to GitHub Pages (sbs_utils repo)
```

This is the **canonical Cosmos docs site**. LegendaryMissions docs are authored in
the [LegendaryMissions repo](https://github.com/artemis-sbs/LegendaryMissions)
(`mkdocs/docs`) and stitched into the **LegendaryMissions** section here at build
time &mdash; sbs_utils stays dependency-free of LM.

## Stitching in LegendaryMissions (multi-repo)

To pull LM's docs into this site, enable `mkdocs-multirepo-plugin` in
`mkdocs.yml` (`pip install mkdocs-multirepo-plugin`), replace the local
`LegendaryMissions: legendary/index.md` nav entry with an import, and add the
plugin:

```yaml
plugins:
  - search
  - macros
  - mkdocstrings: { handlers: { python: { paths: [".."] } } }
  - multirepo:
      repos:
        - section: LegendaryMissions
          import_url: 'https://github.com/artemis-sbs/LegendaryMissions?branch=main&docs_dir=mkdocs/docs/*'
```

Until that's wired, the local `legendary/index.md` placeholder links out to the LM
repo so the standalone build stays green.
