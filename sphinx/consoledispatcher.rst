Console Dispatcher
======================
The ConsoleDispatcher is used to route console related messages to callback functions. Generally this is done to classes.


Artemis Cosmos console system
------------------------------
Artemis Cosmos calls the script function HandleConsoleObjectSelection when an item is selected on a console.

Artemis Cosmos calls the script function HandleCommsButton when a button is pressed on a comms console.

The ConsoleDispatcher is intended receive these and route them to callback functions.
This can further be used to direct these to classes that represent the ships enabling the handling of this code to be handled in context of the ship(s) involved.

The HandleConsoleObjectSelection should call :py:meth:`~sbs_utils.consoledispatcher.ConsoleDispatcher.dispatch_select`
The HandleCommsButton should call :py:meth:`~sbs_utils.consoledispatcher.ConsoleDispatcher.dispatch_comms_message`



.. code-block:: python

   def HandleConsoleObjectSelection(sim, console, obj_selected_id, ship_id):
      ConsoleDispatcher.dispatch_select(sim,ship_id, console,obj_selected_id)

   def HandleCommsButton(sim, button_tag, ship_id, obj_selected_id):
      ConsoleDispatcher.dispatch_comms_message(sim, button_tag, ship_id, obj_selected_id)


Example: Adding Comms to a class
--------------------------------

The best way to use the ConsoleDispatcher is to add comms to a :py:class:`~sbs_utils.spaceobject.SpaceObject` using the :py:meth:`~sbs_utils.consoledispatcher.MCommunications.comms_selected` and :py:class:`~sbs_utils.consoledispatcher.MCommunications` mixin class.
and provide an implementation of  :py:meth:`~sbs_utils.consoledispatcher.MCommunications.comms_selected` and :py:meth:`~sbs_utils.consoledispatcher.MCommunications.comms_message`

To enable comms call :py:meth:`~sbs_utils.consoledispatcher.MCommunications.enable_comms`. This should be called after the SpaceObject has spawned and has an id.

:py:meth:`~sbs_utils.consoledispatcher.MCommunications.enable_comms` takes a face description and it will set self.face_desc.

This can be done on a non-player ship and a PlayerShip. The system will send the proper information.

For a non-player ship the player id is sent.

.. code-block:: python

   class Harvester(SpaceObject, MSpawnActive, MCommunications):
      def some_method(self):
         self.enable_comms(some_face_desc)

      def comms_selected(self, sim, player_id):
         pass

      def comms_message(self, sim, message, player_id):
         pass

For a PlayerShip the other ship id is sent.

.. code-block:: python
   
   class Player(PlayerShip, MCommunications):
      def some_method(self):
         self.enable_comms(some_face_desc)

      def comms_selected(self, sim, other_id):
         pass

      def comms_message(self, sim, message, other_id):
         pass


Example: Sending selection info
------------------------------

A non player ship should send its selection info in comms_selected. This will update the comms to show the name and face of the ship when selected.
The self.face_desc can be used, or the face can be altered based on game conditions e.g. change to angry, changed to new face (change of command) etc.

.. code-block:: python

   class Harvester(SpaceObject, MSpawnActive, MCommunications):
      def comms_selected(self, sim, player_id):
         sbs.send_comms_selection_info(player_id, self.face_desc, "green", self.comms_id)

Example: Sending comms buttons
------------------------------

comms_select is also the place where comms button could be sent to the comms console.
This can be done based on the state of the ship.

.. code-block:: python

   class Harvester(SpaceObject, MSpawnActive, MCommunications):
      def comms_selected(self, sim, player_id):
         sbs.send_comms_selection_info(player_id, self.face_desc, "green", self.comms_id)

        # if Empty it is waiting for what to harvest
        if self.state == HarvesterState.EMPTY_WAITING:
            sbs.send_comms_button_info(player_id, "blue", "Harvest energy", "get_energy")
            sbs.send_comms_button_info(player_id, "red", "Harvest minerals", "get_mineral")
            sbs.send_comms_button_info(player_id, "gold", "Harvest rare metals", "get_rare")
            sbs.send_comms_button_info(player_id, "silver", "Harvest alloys", "get_alloy")
            sbs.send_comms_button_info(player_id, "green", "Harvest replicator fuel", "get_food")

        if self.state == HarvesterState.FULL_WAITING:
            for base in self.find_close_list(sim, 'Spacedock'):
                sbs.send_comms_button_info(player_id, "yellow", f"Head to {base.obj.comms_id}", f"{base.obj.id}")

Example: handling comms button messages
-----------------------------------------
comms_message is called when a comms button is pressed.
The message is the button_tag.

.. code-block:: python

   class Harvester(SpaceObject, MSpawnActive, MCommunications):
     def comms_message(self, sim, message, player_id):

        if message.isnumeric():
            other_id = int(message)
            self.target(sim,other_id, False)
            # every ten seconds r
            self.tsk = TickDispatcher.do_interval(sim,self.think, 5)
            self.tsk.base_id = other_id
            self.state = HarvesterState.RETURNING
            return

        match message:
            case 'get_energy':
                self.resource_type = ResourceTypes.ENERGY
                self.send_comms('Gathering energy', 'green', player_id)
                self.state = HarvesterState.HARVESTING
                self.find_target(sim)
            case 'get_mineral':
                self.resource_type = ResourceTypes.MINERAL
                self.send_comms('Gathering minerals', 'green', player_id)
                self.state = HarvesterState.HARVESTING
                self.find_target(sim)
            case 'get_rare':
                self.resource_type = ResourceTypes.RARE_METAL
                self.send_comms('Gathering rare metals', 'green', player_id)
                self.state = HarvesterState.HARVESTING
                self.find_target(sim)
            case 'get_alloy':
                self.resource_type = ResourceTypes.ALLOY
                self.send_comms('Gathering alloys', 'green', player_id)
                self.state = HarvesterState.HARVESTING
                self.find_target(sim)
            case 'get_food':
                self.resource_type = ResourceTypes.FOOD
                self.send_comms('Gathering replicator fuel', 'green', player_id)
                self.state = HarvesterState.HARVESTING
                self.find_target(sim)
            case '_':
                return

        # Clear buttons?
        sbs.send_comms_selection_info(player_id, self.face_desc, "green", self.comms_id)

non class console handling
----------------------------------------

MCommunications is useful for any class. However, if their is another way desired to handle console messages.

:py:meth:`~sbs_utils.consoledispatcher.ConsoleDispatcher.add_select` adds any callback to the console dispatcher system for handling selection.

:py:meth:`~sbs_utils.consoledispatcher.ConsoleDispatcher.add_message` adds any callback to the console dispatcher system for handling messages.

.. code-block:: python

   def some_select_handler(self, sim, other_id):
      pass

   def some_message_handler(self, sim, message, other_id):
      pass

   def some_function(self, sim, message, player_id):
      ConsoleDispatcher.add_select(some_id, 'comms_targetUID', some_select_handler)
      ConsoleDispatcher.add_message(some_id, 'comms_targetUID', some_message_handler)




API consoledispatcher module
-----------------------------------

.. automodule:: sbs_utils.consoledispatcher
   :members:
   :undoc-members:
   :show-inheritance:
