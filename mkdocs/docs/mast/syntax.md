# Language Basics

* Data
* Task flow
* Conditional
* Loops 
* Scheduling Tasks


## Data
You can create data that is any valid python type.
This data can be used in your {{ab.m}} tasks.

### Simple assignment

To do so you use the assignment statement::

    fred = 3

Assignment has a variable name an equals followed by a value.

### Using python with assignment


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

### Shared data assignment

Data has multiple scopes. Data can be at the scope of a {{ab.m}} story, a scheduler, a task, or a label.

There are times you want data to be shared by all tasks within a story. To share data you add the 'shared' marked in front of the assignment::

    shared enemy_count = 20
    shared beer_count = 8

When using Data, scope is automatically handled. You only need to specify shared at assignment::

    shared beer_count = 8
    my_beer = 0

    # Drink all the beer
    my_beer = my_beer + beer_count
    share beer_count = 0


## Task Flow: Story sections via labels

A {{ab.m}} story is broken into sections using labels.
You also can have comments, and there are also other 'markers' that can help organizing sections and help have them stand out in the file.

### Labels

Labels have a Name with no spaces and are  enclosed in 2 or more equals

````
    ====== GotoBar ====
     . . .
    == ShowHelm ==
     . . .

    ========================================== MoreStuff ===========================
     . . .
```

There are two labels that are implied: main and END.

The label "main" is the very start of the script.
The label "END" end the current task.

They are predefined and don't need to be defined in script.

Labels are not 'functions', one label passes into the next label

```
    ======== One =====
    log "One"
    ======== Two =====
    log "Two"
    ===== Three ====
    log "Three"
````

Expected output

```
 One
 Two
 Three
```

## State/Flow changes: Jump, Push, Pop

There are times you will want to change what part of a task is running.
This is done by redirecting the flow to a label.

### Jump


This can be done by a Jump command. Which is a 'thin arrow' followed by the label name.::

```
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
```

The expected output

```
First
Got Here later
Done
```

### Push/Pop

Push is kind of the "Hold my Beer" of jump. When you Push it remembers the current location. Pop returns back to that location.

Push is a 'thin double arrow' followed by the label name.

Pop returns back to the previous location. Pop is a backwards thin double arrow.

For example
```
log "See you later"
->> PushHere
log "and we're back"
->END
======== PushHere =====
log "Going back"
<<-
```   

The expected output

```
See you later
Going Back
and we're back
```


### Jump to End

To immediately end a task you can use a Jump to End.

Jump to end looks like a Jump with a thin arrow and the label "END"


=== "mast"
    ```
    ===== start ====

    log("See you later")
    ->END
    log("Never gets here")
    ```

=== "Python"

    ```
    @label()
    def start(self):
        print("See you later")
        yield END()
    ```

=== "Output"
    ```
    See you later
    ```

Jump to End ends the task. If that task the only task, the whole story ends.


## Scheduling tasks and waiting for them to complete

A story can have multiple tasks running in parallel.

For example, a ship maybe have multiple Tasks associated with it. 
One tracking it comms, several for its client consoles, and several related to 'quest' it is involved in.

To do so, new task can be scheduled. Either in python or via Mast.

### Scheduling tasks in mast

Schedule a task is similar to a Jump, but it uses the Fat arrow.
The difference is another task begins, and the original task continues on.

=== "Mast"
    ```
    log("before")
    #
    task_schedule(ATask)
    log("after")

    === ATask ===
    log("in task")
    ```

=== "Python"
    ```    
    @label()
    def start(self):
        logger()
        log("before")
        task_schedule(self.a_task)
        log("after")

    @label()
    def a_task(self):
        log("in task")
    ```

=== "Output"
    ```
    before
    after
    in task
    ```


### passing data to a task

You can pass data to a new task. The data passed is different than the original task.

=== "Mast"
    ```
    message = "Different"
    schedule ATask {"message": "Hello"}
    log "{message}"

    === ATask ===
    log "{message}"
    message = "Who cares"
    ```


