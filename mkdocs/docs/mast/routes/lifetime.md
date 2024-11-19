# Lifetime routes
These routes are related to the lifetime of Agents


## Spawn
 
- SPAWNED_ID
- SPAWNED

=== ":mast-icon: {{ab.m}}"   
    ```
    //spawn
    ```

For engineering grid  

=== ":mast-icon: {{ab.m}}"   
    ```
    //spawn/grid
    ```

## Collision

- COLLISION_ORIGIN_ID
- COLLISION_SELECTED_ID

=== ":mast-icon: {{ab.m}}"   
    ```
    //collision/passive
    ```

=== ":mast-icon: {{ab.m}}"   
    ```
    //collision/interactive
    ```

## Damage internal

- DAMAGE_ORIGIN_ID


=== ":mast-icon: {{ab.m}}"   
    ```
    //damage/internal
    ```

=== ":mast-icon: {{ab.m}}"   
    ```
    //damage/heat
    ```

## Damage object

- DAMAGE_ORIGIN_ID
- DAMAGE_PARENT_ID
- DAMAGE_SELECTED_ID

- DAMAGE_SOURCE_ID
- DAMAGE_TARGET_ID

=== ":mast-icon: {{ab.m}}"   
    ```
    //damage/object
    ```

## Destroy and killed

- DESTROYED_ID

=== ":mast-icon: {{ab.m}}"   
    ```
    //damage/destroy
    ```

- DAMAGE_ORIGIN_ID

=== ":mast-icon: {{ab.m}}"   
    ```
    //damage/killed
    ```

## Fighter docking

This maybe refactored.

So use this route sparingly as it will change.
Currently it is triggered when a fighter request dock.
It currently use the raw EVENT data

=== ":mast-icon: {{ab.m}}"   
    ```
    //dock/hangar
    ```


## Ship Docking
Currently the docking code does not use routes. In the future it will.
The refactor of docking did not make it into 1.0
