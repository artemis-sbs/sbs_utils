# TickDispatcher

Artemis Cosmos runs the python script at a set interval (currently once a second).
This is done via the HandleSimulationTick method.

## Usage

The TickDispatcher is used to create tasks that are called when the HandleSimulationTick is called.
The function :py:meth:`~sbs_utils.tickdispatcher.TickDispatcher.dispatch_tick` should be called in HandleSimulationTick, and ideally this is the only code that is needed.


=== "Python"
   ``` py
      def  HandleSimulationTick(sim):
         TickDispatcher.dispatch_tick(sim)
   ```

Importing the hookhandlers module it does by default.

=== "Python"
   ``` py

      from sbs_utils.handlerhooks import *
      # no longer need to implement handlers in script.py
   ```


One could implement their own way of handling time and tick related code, the goal of the TickDispatcher is to have a common way to organize this logic.

A TickTask is similar to Artemis XML's timer events and are ideally more efficient since they only live while they are relevant.

To create a TickTask you can use one of two functions.

* ![Do Once](sbs_utils.tickdispatcher.TickDispatcher.do_once)
* ![Do Once](sbs_utils.tickdispatcher.TickDispatcher.do_interval)

![Do Once](sbs_utils.tickdispatcher.TickDispatcher.do_once) will schedule a task that is run only one time.

![Do interval](sbs_utils.tickdispatcher.TickDispatcher.do_interval) will schedule to run multiple times or continuously.

Both methods take the simulation used to track the start time, a callback function, a delay time. do_interval additionally optionally takes the number of times it should run. The default is None, which is meant to indicate run continuously.

The callback functions will receive the simulation and the task as arguments. Class methods used as a callback will receive 'self' as the first argument.

## Example: run a function once

The following will run the function after 5 seconds.

=== "Python"
   ```
   from sbs_utils.tickdispatcher import TickDispatcher

   def call_me_later(sim, task):
      print('Hello, Tick Tasks')
   
   # Some other place
   TickDispatcher.do_once(sim, call_me_later, 5)   
   ```

The following will run a class method on an object after 5 seconds.

=== "Python"
   ```
   from sbs_utils.tickdispatcher import TickDispatcher

   class MyPlayer(PlayerShip):
      def call_me_later(self, sim, task):
         print('Hello, Tick Tasks')
   
   # Some other place
   player_one = MyPlayer()
   TickDispatcher.do_once(sim, player_one.call_me_later, 5)   
   ```

The following will run a class method on an object after 5 seconds.
This one show using self.

=== "Python"
   ```

   from sbs_utils.tickdispatcher import TickDispatcher

   class MyPlayer(PlayerShip):
      def call_me_later(self, sim, task):
         print('Hello, Tick Tasks')

      def some_other_method(self):      
         TickDispatcher.do_once(sim, self.call_me_later, 5)   
   ```

## Example: run a function multiple times

The following will run the function every 5 seconds, 4 times

=== "Python"
   ```

   from sbs_utils.tickdispatcher import TickDispatcher

   def call_me_later(sim, task):
      print('Hello, Tick Tasks')
   
   # Some other place
   TickDispatcher.do_interval(sim, call_me_later, 5, 4)   
   ```

The following will run a class method on an object after 5 seconds four times.
This one show using self.

=== "Python"
   ```
   from sbs_utils.tickdispatcher import TickDispatcher

   class MyPlayer(PlayerShip):
      def call_me_later(self, sim, task):
         print('Hello, Tick Tasks')

      def some_other_method(self):      
         TickDispatcher.do_interval(sim, self.call_me_later, 5,4)   
   ```

## Example: run continuously

The following will run the function every tick. This can be done with classes as well, those examples will be similar to above.

=== "Python"
   ```
   from sbs_utils.tickdispatcher import TickDispatcher

   def call_me_later(sim, task):
      print('Hello, Tick Tasks')
   
   # Some other place
   TickDispatcher.do_interval(sim, call_me_later, 0)   
   ```
## Example: Stopping a task

The following will run as task and stop it when a condition is met.

=== "Python"
   ```
   from sbs_utils.tickdispatcher import TickDispatcher

   class MyPlayer(PlayerShip):
      def call_me_later(self, sim, task):
         print('Hello, Tick Tasks')
         if some_thing_that_stops_it:
            task.stop()

      def some_other_method(self):      
         TickDispatcher.do_interval(sim, self.call_me_later, 5)   
   ```

## Example: passing data

The following will run will pass data to the callback.


=== "Python"
   ```

   from sbs_utils.tickdispatcher import TickDispatcher

   def call_me_later(sim, task):
      print('Hello, Tick Tasks')
      # use the data attached to the task
      print(task.data)
   
   # Some other place
   thetask = TickDispatcher.do_interval(sim, call_me_later, 0)
   # attach data to the task
   thetask.data = 42
   ```

For completeness: using the object 'self' data

=== "Python"
   ```

   from sbs_utils.tickdispatcher import TickDispatcher

   class MyPlayer(PlayerShip):
      data = 42
      def call_me_later(self, sim, task):
         print('Hello, Tick Tasks')
         print(self.data)

      def some_other_method(self):      
         TickDispatcher.do_interval(sim, self.call_me_later, 5)   
   ```


# API: tickdispatcher module

::: sbs_utils.tickdispatcher
 