=== "Python"
    ```
    @label()
    def start(self):
        self.logger()

        self.schedule_task(self.a_task, {"message": "Hello"})
        self.log(f"{self.task.message}")

    @label()
    def a_task(self):
        self.log(self.task.message)
        self.task.message = "Should not change original"
    ```

=== "Output"
    ```
    different
    Hello
    ```

### Named task and waiting for a Task or Tasks

You can assign a task to a variable by putting a name in front of the fat arrow.

This can be used to await the task later.

Example scheduling a task

=== "Mast"
    ```
    log "Start"
    task1 => ATask
    await task1
    log "Done"

    === ATask ===
    log "task run"
    ```

=== "Output":
    ```
    Start
    task run
    Done
    ```

### Awaiting for any or all tasks


This can be used to await a list of tasks.
You can await for ay task to complete.
And you can await for all tasks to finish.

Example await all

=== "Mast"
    ```
    log("Start")
    task1 = task_schedule(ATask, data= {"say": "Task1"})
    task2 = task_schedule(ATask, data= {"say": "Task2"})
    #### This needs to be refactored
    await join_all(task1,task2]
    log("Done")

    === ATask ===
    log("{say}")
    ```
=== "Output"
    ```
    Start
    Task1
    Task2
    Done
    ```

=== "Mast"
    ```
    log("Start")
    task1 = task_schedule(ATask, data= {"say": "Task1"})
    task2 = task_schedule(ATask, data= {"say": "Task2"})
    #### This needs to be refactored
    await join_any(task1,task2]
    log("Done")

    === ATask ===
    log("{say}")"
    ```

=== "Output"
    ```
    Start
    Task1
    Task2
    Done
    ```

The order maybe be different based on timing of the tasks.

For an await any if any task end, the await is satisfied.


### Canceling a task

You can cancel a tasks by name from another task.

=== "Mast"
    ```
    log("Start")
    task1 task_schedule(ATask)
    task_cancel(task1)
    log("Done")

    === ATask ===
    log("May not run")
    ```

=== "Python"
    ```        
    @label()
    def start(self):
        logger()
        log("Start")
        task1 = task_schedule_task(a_task)
        task_cancel(task1)
        log("Done")

    @label()
    def a_task(self):
        log("May not run")
    ```


=== "Output"

    Start
    Done


## Conditional Statements

{{ab.m}} supports both if and match statements similar to python syntax.
{{ab.pm}} simply uses the python statements.

### If statements

{{ab.m}} supports if statements similar to python with if, elif, and else.
{{ab.m}} is not a whitespace language so you need to close an if with and end_if

If conditionals can be nested as well.

=== "Mast"
    ```
    ===== start ====
    value = 300

    if value < 300:
        log "less"
    elif value > 300:
    log "more"
    else:
        log "equal"
    end_if
    ```

=== "Python"
    ```
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
    ```
    
=== "Output"
    ```
    equal
    ```

### Match statements

{{ab.m}} supports match statements similar to python with match, case.
{{ab.m}} is not a whitespace language so you need to close an if with and end_match

=== "Mast"
    ````
    ===== start ====
    value = 300

    match value:
        case 200:
            log("200")
        case 300:
            log("300")
        case _:
            log*("something else")
    end_match
    ```

=== "Python"
    ```
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
    ```

=== "Output"
    ```
    300
    ```

### For loops

{{ab.m}} supports for loop similar to python with for, break, continue .
{{ab.m}} is not a whitespace language so you need to close an if with and next.

{{ab.pm}} uses the standard python for or while loop.

However, {{ab.m}} support a for ... in loop and a for .. while loop.

=== "Mast"
    ```
    for x in range(3):
        log("{x}")
    next x

    y = 10
    for z while y < 30:
        log("{z} {y}")
        y += 10
    next z

=== "Python"
    ```
    for x in range(3):
        log "{x}"

    y = 10
    z = 0
    while y < 30:
        log "{z} {y}"
        y += 10
        z += 1
    ```


    
=== "Output"
    1
    2
    3
    0 10
    1 20
    2 30




## Comments

Comments provide code extra information to help make it more understandable.

### Comments

Single line comments start with a # and go until the end of the line.

Comments use the # like python does

=== "Mast"
    ```
    fred = 10 # set fred to 10
    ```

