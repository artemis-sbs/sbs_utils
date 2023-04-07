##################
What is Mast 
##################

Mast is an abbreviation for Multiple Agent Story Telling. It is for writing in a narrative flow that tells a 'story'. The stroy has multiple agents: players, non-player characters, etc. Each of these agents have their own story and those stories can have multiple side plots.

Stories have a forward moving flow. There is a begining, a middle and an end. Mast has a programming flow that keep the story moving forward. Mast also allows for interactive narrative this allows for choice and branching of the story, revisiting aspects of the story etc. With this it still flows the story on a single path.

Mast in Artemis Cosmos the multiple agents are the player consoles, the ships and various characters that can be on ships, etc. Artemis cosmos has the ability to add much more charatecters to the game. For example there can be multiple chracters on a space stations that you may interact with. The Damage Control teams can have richer stories and each can be unique.

*********************
Mast execution flow 
*********************

The goal of Mast is to enable non-programmers to be productive in creating interactive narratives.

The Mast language is a programming language that strips many of the programming language concepts that make writing interactive narratives difficult as well a simplified syntax.

The intent is to be approachable to non-programmers. It is not intended to be 'structured' programming language like C++ or Python. 

The flow of mast is similar to the original BASIC programming langauge. The code executes moving forward, it can branch by jumping to new locations (labels). This can be called 'unstructured' programming. Mast was also influenced by choice script, Inkle's Ink, and others.

.. code-block:: mast

    ========= start =======
    log "Hello, world"
    -> goodbye
    ====== not_here =======
    log "I get jumped over"
    ======= goodbye =======
    log "Goodbye"

This is the expected output::

    Hello, world
    Goodbye


****************
Mast and PyMast
****************

Mast is a standalone language running inside of the python system provided by Artemis Cosmos.

PyMast is python code that runs using the Mast execution flow. This gives python programmers the benefits of Mast's simple flow while enabling greater access to the native python.


.. tabs::
   .. code-tab:: mast
      
        ========= start =======
        log "Hello, world"
        -> goodbye
        ====== not_here =======
        log "I get jumped over"
        ======= goodbye =======
        log "Goodbye"


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                print("Hello, world")
                yield self.jump(self.goodbye)

            @label()
            def not_here(self):
                print("I get jumped over")

            @label()
            def goodbye(self):
                print("Goodbye")

This is the expected output::

    Hello, world
    Goodbye
     

***************************
Mast and pausing the flow
***************************

Mast is running as part of a game engine. The engine only give Mast a small amount of time to run. If Mast ran unconditionally it would not allow the engine to run and stall the game. However, there are times a story cannot continue until conditions are met. e.g. A comms button is press, a science scan it started etc.

Mast can "pause" execution and yield control back to the engine. The engine keeps calling MAst and it yields until the condition is met teh the flow can continue.

This example prints "Hello, world" and five seconds later it prints "Goodbye". During that five seonds the engine is able to run because Mast yields control back since it cannot move forward.

This ability to yield control back to the engine is a reason that Mast flow can be enable users to focus on the flow of the story and not how to get the programming lanuage to deal with this.


.. tabs::
   .. code-tab:: mast
      
        ========= start =======
        log "Hello, world"
        delay gui 5s
        log "Goodbye"


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                print("Hello, world")
                yield self.delay(5)
                print("Goodbye")


Yielding control is handled by Mast. If there ever is a time you need to force a yield you can us the Mast 'yeild' command. In PyMast the python keyword yield is used, however you must specify how to yield by providing a PollResults.OK_RUN_AGAIN. There are other types of yields in PyMast. This is not the time to detail those uses. 


.. tabs::
   .. code-tab:: mast
      
        ========= start =======
        log "Hello, world"
        yield
        log "Goodbye"


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                print("Hello, world")
                yield PollResults.OK_RUN_AGAIN
                print("Goodbye")


In future topics there will be other times descibed when Mast yields. Typically this is when MAst is waiting for something to occur. For example:

* time (e.g. the delay used in the examples)
* awaiting a choice to be made in the gui 
* awaiting a comms button to be selected
* awaiting a science scan 

*******************************
Sub plots aka Tasks
*******************************

Mast is MULTI Agent Story Telling so each agent has their own story or event stories.

Mast allows multiple storylines to run in "parallel". 

