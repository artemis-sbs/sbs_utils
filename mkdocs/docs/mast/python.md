# {{ab.pm}}

The MAST Runtime is written in python.

{{ab.pm}} is a version where you do not need to write in mast.
You can write in just native python.

The remote_mission_pick mission is written this way.

The MAST language has been the current focus so this part of the runtime is experimental.

Labels are functions, but they still run as a flow and allow jumps and awaitable futures.

It does not use python native await or future since that requires multi-threading.

{{ab.m}} and {{ab.pm}} share common library. In {{ab.pm}} you must import them in order to use them.

Many example do not list the imports. But the example below does.

=== ":mast-icon: {{ab.m}}"
    ```
    # no import needed in mast
    log("Hello, World")
    ```
        
=== ":simple-python: {{ab.pm}}"

    ``` py
    # need to import from library
    from sbs_utils.procedural.execution import log

    @label
    def some_label(self):
        log("Hello, World")
    ```


