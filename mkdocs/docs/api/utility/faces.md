# The Faces module

The faces module is used for creating face images for comms screens.

Faces are based off of a set of image textures with a grid of cell images.

The set of images is defined in allFaceFiles.txt. This file defines a key name for the texture and an image in the data\\graphics folder.
Cells are 512x512 and the total images must be a valid DirectX12 pixel size.

This set of images can be extended with new textures added to allFacesFiles.txt

## Face generation functions

The faces module has a set of functions to generate random faces for the base set of face image textures provided by Artemis Cosmos.

- `random_skaraan`
- `random_torgoth`
- `random_kralien`
- `random_arvonian`
- `random_zimni`
- `random_terran`
- `random_terran_male`
- `random_terran_female`
- `random_terran_fluid`


 === "python"
    ```
    self.face_desc = random_skaraan()
    ```

There are also function to make it easier to create specific faces by passing indexes to define indexes that represent cells containing know art images for things like hair, eyes, mouth etc.
It may take some experimentation to find the values for your character, but this is a simplified way to create repeatable characters.
Other ways to create consistent faces is to use one of the predefined `Characters` or hand code a face string.

- `skaraan`
- `torgoth`
- `kralien`
- `arvonian`
- `zimni`
- `terran`



=== "Python"
    ```
      self.face_desc = skaraan(0, 1,2,1,3)
    ```

## Character Faces

The class `Characters` has a list of predefined face strings.

These are a good examples for creating a face string by hand.


## The faces string syntax

Face string is a set of layers that reference a cell in a texture separated by a semi-colon.
The first layer is the lowest layer.

<texture-tag> <color-tint> <coll> <row> \[<x-offset>\] \[<y-offset>\];

- <texture-tag> the texture tag specified in allFaceFiles.txt
- <color-tint> a Tint to add to the layer. e.g. changing skin tone
- <coll> the cell's col
- <row> the cell's row
- <x-offset> optional to offset the layer in x
- <y-offset> optional to offset the layer in y


## API: faces module


::: sbs_utils.faces
   