Mast in Artemis Cosmos is inherently a single thread of execution. These storylines do not run exactly in parallel, but you can run multiple things and make sure they run. These are called Tasks, and tasks can be scheduled so that multiple task can run.

For example a Player Ship can run a Task for handling Comms messages, another for Science scan. This player ship could in fact run multiple tasks for handling comms with different sets of ships.

These tasks themselves act as small side stories, They run as long as needed.

In mast tasks are scheduled in mast with a parallel jump, and in PyMast with a schedule_task

.. tabs::
   .. code-tab:: mast
      
        ===== start ====
        # Run another task
        => count_to_ten
        delay gui 15s
        log "done"

        ===== count_to_ten ======
        for x in range(10):
            log "{x}"
            yield
        next x


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                self.schedule_task(self.count_to_ten)
                yield self.delay(15)

            @label()
            def count_to_ten(self):
                for x in range(10):
                    print(x)
                    yield PollResults.OK_RUN_AGAIN

Expected output::

    1
    2
    3
    4
    5
    6
    7
    8
    9
    10
    done

******************
Schedulers
******************

Mast and PyMast run all the tasks using schedulers. This process is mostly hidden to the writer of Mast and PyMast code.

Tasks are run on 'Schedulers' and to put it simply for now, the server and each Console has a scheduler. Additional scheduler can be created but typically the schedulers run associated with a console with the server running a large number of the tasks.

For example, the server runs a scheduler it may have a task for presenting its User Interface/GUI, and maybe have other task to manage the world creation, handing comms, science etc. Consoles typically have a scheduler an mostly as single task for the User Interface/GUI.

The more complex the script, the more tasks that will run. And if the complexity warrants more schedulers can be created. e.g. schedulers for each player ships etc.

When Artemis Cosmos calls the scripting engine, Mast/PyMast will run al the Schedulers and each scheduler runs all of its Tasks. 

As tasks are finished, they are removed. If a scheduler runs and no longer has tasks it is removed.



****************************
Mast Object Model
****************************

Mast needs participants in the story. In stories Artemis Cosmos these participants are:

* The Story itself (aka the server, the game, the engine or the world)
* Bridge Crew (The player consoles)
* The Player ships (Ships control by the Bridge Crew)
* Non-Player ships Starbases, Enemy Ships, Friendly Ships (Things controled by script)
* The terrain element asteroids, pickups, nebula etc.
* Non-Player Crew and Characters (Seen as faces in engineering, Comms etc.)
* Internals ship location (Rooms and other things)

These agents/participants are the things in the Artemis Cosmos world. Each of this agents can have stories and tasks associated with them. 








***************
Basic Language
***************

- Data
- Task flow
- Conditional
- Loops 
- Scheduling Tasks




Data
========
You can create data that is any valid python type.
This data can be used in you mast tasks.

Simple assignment
--------------------

To do so you use the assignment statement::

    fred = 3

Assignment has a variable name an equals followed by a value.

Using python with assignment
-----------------------------

The assignment is simple and has trouble with more complex python statements e.g. a list of list, etc.
To allow more complex assignments you can wrap the value in 'snakes' to have the python compiler used::

    players_inventory = ~~ [ [2,3], [4,5]] ~~

You need at least 2 'snakes' (the tilde character), before and after the python values. But you can have more tha two, and the number doesn't need to be exactly the same, as long as you have at least two::

    players_inventory = 
        ~~~~~~~~~ 
        [
            [2,3], 
            [4,5]
        ] 
        ~~~~~~

Shared data assignment
-----------------------
Data has multiple scopes. Data can be at the scope of a Mast story, For a scheduler, A task, and block

There are times you want data to be shared by all tasks within a story. To share data you add the 'shared' marked in front of the assignment::

    shared enemy_count = 20
    shared beer_count = 8

When using Data, scope is automatically handled you only need to specify shared at assignment::

    shared beer_count = 8
    my_beer = 0

    # Drink all the beer
    my_beer = my_beer + beer_count
    share beer_count = 0


Task Flow: Story sections via labels
=====================================

A mast story is broken into sections using labels.
You also can have comments, and there are also other 'markers' that can help organizing sections and help have them stand out in the file.

Labels
---------

Labels have a Name with no spaces and are  enclosed in 2 or more equals::

    ====== GotoBar ====
     . . .
    == ShowHelm ==
     . . .

    ========================================== MoreStuff ===========================
     . . .

There are two labels that are implied: main and END.

The label "main" is the very start of the script.
The label "END" end the current task.

They are predefined and don't need to be defined in script.

Labels are not 'functions', one label passes into the next label::

    ======== One =====
    log "One"
    ======== Two =====
    log "Two"
    ===== Three ====
    log "Three"

Expected output::

 One
 Two
 Three

State/Flow changes: Jump, Push, Pop
=====================================

There are times you will want to change what part of a task is running.
This is done by redirecting the flow to a label.

Jump
----------

This can be done by a Jump command. Which is a 'thin arrow' followed by the label name.::

    -> Here

    ======== NotHere =====
    log "Got here later"
    -> End

    ======== Here =====
    log "First"
    -> NotHere

    ======== End =====
    log "Done"
    ->END
    ======== Never =====
    log "Can never reach"

The expected output::

    First
    Got Here later
    Done

Push/Pop
----------
Push is kind of the "Hold my Beer" of jump. When you Push it remembers the current location. Pop returns back to that location.

Push is a 'thin double arrow' followed by the label name.

Pop returns back to the previous location. Pop is a backwards thin double arrow.

For example::

    log "See you later"
    ->> PushHere
    log "and we're back"
    ->END
    ======== PushHere =====
    log "Going back"
    <<-
    
The expected output::

    See you later
    Going Back
    and we're back



Jump to End
-------------
To immediately end a task you can use a Jump to End.

Jump to end looks like a Jump with a thin arrow and the label "END"


.. tabs::
   .. code-tab:: mast

        ===== start ====
        log "See you later"
        ->END
        log "Never gets here"


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                print("See you later")
                yield PollResults.OK_END

The expected output::

    See you later

Jump to End ends the task. If that task the only task, the whole story ends.


Scheduling tasks and waiting for them to complete
==================================================
A story can have multiple tasks running in parallel.

For example, a ship maybe have multiple Tasks associated with it. 
One tracking it comms, several for its client consoles, and several related to 'quest' it is involved in.

To do so, new task can be scheduled. Either in python or via Mast.

Scheduling tasks in mast
--------------------------

Schedule a task is similar to a Jump, but it uses the Fat arrow.
The difference is another task begins, and the original task continues on.

Example scheduling a task::

    log "before"
    => ATask
    log "after"

    === ATask ===
    log "in task"

Expected output::
    
    before
    after
    in task


passing data to a task
------------------------

You can pass data to a new task. The data passed is different than the original task.

Example scheduling a task::

    message = "Different"
    => ATask {"message": "Hello"}
    log "{message}"

    === ATask ===
    log "{message}"
    message = "Who cares"

Expected output::

    different
    Hello

Named task and waiting for a Task or Tasks
------------------------------------------------

You can assign a task to a variable by putting a name in front of the fat arrow.

This can be used to await the task later.

Example scheduling a task::

    log "Start"
    task1 => ATask
    await task1
    log "Done"

    === ATask ===
    log "task run"

Expected output::

 Start
 task run
 Done


Awaiting for any or all tasks
------------------------------------------------

This can be used to await a list of tasks.
You can await for ay task to complete.
And you can await for all tasks to finish.

Example await all::

    log "Start"
    task1 => ATask {"say": "Task1"}
    task2 => ATask {"say": "Task2"}
    await all [task1,task2]
    log "Done"

    === ATask ===
    log "{say}"

Expected output::

 Start
 Task1
 Task2
 Done

Example await any::

    log "Start"
    task1 => ATask {"say": "Task1"}
    task2 => ATask {"say": "Task2"}
    await any [task1,task2]
    log "Done"

    === ATask ===
    log "{say}"

Expected output::

 Start
 Task1
 Task2
 Done


The order maybe be different based on timing of the tasks.

For an await any if any task end, the await is satisfied.


Canceling a task
-------------------

You can cancel a tasks by name from another task.

Example cancel::

    log "Start"
    task1 => ATask
    cancel task1
    log "Done"

    === ATask ===
    log "May not run"

Expected output::

 Start
 Done


Conditional Statements
=========================

Mast supports both a if and match statements similar to python's.
PyMast simply uses the python statements.

If statements
----------------

Mast supports if statements similar to python with if, elif, and else.
Mast is not a whitespace language so you need to close an if with and end_if

If conditionals can be nested as well.

.. tabs::
   .. code-tab:: mast
      
        ===== start ====
        value = 300

        if value < 300:
            log "less"
        elif value > 300:
        log "more"
        else:
            log "equal"
        end_if


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                value = 300
                if value < 300:
                    log "less"
                elif value > 300:
                    log "more"
                else:
                    log "equal"
                
    
Expected output::

    equal


Match statements
----------------

Mast supports match statements similar to python with match, case.
Mast is not a whitespace language so you need to close an if with and end_match

.. tabs::
   .. code-tab:: mast
      
        ===== start ====
        value = 300

        match value:
            case 200:
                log "200"
            case 300:
                log "300"
            case _:
                log "something else"
        end_match


   .. code-tab:: py PyMast

        class Story(PyMastStory):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
            @label()
            def start(self):
                value = 300
                match value:
                    case 200:
                        log "200"
                    case 300:
                        log "300"
                    case _:
                        log "something else"


Expected output::
    
    300


For loops
----------------

Mast supports for loop similar to python with for, break, continue .
Mast is not a whitespace language so you need to close an if with and next.

PyMast uses the standard python for or while loop.

However, mast support a for ... in loop and a for .. while loop.

.. tabs::
    .. code-tab:: mast

        for x in range(3):
            log "{x}"
        next x

        y = 10
        for z while y < 30:
            log "{z} {y}"
            y += 10
        next z

    .. code-tab:: py PyMast

        for x in range(3):
            log "{x}"

        y = 10
        z = 0
        while y < 30:
            log "{z} {y}"
            y += 10
            z += 1


    
Expected output::

 1
 2
 3
 0 10
 1 20
 2 30




Comments and Markers
======================

Comments provide code extra information to help make it more understandable.

Mast provides comments, Multi-line comments and markers to help make the code easier to understand and navigate.

Comments
----------------------------
Single line comments start with a # and go until the end of the line.

Comments use the # like python does::

    fred = 10 # set fred to 10

Multi line Comments aka block comments
----------------------------------------

You can have a c style block comment::

    /*********
    Beware
    This is the tricky part
    ****/


Using block comments to 'disable' code it can quickly get confusing. Therefore, an additional block comment is supported.


Importing
==================

You can break up mast content into multiple files and use import to included them::

    import story_two.mast

The import command also supports importing from a zip fill::

    from my_lib.zip import bar.mast

One use of the zip file concept it to create a sharable library of things.


Logging
================

Mast supports syntax to simplify pythons logging features.

The logger command sets up logging. 

Logging needs to be enabled

Logging can enabled for stdout, to a string stream (stringIO) variable, and a file::

    # enable logging to stdout
    logger
    # enable logging to stdout, and a string
    logger string my_string_logger
    # enable logging to stdout, and a file
    logger file "{mission_dir}/my_log.log"
    # enable logging to stdout, a string and a file
    logger string my_string_logger file "{mission_dir}/my_log.log"

You can have multiple loggers, each logger can have separate strings, or files.

The default logger does not need to specify the name.

To create a new loggers by using the logger command specifying a name::

    logger name tonnage string tonnage

The log command is how you send messages to the log::

    log "Hello, World"
    log name tonnage "Tonnage score {tonnage}"

The log command can accept levels::

    log "Hello, World" info
    log "Hello, World" debug
    log "Hello, World" error

These are visible is the stdout messages.


Delay command
==================

The delay command continues to execute for a period of time.

A Delay needs a clock to use Artemis Cosmos has two clocks and sim.
The gui clock is running continuously (realtime), the sim clock can be paused when the simulation is not running(game time).

For gui and other things use the gui clock.
If you want to delay 10s of game time use sim.

Delay can specify minutes and seconds. Some examples::

    delay gui 1m
    delay gui 10s
    delay gui 1m 5s
    delay sim 10m

.. tabs::
    .. code-tab:: mast

        for x in range(3):
            log "{x}"
            delay gui 1s
        next x

    .. code-tab:: py PyMast

        for x in range(3):
            log "{x}"
            yield self.delay(5)

    
Expected output::

 1
 2
 3



