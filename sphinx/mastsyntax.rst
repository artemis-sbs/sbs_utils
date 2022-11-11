##################
Language Basics
##################

Mast is an abbreviation for Multiple Actor/Audience Story Telling. So, it is for writing Multiplayer choose your own adventure types of stories.

Mast is a interpreted scripting Language for adding interactivity, narrative, quest etc.

The  Mast technology can be used in many various systems. What may be different is the actors, tasks and events that are in the system.

Mast in Artemis Cosmos the multiple actors are the players, the ships and various characters that can be on ships, etc.

Task and events that are specific  for Artemis Cosmos are things like ship comms, targeting, the startup screen, client console screens.


*****************************
Language high level concepts
*****************************
This section will present terms of how Mast works and how mast code is organized.

- story aka mast
- data
- tasks
- scheduler
- labels and states

The language itself is for describing a mast Story. A story consists of a sets of data, Tasks and events.

Data is values and can be things like Ship, Characters, Inventories of objects etc.

A Tasks a set of steps or states that run.

A Task is scheduled (using a scheduler)

A scheduler manages the running of multiple Tasks. Typically the scheduler is sort of the wizard behind the curtain.

Tasks can be organized into sections called labels.

Labels also are points that the task can transition to i.e. within a task you can jump around from one label to another.

Therefore, a Label can represent changing a Task from one state, to another.


Typically, a task runs sequentially but not necessarily synchronously. It stays on a line of code, until that line is completed.
So it can stay on the same line of code for quite some time. e.g. telling it to wait until a ship is near another ship::

    await tsn01 near ds91 700 timeout 4m:
        -> ReachedStation
    timeout:
        -> DidNotReachInTime
    end_await

The example, waits for the event when the ships tsn01 is 700 away from ds91.
If it gets there within 4 minutes, it jumps to the label ReachedStation changing to that state.
If it doesn't reach it in time, it changes to the state DidNotReachInTime.

It is import to understand, while it is waiting on the line of code it is not preventing the game or other tasks from running.

Synchronous vs. Asynchronous programming can be highly complicated. Mast tries to simplify this greatly.


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

    ======== PushHere =====
    log "Going back"
    <<-
    
The expected output::

    See you later
    Going Back
    and we're back


Pop n' Jump
-------------

There are some admittedly rare occasions where you do not want to return to the pop location.
The push need to be cleared before you can jump to a different location.

The Pop and Jump allows this odd case.

Pop and Jump returns back to the previous location then immediately jumps to another location.
Pop and jump is a backwards thin double arrow, a name and the two more arrow heads.

It may seem odd, but the Pop needs to occur. Otherwise its is waisting memory remembering the push location.

For example::

    log "See you later"
    ->> PushHere
    log "and we're back"

    ======== PushHere =====
    log "Going places!"
    <<-NewPlace<<

    ======== HereInstead =====
    log "New place"

The expected output::

    See you later
    Going places!
    New place

Jump to End
-------------
To immediately end a task you can use a Jump to End.

Jump to end looks like a Jump with a thin arrow and the label "END"::

For example::

    log "See you later"
    ->END
    log "Never gets here"

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

If statements
----------------

Mast supports if statements similar to python with if, elif, and else.
Mast is not a whitespace language so you need to close an if with and end_if

If conditionals can be nested as well.

Example if::

    value = 300

    if value < 300:
        log "less"
    elif value > 300:
       log "more"
    else:
        log "equal"
    end_if

Expected output::

    equal


Match statements
----------------

Mast supports match statements similar to python with match, case.
Mast is not a whitespace language so you need to close an if with and end_match

Example match::

    value = 300

    match value:
        case 200:
            log "200"
        case 300:
            log "300"
        case _:
            log "something else"
    end_match

Expected output::
    
    300


For loops
----------------

Mast supports for loop similar to python with for, break, continue .
Mast is not a whitespace language so you need to close an if with and next.

However, mast support a for ... in loop and a for .. while loop.

Example for::

    for x in range(3):
        log "{x}"
    next x

    y = 10
    for z while y < 30:
        log "{z} {y}"
        y = y + 10
    next z
    
    
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


Named block comments
----------------------

You can have a named block comment enclosing the name in using 3 or more !.
You must explicitly end the comment with the name as well::

    !!!! skipthis !!!!!!!!!
    beer = 0
    vodka = 0
    !!!! end skipthis !!!!!

This allows for nested block comments as well::

    !!!! skipthis !!!!!!!!!
    beer = 0
    vodka = 0
    !!!! skipthistoo !!!!!!!!!
    wine = 0
    !!!! end skipthistoo !!!!!
    something = 12
    !!!! end skipthis !!!!!


Markers
---------

Markers are repeating characters used to imply make text stand out as you scroll.
Marker are simply removed when they are seen.
The markers are any time you have 3 or of the same marker character.
Marker characters are dash(-), plus(+) or asterisk(*)

    **********if beer == 0*************
        vodka = 0
    *********end_if ************

Again they are simply to make some code to stand out and ideal help scanning code.
You don't need to use them.


Delay,

Import,

Logging
================

 logger name test1 file "{mission_dir}/test1.out"

