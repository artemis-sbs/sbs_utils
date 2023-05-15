Tutorial: Simple AI
############################



Create mission 
======================

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
      

Add a router for ai
*************************


Routers create tasks automatically a needed and starts running at a specific label.
That label that uses logic to route to other labels based on certain conditions.


.. tabs::
   .. code-tab:: mast Mast

         # at the top of the mast file add 
         # Configure the label where comms routing occurs
         route spawn route_ai

   .. code-tab:: py PyMast

       # in the __init__ of the story add 
       self.route_spawn(self.route_ai)
    




Add a task to route AI
========================


.. tabs::
   .. code-tab:: mast mast
     
      ========== route_ai =========
      #
      # SPAWNED_ID is a special value of the ID of the thing spawned
      #
      if has_role(SPAWNED_ID, "raider"):
         jump npc_targeting_ai
      end_if
      #if not a raider end the task
      ->END




   .. code-tab:: py PyMast

      @label()    
      def route_ai(self):
         #
         # SPAWNED_ID is a special value of the ID of the thing spawned
         #
         if query.has_role(self.task.SPAWNED_ID, "raider"):
               yield self.jump(self.npc_targeting_ai)
         



Add a task to do np targeting AI
===================================


.. tabs::
   .. code-tab:: mast mast
 
      =====  npc_targeting_ai   =========

      the_target = closest(SPAWNED_ID, role("__PLAYER__"), 2000)
      if the_target is None:
         the_target = closest(SPAWNED_ID, role("Station"))
      end_if
      if the_target is not None:
         do target(sim, SPAWNED_ID, the_target, True)
      end_if

      delay sim 5s
      jump npc_targeting_ai



   .. code-tab:: py PyMast
   

      @label()    
      def npc_targeting_ai(self):
         the_target = query.closest(self.task.SPAWNED_ID, query.role("__PLAYER__"), 2000)
         if the_target is None:
               the_target = query.closest(self.task.SPAWNED_ID, query.role("Station"))
         if the_target is not None:
               query.target(self.sim, self.task.SPAWNED_ID, the_target, True)

         yield self.delay(5)
         yield self.jump(self.npc_targeting_ai)




