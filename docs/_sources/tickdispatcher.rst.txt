TickDispatcher
===================
Artemis Cosmos runs the python script at a set interval (currently once a second).
This is done via the HandleSimulationTick method.

The TickDispatcher is used to create tasks that are called when the HandleSimulationTick is called.
The function should be called in TickDispatcher.dispatch_tick(), and ideally this is the only code that is needed.


.. code-block:: python

     def  HandleSimulationTick(sim):
        TickDispatcher.dispatch_tick(sim)


One could implement their own way of handling time and tick related code, the goal of the TickDispatcher is to have a common way to organize this logic.

A TickTask is similar to Artemis XML's timer events and are ideally more efficient since they only live while they are relevant.

To create a TickTask you can use one of two functions.

* :py:meth:`~sbs_utils.tickdispatcher.TickDispatcher.do_once`
* :py:meth:`~sbs_utils.tickdispatcher.TickDispatcher.do_interval`

:py:meth:`~sbs_utils.tickdispatcher.TickDispatcher.do_once` will schedule a task that is run only one time.

:py:meth:`~sbs_utils.tickdispatcher.TickDispatcher.do_interval` will schedule to run multiple times or continuously.

Both methods take the simulation used to track the start time, a callback function, a a delay time. do_interval additionally optionally takes the number of times it should run. The default is None, which is meant to indicate run continuously.

The callback functions will receive the simulation and the task as arguments. Class methods used as a callback will receive 'self' as the first argument.

Example: run a function once
---------------------------------
The following fill run the function after 5 seconds.

.. code-block:: python

      from sbs_utils.tickdispatcher import TickDispatcher

      def call_me_later(sim, task):
         print('Hello, Tick Tasks')
      
      # Some other place
      TickDispatcher.do_once(sim, call_me_later, 5)   


The following fill run a class method on an object after 5 seconds.

.. code-block:: python

      from sbs_utils.tickdispatcher import TickDispatcher

      class MyPlayer(PlayerShip):
         def call_me_later(self, sim, task):
            print('Hello, Tick Tasks')
      
      # Some other place
      player_one = MyPlayer()
      TickDispatcher.do_once(sim, player_one.call_me_later, 5)   


The following fill run a class method on an object after 5 seconds.
This one show using self.

.. code-block:: python
   
      from sbs_utils.tickdispatcher import TickDispatcher

      class MyPlayer(PlayerShip):
         def call_me_later(self, sim, task):
            print('Hello, Tick Tasks')

         def some_other_method(self):      
            TickDispatcher.do_once(sim, self.call_me_later, 5)   

Example: run a function multiple times
--------------------------------------
The following fill run the function every 5 seconds, 4 times

.. code-block:: python

      from sbs_utils.tickdispatcher import TickDispatcher

      def call_me_later(sim, task):
         print('Hello, Tick Tasks')
      
      # Some other place
      TickDispatcher.do_interval(sim, call_me_later, 5, 4)   

The following fill run a class method on an object after 5 seconds four times.
This one show using self.

.. code-block:: python
   
      from sbs_utils.tickdispatcher import TickDispatcher

      class MyPlayer(PlayerShip):
         def call_me_later(self, sim, task):
            print('Hello, Tick Tasks')

         def some_other_method(self):      
            TickDispatcher.do_interval(sim, self.call_me_later, 5,4)   

Example: run continuously
-------------------------
The following fill run the function every tick. This can be done with classes as well, those examples will be similar to above.

.. code-block:: python

      from sbs_utils.tickdispatcher import TickDispatcher

      def call_me_later(sim, task):
         print('Hello, Tick Tasks')
      
      # Some other place
      TickDispatcher.do_interval(sim, call_me_later, 0)   

Example: Stopping a task
-------------------------
The following fill run as task and stop it when a condition is met.

.. code-block:: python
   
      from sbs_utils.tickdispatcher import TickDispatcher

      class MyPlayer(PlayerShip):
         def call_me_later(self, sim, task):
            print('Hello, Tick Tasks')
            if some_thing_that_stops_it:
               task.stop()

         def some_other_method(self):      
            TickDispatcher.do_interval(sim, self.call_me_later, 5)   

Example: passing data
-------------------------
The following fill run will pass data to the callback.

.. code-block:: python

      from sbs_utils.tickdispatcher import TickDispatcher

      def call_me_later(sim, task):
         print('Hello, Tick Tasks')
         # use the data attached to the task
         print(task.data)
      
      # Some other place
      thetask = TickDispatcher.do_interval(sim, call_me_later, 0)
      # attach data to the task
      thetask.data = 42

For completeness so using the object 'self' data

.. code-block:: python
   
      from sbs_utils.tickdispatcher import TickDispatcher

      class MyPlayer(PlayerShip):
         data = 42
         def call_me_later(self, sim, task):
            print('Hello, Tick Tasks')
            print(self.data)

         def some_other_method(self):      
            TickDispatcher.do_interval(sim, self.call_me_later, 5)   



API: tickdispatcher module
--------------------------------

.. automodule:: sbs_utils.tickdispatcher
   :members:
   :undoc-members:
   :show-inheritance:

