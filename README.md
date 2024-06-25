# SBS_Utils
SBS utils are a higher level abstraction for creating and managing things in Artemis Cosmos python.

## Documentation
For the full documentaton see:
[Library Documentation](https://artemis-sbs.github.io/sbs_utils/index.html)


## Contributing
To develop and change this library clone this repo into the missions directory in Artemis Cosmos.

This has a stub mission file for running tests.

### update the docs. run:
When adding to this library, the documentation should be updated in the mkdocs folder.

To use the doc you need to install several python libraries:

```
pip install mkdocs-material
pip install mkdocstrings
pip install mkdocstrings[python]

```

To view the docs with live updates as you edit:

```
cd mkdocs
mkdocs serve
```

to publish the docs github :

```
cd mkdocs
mkdocs gh-deploy --force 
```

note: The docs use Graphviz to generate some images.
the location of graphviz may need to change in the conf.py for sphinx since it is hard coded to a location that is not likely the same for everyone.


### Creating a version release and sbslib
This uses github actions to create the release when a tag is created.

```
git tag -a vXX.XX.XX -m "Some comment"
git push --tags
```

## redo release
Delete the tag and the create it again
```
git tag -d tagname
git push --delete origin tagname
```

## Make sure to

Update the docs 
- delete docs content (except nojekyl)

```
sphinx\make html
```

Update typings
- delete typings content
- Run the script in artemis
- select 'stubgen'


------------------------
Post EA3 stuff

- Add with statement
- add margin to layout objects, border?
- add gui_sub_section
- add gui_canvas
- add gui_text_area


``` py
//spawn if has_roles(SPAWNED_ID, "monster, typhon, classic")

-- ai_loop
->END if  not object_exists(SPAWNED_ID)

_target = closest(SPAWNED_ID, broad_test_around(SPAWNED_ID, 5000,5000, 0xf0)-role("__terrain__")-role("monster"))
if _target is None:
    clear_target(SPAWNED_ID)
else:
    #print("Typhon hunting")
    target(SPAWNED_ID, _target)

await delay_sim(seconds=5)

jump ai_loop
```

``` py
@spawn
def monster_ai():
    task = FrameContext.task
    SPAWNED_ID = task.get_variable("SPAWNED_ID")

    if not has_roles(SPAWNED_ID, "monster, typhon, classic"):
        yield PollResults.OK_FAIL

    if  not object_exists(SPAWNED_ID):
        yield POllResults.OK_END

    _target = closest(SPAWNED_ID, broad_test_around(SPAWNED_ID, 5000,5000, 0xf0)-role("__terrain__")-role("monster"))
    if _target is None:
        clear_target(SPAWNED_ID)
    else:
        #print("Typhon hunting")
        target(SPAWNED_ID, _target)

    yield AWAIT(delay_sim(seconds=5))
    yield jump(monster_ai)
```