### Multi line Comments aka block comments

You can have a c style block comment

=== "Mast"
    ```
    /*********
    Beware
    This is the tricky part
    ****/
    ```

Using block comments to 'disable' code it can quickly get confusing. Therefore, an additional block comment is supported.


## Importing

You can break up mast content into multiple files and use import to included them

=== "Mast"
    ```
    import story_two.mast
    ```

The import command also supports importing from a zip fill

=== "Mast"
    ```
    from my_lib.zip import bar.mast
    ```

One use of the zip file concept it to create a sharable library of things.


## Logging

{{ab.m}} supports syntax to simplify pythons logging features.


### logger command

The logger command sets up logging. 

Logging needs to be enabled

Logging can enabled for stdout, to a string stream (stringIO) variable, and a file


=== "Mast"
    ```
    # enable logging to stdout
    logger()
    # enable logging to stdout, and a string
    logger(var="string my_string_logger")
    # enable logging to stdout, and a file
    logger(file="{mission_dir}/my_log.log")
    # enable logging to stdout, a string and a file
    logger(var="my_string_logger", file="{mission_dir}/my_log.log")
    ```

=== "Python"
    ```
    @label
    def some_label(self):
        # Logging to stdout
        logger()
        # Logging to string IO
        logger(var="my_string_logger")
        # Logging to file
        logger(file="{mission_dir}/my_log.log")
        logger()
    ```        

You can have multiple loggers, each logger can have separate strings, or files.

The default logger does not need to specify the name.

To create a new loggers by using the logger command specifying a name

=== "Mast"
    ```
    logger(name="tonnage")
    logger(name="tonnage", var="tonnage")
    logger(name="tonnage",file="{get_mission_dir()}/tonnage.txt")
    ```

==== "Python"
    ```

    # this import is needed for get_mission_dir
    from sbs_utils.fs import get_mission_dir

    @label
    def some_label(self):
        logger(name="tonnage")
        logger(name="tonnage", var="tonnage")
        logger(name="tonnage",file="{get_mission_dir()}/tonnage.txt")
    ```

### log command

The log command is how you send messages to the log.

=== "Mast"
    ```
    # no logger name defaults to name "mast"
    log("Hello, World")
    # Specify a name to log to a secondary logger
    log("Tonnage score {tonnage}", name="tonnage")
    ```
        
=== "Python"
    ```
    @label
    def some_label(self):
        # no logger name defaults to name "mast"
        log("Hello, World")
        # Specify a name to log to a secondary logger
        log("Tonnage score {tonnage}", name="tonnage")
    ```
            

The log command can accept levels. These are visible is the stdout messages.


=== "Mast"
    ```
    log("Hello, World", level="info")
    log("Hello, World", level= "debug")
    log("Hello, World", level= "error")
    ```

=== "Python"
    ```
    @label
    def some_label(self):

        log("Hello, World", level="info")
        log("Hello, World", level= "debug")
        log("Hello, World", level= "error")
    ```

 

## Delay commands

The delay command continues to execute for a period of time.

A Delay needs a clock to use. Artemis Cosmos has two clocks: gui and sim.
The gui clock is running continuously (realtime). The sim clock can be paused when the simulation is not running (game time).

For gui and other things use the gui clock.
If you want to delay 10s of game time use sim.

Delay can specify minutes and seconds.


=== "Mast"           
    ```
    await delay_app(minutes=1)
    await delay_app(seconds=10)
    await delay_app(seconds=5, minutes=1)
    await delay_sim(0, 10)
    ```

=== "Python"           
    ```
    yield AWAIT(delay_app(minutes=1))
    yield AWAIT(delay_app(seconds=10))
    yield AWAIT(delay_app(seconds=5, minutes=1))
    yield AWAIT(delay_sim(0, 10))
    ```

Delay can delay the flow of the code

=== "Mast"
    ```
    for x in range(3):
        log("{x}")
        await delay_app(1)
    next x
    ```

=== "Python"
    ```
    for x in range(3):
        log("{x}")
        yield AWAIT(delay_app(1))
    next x
    ```

    
=== "Output"
    ```
    1
    2
    3
    ```


