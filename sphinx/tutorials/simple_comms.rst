Tutorial: Simple Comms
===================================



Create mission 
*********************

Create the mission from using a starter mission.


.. tabs::
   .. code-tab:: shell mast

    .\fetch artemis-sbs mast_starter simple_ai    


   .. code-tab:: shell PyMast
    
    .\fetch artemis-sbs pymast_starter simple_ai


Add more stations
======================


.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
      # Create a space station
      ds1 = npc_spawn(1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = npc_spawn(1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")


   .. code-tab:: py PyMast
      :emphasize-lines: 3

      # Create a space station
      ds1 = Npc().spawn(self.sim, 1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = Npc().spawn(self.sim, -1000,0,1000, "DS2", "tsn", "starbase_command", "behav_station")
      

Add role
===============

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 4
      
      # Create a space station
      ds1 = npc_spawn(1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = npc_spawn(1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")
      do add_role({ds1.id, ds2.id}, "Station")


   .. code-tab:: py PyMast
      :emphasize-lines: 4

      # Create a space station
      ds1 = Npc().spawn(self.sim, 1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = Npc().spawn(self.sim, 1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")
      query.add_role({ds1.id, ds2.id}, "Station")
      


Add a router for comms
*************************


Routers create tasks automatically a needed and starts running at a specific label.
That label that uses logic to route to other labels based on certain conditions.

.. tabs::
   .. code-tab:: mast Mast

         # at the top of the mast file add 
         # Configure the label where comms routing occurs
         route comms comms_route

   .. code-tab:: py PyMast

       # in the __init__ of the story add 
       self.route_comms(self.comms_route)
    

Add router label and logic 
****************************

This label is called for a player ship (COMMS_ORIGIN_ID)
and the COMMS_SELECTED_ID ship has not been communicated with
this is used to resolve where to START the conversation with the TO ship
COMMS_SELECTED_ID is the id of the target



.. tabs::
   .. code-tab:: mast Mast
      
         ================ comms_route ==================
         if has_role(COMMS_SELECTED_ID, 'Station'):
            jump comms_station
         elif has_role(COMMS_SELECTED_ID, 'raider'):
            jump npc_comms
         end_if

         # Anything else has no comms buttons
         # and static as the id
         comms_info "static"

         ->END


   .. code-tab:: py PyMast

         @label()
         def comms_route(self):
            if has_role(COMMS_SELECTED_ID, 'Station'):
               yield self.jump(comms_station)
            elif has_role(COMMS_SELECTED_ID, 'raider'):
               yield self.jump(npc_comms)

            # Anything else has no comms buttons
            # and static as the id
            self.comms_info("static")
            yield self.end()


.. tabs::
   .. code-tab:: mast Mast

      ================ npc_comms ==================

      await comms:
         + "Hail":
            receive "We will destroy you, disgusting Terran scum!"
         + "Surrender now":
            receive  """OK we give up"""
      end_await
      jump npc_comms



   .. code-tab:: py PyMast

      @label()
      def npc_comms(self):

         def button_hail(story, comms):
            comms.receive("We will destroy you, disgusting Terran scum!")

         def button_surrender(story, comms):
            comms.receive("""OK we give up""")

         self.await_comms{{
            "Hail": button_hail,
            "Surrender now": button_surrender
            })
            yield self.jump(npc_comms)

.. tabs::
   .. code-tab:: mast Mast

      ======== comms_station ====== 
      
      await comms:
         + "Hail":
            transmit "Hello"
            receive "Yo"

      end_await
      jump comms_station


   .. code-tab:: py PyMast

      @label()
      def comms_station(self):

         def button_hail(story, comms):
            # Message to station
            comms.transmit("Hello")
            #message from station
            comms.receive("Yo")

         self.await_comms{{
            "Hail": button_hail,
            })
            yield self.jump(comms_station)

    



    



