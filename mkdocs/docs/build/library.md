# The Library — in-game reading

The **Library** tab is one shelf that several things can put a book on. LegendaryMissions
contributes its galactic helpfile, Open Universe contributes its codex, and your mission
contributes its own — each becomes a chapter of one document rather than a tab of its own.

## Adding your lore

Write an `.amd` file the way you would any document — link-form headings, prose bodies:

```
# [The Kessel Papers](kessel_papers)

## [The Belt](belt)

### [Ore Haulers](haulers)

They run silent through the rocks, and the clans do not.
```

Then register it once, at the top level of your mission or addon:

```
lore_register("kessel", "The Kessel Papers", "kessel_papers.amd")
```

That is the whole integration. `lore_register(key, display, file)` takes the name the
chapter is filed under, the title a reader sees, and the file to read.

## What follows from registering

**Registering is what makes the Library exist.** There is no separate "add the tab" step,
and no flag to turn it on. A mission that registers nothing has no Library tab at all —
so loading an addon for its *machinery* never leaves you with an empty shelf.

**A source that resolves to nothing is skipped.** Register a file you have not written yet
and nothing appears; write it and the chapter shows up. Nothing errors either way.

**Files are found in your mission first.** The order is your mission folder, then the addon
the registration came from, then any other addon your `story.json` declares. So a mission
can supply its own `library_docs.amd` and have it used instead of the one a library ships.

**Registering a key twice replaces it.** That is how you substitute somebody else's
chapter for your own:

```
lore_register("lm", "Our Own Records", "our_records.amd")
```

## Not wanting somebody else's lore

Content lives in its own addon so you can decline it. LegendaryMissions keeps its fiction
in `lm_lore`, separate from the `documents` addon that provides the reader and the quest
log. Omit `lm_lore` from your `story.json` and you keep the screens without the Zunok
helpfile.

That is the general rule for building on a library: an addon that holds **content** is one
you opt into, while an addon that holds **machinery** is one you depend on.

## Help is not lore

The **Help** tab is separate on purpose. "How do I use the Weapons console" is
instructions, and filing it inside the fiction would make both harder to read.
