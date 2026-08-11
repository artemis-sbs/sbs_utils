# Publishing AMD: `sbs site`

```
sbs site <folder> --emit includes    refill the generated blocks in a docs tree
sbs site <folder> --emit records     write a page per .amd, and the nav to reach it
sbs site <folder> --emit site        build a standalone HTML site
sbs site <folder> --emit <what> --check    write nothing; fail if anything is stale
```

!!! info "Not `sbs docs`"
    [`sbs docs`](amd-docs.md) renders one **printable document** through four editorial
    lenses. This makes a **website**. Two nouns, two commands.

## Why it exists

A page that explains AMD has to show some AMD, and every one of those examples was
hand-copied. Copies rot. Measured across the shipped documentation when this was
written:

| Page | What had drifted |
|---|---|
| Open Universe's complete example | a 331-line copy of a 364-line file - a whole `## [Effects](effects)` chapter missing, `Reward:` become `Pays:` |
| Legendary Missions' boss guide | a hand-maintained table of a folder scan, and two examples missing fields the shipped file carries |
| Three separate reference tables | taught `When:` as the **completion** trigger |

That last one is not cosmetic. `When:` is an alias of **`Starts when:`** - the *start*
trigger. A quest written from those pages arms on its trigger and then waits forever
on a `Done when:` it does not have, so it never completes and its `Then: reveal` never
fires. Every shipped `.amd` was correct; only the prose was wrong, which is the kind of
wrong that looks like documentation.

Separately, about 380 records across the two shipped missions had **no web presence at
all** - the race lore, the console help, the sides, the casino's bar patrons.

## `--emit includes` - stop copying, start quoting

A page declares what it wants between two comments, and the generator refills the span.
The prose around it is untouched; only the *quoted* part stops being a copy.

```markdown
<!-- amd:begin excerpt maps/bosses/warlord.amd#warlord -->
<!-- amd:end -->
```

Five directives, and the vocabulary is closed - an unknown one **fails the run** rather
than leaving the stale copy in place:

| Directive | Produces |
|---|---|
| `excerpt <file>` | the whole file, fenced |
| `excerpt <file>#<key>` | one record |
| `excerpt <file>#<key> --with-children` | a record and everything under it |
| `fields <archetype> [--only a,b,c]` | the field table for a kind of record |
| `index <glob> [--fields a,b]` | what a folder currently holds |

`excerpt` quotes the **source bytes**, deliberately: the reader is being shown *what to
type*, so a round-trip through the parser would be the wrong answer even when it agreed.

`fields` reads [the schema](../build/quests.md), so its prose comes from the same table
entry the parser reads and cannot drift from it. It is archetype-keyed, which is how it
says something a flat hand-written table structurally cannot: `When:` is a start trigger
on a **quest** and a comms surface on **dialogue**.

## `--emit records` - a page per file

One `.amd` file becomes one page and every record an anchor on it. That is the decision
the in-game reader already made - each registered source is a top-level section, so the
chapter unit is the file. Page-per-record would be 89 pages, most of them one hail.

Wikilinks, `Part of:`, `Then: reveal` and player **choices** all become real links, so a
dialogue tree is browsable the way it plays.

Per-repo choices live in `mkdocs/records.json`:

```json
{
  "nav_title": "The mission data",
  "titles":  { "documents/help_docs.amd": "Console help" },
  "split":   ["maps/peacetime_remastered.amd"],
  "exclude": ["documents/quest.amd"]
}
```

`split` is **declared, never inferred from a record count** - a threshold would silently
change a page's URL the day a file grows past it.

!!! warning "Generated pages are committed into the mission's own repo"
    The parent documentation site stitches Legendary Missions and Open Universe in with
    the multirepo plugin, which clones them **from GitHub at build time**. Anything
    generated only in the parent would never appear on the site.

## `--emit site` - a folder you can double-click

Static HTML: left nav, per-page contents, search, no server, no CDN, no web fonts.
It shares the emitter - the same markdown the mkdocs pages are written from is what
gets parsed here, so the two outputs cannot disagree.

Search ships as a script assigning a global, not a JSON file fetched at runtime,
because `fetch()` is blocked on `file://` and the whole point is a folder you can open
off disk.

## Faces

A `face://` spec is a layer stack over a race atlas, composited at display time on a
canvas. For the web it is **baked to a PNG once**, at generate time - which works in
mkdocs, in the standalone site, in a plain markdown preview and in print, with no
JavaScript. The alternative costs about 6.8 MB of atlases committed into a mission repo
and still shows nothing wherever scripting is off.

The PNG's name comes from the **spec**, so a face that has been composited and committed
resolves on a machine with no Cosmos install at all. That is what makes these pages
reproducible in CI. Only a *new* face needs the atlases.

`ship://` is a 3D hull tag, not a picture - the `.png` beside a mesh is a diffuse
texture and prints as a near-white box - so the page names it instead.

## `--check`, and CI

`--check` writes nothing and exits non-zero if anything would change. Without it,
regeneration is something a person has to remember, which is the same failure wearing a
tool's clothes.

Both mission repos run it on every push (`.github/workflows/docs.yml`). If it fails,
run the command it names and commit the result.

!!! note "One mission per process"
    `amd_register_fields` writes into a process-global table and is **cumulative**, so
    documenting two missions in one interpreter lists the first one's fields in the
    second one's tables. `sbs site` refuses a second mission outright rather than
    emitting a table that depends on load order.
