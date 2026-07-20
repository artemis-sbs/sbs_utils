# sbs_utils Test Range

A standalone **visual** test-range mission for **sbs_utils** library features.

It complements the headless unit tests: `sbs_utils/tests/` proves the library is
**correct** (asserting emitted `send_gui_*`, structures, etc.); this range lets you
**look at** a feature in a running console — pick a map, see it render, click it.

## Run it

From `missions/sbs_utils/`:

```
# see a container in the browser mock
python -m cosmos_dev.mission_runner test_range --map gui_list       --gui --use-working-tree
python -m cosmos_dev.mission_runner test_range --map gui_grid       --gui --use-working-tree
python -m cosmos_dev.mission_runner test_range --map gui_table      --gui --use-working-tree
python -m cosmos_dev.mission_runner test_range --map gui_containers --gui --use-working-tree

# smoke-check a map loads with no runtime error (no window)
python -m cosmos_dev.mission_runner test_range --map gui_list --test 8 --use-working-tree
```

`--use-working-tree` runs *this* working tree's sbs_utils, so you see your local
changes rather than the packaged `.sbslib`.

## Maps

| Map | Shows |
|---|---|
| `gui_list` | `gui_list` — a data-bound listbox with a MAST-authored row (scrolls + selects) |
| `gui_grid` | `gui_grid` — items flowed into even columns (a button palette) |
| `gui_table` | `gui_table` — declarative columns + header, with control cells |
| `gui_containers` | all three side by side, for a quick eyeball |

## Adding a map

Drop a `maps/<name>.mast` with an `@map/<name> "Title"` header that reroutes to a
server label which builds the layout and ends in `await gui()`, then `import` it
in `story.mast`. No test harness needed — this range is for looking, not asserting.
