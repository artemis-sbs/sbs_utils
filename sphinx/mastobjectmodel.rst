########################
SBS Utils Object Model
########################

Sbs Utils creates an oObject model. This Object Model is used by Mast and PyMast.

Mast needs participants in the story. In stories Artemis Cosmos these participants are:

* The Story itself (aka the server, the game, the engine or the world)
* Bridge Crew (The player consoles)
* The Player ships (Ships control by the Bridge Crew)
* Non-Player ships Starbases, Enemy Ships, Friendly Ships (Things controled by script)
* The terrain element asteroids, pickups, nebula etc.
* Non-Player Crew and Characters (Seen as faces in engineering, Comms etc.)
* Internals ship location (Rooms and other things)

These agents/participants are the things in the Artemis Cosmos world. Each of this agents can have stories and tasks associated with them. 


* Engine objects
    * engine data set
* Script Objects
    * roles
    * Inventory
    * Linked


Engine, script and persisted
*****************************

The object model is designed to work with three sets of the model data: 

* Engine
* Script
* Persisted

Engine data
====================

Engine data are in memory objects that the engine manages.

Engine data is the data the the Artemis Cosmos game engine deals with. This the data that get ships, etc drawn on screen and the engine manages low level behavior (e.g. moving a ship from a pont a to point b)

Engine data has:

* The object its self
* A engine type (Player, Active, Passive)
* data tag
* tick type / behavior
* A data set

Engine object 
-------------------

The engine object provides the raw object in the engine.

There are two types of engine objects 

*  :py:class:`~sbs.space_object`
*  :py:class:`~sbs.grid_object`


 It has data the is common to all engine objects.

* side
* position
* steering properties

An engine data has a 'data set' this is data that can be different for space objects. e.g. a player ship data set may have ship systems, while an asteroid does not.

The engine 'type' is the high level behavior type of player, active, and passive. 

* player are player ships.
* Active are npc, space docks, friendly and enemy ships etc.
* Passive are terrain e.g. nebula, asteroids etc.

The data tag relates to the artwork and other properties that are assigned to the object. The values are defined in ship_dat.json. The values are used by the engine, and some of these values are available in the data set.

The tick type is a engine level behavior setting. For example specifying the object is a player ship, npc ship, vs. a space dock.



that script can get and set data that the engine uses. Scripts can change this data and see those change reflected in the engine (e.g. Add torpedoes to a ship.)


Script data
====================


Script data are python object in memory that script manages.

Script data is a reflection of the Engine Data, and can also be used to synchronize with a persisted model.


*  :py:class:`~sbs_utils.spaceobject.SpaceObject`
*  :py:class:`~sbs_utils.gridobject.GridObject`



- :py:class:`~sbs_utils.objects.PlayerShip`
- :py:class:`~sbs_utils.objects.Npc` 
- :py:class:`~sbs_utils.objects.Active`
- :py:class:`~sbs_utils.objects.Terrain`
- :py:class:`~sbs_utils.objects.Passive`

role
---------

Script object can have multiple "roles". Roles are similar to 'hashtags' in social media apps. You can tag script objects with a role. 

Links 
-------------

Links are named relationship between two objects.


Inventory
------------

Inventory is data that can be added to any object.





Persisted data 
====================

NOTE: This is speculative of how the persisted data will work in the future.
NOTE: This is just really notes on what is hoped to accomplish


Persistence will persist:

* Engine Objects 
* roles
* Links
* Inventory


There should be a db_query that has similar functions to the query module.
e.g. so that you can retrieve from the data base using similar set operation

sector_objects = db_query.broadtest(100000, 100000, 150000, 150000, -1)
db_query.spawn(sector_objects)




.. tabs::

   .. code-tab:: sqlite3 SqlLite


        CREATE TABLE engine_object (
            db_id INTEGER NOT NULL PRIMARY KEY,
            data JSON NOT NULL
            -- What else 
        );

   .. code-tab:: json Firebase

     "engine_objects": {
        "<db_id>": {
            "data": { . . .}
        }
     }



.. tabs::

   .. code-tab:: sqlite3 SqlLite

        CREATE TABLE role (
        role TEXT NOT NULL,
        FOREIGN KEY (db_id) REFERENCES engine_object (db_id) 
                    ON DELETE CASCADE ON UPDATE NO ACTION,
        PRIMARY KEY(role, db_id)
        );

   .. code-tab:: json Firebase

        "roles": {
            "<role>": {1,2,3,}
         }

.. tabs::

   .. code-tab:: sqlite3 SqlLite

        CREATE TABLE link (
        link TEXT NOT NULL,
        FOREIGN KEY (from_db_id) REFERENCES engine_object (db_id) 
                    ON DELETE CASCADE ON UPDATE NO ACTION,
        FOREIGN KEY (to_db_id) REFERENCES engine_object (db_id) 
                    ON DELETE CASCADE ON UPDATE NO ACTION,
        PRIMARY KEY(role, from_db_id, to_db_id)
        );

   .. code-tab:: json Firebase

        "links":{
            "<link>":  {(1,9), (2,7) , (3,8)}
        }     


.. tabs::

   .. code-tab:: sqlite3 SqlLite

        CREATE TABLE inventory (
        name TEXT NOT NULL,
        FOREIGN KEY (db_id) REFERENCES engine_object (db_id) 
                    ON DELETE CASCADE ON UPDATE NO ACTION,
        value JSON NOT NULL,
        PRIMARY KEY(role, db_id, value)
        );

   .. code-tab:: json Firebase

    // Not sure this one is right
    "inventory":{
        "<key>":  {
            "<db_id>": <value>
        }
    }     
