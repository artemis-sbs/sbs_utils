Entry Points, events, and handlers
===================================

Computer programs need a place to start executing code. This is where the system calls code. This is called an entry point where the system enters code that extends it.

Artemis Cosmos has multiple entry points. These are where the Artemis Cosmos engine calls code in a missions script.

Artemis Cosmos has certain events that occur where it allows scripters do alter how the game runs.

The events include:

- Presenting GUI elements
- When users interact with the presented GUI elements
- When a client connects to the server
- Periodically while the simulation runs called a 'tick'
- When elements of the game are damaged
- When a user selects something on a console
- When a user presses a comms button

Mission script handlers
--------------------------

At the highest level a mission script provides these entry points by supplying a handler function.

A mission script provides handler functions for all the entry points Artemis Cosmos expects.

The following functions need to be provided:

- HandlePresentGUI
- HandlePresentGUIMessage
- HandleClientConnect
- HandleSimulationTick
- HandleDamageEvent
- HandleConsoleObjectSelection
- HandleCommsButton

And more could be added over time.


Coding handlers
----------------

The most basic mission needs to supply a function for each of these. When the events occurs in the Artemis Cosmos engine, the engine will call the entry point, and without the handler provided it will crash the mission script. 

.. code-block:: python
    
    def HandlePresentGUI(sim):
        pass

    def HandlePresentGUIMessage(sim, message_tag, clientID, data):
        pass

    def HandleClientConnect(sim, clientID):
        pass
    
    def  HandleSimulationTick(sim):
        pass

    def HandleDamageEvent(sim, damage_event):
        pass

    def HandleConsoleObjectSelection(sim, console, obj_selected_id, ship_id):
        pass

    def HandleCommsButton(sim, button_tag, ship_id, obj_selected_id):
        pass

sbs_utils systems and default handlers
----------------------------------------

sbs_utils provides two things to make creating missions scripts simpler.

- Systems
- Default handlers


sbs_utils systems
^^^^^^^^^^^^^^^^^^^^^^

Systems provide a for handling things in a common why.

- The GUI System
- The tick Dispatcher
- The Damage Dispatcher
- The Console Dispatcher


The Gui system is handles presentation of Guis. It does so by handling the HandlePresentGui, HandlePresentGUIMessage, and HandleClientConnect.
The Tick Dispatcher handle the HandleSimulationTick by providing time delayed function calls.
The Damage Dispatcher is for handling the HandleDamageEvent.
The Console Dispatcher  is for handling the HandleConsoleObjectSelection and HandleCommsButton.

default handlers
^^^^^^^^^^^^^^^^^^^

sbs_utils provides a default implementation of all the Entry point handlers.
The default behavior implements the hnadlers to call the appropriate sbs_utils system as described above.

to use the default handlers and connect a mission script to these systems.

In a mission's script.py import the handlers with the one line below. With that that should be it. The mission script should now be set to use sbs_utils systems and provide all handlers.

.. code-block:: python
    
    from lib.sbs_utils.handlerhooks import *


A mission script can override these defaults by defining the handler. 
If this is done, you may want to check the code to make sure the handler still calls any of the sbs_utils system it should.

.. code-block:: python
    
    from lib.sbs_utils.handlerhooks import *

    #overriding default
    def HandleClientConnect(sim, clientID):
        # call the gui system's code
        Gui.add_client(sim,clientID)
        # add you additional code


























