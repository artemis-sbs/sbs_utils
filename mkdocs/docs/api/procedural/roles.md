# The roles system

The SpaceObject class has methods for assigning and removing 'roles' to objects.

Roles are like sides but can be more dynamic and are not seen by the simulation.
You can have multiple roles on an object. Roles can be used in targeting etc.



** This need more documentation**
placing examples for now


## Adding a role

=== "Python"
      ```
      add_role(some_id, 'spy')
      ```

## Remove a role


=== "Python"
      ```
      remove_role(some_id, 'spy')
      ```


## Check for a role
------------------------------

=== "PyThon"
      ```
      if has_role(some_id, 'spy')
            pass
      ```

# Using with targeting


=== "PyThon"
      ```
      close = closest(some_id, role("spy"))
      # class names are included in roles
      close = closest(some_id, role("station"))
      # side is included in roles
      close = closest(some_id, role("tsn"))
      ```

# API: Roles

::: sbs_utils.procedural.roles