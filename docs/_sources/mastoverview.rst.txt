##################
What is Mast 
##################

Mast is an abbreviation for Multiple Agent Story Telling. It is for writing in a narrative flow that tells a 'story'. The stroy has multiple agents: players, non-player characters, etc. Each of these agents have their own story and those stories can have multiple side plots.

Stories have a forward moving flow. There is a beginning, a middle and an end. Mast has a programming flow that keep the story moving forward. Mast also allows for interactive narrative this allows for choice and branching of the story, revisiting aspects of the story etc. With this it still flows the story on a single path.

Mast in Artemis Cosmos the multiple agents are the player consoles, the ships and various characters that can be on ships, etc. Artemis cosmos has the ability to add much more charatecters to the game. For example there can be multiple chracters on a space stations that you may interact with. The Damage Control teams can have richer stories and each can be unique.

Mast provides and new simple programming language that enables:

* Language that flows more like a narrative or film script
* Easy and rich GUIs for the pause scene and the Artemis Cosmos consoles
* a Task/State Driven system managing multiple tasks in parallel e.g. a quest with side quests
* Behavior tree for complex AI and Dialogs
* I similar to Visual Novel systems e.g. RenPy, Inkle Ink, and Choice script

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


