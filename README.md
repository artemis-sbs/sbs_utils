# SBS_Utils
SBS utils are a higher level abstraction for creating and managing things in Artemis Cosmos python.

## Documentation
For the full documentaton see:
[Library Documentation](https://artemis-sbs.github.io/sbs_utils/index.html)


## Contributing
To develop and change this library clone this repo into the missions directory in Artemis Cosmos.

This has a stub mission file for running tests.

### update the docs. run:
When adding to this library, the documentation should be updated in the sphinx folder.

to update the docs run:
```
sphinx\make html
```

note: The docs use Graphviz to generate some images.
the location of graphviz may need to change in the conf.py for sphinx since it is hard coded to a location that is not likely the same for everyone.


### Creating a version release and sbslib
This uses github actions to create the release when a tag is created.

```
git tag -a vXX.XX.XX -m "Some comment"
git push --tags
```