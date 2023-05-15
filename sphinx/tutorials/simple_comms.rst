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
         route comms select comms_route

   .. code-tab:: py PyMast

       # in the __init__ of the story add 
       self.route_comms_select(self.comms_route)
    

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

    
Update router for internal comms
**********************************

This label is called for a player ship (COMMS_ORIGIN_ID)
and the COMMS_SELECTED_ID ship has not been communicated with
this is used to resolve where to START the conversation with the TO ship
COMMS_SELECTED_ID is the id of the target



.. tabs::
   .. code-tab:: mast Mast
         :emphasize-lines: 3-8
      
         ================ comms_route ==================

         if COMMS_SELECTED_ID == COMMS_ORIGIN_ID:
            # This is the same ship
            jump internal_comms
         elif has_role(COMMS_SELECTED_ID, 'Station'):
            jump comms_station
         elif has_role(COMMS_SELECTED_ID, 'raider'):
            jump npc_comms
         end_if

         # Anything else has no comms buttons
         # and static as the id
         comms_info "static"

         ->END



   .. code-tab:: py PyMast
         :emphasize-lines: 3-7

         @label()
         def comms_route(self):
            if self.task.COMMS_SELECTED_ID == self.task.COMMS_ORIGIN_ID:
                  # This is the same ship
                  yield self.jump(self.internal_comms)
            elif query.has_role(self.task.COMMS_SELECTED_ID, 'Station'):
                  yield self.jump(self.comms_station)
            elif query.has_role(self.task.COMMS_SELECTED_ID, 'raider'):
                  yield self.jump(self.npc_comms)

            # Anything else has no comms buttons
            # and static as the id
            self.comms_info("static")
            yield self.end()



Add logic for internal comms
**********************************


.. tabs::
   .. code-tab:: mast Mast
         :emphasize-lines: 3-8
      
        ================ internal_comms ==================
         #
         # Setup faces for the departments
         #
         doctor = random_terran()
         biologist = random_terran()
         counselor = random_terran()
         major = random_terran()
         sec = "Security"

         ================ internal_comms_loop ==================
         #
         # Shows button color, face and title overrides
         #
         await comms:
            + "Sickbay" color "blue":
               receive "The crew health is great!" title "sickbay" face "{doctor}" color "blue"
            + "Security" color "red":
               receive  "All secure" title sec face major color "red"
            + "Exobiology" color "green":
               receive  "Testing running, one moment" title "Exobiology" face biologist color "green"
               # It is best to schedule delayed responses so the comms buttons are not stalled
               schedule test_finished
            + "counselor" color "cyan":
               receive  "Something is disturbing the crew" title "counselor" face counselor color "cyan"
               #
               # but you can delay comms, There will be no buttons during this delay
               #
               delay sim 3s
               receive  "Things feel like they are getting worse" title "counselor" face counselor color "cyan"
         end_await
         -> internal_comms_loop




   .. code-tab:: py PyMast
         :emphasize-lines: 3-7

         #================ internal_comms ==================
         @label()
         def internal_comms(self):
            #
            # Setup faces for the departments
            #
            self.task.doctor = faces.random_terran()
            self.task.biologist = faces.random_terran()
            self.task.counselor = faces.random_terran()
            self.task.major = faces.random_terran()
            yield self.jump(self.internal_comms_loop)

         # ================ internal_comms_loop ==================
         @label()
         def internal_comms_loop(self):
            def button_sickbay(story, comms):
                  comms.receive("The crew health is great!", face=story.task.doctor, color="blue", title="sickbay")
            def button_security(story, comms):
                  comms.receive("All secure", face=story.task.major, color="red", title="security")
            def button_exobiology(story, comms):
                  comms.receive("Testing running, one moment", face=story.task.biologist, color="green", title="exobiology")
            def button_counselor(story, comms):
                  comms.receive("Something is disturbing the crew", face=story.task.counselor, color="cyan", title="counselor")
                  yield self.task.delay(seconds=2, use_sim=True)
                  comms.receive("Things feel like they are getting worse", face=story.task.counselor, color="cyan", title="counselor")
            
            yield self.await_comms({
                  "sickbay": button_sickbay,
                  "security": button_security,
                  "exobiology": button_exobiology,
                  "counselor": button_counselor,
            })
            # loop
            yield self.jump(self.internal_comms_loop)


Add a router for engineering comms
**************************************


Routers create tasks automatically a needed and starts running at a specific label.
That label that uses logic to route to other labels based on certain conditions.

.. tabs::
   .. code-tab:: mast Mast
      :emphasize-lines: 2
         
         route comms select comms_route
         route grid select damcon_route


   .. code-tab:: py PyMast
      :emphasize-lines: 3

      # in the __init__ of the story add 
      self.route_comms_select(self.handle_comms)
      self.route_grid_select(self.damcon_route)



Create routing logic for  engineering comms
**********************************************

.. tabs::
   .. code-tab:: mast Mast
         
         ================ damcon_route ==================

         # COMMS_SELECTED_ID is the id of the target

         if has_role(COMMS_SELECTED_ID, 'flint'):
            jump comms_flintstone
         elif has_role(COMMS_SELECTED_ID, 'rubble'):
            jump comms_rubble
         end_if
         ->END



   .. code-tab:: py PyMast
      
      # ================ damcon_route ==================
      @label()
      def damcon_route(self):
         # COMMS_SELECTED_ID is the id of the target
         if query.has_role(self.task.COMMS_SELECTED_ID, 'flint'):
               yield self.jump(self.comms_flintstone)
         elif query.has_role(self.task.COMMS_SELECTED_ID, 'rubble'):
               yield self.jump(self.comms_rubble)



Create routing logic for flint's
**********************************************

.. tabs::
   .. code-tab:: mast Mast
         
         ================ comms_flintstone ==================
         await comms:
            + "Hail":
               have client_id broadcast "Yabba Daba Dooo"

         end_await
         -> comms_flintstone

   .. code-tab:: py PyMast
      
         # ================ comms_flintstone ==================
         @label()
         def comms_flintstone(self):
            def button_hail(story, comms):
                  comms.broadcast(story.client_id, "Yabba Daba Dooo", "orange")
                  

            yield self.await_comms({
                  "Hail": button_hail
            })
            # -> comms_flintstone
            yield self.jump(self.comms_flintstone)


Create routing logic for rubble's
**********************************************

.. tabs::
   .. code-tab:: mast Mast
         
         ================ comms_rubble ==================
         await comms:
            + "Hail":
               have client_id broadcast "Who ya doing fred?"

         end_await
         -> comms_rubble


   .. code-tab:: py PyMast
      
         # ================ comms_rubble ==================
         @label()
         def comms_rubble(self):
            def button_hail(story, comms):
                  comms.broadcast(story.client_id, "Hey fred .... how you doin fred?", "brown")


            yield self.await_comms({
                  "Hail": button_hail
            })
            # -> comms_flintstone
            yield self.jump(self.comms_rubble)




    





    



