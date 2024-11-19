# User Interaction routes
There are a number of events that are routed due to user interactions.


These values are provided to the task when running the routes.

For comms:

- COMMS_ORIGIN_ID - The engine ID of the player ship for the comms console
- COMMS_ORIGIN - The python Agent of the player ship for the comms console
- COMMS_SELECTED_ID - The engine ID of the Agent being communicated with
- COMMS_SELECTED - The python Agent of being communicated with

For comms2d:

- COMMS2D_ORIGIN_ID - The engine ID of the player ship for the comms console
- COMMS2D_ORIGIN - The python Agent of the player ship for the comms console
- COMMS2D_SELECTED_ID - The engine ID of the Agent being communicated with
- COMMS2D_SELECTED - The python Agent of being communicated with

For normal:

- NORMAL_ORIGIN_ID - The engine ID of the player ship for the comms console
- NORMAL_ORIGIN - The python Agent of the player ship for the comms console
- NORMAL_SELECTED_ID - The engine ID of the Agent being communicated with
- NORMAL_SELECTED - The python Agent of being communicated with

For Weapons:

- WEAPONS_ORIGIN_ID - The engine ID of the player ship for the comms console
- WEAPONS_ORIGIN - The python Agent of the player ship for the comms console
- WEAPONS_SELECTED_ID - The engine ID of the Agent being communicated with
- WEAPONS_SELECTED - The python Agent of being communicated with

For Science:

- SCIENCE_ORIGIN_ID - The engine ID of the player ship for the comms console
- SCIENCE_ORIGIN - The python Agent of the player ship for the comms console
- SCIENCE_SELECTED_ID - The engine ID of the Agent being communicated with
- SCIENCE_SELECTED - The python Agent of being communicated with

For select/grid:

- COMMS_ORIGIN_ID - The engine ID of the player ship for the comms console
- COMMS_ORIGIN - The python Agent of the player ship for the comms console
- COMMS_SELECTED_ID - The engine ID of the Agent being communicated with
- COMMS_SELECTED - The python Agent of being communicated with

For all other grid:

- GRID_ORIGIN_ID - The engine ID of the player ship for the comms console
- GRID_ORIGIN - The python Agent of the player ship for the comms console
- GRID_SELECTED_ID - The engine ID of the Agent being communicated with
- GRID_SELECTED - The python Agent of being communicated with

All also receive the raw event in the variable EVENT

## Selection
When the selection is changed on a console.

=== ":mast-icon: {{ab.m}}"   
    ```
    //select/comms
    ```


=== ":mast-icon: {{ab.m}}"   
    ```
    //select/comms2d
    ```


=== ":mast-icon: {{ab.m}}"   
    ```
    //select/normal
    ```


=== ":mast-icon: {{ab.m}}"   
    ```
    //select/weapons
    ```


=== ":mast-icon: {{ab.m}}"   
    ```
    //select/science
    ```


=== ":mast-icon: {{ab.m}}"   
    ```
    //select/grid
    ```



## Focus
When the focus is changed on a console. This is similar to select, but will not run if the selected item was already selected.

=== ":mast-icon: {{ab.m}}"   
    ```
    //focus/comms
    ```
text

=== ":mast-icon: {{ab.m}}"   
    ```
    //focus/comms2d
    ```
text

=== ":mast-icon: {{ab.m}}"   
    ```
    //focus/normal
    ```
text

=== ":mast-icon: {{ab.m}}"   
    ```
    //focus/weapons
    ```
text

=== ":mast-icon: {{ab.m}}"   
    ```
    //focus/science
    ```
text

=== ":mast-icon: {{ab.m}}"   
    ```
    //focus/grid
    ```
text



## Point 
When the 2D View is clicked on an open area the point is available.

the EVENT.source_point has the point vaule.


=== ":mast-icon: {{ab.m}}"   
    ```
    //point/comms2d
    ```

text

=== ":mast-icon: {{ab.m}}"   
    ```
    //point/normal
    ```

text

=== ":mast-icon: {{ab.m}}"   
    ```
    //point/comms
    ```

text

=== ":mast-icon: {{ab.m}}"   
    ```
    //point/weapons
    ```

text

=== ":mast-icon: {{ab.m}}"   
    ```
    //point/science 
    ```

text

=== ":mast-icon: {{ab.m}}"   
    ```
    //point/grid
    ```

text


## Object 
This is currently just for the grid. When a grid object arrives at a path location.

=== ":mast-icon: {{ab.m}}"   
    ```
    //object/grid
    ```
    

