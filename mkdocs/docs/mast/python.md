# {{ab.pm}}

The MAST Runtime is written in python.

{{ab.pm}} is a version where you do not need to write in mast.
You can write in just native python.

The remote_mission_pick mission is written this way.

The MAST language has been the current focus so this part of the runtime is experimental.

Labels are functions, but they still run as a flow and allow jumps and awaitable futures.

It does not use python native await or future since that requires multi-threading.



